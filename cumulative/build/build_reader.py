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


ROOT = Path(__file__).resolve().parents[2]
CUMULATIVE = ROOT / "cumulative"
SUPPORT = CUMULATIVE / "support"
DEPS = SUPPORT / "dependencies"
PROFILES = SUPPORT / "profiles"
COMPONENTS = CUMULATIVE / "evidence" / "components"
OUTPUT = CUMULATIVE / "output" / "pdf"
RECEIPTS = CUMULATIVE / "receipts"
SUPPORT_RECEIPT = RECEIPTS / "SUPPORT_CLOSURE.json"
CHAPTER_INVENTORY = SUPPORT / "CHAPTERS.json"
BUILD_RECEIPT = RECEIPTS / "CUMULATIVE_BUILD.json"
FAILURE_RECEIPT = RECEIPTS / "CUMULATIVE_BUILD_FAILURE.json"
CH99_VBOX_ADJUDICATION = RECEIPTS / "attempts" / "attempt5" / "CH099_VBOX_ADJUDICATION.json"
FINAL_VISUAL_QA = RECEIPTS / "CUMULATIVE_VISUAL_QA.json"
FINAL_PDF = OUTPUT / "stacks-project-ko-kr-cumulative-r3.pdf"
REPLAY_PDF = OUTPUT / ".stacks-project-ko-kr-cumulative-r3.replay.pdf"

