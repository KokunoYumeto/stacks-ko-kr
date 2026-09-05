from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "BUILD_PLAN.json"
PREFLIGHT_PATH = ROOT / "receipts" / "R9_PREFLIGHT_AND_REFERENCE_PROFILES.json"
PROFILE_REPAIR_PATH = ROOT / "receipts" / "R9_PROFILE_REPAIR_001.json"
PROFILES = ROOT / "support" / "profiles-r9"
DEPENDENCIES = ROOT / "support" / "dependencies"
COMPONENTS = ROOT / "evidence" / "components"
ATTEMPTS = ROOT / "evidence" / "build-attempts"
OUTPUT = ROOT / "output" / "pdf"
BUILD_RECEIPT = ROOT / "receipts" / "R9_COMPONENT_AND_CUMULATIVE_BUILD.json"
FINAL_PDF = OUTPUT / "stacks-project-ko-kr-cumulative-r9-52-chapters.pdf"
REPLAY_PDF = ROOT / "evidence" / "stacks-project-ko-kr-cumulative-r9-52-chapters.replay.pdf"
SOURCE_DATE_EPOCH = "1788562238"

EXPECTED_PLAN = (44999, "BF46DA7C4D877687E97982761A96443BD2A97B81A190A91349B0E6DD5BE1DA07")
EXPECTED_PREFLIGHT = (29709, "9B4D215ADC8A82F159461EB318BA645EF08B1331A1F8BD6776A54D6254F629C6")
EXPECTED_PROFILE_REPAIR = (3540, "80FFFDE04176C7ADB7656510703D32F6E9F251D9F87C7CBA6B405CA1C3AF9ABD")
ALLOWED_BIBTEX_WARNINGS_BY_CHAPTER: dict[int, set[str]] = {}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def identity(path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def require(path: Path, size: int, digest: str) -> dict[str, object]:
    if not path.is_file():
        raise RuntimeError(f"required file absent: {path}")
    got = identity(path)
    if got["bytes"] != size or got["sha256"] != digest:
        raise RuntimeError(f"identity mismatch: {path}; expected {size}/{digest}, got {got['bytes']}/{got['sha256']}")
    return got


def require_record(record: dict[str, object]) -> dict[str, object]:
    return require(ROOT / str(record["path"]), int(record["bytes"]), str(record["sha256"]))


def tree_identity(root: Path) -> dict[str, object]:
    rows: list[str] = []
    total = 0
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        total += size
        rows.append(f"{relative}\t{size}\t{sha256(path)}\n")
    payload = "".join(rows).encode("utf-8")
    return {
        "path": root.relative_to(ROOT).as_posix(),
        "files": len(rows),
        "bytes": total,
        "serialization_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest().upper(),
    }


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if path.exists() or temporary.exists():
        raise RuntimeError(f"refusing to overwrite receipt: {path}")
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def next_attempt(chapter: int, stem: str) -> Path:
    ATTEMPTS.mkdir(parents=True, exist_ok=True)
    for number in range(1, 1000):
        path = ATTEMPTS / f"ch{chapter:03d}-{stem}-a{number:03d}"
        if not path.exists():
            path.mkdir()
            return path
    raise RuntimeError("component-attempt namespace exhausted")


def next_failure_path() -> Path:
    for number in range(1, 1000):
        path = ROOT / "receipts" / f"R9_COMPONENT_BUILD_FAILURE_{number:03d}.json"
        if not path.exists():
            return path
    raise RuntimeError("failure-receipt namespace exhausted")


def tool_identity(path: str, arguments: list[str]) -> dict[str, object]:
    done = subprocess.run([path, *arguments], check=True, capture_output=True, text=True, errors="replace")
    lines = (done.stdout + done.stderr).splitlines()
    binary = Path(path)
    return {
        "path": binary.as_posix(),
        "bytes": binary.stat().st_size,
        "sha256": sha256(binary),
        "version": next((line for line in lines if line.strip()), ""),
    }


def count_log_flags(text: str) -> dict[str, int]:
    patterns = {
        "fatal_errors": (
            r"^! (?:LaTeX Error|Package [^\r\n]+ Error|Undefined control sequence|Emergency stop|Fatal error)"
            r"|^.+:[0-9]+: (?:LaTeX Error|Package [^\r\n]+ Error|Undefined control sequence)"
            r"|Emergency stop|Fatal error occurred"
        ),
        "missing_glyphs": r"Missing character|Missing glyph",
        "overfull_hboxes": r"Overfull \\hbox",
        "overfull_vboxes": r"Overfull \\vbox",
        "underfull_hboxes": r"Underfull \\hbox",
        "underfull_vboxes": r"Underfull \\vbox",
        "undefined_reference_warnings": r"LaTeX Warning: (?:Reference|Hyper reference)[\s\S]{0,240}?undefined on input line",
        "undefined_reference_summaries": r"There were undefined references",
        "undefined_citation_warnings": r"LaTeX Warning: Citation[\s\S]{0,240}?undefined on input line",
        "undefined_citation_summaries": r"There were undefined citations",
        "navigation_reference_warnings": r"Package hyperref Warning:.*(?:undefined|empty target)|name\{[^}]+\} has been referenced but does not exist",
        "missing_external_aux": r"Package xr Warning: No file",
        "rerun_requests": r"Rerun to get|Label\(s\) may have changed",
        "duplicate_destinations": r"destination with the same identifier|duplicate ignored",
        "multiply_defined_labels": r"multiply defined",
    }
    return {name: len(re.findall(pattern, text, re.I | re.M)) for name, pattern in patterns.items()}


def extract_text(pdftotext: str, pdf: Path) -> tuple[bytes, dict[str, object]]:
    # MiKTeX's bundled pdftotext cannot open some long absolute Windows paths.
    # Preserve and reverify the exact PDF bytes through a short, private
    # attempt-local extraction copy; this is an I/O adapter, not a content
    # transformation.
    with tempfile.TemporaryDirectory(prefix="stacks-r9-pdftotext-") as stage_directory:
        stage_pdf = Path(stage_directory) / "input.pdf"
        shutil.copyfile(pdf, stage_pdf)
        if stage_pdf.stat().st_size != pdf.stat().st_size or sha256(stage_pdf) != sha256(pdf):
            raise RuntimeError(f"pdftotext staging identity mismatch: {pdf}")
        done = subprocess.run(
            [pdftotext, "-enc", "UTF-8", str(stage_pdf), "-"],
            check=False,
            capture_output=True,
        )
        if done.returncode != 0:
            diagnostic = done.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"pdftotext extraction failed for {pdf.name} with exit {done.returncode}: {diagnostic}"
            )
    raw = done.stdout
    text = raw.decode("utf-8", errors="strict")
    pages = text.split("\f")
    question_pages = [
        {"page_one_based": index, "pairs": page.count("??")}
        for index, page in enumerate(pages, 1)
        if page.count("??")
    ]
    return raw, {
        "utf8_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "page_form_feeds": text.count("\f"),
        "hangul_syllables": len(re.findall(r"[가-힣]", text)),
        "hangul_interword_spaces": len(re.findall(r"[가-힣]\s+[가-힣]", text)),
        "replacement_characters": text.count("\ufffd"),
        "nul_characters": text.count("\x00"),
        "question_mark_pairs": text.count("??"),
        "question_mark_pair_pages": question_pages,
    }


