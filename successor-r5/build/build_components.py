from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import traceback
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "BUILD_PLAN.json"
PREFLIGHT_PATH = ROOT / "receipts" / "P11_REBUILD_PREFLIGHT.json"
PROFILES = ROOT / "support" / "profiles-r2"
DEPS = ROOT / "support" / "dependencies"
COMPONENTS = ROOT / "evidence" / "components"
ATTEMPTS = ROOT / "evidence" / "build-attempts"
OUTPUT = ROOT / "output" / "pdf"
BUILD_RECEIPT = ROOT / "receipts" / "P11_COMPONENT_AND_CUMULATIVE_BUILD.json"
REFERENCE_REPAIR = ROOT / "receipts" / "P11_REFERENCE_CLOSURE_REPAIR.json"
BIBTEX_WARNING_ADJUDICATION = ROOT / "receipts" / "P11_BIBTEX_WARNING_ADJUDICATION.json"
FINAL_PDF = OUTPUT / "stacks-project-ko-kr-cumulative-r5.pdf"
REPLAY_PDF = ROOT / "evidence" / "stacks-project-ko-kr-cumulative-r5.replay.pdf"
SOURCE_DATE_EPOCH = "1788562238"

EXPECTED_PLAN = (5948, "4472814B4F9878D9E6F728917935F92C545830785AE96E5C11891DF8CC71F5A4")
EXPECTED_PREFLIGHT = (246703, "1494B58D2F9BEB509E57920BC77D4C176B032F4E98D56CF8E067FB23E9868225")
EXPECTED_REFERENCE_REPAIR = (11081, "EECA176E712DF33159857DC4FD28E94414562ECBCF463A0A120B7867AA233990")
EXPECTED_BIBTEX_WARNING_ADJUDICATION = (3644, "B482E8EE2F1AA062E912E7FE3A92358AEFFEB50DF07F30BBFE51256EDB849EBF")
ADJUDICATED_CH100_WARNING = "Warning--missing pages in rydh_etale_devissage"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def identity(path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def require(path: Path, size: int, digest: str) -> dict[str, object]:
    got = identity(path)
    if got["bytes"] != size or got["sha256"] != digest:
        raise RuntimeError(f"identity mismatch: {path}")
    return got


def load_bibtex_warning_adjudication() -> tuple[dict[str, object], dict[int, tuple[str, ...]]]:
    receipt_id = require(BIBTEX_WARNING_ADJUDICATION, *EXPECTED_BIBTEX_WARNING_ADJUDICATION)
    receipt = json.loads(BIBTEX_WARNING_ADJUDICATION.read_text(encoding="utf-8"))
    warning = receipt.get("failed_attempt", {}).get("warning", {})
    entry = receipt.get("frozen_bibliography", {}).get("entry", {})
    citations = receipt.get("citation_loci", {})
    adjudication = receipt.get("adjudication", {})
    if (
        receipt.get("schema") != "interlanguage.stacks_cjk.ko_p11_bibtex_warning_adjudication/v1"
        or receipt.get("scope", {}).get("chapter") != 100
        or receipt.get("scope", {}).get("stem") != "stacks-properties"
        or warning.get("line_one_based") != 8
        or warning.get("exact") != ADJUDICATED_CH100_WARNING
        or warning.get("occurrences") != 1
        or entry.get("key") != "rydh_etale_devissage"
        or entry.get("line_start_one_based") != 6230
        or entry.get("line_end_one_based") != 6235
        or entry.get("missing_field") != "PAGES"
        or citations.get("authority", {}).get("line_one_based") != 2781
        or citations.get("korean_target", {}).get("line_one_based") != 2518
        or adjudication.get("classification") != "NONBLOCKING_FROZEN_BIBLIOGRAPHY_METADATA_OMISSION"
        or adjudication.get("allowed_warning") != ADJUDICATED_CH100_WARNING
        or adjudication.get("allowed_chapter") != 100
        or adjudication.get("allowed_occurrences_max") != 1
        or receipt.get("result") != "PASS_APPEND_ONLY_NONBLOCKING_FROZEN_BIBLIOGRAPHY_METADATA_OMISSION_ADJUDICATED"
    ):
        raise RuntimeError("BibTeX warning adjudication semantic gate failed")

    bindings = (
        (receipt.get("trigger_failure", {}), "receipts/P11_COMPONENT_BUILD_FAILURE_002.json", 1947, "9F8523231BACB11E61ED3B480620E1119C76B215D271573B408B2FB621861029"),
        (receipt.get("failed_attempt", {}).get("pdf", {}), "evidence/build-attempts/ch100-stacks-properties-a001/ch100-stacks-properties.pdf", 322640, "91A64F18CFC38B390C0C656B2140D8201002599A18D3113C086B014A407E69A8"),
        (receipt.get("failed_attempt", {}).get("blg", {}), "evidence/build-attempts/ch100-stacks-properties-a001/ch100-stacks-properties.blg", 1098, "A64C6BCE418D722AF3F358FBD4D3F35A623000DF487BF159F3B08FCDACA4EB28"),
        (receipt.get("frozen_bibliography", {}), "support/dependencies/my.bib", 210197, "AE2BA8729BECFD5BAA4FDC9448EB5332ED1EC727BD41CAF0937EBA02E367521E"),
        (citations.get("authority", {}), "authority/a04446e/stacks-properties.tex", 120421, "59D6B6DF8F528ED5D3A68D9B9D74622E9B643F3622CC4D381BB46CC27A990016"),
        (citations.get("korean_target", {}), "inputs/p11/ko/stacks-properties.tex", 128709, "267947D63266B021224D1F46905C8C728EED8F82A627EF902B4666F2D73E96D1"),
    )
    for recorded, relative, size, digest in bindings:
        expected = {"path": relative, "bytes": size, "sha256": digest}
        if {key: recorded.get(key) for key in expected} != expected:
            raise RuntimeError(f"BibTeX warning adjudication binding changed: {relative}")
        require(ROOT / relative, size, digest)

    blg_lines = (ROOT / "evidence/build-attempts/ch100-stacks-properties-a001/ch100-stacks-properties.blg").read_text(
        encoding="utf-8", errors="strict"
    ).splitlines()
    bib_lines = (ROOT / "support/dependencies/my.bib").read_text(encoding="utf-8", errors="strict").splitlines()
    authority_lines = (ROOT / "authority/a04446e/stacks-properties.tex").read_text(encoding="utf-8", errors="strict").splitlines()
    target_lines = (ROOT / "inputs/p11/ko/stacks-properties.tex").read_text(encoding="utf-8", errors="strict").splitlines()
    if blg_lines[7] != ADJUDICATED_CH100_WARNING or blg_lines.count(ADJUDICATED_CH100_WARNING) != 1:
        raise RuntimeError("BibTeX warning adjudication BLG locus changed")
    if bib_lines[6229:6235] != entry.get("exact_lines"):
        raise RuntimeError("BibTeX warning adjudication bibliography locus changed")
    if authority_lines[2780] != citations["authority"].get("exact_line") or authority_lines.count(citations["authority"].get("exact_line")) != 1:
        raise RuntimeError("BibTeX warning adjudication authority cite locus changed")
    if target_lines[2517] != citations["korean_target"].get("exact_line") or target_lines.count(citations["korean_target"].get("exact_line")) != 1:
        raise RuntimeError("BibTeX warning adjudication Korean cite locus changed")
    return receipt_id, {100: (ADJUDICATED_CH100_WARNING,)}


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
    raise RuntimeError("component attempt namespace exhausted")


def next_failure_path() -> Path:
    for number in range(1, 1000):
        path = ROOT / "receipts" / f"P11_COMPONENT_BUILD_FAILURE_{number:03d}.json"
        if not path.exists():
            return path
    raise RuntimeError("failure receipt namespace exhausted")


def tool_identity(path: str, arguments: list[str]) -> dict[str, object]:
    done = subprocess.run([path, *arguments], check=True, capture_output=True, text=True, errors="replace")
    lines = (done.stdout + done.stderr).splitlines()
    return {"path": Path(path).as_posix(), "version": next((line for line in lines if line.strip()), "")}


def count_log_flags(text: str) -> dict[str, int]:
    patterns = {
        "fatal_errors": r"^! |Undefined control sequence|Emergency stop|Fatal error occurred",
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


def unexpected_bibtex_warnings(
    chapter: int,
    warnings: list[str],
    chapter_allowances: dict[int, tuple[str, ...]],
) -> list[str]:
    allowed = {"Warning--missing pages in EGA", "Warning--missing pages in lieblich_remarks"}
    remaining_chapter_allowances = list(chapter_allowances.get(chapter, ()))
    unexpected = []
    for line in warnings:
        if line in allowed:
            continue
        if line in remaining_chapter_allowances:
            remaining_chapter_allowances.remove(line)
            continue
        unexpected.append(line)
    return unexpected


def extract_text(pdftotext: str, pdf: Path) -> tuple[bytes, dict[str, object]]:
    done = subprocess.run([pdftotext, "-enc", "UTF-8", str(pdf), "-"], check=True, capture_output=True)
    raw = done.stdout
    text = raw.decode("utf-8", errors="strict")
    pages = text.split("\f")
    pair_pages = [
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
        "question_mark_pair_pages": pair_pages,
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


def validate_component_pdf(pdf: Path, pdftotext: str, chapter: int) -> tuple[PdfReader, dict[str, object]]:
    reader = PdfReader(pdf, strict=True)
    if reader.is_encrypted or not reader.pages:
        raise RuntimeError(f"chapter {chapter}: strict PDF open/page gate failed")
    boxes = {tuple(round(float(value), 3) for value in page.mediabox) for page in reader.pages}
    if len(boxes) != 1:
        raise RuntimeError(f"chapter {chapter}: nonuniform page boxes")
    raw, extraction = extract_text(pdftotext, pdf)
    if extraction["replacement_characters"] or extraction["nul_characters"]:
        raise RuntimeError(f"chapter {chapter}: Unicode extraction hazard: {extraction}")
    if extraction["hangul_syllables"] == 0 or extraction["hangul_interword_spaces"] < 10:
        raise RuntimeError(f"chapter {chapter}: Korean word-spacing extraction gate failed: {extraction}")
    text = re.sub(r"\s+", " ", raw.decode("utf-8")).strip()
    if chapter == 94 and "여기서는 대수 스택을 정의하고 몇 가지 매우 기초적인 관찰을 한다" not in text:
        raise RuntimeError("chapter 94: known Korean interword-spacing witness not preserved")
    fonts = font_audit(reader)
    if not fonts["all_embedded"]:
        raise RuntimeError(f"chapter {chapter}: nonembedded font detected")
    return reader, {
        "strict_open": True,
        "encrypted": False,
        "pages": len(reader.pages),
        "page_boxes": [list(values) for values in sorted(boxes)],
        "uniform_page_box": True,
        "extraction": extraction,
        "font_audit": fonts,
    }


def validate_existing_component(final: Path, target_sha: str) -> dict[str, object] | None:
    receipt_path = final / "COMPONENT_BUILD.json"
    if not receipt_path.is_file():
        return None
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    pdf = final / str(receipt.get("pdf_filename", ""))
    if (
        receipt.get("result") != "PASS_COMPONENT_REBUILT_WITH_KOREAN_WORD_SPACING"
        or receipt.get("target", {}).get("sha256") != target_sha
        or not pdf.is_file()
        or identity(pdf) != receipt.get("pdf")
    ):
        raise RuntimeError(f"existing component receipt failed replay: {final}")
    receipt["resume_disposition"] = "reused_exact_completed_component"
    return receipt


def build_component(
    chapter: dict[str, object],
    tools: dict[str, str],
    bibtex_warning_allowances: dict[int, tuple[str, ...]],
    bibtex_warning_adjudication_id: dict[str, object],
) -> dict[str, object]:
    number = int(chapter["chapter"])
    stem = str(chapter["stem"])
    job = f"ch{number:03d}-{stem}"
    profile = PROFILES / job
    target_entry = chapter["target"]
    target = ROOT / str(target_entry["path"])
    final = COMPONENTS / job
    existing = validate_existing_component(final, str(target_entry["sha256"])) if final.exists() else None
    if existing is not None:
        return existing
    if final.exists():
        raise RuntimeError(f"unrecognized existing component directory: {final}")
    attempt = next_attempt(number, stem)
    environment = os.environ.copy()
    environment["TEXINPUTS"] = f"{profile};{profile / 'xr'};{DEPS};"
    environment["BIBINPUTS"] = f"{DEPS};"
    environment["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    environment["FORCE_SOURCE_DATE"] = "1"
    environment["TZ"] = "UTC"
    environment["PYTHONHASHSEED"] = "0"
    pass_kinds = ("xelatex", "bibtex", "xelatex", "xelatex", "xelatex")
    passes = []
    for index, kind in enumerate(pass_kinds, 1):
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
            "console": identity(console),
        })
        print(json.dumps({"chapter": number, "pass": index, "tool": kind, "exit_code": done.returncode}), flush=True)
        if done.returncode != 0:
            raise RuntimeError(f"chapter {number} pass {index} {kind} failed; see {console}")

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
    blg_text = blg.read_text(encoding="utf-8", errors="replace")
    bibtex_warnings = re.findall(r"^Warning--.*$", blg_text, re.M)
    unexpected = unexpected_bibtex_warnings(number, bibtex_warnings, bibtex_warning_allowances)
    if unexpected:
        raise RuntimeError(f"chapter {number}: unexpected BibTeX warnings: {unexpected}")
    _reader, pdf_validation = validate_component_pdf(pdf, tools["pdftotext"], number)
    attempt.rename(final)
    passes_final = []
    for item in passes:
        copied = dict(item)
        copied["console"] = identity(final / Path(str(item["console"]["path"])).name)
        passes_final.append(copied)
    tex_log = final / tex_log.name
    pdf = final / pdf.name
    bbl = final / bbl.name
    blg = final / blg.name
    fls = final / fls.name
    receipt = {
        "schema": "interlanguage.stacks_cjk.ko_p11_manager_component_build/v1",
        "record_id": f"STACKS-CJK-KO-P11-R5-CH{number:03d}-BUILD-20260905",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "chapter": number,
        "stem": stem,
        "target": identity(target),
        "passes": passes_final,
        "tex_log": identity(tex_log),
        "bbl": identity(bbl),
        "blg": identity(blg),
        "fls": identity(fls),
        "log_flags": flags,
        "bibtex_warning_lines": bibtex_warnings,
        "pdf_filename": pdf.name,
        "pdf": identity(pdf),
        "pdf_validation": pdf_validation,
        "adapter": {
            "preamble": identity(profile / "ko_preamble.tex"),
            "cjkspace_enabled": True,
            "producer_preamble_used": False,
        },
        "result": "PASS_COMPONENT_REBUILT_WITH_KOREAN_WORD_SPACING",
        "canon_admission": "PENDING_CUMULATIVE_AND_PAGE_COMPLETE_VISUAL_QA",
    }
    if bibtex_warning_allowances.get(number):
        receipt["bibtex_warning_adjudication"] = bibtex_warning_adjudication_id
    atomic_json(final / "COMPONENT_BUILD.json", receipt)
    receipt["receipt"] = identity(final / "COMPONENT_BUILD.json")
    final_receipt = json.loads((final / "COMPONENT_BUILD.json").read_text(encoding="utf-8"))
    final_receipt["receipt"] = identity(final / "COMPONENT_BUILD.json")
    return final_receipt


def merge_pdf(plan: dict[str, object], new_components: list[dict[str, object]], destination: Path) -> dict[str, object]:
    new_by_chapter = {int(item["chapter"]): item for item in new_components}
    inherited_by_chapter = {int(item["chapter"]): item for item in plan["inherited_chapters"]}
    writer = PdfWriter()
    starts = []
    stripped = 0
    page_offset = 0
    for chapter in plan["cumulative_order"]:
        if chapter in new_by_chapter:
            component = new_by_chapter[chapter]
            pdf = COMPONENTS / f"ch{chapter:03d}-{component['stem']}" / str(component["pdf_filename"])
            title = next(item["title"] for item in plan["new_chapters"] if int(item["chapter"]) == chapter)
        else:
            item = inherited_by_chapter[chapter]
            pdf = ROOT / str(item["pdf"])
            title = item["title"]
        reader = PdfReader(pdf, strict=True)
        starts.append({"chapter": chapter, "title": title, "page_index_zero_based": page_offset, "pages": len(reader.pages), "pdf": identity(pdf)})
        for page in reader.pages:
            annotations = page.get("/Annots", [])
            annotations = annotations.get_object() if hasattr(annotations, "get_object") else annotations
            stripped += len(annotations)
            page.pop(NameObject("/Annots"), None)
            writer.add_page(page)
            page_offset += 1
    parent = writer.add_outline_item("한국어 누적 리더 / Korean Cumulative Reader", 0)
    for item in starts:
        writer.add_outline_item(f"제{item['chapter']}장: {item['title']}", item["page_index_zero_based"], parent=parent)
    writer.add_metadata({
        "/Title": "Stacks Project 한국어 누적 리더 - 21 chapters",
        "/Author": "Interlanguage project",
        "/Subject": "Receipt-bound Korean cumulative integration at frozen Stacks commit a04446e57ec1fbc252a871afcec7752fb2807b14",
        "/Creator": "Deterministic Korean P11 r5 cumulative builder",
        "/Producer": "pypdf",
        "/CreationDate": "D:20260905000000Z",
        "/ModDate": "D:20260905000000Z",
    })
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        writer.write(stream)
    return {"chapter_starts": starts, "pages": page_offset, "source_annotations_stripped": stripped}


def verify_merged(pdf: Path, expected_pages: int, pdftotext: str) -> dict[str, object]:
    reader = PdfReader(pdf, strict=True)
    if reader.is_encrypted or len(reader.pages) != expected_pages:
        raise RuntimeError("cumulative PDF strict open/page gate failed")
    annotations = 0
    boxes = set()
    for page in reader.pages:
        boxes.add(tuple(round(float(value), 3) for value in page.mediabox))
        annotations += len(page.get("/Annots", []))
    if annotations:
        raise RuntimeError("cumulative annotation stripping failed")
    _raw, extraction = extract_text(pdftotext, pdf)
    if extraction["replacement_characters"] or extraction["nul_characters"] or extraction["hangul_syllables"] == 0:
        raise RuntimeError(f"cumulative extraction gate failed: {extraction}")
    if not reader.outline:
        raise RuntimeError("cumulative outline missing")
    return {
        "strict_open": True,
        "encrypted": False,
        "pages": len(reader.pages),
        "uniform_page_box": len(boxes) == 1,
        "page_boxes": [list(item) for item in sorted(boxes)],
        "annotations": annotations,
        "outline_present": True,
        "extraction": extraction,
    }


def main() -> None:
    if BUILD_RECEIPT.exists() or FINAL_PDF.exists() or REPLAY_PDF.exists():
        raise RuntimeError("build outputs already exist; inspect rather than duplicate")
    plan_id = require(PLAN_PATH, *EXPECTED_PLAN)
    preflight_id = require(PREFLIGHT_PATH, *EXPECTED_PREFLIGHT)
    reference_repair_id = require(REFERENCE_REPAIR, *EXPECTED_REFERENCE_REPAIR)
    bibtex_warning_adjudication_id, bibtex_warning_allowances = load_bibtex_warning_adjudication()
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if plan.get("classification") != "PASS_READY_FOR_MUTEX_SERIALIZED_COMPONENT_BUILD" or preflight.get("result") != "PASS_READY_FOR_MUTEX_SERIALIZED_COMPONENT_BUILD":
        raise RuntimeError("preflight state does not authorize build")
    preflight_by_chapter = {int(item["chapter"]): item for item in preflight["new_chapter_replay"]}
    for chapter in plan["new_chapters"]:
        evidence = preflight_by_chapter[int(chapter["chapter"])]
        target = ROOT / str(chapter["target"])
        authority = ROOT / str(chapter["authority"])
        require(target, int(evidence["target"]["bytes"]), str(evidence["target"]["sha256"]))
        require(authority, int(evidence["authority"]["bytes"]), str(evidence["authority"]["sha256"]))
    repair = json.loads(REFERENCE_REPAIR.read_text(encoding="utf-8"))
    if repair.get("result") != "PASS_APPEND_ONLY_REFERENCE_CLOSURE_REPAIR_READY_FOR_NEW_SERIALIZED_ATTEMPT":
        raise RuntimeError("reference-closure repair is not PASS")
    for chapter in plan["new_chapters"]:
        profile = PROFILES / f"ch{int(chapter['chapter']):03d}-{chapter['stem']}"
        if (profile / "ko_preamble.tex").read_text(encoding="utf-8").count(r"\xeCJKsetup{CJKspace=true}") != 1:
            raise RuntimeError(f"Korean CJK-space adapter changed: {profile}")
        if len(list((profile / "xr").glob("*.aux"))) != 117:
            raise RuntimeError(f"AUX universe changed: {profile}")

    tools = {name: shutil.which(name) for name in ("xelatex", "bibtex", "pdftotext")}
    if any(value is None for value in tools.values()):
        raise RuntimeError(f"required build tool unavailable: {tools}")
    resolved = {name: str(path) for name, path in tools.items()}
    tool_ids = {
        "xelatex": tool_identity(resolved["xelatex"], ["--version"]),
        "bibtex": tool_identity(resolved["bibtex"], ["--version"]),
        "pdftotext": tool_identity(resolved["pdftotext"], ["-v"]),
    }
    started = datetime.now(timezone.utc)
    components = []
    try:
        for chapter in plan["new_chapters"]:
            evidence = preflight_by_chapter[int(chapter["chapter"])]
            material = dict(chapter)
            material["target"] = evidence["target"]
            components.append(build_component(
                material,
                resolved,
                bibtex_warning_allowances,
                bibtex_warning_adjudication_id,
            ))
        merge = merge_pdf(plan, components, FINAL_PDF)
        replay_merge = merge_pdf(plan, components, REPLAY_PDF)
        if sha256(FINAL_PDF) != sha256(REPLAY_PDF) or FINAL_PDF.stat().st_size != REPLAY_PDF.stat().st_size:
            raise RuntimeError("deterministic cumulative byte replay failed")
        verification = verify_merged(FINAL_PDF, int(merge["pages"]), resolved["pdftotext"])
        replay_verification = verify_merged(REPLAY_PDF, int(replay_merge["pages"]), resolved["pdftotext"])
        receipt = {
            "schema": "interlanguage.stacks_cjk.ko_p11_component_and_cumulative_build/v1",
            "record_id": "STACKS-CJK-KO-P11-R5-BUILD-20260905",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "started_utc": started.isoformat(),
            "build_plan": plan_id,
            "preflight": preflight_id,
            "reference_closure_repair": reference_repair_id,
            "bibtex_warning_adjudication": bibtex_warning_adjudication_id,
            "tools": tool_ids,
            "components": components,
            "merge": merge,
            "cumulative_pdf": identity(FINAL_PDF),
            "cumulative_verification": verification,
            "deterministic_replay_pdf": identity(REPLAY_PDF),
            "deterministic_replay_verification": replay_verification,
            "byte_identical_replay": True,
            "checks": {
                "nine_manager_owned_component_builds": "PASS",
                "korean_word_spacing": "PASS",
                "zero_unresolved_tex_references_and_citations": "PASS",
                "fonts_embedded": "PASS",
                "twenty_one_chapter_order": "PASS",
                "annotations_stripped_and_outline_present": "PASS",
                "deterministic_cumulative_byte_replay": "PASS",
            },
            "result": "PASS_BUILD_AND_DETERMINISTIC_CUMULATIVE_ASSEMBLY_PENDING_PAGE_COMPLETE_VISUAL_QA",
            "canon_admission": "NOT_YET_ADMITTED_PENDING_PAGE_COMPLETE_VISUAL_QA",
        }
        atomic_json(BUILD_RECEIPT, receipt)
        print(json.dumps({"receipt": identity(BUILD_RECEIPT), "pdf": identity(FINAL_PDF), "pages": verification["pages"], "result": receipt["result"]}, ensure_ascii=False), flush=True)
    except BaseException as exc:
        failure = {
            "schema": "interlanguage.stacks_cjk.ko_p11_component_build_failure/v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "started_utc": started.isoformat(),
            "build_plan": plan_id,
            "preflight": preflight_id,
            "reference_closure_repair": reference_repair_id,
            "bibtex_warning_adjudication": bibtex_warning_adjudication_id,
            "completed_components": [int(item["chapter"]) for item in components],
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "result": "FAIL_CLOSED",
            "resume": "reuse every exact completed component; create a fresh numbered attempt for the first incomplete chapter",
        }
        path = next_failure_path()
        atomic_json(path, failure)
        raise


if __name__ == "__main__":
    main()