EXPECTED_SUPPORT_RECEIPT = (312494, "83EAF1D0300B3760908BBC737D1F48A89EB5516CB0F5427BD9C3C990C4067DBC")
EXPECTED_CHAPTER_INVENTORY = (7000, "9943F6DF5EDBF9FC4274F4C11E11E9854BEEC4AEB3C87518D6C19FB08069852F")
EXPECTED_DEPS = {
    "my.bib": (210197, "AE2BA8729BECFD5BAA4FDC9448EB5332ED1EC727BD41CAF0937EBA02E367521E"),
    "stacks-project.cls": (60186, "DBACE0CB163B1B24F2816D89C547A3D487D51D59EDE0303FAD079E8AE3F93254"),
    "hyperref.cfg": (124, "50B882C8244281806C3245AFF3B70FB1577B01A405246896B2AC96A90C9C8307"),
    "tags/tags": (969923, "098F77CCE75F8359F1EACB22B7AA0088099B09E5B3FFCAD2DE513CBD1A8A9F1C"),
}
EXPECTED_CH99_VBOX_ADJUDICATION = (3299, "AFB0D4E03C800F5DDDCF3D31ABECF719DA7EAFD9EE4EF1C764413EC737CD4D80")
EXPECTED_FINAL_VISUAL_QA = (13024, "2835BF0377C345B8343772D70E8EBA36D6D65C498EB7D6753D6B8D1BA08B9E4E")
EXPECTED_CH99_VBOX_PROBES = {
    "cumulative/evidence/attempts/attempt5/ch099-vbox-probe/page-42.png": (461257, "6926872FE3FD2194C67FDBA36E7556BF717899F6E3B78EAC6AB7406B76AAE1F6"),
    "cumulative/evidence/attempts/attempt5/ch099-vbox-probe/page-43.png": (593463, "71C577B28AE592B37C9B02FD23DE5A1132960697C62F8AED656A75EAB7FBE662"),
    "cumulative/evidence/attempts/attempt5/ch099-vbox-probe/page-44.png": (545345, "556499A10304A42BCB14D1AF2D13ADCF51565B26B6D852A04A7A01537B2BB07F"),
    "cumulative/evidence/attempts/attempt5/ch099-vbox-probe/page-45.png": (491356, "0EDE625CC65C1B54AB8D1AB8FC1F6C5513625220E74036B24A70B867DCEFA029"),
}
CANONICAL_ORDER = [17, 60, 61, 62, 63, 64, 65, 66, 67, 68, 71, 99]
SOURCE_DATE_EPOCH = "1788562238"
CH64_INHERITED_XYPIC_EXTRACTION = {
    "utf8_bytes": 106814,
    "sha256": "2EBCB37CC8CF0F984084F28E9A7C78C1943EC64D32E08E06A441F006289BB79F",
    "page_form_feeds": 40,
    "hangul_syllables": 19475,
    "replacement_characters": 0,
    "nul_characters": 0,
    "question_mark_pairs": 6,
    "question_mark_pair_pages": [
        {"page_one_based": 2, "pairs": 3},
        {"page_one_based": 3, "pairs": 3},
    ],
}
CH67_INHERITED_XYPIC_EXTRACTION = {
    "utf8_bytes": 328209,
    "sha256": "7CC0BE0FD888A504426EDDF1CCDD814F0AFF3FEE1A5AAC03B5B6FC497ACEFB44",
    "page_form_feeds": 95,
    "hangul_syllables": 69958,
    "replacement_characters": 0,
    "nul_characters": 0,
    "question_mark_pairs": 3,
    "question_mark_pair_pages": [
        {"page_one_based": 86, "pairs": 3},
    ],
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def identity(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": sha256_bytes(data)}


def require_identity(path: Path, size: int, sha: str) -> dict:
    got = identity(path)
    if got["bytes"] != size or got["sha256"] != sha:
        raise RuntimeError(f"identity mismatch: {path}")
    return got


def tool_identity(path: str, version_args: list[str]) -> dict:
    done = subprocess.run([path, *version_args], check=True, capture_output=True, text=True, errors="replace")
    lines = (done.stdout + done.stderr).splitlines()
    return {"path": Path(path).as_posix(), "version": next((line for line in lines if line.strip()), "")}


def count_log_flags(text: str) -> dict:
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


def extract_text(pdftotext: str, pdf: Path) -> tuple[str, dict]:
    done = subprocess.run([pdftotext, "-enc", "UTF-8", str(pdf), "-"], check=True, capture_output=True)
    text = done.stdout.decode("utf-8", errors="strict")
    question_mark_pair_pages = [
        {"page_one_based": index, "pairs": page.count("??")}
        for index, page in enumerate(text.split("\f"), 1)
        if page.count("??")
    ]
    return text, {
        "utf8_bytes": len(done.stdout),
        "sha256": sha256_bytes(done.stdout),
        "page_form_feeds": text.count("\f"),
        "hangul_syllables": len(re.findall(r"[가-힣]", text)),
        "replacement_characters": text.count("\ufffd"),
        "nul_characters": text.count("\x00"),
        "question_mark_pairs": text.count("??"),
        "question_mark_pair_pages": question_mark_pair_pages,
    }


def build_component(chapter: dict, engines: dict[str, str], pdftotext: str) -> dict:
    number = chapter["chapter"]
    stem = chapter["stem"]
    job = f"ch{number:03d}-{stem}"
    target = ROOT / chapter["target"]["path"]
    source = ROOT / chapter["source"]["path"]
    profile = PROFILES / chapter["profile"]
    out = COMPONENTS / job
    pass_specs = [(index, kind, out / f"pass-{index}-{kind}.console.log") for index, kind in enumerate(("xelatex", "bibtex", "xelatex", "xelatex", "xelatex"), 1)]
    completed_outputs = [out / f"{job}{suffix}" for suffix in (".log", ".pdf", ".bbl", ".blg", ".aux")]
    reuse_completed_passes = out.exists() and all(path.is_file() for _, _, path in pass_specs) and all(path.is_file() for path in completed_outputs)
    if out.exists() and any(out.iterdir()) and not reuse_completed_passes:
        raise RuntimeError(f"incomplete component output already exists: {out}")
    out.mkdir(parents=True, exist_ok=True)

    support_files = [profile / "preamble.tex", profile / "ko_preamble.tex", profile / "chapters.tex", profile / "ko_chapters.tex", profile / "xr-map.tsv"]
    for path in support_files:
        if not path.is_file():
            raise RuntimeError(f"missing support file: {path}")
    aux_files = sorted((profile / "xr").glob("*.aux"))
    if len(aux_files) != 117:
        raise RuntimeError(f"Chapter {number} AUX universe incomplete: {len(aux_files)}")

    env = os.environ.copy()
    env["TEXINPUTS"] = f"{profile};{profile / 'xr'};{DEPS};"
    env["BIBINPUTS"] = f"{DEPS};"
    env["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    env["FORCE_SOURCE_DATE"] = "1"
    env["TZ"] = "UTC"
    env["PYTHONHASHSEED"] = "0"
    passes = []
    for pass_number, kind, console in pass_specs:
        if reuse_completed_passes:
            passes.append({
                "pass": pass_number, "tool": kind, "exit_code": 0, "console": identity(console),
                "resume_disposition": "reused_exact_completed_pass_from_fail_closed_prior_attempt",
            })
            print(json.dumps({"chapter": number, "pass": pass_number, "tool": kind, "reused": True}), flush=True)
            continue
        command = [engines[kind], job] if kind == "bibtex" else [
            engines[kind], "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error",
            "-file-line-error", f"-jobname={job}", str(target),
        ]
        started = datetime.now(timezone.utc)
        with console.open("wb") as stream:
            done = subprocess.run(command, cwd=out, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=900)
        ended = datetime.now(timezone.utc)
        passes.append({
            "pass": pass_number, "tool": kind, "exit_code": done.returncode,
            "started_utc": started.isoformat(), "ended_utc": ended.isoformat(), "console": identity(console),
        })
        print(json.dumps({"chapter": number, "pass": pass_number, "tool": kind, "exit_code": done.returncode}), flush=True)
        if done.returncode != 0:
            raise RuntimeError(f"Chapter {number} pass {pass_number} {kind} failed; see {console}")

    tex_log = out / f"{job}.log"
    pdf = out / f"{job}.pdf"
    bbl = out / f"{job}.bbl"
    blg = out / f"{job}.blg"
    for required in (tex_log, pdf, bbl, blg):
        if not required.is_file():
            raise RuntimeError(f"Chapter {number} missing build output: {required}")
    tex_log_text = tex_log.read_text(encoding="utf-8", errors="replace")
    flags = count_log_flags(tex_log_text)
    overfull_vbox_lines = re.findall(r"^Overfull \\vbox.*$", tex_log_text, re.M)
    disallowed = [
        "fatal_errors", "missing_glyphs", "undefined_reference_warnings",
        "undefined_reference_summaries", "undefined_citation_warnings", "undefined_citation_summaries",
        "navigation_reference_warnings", "missing_external_aux", "rerun_requests", "duplicate_destinations",
        "multiply_defined_labels",
    ]
    if any(flags[name] for name in disallowed):
        raise RuntimeError(f"Chapter {number} final log gate failed: {flags}")
    layout_warning_exception = None
    if flags["overfull_vboxes"]:
        expected_warning = "Overfull \\vbox (1.12279pt too high) has occurred while \\output is active []"
        if number != 99 or overfull_vbox_lines != [expected_warning]:
            raise RuntimeError(f"Chapter {number} final vertical-box gate failed: {overfull_vbox_lines}")
        adjudication = require_identity(CH99_VBOX_ADJUDICATION, *EXPECTED_CH99_VBOX_ADJUDICATION)
        final_visual_qa = require_identity(FINAL_VISUAL_QA, *EXPECTED_FINAL_VISUAL_QA)
        layout_warning_exception = {
            "classification": "EXACT_PROFILE_LOCAL_NONBLOCKING_VBOX_WARNING",
            "warning": expected_warning,
            "count": 1,
            "adjudication": adjudication,
            "page_complete_visual_qa_receipt": final_visual_qa,
            "new_or_unreviewed_overfull_vboxes": 0,
            "required_cumulative_page_complete_visual_qa": True,
        }
    blg_text = blg.read_text(encoding="utf-8", errors="replace")
    bibtex_warning_lines = re.findall(r"^Warning--.*$", blg_text, re.M)
    allowed_bibtex_warning_lines = {
        "Warning--missing pages in EGA",
        "Warning--missing pages in lieblich_remarks",
    }
    unexpected_bibtex_warnings = [line for line in bibtex_warning_lines if line not in allowed_bibtex_warning_lines]
    if unexpected_bibtex_warnings:
        raise RuntimeError(f"Chapter {number} unexpected BibTeX warnings: {unexpected_bibtex_warnings}")

    reader = PdfReader(pdf, strict=True)
    if reader.is_encrypted or not reader.pages:
        raise RuntimeError(f"Chapter {number} PDF open/page gate failed")
    extracted_text, extraction = extract_text(pdftotext, pdf)
    if extraction["replacement_characters"] or extraction["nul_characters"] or extraction["hangul_syllables"] == 0:
        raise RuntimeError(f"Chapter {number} extraction gate failed: {extraction}")
    inherited_extraction_exception = None
    if number == 64:
        if extraction != CH64_INHERITED_XYPIC_EXTRACTION:
            raise RuntimeError(f"Chapter 64 inherited Xy-pic extraction identity changed: {extraction}")
        inherited_extraction_exception = {
            "classification": "EXACT_INHERITED_XYPIC_DIAGRAM_TEXT_EXTRACTION",
            "scope": "chapter 64 pages 2-3 only",
            "new_or_unexplained_question_mark_pairs": 0,
            "prior_admitted_component_pdf_sha256": "4D59525DF4D5158D19463A1FC6EBFD2FBE38F5D8184777C3EFE960B0E8515276",
            "prior_page_complete_visual_qa_sha256": "416FC781E42737CBCBAF0BF589360D298A8BC94E279459409AD38ADD52C5BBDE",
            "required_cumulative_visual_reinspection": True,
        }
    elif number == 67:
        if extraction != CH67_INHERITED_XYPIC_EXTRACTION:
            raise RuntimeError(f"Chapter 67 inherited Xy-pic extraction identity changed: {extraction}")
        inherited_extraction_exception = {
            "classification": "EXACT_INHERITED_XYPIC_DIAGRAM_TEXT_EXTRACTION",
            "scope": "chapter 67 page 86 only",
            "new_or_unexplained_question_mark_pairs": 0,
            "prior_admitted_component_pdf_sha256": "AB68EFC697F00E0D65D6497D0ADBDF1A92ED1474CC2EB9DA39423921A7AAAA11",
            "prior_page_complete_visual_qa_sha256": "29D683EC7C972BC7D6081F588D63DFF19A18703E52671037353F106D14C33C30",
            "required_cumulative_visual_reinspection": True,
        }
    elif extraction["question_mark_pairs"]:
        raise RuntimeError(f"Chapter {number} extraction gate failed: {extraction}")

    receipt = {
        "schema": "interlanguage.stacks_cjk.ko_cumulative_component_build/v1",
        "record_id": f"STACKS-CJK-KO-R3-B{number:06d}",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "chapter": number, "part": chapter["part"], "stem": stem, "title": chapter["title"],
        "target": identity(target), "source": identity(source),
        "support_profile": chapter["profile"],
        "support_files": [identity(path) for path in support_files],
        "aux_files": len(aux_files),
        "passes": passes,
        "tex_log": identity(tex_log), "bbl": identity(bbl), "blg": identity(blg),
        "log_flags": flags,
        "overfull_vbox_lines": overfull_vbox_lines,
        "layout_warning_exception": layout_warning_exception,
        "bibtex_warning_lines": bibtex_warning_lines,
        "bibtex_warnings_all_known_immutable_metadata_omissions": not unexpected_bibtex_warnings,
        "pdf": {**identity(pdf), "pages": len(reader.pages)},
        "extraction": extraction,
        "inherited_extraction_exception": inherited_extraction_exception,
        "result": "PASS_COMPONENT_BUILD_ZERO_UNRESOLVED_REFS_AND_ZERO_UNEXPLAINED_QUESTION_PAIRS",
    }
    receipt_path = out / "COMPONENT_BUILD.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["receipt"] = identity(receipt_path)
    del extracted_text
    return receipt


def merge_reader(chapters: list[dict], components: list[dict], output: Path) -> dict:
    writer = PdfWriter()
    starts = []
    stripped_annotations = 0
    page_offset = 0
    for chapter, component in zip(chapters, components, strict=True):
        pdf = ROOT / component["pdf"]["path"]
        reader = PdfReader(pdf, strict=True)
        starts.append({"chapter": chapter["chapter"], "title": chapter["title"], "page_index_zero_based": page_offset})
        for page in reader.pages:
            annotations = page.get("/Annots", [])
            resolved_annotations = annotations.get_object() if hasattr(annotations, "get_object") else annotations
            stripped_annotations += len(resolved_annotations)
            page.pop(NameObject("/Annots"), None)
            writer.add_page(page)
            page_offset += 1

    parent = writer.add_outline_item("한국어 누적 리더 / Korean Cumulative Reader", 0)
    for item in starts:
        writer.add_outline_item(f"제{item['chapter']}장: {item['title']}", item["page_index_zero_based"], parent=parent)
    writer.add_metadata({
        "/Title": "Stacks Project 한국어 누적 리더 - Chapters 17, 60-68, 71, 99",
        "/Author": "Interlanguage project",
        "/Subject": "Receipt-bound Korean cumulative integration at frozen Stacks commit a04446e57ec1fbc252a871afcec7752fb2807b14",
        "/Creator": "Deterministic r3 cumulative builder",
        "/Producer": "pypdf",
        "/CreationDate": "D:20260905000000Z",
        "/ModDate": "D:20260905000000Z",
    })
    with output.open("wb") as stream:
        writer.write(stream)
    return {"chapter_starts": starts, "source_annotations_stripped": stripped_annotations, "pages": page_offset}


def verify_merged(pdf: Path, expected_pages: int, pdftotext: str, expected_pair_pages: list[dict]) -> dict:
    reader = PdfReader(pdf, strict=True)
    if reader.is_encrypted or len(reader.pages) != expected_pages:
        raise RuntimeError("merged PDF page/open gate failed")
    page_boxes = set()
    link_annotations = 0
    other_annotations = 0
    for page in reader.pages:
        page_boxes.add(tuple(round(float(value), 3) for value in page.mediabox))
        for ref in page.get("/Annots", []):
            annotation = ref.get_object()
            if annotation.get("/Subtype") == "/Link":
                link_annotations += 1
            else:
                other_annotations += 1
    if link_annotations or other_annotations:
        raise RuntimeError(f"merged annotation stripping failed: links={link_annotations}, other={other_annotations}")
    _, extraction = extract_text(pdftotext, pdf)
    if extraction["replacement_characters"] or extraction["nul_characters"] or extraction["hangul_syllables"] == 0:
        raise RuntimeError(f"merged extraction gate failed: {extraction}")
    if extraction["question_mark_pairs"] != 9 or extraction["question_mark_pair_pages"] != expected_pair_pages:
        raise RuntimeError(f"merged extraction has new, missing, or displaced question-mark pairs: {extraction}")
    outline = reader.outline
    if not outline:
        raise RuntimeError("merged PDF outline missing")
    return {
        "strict_open": True,
        "encrypted": False,
        "pages": len(reader.pages),
        "page_boxes": [list(values) for values in sorted(page_boxes)],
        "uniform_page_box": len(page_boxes) == 1,
        "link_annotations": link_annotations,
        "other_annotations": other_annotations,
        "unresolved_link_targets": 0,
        "outline_present": True,
        "outline_top_level_items": len(outline),
        "extraction": extraction,
        "inherited_extraction_exception": {
            "classification": "EXACT_INHERITED_CHAPTER_64_XYPIC_DIAGRAM_TEXT_EXTRACTION",
            "expected_question_mark_pairs": 9,
            "expected_pair_pages": expected_pair_pages,
            "new_or_unexplained_question_mark_pairs": 0,
            "required_cumulative_visual_reinspection": True,
        },
    }


def main() -> None:
    if BUILD_RECEIPT.exists() or FINAL_PDF.exists() or REPLAY_PDF.exists():
        raise RuntimeError("cumulative build output already exists; inspect instead of duplicating")
    support_identity = require_identity(SUPPORT_RECEIPT, *EXPECTED_SUPPORT_RECEIPT)
    support_receipt = json.loads(SUPPORT_RECEIPT.read_text(encoding="utf-8"))
    if not support_receipt.get("build_authorized") or support_receipt.get("result") != "PASS_COMPLETE_EXACT_SUPPORT_TREE_AND_AUX_CLOSURE":
        raise RuntimeError("support closure gate not satisfied")
    chapter_inventory_identity = require_identity(CHAPTER_INVENTORY, *EXPECTED_CHAPTER_INVENTORY)
    inventory = json.loads(CHAPTER_INVENTORY.read_text(encoding="utf-8"))
    chapters = inventory["chapters"]
    if [item["chapter"] for item in chapters] != CANONICAL_ORDER:
        raise RuntimeError("canonical chapter order mismatch")
    dependency_identities = [require_identity(DEPS / rel, *expected) for rel, expected in EXPECTED_DEPS.items()]

    tools = {name: shutil.which(name) for name in ("xelatex", "bibtex", "pdftotext")}
    if not all(tools.values()):
        raise RuntimeError(f"missing required build tools: {tools}")
    tool_identities = {
        "xelatex": tool_identity(tools["xelatex"], ["--version"]),
        "bibtex": tool_identity(tools["bibtex"], ["--version"]),
        "pdftotext": tool_identity(tools["pdftotext"], ["-v"]),
    }

    if any(OUTPUT.iterdir()):
        raise RuntimeError("PDF output directory is not empty")
    components = []
    for chapter in chapters:
        components.append(build_component(chapter, {"xelatex": tools["xelatex"], "bibtex": tools["bibtex"]}, tools["pdftotext"]))

    expected_pages = sum(item["pdf"]["pages"] for item in components)
    expected_pair_pages = []
    for chapter_number, relative_pair_pages in (
        (64, CH64_INHERITED_XYPIC_EXTRACTION["question_mark_pair_pages"]),
        (67, CH67_INHERITED_XYPIC_EXTRACTION["question_mark_pair_pages"]),
    ):
        chapter_index = next(index for index, chapter in enumerate(chapters) if chapter["chapter"] == chapter_number)
        start_page_one_based = 1 + sum(item["pdf"]["pages"] for item in components[:chapter_index])
        expected_pair_pages.extend({
            "page_one_based": start_page_one_based + pair_page["page_one_based"] - 1,
            "pairs": pair_page["pairs"],
        } for pair_page in relative_pair_pages)
    merge_a = merge_reader(chapters, components, FINAL_PDF)
    merge_b = merge_reader(chapters, components, REPLAY_PDF)
    final_identity = identity(FINAL_PDF)
    replay_identity = identity(REPLAY_PDF)
    if final_identity["bytes"] != replay_identity["bytes"] or final_identity["sha256"] != replay_identity["sha256"]:
        raise RuntimeError("deterministic merged-PDF replay mismatch")
    REPLAY_PDF.unlink()
    mechanics = verify_merged(FINAL_PDF, expected_pages, tools["pdftotext"], expected_pair_pages)

    receipt = {
        "schema": "interlanguage.stacks_cjk.ko_cumulative_build/v1",
        "record_id": "STACKS-CJK-KO-CUMULATIVE-R3-BUILD-20260905",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "successor_id": "integration-20260905-r3",
        "canonical_order": CANONICAL_ORDER,
        "support_gate": support_identity,
        "chapter_inventory": chapter_inventory_identity,
        "dependencies": dependency_identities,
        "tools": tool_identities,
        "source_date_epoch": SOURCE_DATE_EPOCH,
        "components": components,
        "component_count": len(components),
        "component_pages": expected_pages,
        "merge": merge_a,
        "deterministic_merge_replay": {
            "runs": 2,
            "byte_identical": True,
            "bytes": final_identity["bytes"],
            "sha256": final_identity["sha256"],
        },
        "reader_pdf": {**final_identity, **mechanics},
        "gates": {
            "ordinary_reference_warnings": 0,
            "navigation_reference_warnings": 0,
            "extracted_question_mark_pairs": 9,
            "new_or_unexplained_question_mark_pairs": 0,
            "inherited_question_mark_pair_scope": expected_pair_pages,
            "missing_glyphs": 0,
            "undefined_citations": 0,
            "malformed_or_unresolved_links": 0,
            "canonical_outline": "PASS",
            "source_math_replay": "PASS_VIA_SUPPORT_RECEIPT",
        },
        "visual_qa": "PENDING_PAGE_COMPLETE_RENDER",
        "publication": False,
        "result": "PASS_CUMULATIVE_BUILD_PENDING_PAGE_COMPLETE_VISUAL_QA",
    }
    BUILD_RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(BUILD_RECEIPT.read_text(encoding="utf-8"))
    print(json.dumps({
        "result": receipt["result"], "receipt": identity(BUILD_RECEIPT), "pdf": final_identity,
        "chapters": len(components), "pages": expected_pages,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        failure = {
            "schema": "interlanguage.stacks_cjk.ko_cumulative_build_failure/v1",
            "record_id": "STACKS-CJK-KO-CUMULATIVE-R3-BUILD-FAILURE-20260905",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "next_executable_action": "Inspect the exact retained component/pass evidence, repair only the deterministic r3 build route, and resume without touching r2 or producer trees.",
            "result": "FAIL_CLOSED_NO_PUBLICATION",
        }
        FAILURE_RECEIPT.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"result": failure["result"], "failure_receipt": identity(FAILURE_RECEIPT), "error": str(exc)}, ensure_ascii=False), flush=True)
        raise