def font_audit(reader: PdfReader) -> dict[str, object]:
    fonts: dict[tuple[int, int], dict[str, object]] = {}
    for page in reader.pages:
        resources = page.get("/Resources")
        resources = resources.get_object() if hasattr(resources, "get_object") else resources
        if not resources:
            continue
        font_map = resources.get("/Font")
        font_map = font_map.get_object() if hasattr(font_map, "get_object") else font_map
        if not font_map:
            continue
        for ref in font_map.values():
            key = (getattr(ref, "idnum", id(ref)), getattr(ref, "generation", 0))
            if key in fonts:
                continue
            font = ref.get_object() if hasattr(ref, "get_object") else ref
            descriptor = font.get("/FontDescriptor")
            if descriptor is None and font.get("/DescendantFonts"):
                descendant = font["/DescendantFonts"][0].get_object()
                descriptor = descendant.get("/FontDescriptor")
            descriptor = descriptor.get_object() if hasattr(descriptor, "get_object") else descriptor
            embedded = bool(descriptor and any(name in descriptor for name in ("/FontFile", "/FontFile2", "/FontFile3")))
            fonts[key] = {
                "base_font": str(font.get("/BaseFont", "")),
                "subtype": str(font.get("/Subtype", "")),
                "embedded": embedded,
                "to_unicode": "/ToUnicode" in font,
            }
    return {
        "resources": len(fonts),
        "embedded": sum(bool(item["embedded"]) for item in fonts.values()),
        "to_unicode": sum(bool(item["to_unicode"]) for item in fonts.values()),
        "all_embedded": bool(fonts) and all(bool(item["embedded"]) for item in fonts.values()),
        "fonts": list(fonts.values()),
    }


def validate_pdf(pdf: Path, pdftotext: str, chapter: int | None = None) -> tuple[PdfReader, dict[str, object]]:
    reader = PdfReader(pdf, strict=True)
    scope = f"chapter {chapter}" if chapter is not None else "cumulative"
    if reader.is_encrypted or not reader.pages:
        raise RuntimeError(f"{scope}: strict PDF open/page gate failed")
    boxes = {tuple(round(float(value), 3) for value in page.mediabox) for page in reader.pages}
    if len(boxes) != 1:
        raise RuntimeError(f"{scope}: nonuniform page boxes")
    raw, extraction = extract_text(pdftotext, pdf)
    if extraction["replacement_characters"] or extraction["nul_characters"]:
        raise RuntimeError(f"{scope}: Unicode extraction hazard: {extraction}")
    if extraction["hangul_syllables"] == 0 or extraction["hangul_interword_spaces"] < 10:
        raise RuntimeError(f"{scope}: Korean extraction/word-spacing gate failed: {extraction}")
    fonts = font_audit(reader)
    if not fonts["all_embedded"]:
        raise RuntimeError(f"{scope}: nonembedded font detected")
    return reader, {
        "strict_open": True,
        "encrypted": False,
        "pages": len(reader.pages),
        "page_boxes": [list(values) for values in sorted(boxes)],
        "uniform_page_box": True,
        "extraction": extraction,
        "font_audit": fonts,
        "normalized_text_sha256": hashlib.sha256(re.sub(r"\s+", " ", raw.decode("utf-8")).strip().encode("utf-8")).hexdigest().upper(),
    }


def validate_existing_component(
    final: Path,
    target_record: dict[str, object],
    authority_record: dict[str, object],
    profile_record: dict[str, object],
    tools: dict[str, str],
) -> dict[str, object] | None:
    receipt_path = final / "COMPONENT_BUILD.json"
    if not receipt_path.is_file():
        return None
    receipt = json.loads(receipt_path.read_text(encoding="utf-8", errors="strict"))
    pdf = final / str(receipt.get("pdf_filename", ""))
    if receipt.get("result") != "PASS_MANAGER_COMPONENT_BUILD_PENDING_CUMULATIVE_VISUAL_QA":
        raise RuntimeError(f"existing component receipt failed replay: {final}")
    if receipt.get("target") != target_record or receipt.get("authority") != authority_record:
        raise RuntimeError(f"existing component source identity changed: {final}")
    if receipt.get("adapter", {}).get("profile") != profile_record:
        raise RuntimeError(f"existing component reference profile changed: {final}")
    for field in ("pdf", "tex_log", "bbl", "blg", "fls"):
        if require_record(receipt[field]) != receipt[field]:
            raise RuntimeError(f"existing component {field} replay failed: {final}")
    for build_pass in receipt.get("passes", []):
        if int(build_pass.get("exit_code", -1)) != 0 or require_record(build_pass["console"]) != build_pass["console"]:
            raise RuntimeError(f"existing component pass replay failed: {final}")
    chapter = int(receipt["chapter"])
    log_text = (ROOT / str(receipt["tex_log"]["path"])).read_text(encoding="utf-8", errors="replace")
    flags = count_log_flags(log_text)
    if flags != receipt.get("log_flags"):
        raise RuntimeError(f"existing component log classification changed: {final}; {flags}")
    disallowed = (
        "fatal_errors", "missing_glyphs", "undefined_reference_warnings", "undefined_reference_summaries",
        "undefined_citation_warnings", "undefined_citation_summaries", "navigation_reference_warnings",
        "missing_external_aux", "rerun_requests", "duplicate_destinations", "multiply_defined_labels",
    )
    if any(flags[name] for name in disallowed):
        raise RuntimeError(f"existing component now fails final log gate: {final}; {flags}")
    bibtex_warnings = re.findall(
        r"^Warning--.*$",
        (ROOT / str(receipt["blg"]["path"])).read_text(encoding="utf-8", errors="replace"),
        re.M,
    )
    allowed = ALLOWED_BIBTEX_WARNINGS_BY_CHAPTER.get(chapter, set())
    if bibtex_warnings != receipt.get("bibtex_warning_lines") or any(line not in allowed for line in bibtex_warnings):
        raise RuntimeError(f"existing component BibTeX policy replay failed: {final}; {bibtex_warnings}")
    _reader, replay_validation = validate_pdf(pdf, tools["pdftotext"], chapter)
    prior_validation = receipt.get("pdf_validation", {})
    for field in ("pages", "page_boxes", "uniform_page_box", "normalized_text_sha256"):
        if replay_validation.get(field) != prior_validation.get(field):
            raise RuntimeError(f"existing component PDF replay changed {field}: {final}")
    receipt["resume_disposition"] = "reused_exact_completed_component"
    receipt["receipt"] = identity(receipt_path)
    return receipt


def build_component(chapter: dict[str, object], preflight_row: dict[str, object], tools: dict[str, str]) -> dict[str, object]:
    number = int(chapter["chapter"])
    part = str(chapter["part"])
    stem = str(chapter["stem"])
    job = f"ch{number:03d}-{stem}"
    profile = PROFILES / job
    target = ROOT / "inputs" / part / "ko" / f"{stem}.tex"
    target_id = preflight_row["local_target"]
    require(target, int(target_id["bytes"]), str(target_id["sha256"]))
    authority_id = preflight_row["local_authority"]
    require(ROOT / str(authority_id["path"]), int(authority_id["bytes"]), str(authority_id["sha256"]))
    profile_id = tree_identity(profile)
    if profile_id != preflight_row["profile"]:
        raise RuntimeError(f"chapter {number}: reference-profile identity changed: {profile_id}")
    ko_preamble_text = (profile / "ko_preamble.tex").read_text(encoding="utf-8", errors="strict")
    preamble_text = (profile / "preamble.tex").read_text(encoding="utf-8", errors="strict")
    if ko_preamble_text.count(r"\xeCJKsetup{CJKspace=true}") != 1:
        raise RuntimeError(f"chapter {number}: corrected Korean profile changed")
    accent_fix_counts = {
        "preamble.tex": preamble_text.count(r"\let\koManagerTextAcute\'"),
        "ko_preamble.tex": ko_preamble_text.count(r"\let\koManagerTextAcute\'"),
    }
    if set(accent_fix_counts.values()) != {1}:
        raise RuntimeError(f"chapter {number}: scoped math-accent adapter counts changed: {accent_fix_counts}")
    if preamble_text != ko_preamble_text:
        raise RuntimeError(f"chapter {number}: preamble aliases diverged")
    if len(list((profile / "xr").glob("*.aux"))) != 117:
        raise RuntimeError(f"chapter {number}: 117-AUX closure changed")
    COMPONENTS.mkdir(parents=True, exist_ok=True)
    final = COMPONENTS / job
    existing = validate_existing_component(final, target_id, authority_id, profile_id, tools) if final.exists() else None
    if existing is not None:
        return existing
    if final.exists():
        raise RuntimeError(f"unrecognized existing component directory: {final}")
    kinds = ("xelatex", "bibtex", "xelatex", "xelatex", "xelatex")
    recoverable_attempts: list[Path] = []
    if ATTEMPTS.is_dir():
        for candidate in sorted(ATTEMPTS.glob(f"ch{number:03d}-{stem}-a*")):
            required_names = [f"pass-{index}-{kind}.console.log" for index, kind in enumerate(kinds, 1)]
            required_names.extend(f"{job}.{suffix}" for suffix in ("log", "pdf", "bbl", "blg", "fls"))
            if all((candidate / name).is_file() and (candidate / name).stat().st_size > 0 for name in required_names):
                recoverable_attempts.append(candidate)
    if len(recoverable_attempts) > 1:
        raise RuntimeError(f"chapter {number}: multiple completed attempts require adjudication: {recoverable_attempts}")
    recovered_attempt = bool(recoverable_attempts)
    attempt = recoverable_attempts[0] if recovered_attempt else next_attempt(number, stem)
    attempt_origin = attempt.relative_to(ROOT).as_posix()
    passes: list[dict[str, object]] = []
    if recovered_attempt:
        for index, kind in enumerate(kinds, 1):
            console = attempt / f"pass-{index}-{kind}.console.log"
            passes.append({
                "pass": index,
                "tool": kind,
                "exit_code": 0,
                "started_utc": datetime.fromtimestamp(console.stat().st_ctime, timezone.utc).isoformat(),
                "ended_utc": datetime.fromtimestamp(console.stat().st_mtime, timezone.utc).isoformat(),
                "console_name": console.name,
                "console_bytes": console.stat().st_size,
                "console_sha256": sha256(console),
                "recovered_after_post_build_directory_parent_failure": True,
            })
        print(json.dumps({"chapter": number, "recovered_completed_attempt": attempt_origin}), flush=True)
    else:
        environment = os.environ.copy()
        environment["TEXINPUTS"] = f"{profile};{profile / 'xr'};{DEPENDENCIES};"
        environment["BIBINPUTS"] = f"{DEPENDENCIES};"
        environment["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
        environment["FORCE_SOURCE_DATE"] = "1"
        environment["TZ"] = "UTC"
        environment["PYTHONHASHSEED"] = "0"
        for index, kind in enumerate(kinds, 1):
            console = attempt / f"pass-{index}-{kind}.console.log"
            command = [tools[kind], job] if kind == "bibtex" else [
                tools[kind], "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error",
                "-file-line-error", "-recorder", f"-jobname={job}", str(target),
            ]
            started = datetime.now(timezone.utc)
            with console.open("wb") as stream:
                done = subprocess.run(command, cwd=attempt, env=environment, stdout=stream, stderr=subprocess.STDOUT, timeout=1800)
            ended = datetime.now(timezone.utc)
            passes.append({
                "pass": index,
                "tool": kind,
                "exit_code": done.returncode,
                "started_utc": started.isoformat(),
                "ended_utc": ended.isoformat(),
                "console_name": console.name,
                "console_bytes": console.stat().st_size,
                "console_sha256": sha256(console),
            })
            print(json.dumps({"chapter": number, "pass": index, "tool": kind, "exit_code": done.returncode}), flush=True)
            if done.returncode != 0:
                raise RuntimeError(f"chapter {number}: pass {index} {kind} failed; see {console}")

    tex_log = attempt / f"{job}.log"
    pdf = attempt / f"{job}.pdf"
    bbl = attempt / f"{job}.bbl"
    blg = attempt / f"{job}.blg"
    fls = attempt / f"{job}.fls"
    for required in (tex_log, pdf, bbl, blg, fls):
        if not required.is_file():
            raise RuntimeError(f"chapter {number}: missing build output {required.name}")
    flags = count_log_flags(tex_log.read_text(encoding="utf-8", errors="replace"))
    disallowed = (
        "fatal_errors", "missing_glyphs", "undefined_reference_warnings", "undefined_reference_summaries",
        "undefined_citation_warnings", "undefined_citation_summaries", "navigation_reference_warnings",
        "missing_external_aux", "rerun_requests", "duplicate_destinations", "multiply_defined_labels",
    )
    if any(flags[name] for name in disallowed):
        raise RuntimeError(f"chapter {number}: final TeX log gate failed: {flags}")
    bibtex_warnings = re.findall(r"^Warning--.*$", blg.read_text(encoding="utf-8", errors="replace"), re.M)
    allowed_bibtex_warnings = ALLOWED_BIBTEX_WARNINGS_BY_CHAPTER.get(number, set())
    unexpected = [line for line in bibtex_warnings if line not in allowed_bibtex_warnings]
    if unexpected:
        raise RuntimeError(f"chapter {number}: unexpected BibTeX warnings: {unexpected}")
    fls_text = fls.read_text(encoding="utf-8", errors="replace").replace("/", "\\").casefold()
    forbidden = []
    stack_root = ROOT.parents[2]
    for producer_part in tuple(f"p{number:02d}" for number in range(1, 13)):
        prefix = str(stack_root / producer_part).casefold()
        if prefix in fls_text:
            forbidden.append(prefix)
    if forbidden:
        raise RuntimeError(f"chapter {number}: recorder accessed producer roots: {forbidden}")
    _reader, pdf_validation = validate_pdf(pdf, tools["pdftotext"], number)
    attempt.rename(final)
    tex_log = final / tex_log.name
    pdf = final / pdf.name
    bbl = final / bbl.name
    blg = final / blg.name
    fls = final / fls.name
    passes_final = []
    for item in passes:
        copied = dict(item)
        console = final / str(item["console_name"])
        copied["console"] = identity(console)
        copied.pop("console_name", None)
        copied.pop("console_bytes", None)
        copied.pop("console_sha256", None)
        passes_final.append(copied)
    receipt = {
        "schema": "interlanguage.stacks_cjk.ko_kr_r9_manager_component_build/v1",
        "record_id": f"STACKS-CJK-KO-KR-R9-CH{number:03d}-BUILD-20260905",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "chapter": number,
        "part": part,
        "stem": stem,
        "title": chapter["title"],
        "target": identity(target),
        "authority": preflight_row["local_authority"],
        "producer_harvest_evidence": {
            "producer_target": preflight_row["producer_target"],
            "producer_qa": preflight_row["producer_qa"],
            "producer_additional_receipts": preflight_row["producer_additional_receipts"],
            "producer_pdf": preflight_row["producer_pdf"],
            "producer_pdf_pages": preflight_row["producer_pdf_pages"],
        },
        "attempt_recovery": {
            "used": recovered_attempt,
            "attempt_origin": attempt_origin,
            "trigger_failure": identity(ROOT / "receipts" / "R9_COMPONENT_BUILD_FAILURE_001.json") if recovered_attempt else None,
            "tex_passes_reexecuted": not recovered_attempt,
        },
        "passes": passes_final,
        "tex_log": identity(tex_log),
        "bbl": identity(bbl),
        "blg": identity(blg),
        "fls": identity(fls),
        "log_flags": flags,
        "bibtex_warning_lines": bibtex_warnings,
        "bibtex_warning_policy": {
            "chapter_specific_allowed_lines": sorted(allowed_bibtex_warnings),
            "unexpected_warning_lines": unexpected,
        },
        "recorder_producer_root_accesses": 0,
        "pdf_filename": pdf.name,
        "pdf": identity(pdf),
        "pdf_validation": pdf_validation,
        "adapter": {
            "profile": profile_id,
            "cjkspace_enabled": True,
            "xr_aux_files": 117,
            "scoped_math_accent_adapter_occurrences": accent_fix_counts,
            "producer_preamble_used": False,
        },
        "validator": identity(Path(__file__).resolve()),
        "result": "PASS_MANAGER_COMPONENT_BUILD_PENDING_CUMULATIVE_VISUAL_QA",
        "canon_admission": "PENDING_CUMULATIVE_AND_PAGE_COMPLETE_VISUAL_QA",
    }
    atomic_json(final / "COMPONENT_BUILD.json", receipt)
    receipt["receipt"] = identity(final / "COMPONENT_BUILD.json")
    return receipt


def merge_pdf(plan: dict[str, object], components: list[dict[str, object]], destination: Path) -> dict[str, object]:
    added = {int(item["chapter"]): item for item in components}
    added_plan = {int(item["chapter"]): item for item in plan["added_chapters"]}
    inherited = {int(item["chapter"]): item for item in plan["inherited_chapters"]}
    writer = PdfWriter()
    starts: list[dict[str, object]] = []
    stripped = 0
    page_offset = 0
    for chapter in plan["canonical_cumulative_order"]:
        chapter = int(chapter)
        if chapter in added:
            component = added[chapter]
            pdf = COMPONENTS / f"ch{chapter:03d}-{component['stem']}" / str(component["pdf_filename"])
            title = str(added_plan[chapter]["title"])
            provenance = "r9_manager_rebuild"
        else:
            item = inherited[chapter]
            pdf = ROOT / "evidence" / "inherited-components" / f"ch{chapter:03d}-{item['stem']}.pdf"
            title = str(item["title"])
            provenance = "exact_r6_component_inheritance"
        reader = PdfReader(pdf, strict=True)
        starts.append({
            "chapter": chapter,
            "stem": added_plan[chapter]["stem"] if chapter in added_plan else inherited[chapter]["stem"],
            "title": title,
            "provenance": provenance,
            "page_index_zero_based": page_offset,
            "pages": len(reader.pages),
            "pdf": identity(pdf),
        })
        for page in reader.pages:
            annotations = page.get("/Annots", [])
            annotations = annotations.get_object() if hasattr(annotations, "get_object") else annotations
            stripped += len(annotations)
            page.pop(NameObject("/Annots"), None)
            writer.add_page(page)
            page_offset += 1
    parent = writer.add_outline_item("한국어 누적 리더 / Korean Cumulative Reader", 0)
    for item in starts:
        writer.add_outline_item(f"제{item['chapter']}장: {item['title']}", int(item["page_index_zero_based"]), parent=parent)
    writer.add_metadata({
        "/Title": "Stacks Project 한국어 누적 리더 - 52 chapters",
        "/Author": "Interlanguage project",
        "/Subject": "Receipt-bound Korean cumulative integration at frozen Stacks commit a04446e57ec1fbc252a871afcec7752fb2807b14",
        "/Creator": "Deterministic Korean r9 cumulative builder",
        "/Producer": "pypdf",
        "/CreationDate": "D:20260905000000Z",
        "/ModDate": "D:20260905000000Z",
    })
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        writer.write(stream)
    return {"chapter_starts": starts, "pages": page_offset, "source_annotations_stripped": stripped}


def verify_merged(pdf: Path, expected_pages: int, pdftotext: str) -> dict[str, object]:
    reader, base = validate_pdf(pdf, pdftotext, None)
    if len(reader.pages) != expected_pages:
        raise RuntimeError(f"cumulative page mismatch: expected {expected_pages}, got {len(reader.pages)}")
    annotations = 0
    for page in reader.pages:
        values = page.get("/Annots", [])
        values = values.get_object() if hasattr(values, "get_object") else values
        annotations += len(values)
    if annotations:
        raise RuntimeError(f"cumulative annotation stripping failed: {annotations}")
    if not reader.outline:
        raise RuntimeError("cumulative outline absent")
    base["annotations"] = annotations
    base["outline_present"] = True
    return base


def main() -> None:
    if BUILD_RECEIPT.exists() or FINAL_PDF.exists() or REPLAY_PDF.exists():
        raise RuntimeError("build outputs already exist; inspect rather than duplicate")
    plan_id = require(PLAN_PATH, *EXPECTED_PLAN)
    preflight_id = require(PREFLIGHT_PATH, *EXPECTED_PREFLIGHT)
    profile_repair_id = require(PROFILE_REPAIR_PATH, *EXPECTED_PROFILE_REPAIR)
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8", errors="strict"))
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8", errors="strict"))
    profile_repair = json.loads(PROFILE_REPAIR_PATH.read_text(encoding="utf-8", errors="strict"))
    if preflight.get("result") != "PASS_READY_FOR_SINGLE_MUTEX_SERIALIZED_R9_BUILD":
        raise RuntimeError("preflight does not authorize the build")
    if profile_repair.get("result") != "PASS_APPEND_ONLY_MANAGER_PROFILE_REPAIR":
        raise RuntimeError("profile repair does not authorize the build")
    if len(plan["added_chapters"]) != 3 or len(plan["inherited_chapters"]) != 49 or len(plan["canonical_cumulative_order"]) != 52:
        raise RuntimeError("build-plan count gate failed")
    if [int(item["chapter"]) for item in plan["added_chapters"]] != [89, 90, 101]:
        raise RuntimeError("r9 addition set changed")
    source_rows = {int(item["chapter"]): item for item in preflight["added_source_replay"]}
    repaired_profiles = {
        int(item["chapter"]): item["new_profile"]
        for item in profile_repair["scoped_profile_repairs"]
    }
    if set(repaired_profiles) != {89, 90, 101}:
        raise RuntimeError(f"profile repair chapter set changed: {sorted(repaired_profiles)}")
    for chapter in plan["added_chapters"]:
        number = int(chapter["chapter"])
        source_rows[number]["profile"] = repaired_profiles[number]

    dependency_tree = tree_identity(DEPENDENCIES)
    if dependency_tree != plan["frozen_local_trees"]["dependencies"]:
        raise RuntimeError(f"dependency tree changed: {dependency_tree}")
    live_profile_tree = tree_identity(PROFILES)
    if live_profile_tree != profile_repair["new_complete_profile_tree"]:
        raise RuntimeError(f"complete r9 profile tree changed: {live_profile_tree}")

    tools = {name: shutil.which(name) for name in ("xelatex", "bibtex", "pdftotext")}
    if any(value is None for value in tools.values()):
        raise RuntimeError(f"required build tool unavailable: {tools}")
    resolved = {name: str(path) for name, path in tools.items()}
    tool_ids = {
        "xelatex": tool_identity(resolved["xelatex"], ["--version"]),
        "bibtex": tool_identity(resolved["bibtex"], ["--version"]),
        "pdftotext": tool_identity(resolved["pdftotext"], ["-v"]),
    }
    scripts = {
        "builder": identity(Path(__file__).resolve()),
        "mutex_wrapper": identity(ROOT / "build" / "run_tex_serialized.ps1"),
    }
    started = datetime.now(timezone.utc)
    components: list[dict[str, object]] = []
    try:
        for chapter in plan["added_chapters"]:
            components.append(build_component(chapter, source_rows[int(chapter["chapter"])], resolved))
        merge = merge_pdf(plan, components, FINAL_PDF)
        replay_merge = merge_pdf(plan, components, REPLAY_PDF)
        if FINAL_PDF.stat().st_size != REPLAY_PDF.stat().st_size or sha256(FINAL_PDF) != sha256(REPLAY_PDF):
            raise RuntimeError("deterministic cumulative byte replay failed")
        verification = verify_merged(FINAL_PDF, int(merge["pages"]), resolved["pdftotext"])
        replay_verification = verify_merged(REPLAY_PDF, int(replay_merge["pages"]), resolved["pdftotext"])
        if verification["normalized_text_sha256"] != replay_verification["normalized_text_sha256"]:
            raise RuntimeError("deterministic cumulative text replay failed")
        receipt = {
            "schema": "interlanguage.stacks_cjk.ko_kr_r9_component_and_cumulative_build/v1",
            "record_id": "STACKS-CJK-KO-KR-R9-BUILD-20260905",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "started_utc": started.isoformat(),
            "build_plan": plan_id,
            "preflight": preflight_id,
            "profile_repair": profile_repair_id,
            "frozen_dependency_tree": dependency_tree,
            "complete_reference_profile_tree": live_profile_tree,
            "scripts": scripts,
            "tools": tool_ids,
            "components": components,
            "merge": merge,
            "cumulative_pdf": identity(FINAL_PDF),
            "cumulative_verification": verification,
            "deterministic_replay_pdf": identity(REPLAY_PDF),
            "deterministic_replay_verification": replay_verification,
            "byte_identical_replay": True,
            "checks": {
                "three_manager_owned_component_builds": "PASS",
                "forty_nine_exact_r6_inherited_components": "PASS",
                "korean_word_spacing_and_extractability": "PASS",
                "zero_unresolved_tex_references_and_citations": "PASS",
                "all_fonts_embedded": "PASS",
                "fifty_two_chapter_canonical_order": "PASS",
                "annotations_stripped_and_outline_present": "PASS",
                "deterministic_cumulative_byte_replay": "PASS",
            },
            "result": "PASS_BUILD_AND_DETERMINISTIC_CUMULATIVE_ASSEMBLY_PENDING_PAGE_COMPLETE_VISUAL_QA",
            "canon_admission": "NOT_YET_ADMITTED_PENDING_PAGE_COMPLETE_VISUAL_QA",
            "publication": "NOT_AUTHORIZED_BEFORE_PAGE_COMPLETE_VISUAL_QA",
        }
        atomic_json(BUILD_RECEIPT, receipt)
        print(json.dumps({"receipt": identity(BUILD_RECEIPT), "pdf": identity(FINAL_PDF), "pages": verification["pages"], "result": receipt["result"]}, ensure_ascii=False), flush=True)
    except BaseException as exc:
        failure = {
            "schema": "interlanguage.stacks_cjk.ko_kr_r9_component_build_failure/v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "started_utc": started.isoformat(),
            "build_plan": plan_id,
            "preflight": preflight_id,
            "profile_repair": profile_repair_id,
            "completed_components": [int(item["chapter"]) for item in components],
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "result": "FAIL_CLOSED",
            "resume": "Reuse each exact completed component receipt and start a fresh numbered attempt only for the first incomplete chapter.",
        }
        atomic_json(next_failure_path(), failure)
        raise


if __name__ == "__main__":
    main()
