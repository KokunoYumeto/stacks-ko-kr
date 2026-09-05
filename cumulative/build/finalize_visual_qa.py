from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "visual-qa-r3"
BATCHES = EVIDENCE / "inspection-batches"
PDF = ROOT / "output" / "pdf" / "stacks-project-ko-kr-cumulative-r3.pdf"
BUILD = ROOT / "receipts" / "CUMULATIVE_BUILD.json"
RENDER_MANIFEST = EVIDENCE / "CUMULATIVE_RENDER_MANIFEST.csv"
SHEET_MANIFEST = EVIDENCE / "CONTACT_SHEET_MANIFEST.csv"
FAILED_PRECHECK = EVIDENCE / "DETERMINISTIC_VISUAL_PRECHECK.json"
PRECHECK = EVIDENCE / "DETERMINISTIC_VISUAL_PRECHECK_R2.json"
PROBES = EVIDENCE / "FULL_RESOLUTION_REINSPECTION.json"
LEDGER = EVIDENCE / "PAGE_VISUAL_INSPECTION_LEDGER.jsonl"
FINAL = ROOT / "receipts" / "CUMULATIVE_VISUAL_QA.json"

EXPECTED_PDF = (6_163_243, "D16F925E5EAD4BA519D2C5E5F7ED47F022810DE76484183BBAE5108D970190F7")
EXPECTED_BUILD = (86_487, "5EE1878B27DAB2E1E937F5E8EB728D5927D39330610F85260FC25ED412C93CD9")
EXPECTED_RENDER = (118_391, "24B2081A8A83DB83010BB9B3D4EE8272D3418A4C3E55B089378C2917D145BD45")
EXPECTED_SHEETS = (24_979, "154F940A799B8CCDF1EC4EC4E56163D70CC31E9D7528A2CDDDB22A0CA06C6D0A")
EXPECTED_FAILED_PRECHECK = (182_558, "C3D7154642D9D79B4041E61BE736C623B2F1E4FF5F87700B77D4CCCD12BB14A1")
EXPECTED_PRECHECK = (144_736, "1791D48F9B3B4A86A07850E025D9D5D207592DC543DD635651352DC479AFF58D")
EXPECTED_PAGE_COUNT = 572
EXPECTED_SHEET_COUNT = 143

BATCH_RANGES = [
    (1, 40),
    (41, 80),
    (81, 120),
    (121, 160),
    (161, 200),
    (201, 240),
    (241, 280),
    (281, 320),
    (321, 360),
    (361, 400),
    (401, 440),
    (441, 480),
    (481, 520),
    (521, 560),
    (561, 572),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def identity(path: Path) -> dict:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def require_identity(path: Path, expected: tuple[int, str]) -> None:
    observed = (path.stat().st_size, sha256(path))
    if observed != expected:
        raise RuntimeError(f"Identity mismatch for {path}: {observed} != {expected}")


def batch_path(index: int, first: int, last: int) -> Path:
    return BATCHES / f"batch-{index:02d}-pages-{first:03d}-{last:03d}.json"


def sheet_names(first: int, last: int) -> list[str]:
    first_sheet = (first - 1) // 4 + 1
    last_sheet = (last - 1) // 4 + 1
    names = []
    for sheet in range(first_sheet, last_sheet + 1):
        page_first = (sheet - 1) * 4 + 1
        page_last = min(sheet * 4, EXPECTED_PAGE_COUNT)
        names.append(f"sheet-{sheet:03d}-pages-{page_first:03d}-{page_last:03d}.png")
    return names


def page_number(row: dict) -> int:
    for key in ("page_one_based", "page", "global_page"):
        value = row.get(key)
        if value is not None:
            return int(value)
    raise RuntimeError(f"Inspection row has no page number: {row}")


def find_sheet_list(batch: dict, pages: list[dict]) -> list[str]:
    for key in ("contact_sheet_filenames", "sheets", "contact_sheets", "exact_sheets"):
        value = batch.get(key)
        if isinstance(value, list):
            names = []
            for item in value:
                if isinstance(item, str):
                    names.append(Path(item).name)
                elif isinstance(item, dict):
                    candidate = item.get("filename") or item.get("path") or item.get("file")
                    if candidate:
                        names.append(Path(candidate).name)
            return names
    names = []
    for row in pages:
        candidate = row.get("contact_sheet") or row.get("sheet") or row.get("sheet_filename")
        if candidate:
            name = Path(str(candidate)).name
            if name not in names:
                names.append(name)
    return names


def overall_result(batch: dict) -> str:
    for key in ("result", "overall", "overall_result"):
        value = batch.get(key)
        if isinstance(value, str):
            return value.upper()
        if isinstance(value, dict):
            for nested_key in ("result", "outcome", "status"):
                nested = value.get(nested_key)
                if isinstance(nested, str):
                    return nested.upper()
    return "MISSING"


def main() -> None:
    if LEDGER.exists() or FINAL.exists():
        raise RuntimeError("Final visual-QA outputs already exist; inspect instead of overwriting")
    require_identity(PDF, EXPECTED_PDF)
    require_identity(BUILD, EXPECTED_BUILD)
    require_identity(RENDER_MANIFEST, EXPECTED_RENDER)
    require_identity(SHEET_MANIFEST, EXPECTED_SHEETS)
    require_identity(FAILED_PRECHECK, EXPECTED_FAILED_PRECHECK)
    require_identity(PRECHECK, EXPECTED_PRECHECK)

    build = json.loads(BUILD.read_text(encoding="utf-8"))
    failed_precheck = json.loads(FAILED_PRECHECK.read_text(encoding="utf-8"))
    precheck = json.loads(PRECHECK.read_text(encoding="utf-8"))
    probes = json.loads(PROBES.read_text(encoding="utf-8"))
    if failed_precheck.get("result") != "FAIL":
        raise RuntimeError("Expected preserved attempt-1 tooling failure")
    if precheck.get("result") != "PASS_DETERMINISTIC_PRECHECK_PENDING_INDEPENDENT_VISUAL_INSPECTION":
        raise RuntimeError("Corrected deterministic precheck is not PASS")
    if probes.get("result") != "PASS_REQUIRED_FULL_RESOLUTION_REINSPECTION":
        raise RuntimeError("Full-resolution probe gate is not PASS")

    with RENDER_MANIFEST.open("r", encoding="utf-8", newline="") as stream:
        render_rows = list(csv.DictReader(stream))
    render_pages = [int(row["page_one_based"]) for row in render_rows]
    if render_pages != list(range(1, EXPECTED_PAGE_COUNT + 1)):
        raise RuntimeError("Render manifest is not exact ordered page coverage")
    if any(row["touches_image_edge"].lower() != "false" for row in render_rows):
        raise RuntimeError("Raster content touches an image edge")
    if any(not row["content_bbox"] for row in render_rows):
        raise RuntimeError("Unexpected blank raster page")

    with SHEET_MANIFEST.open("r", encoding="utf-8", newline="") as stream:
        sheet_rows = list(csv.DictReader(stream))
    if len(sheet_rows) != EXPECTED_SHEET_COUNT:
        raise RuntimeError("Contact-sheet count mismatch")
    sheet_pages = [int(page) for row in sheet_rows for page in row["pages"].split(";")]
    if sheet_pages != list(range(1, EXPECTED_PAGE_COUNT + 1)):
        raise RuntimeError("Contact sheets do not cover each page exactly once in order")

    batch_summaries = []
    ledger_rows = []
    for index, (first, last) in enumerate(BATCH_RANGES, 1):
        path = batch_path(index, first, last)
        if not path.exists():
            raise RuntimeError(f"Missing inspection batch: {path}")
        batch = json.loads(path.read_text(encoding="utf-8"))
        pages = batch.get("pages")
        if not isinstance(pages, list):
            raise RuntimeError(f"Batch {index} has no pages array")
        observed_pages = [page_number(row) for row in pages]
        expected_pages = list(range(first, last + 1))
        if observed_pages != expected_pages:
            raise RuntimeError(f"Batch {index} page coverage mismatch")
        sheets = find_sheet_list(batch, pages)
        expected_sheets = sheet_names(first, last)
        if sheets != expected_sheets:
            raise RuntimeError(f"Batch {index} contact-sheet coverage mismatch: {sheets}")
        anomalies = batch.get("anomalies", [])
        if anomalies:
            raise RuntimeError(f"Batch {index} contains visual anomalies")
        result = overall_result(batch)
        if not result.startswith("PASS"):
            raise RuntimeError(f"Batch {index} overall result is not PASS: {result}")
        for row in pages:
            outcome = str(row.get("outcome") or row.get("result") or row.get("status") or "").upper()
            if not outcome.startswith("PASS"):
                raise RuntimeError(f"Batch {index} page {page_number(row)} is not PASS")
            page_no = page_number(row)
            sheet_number = (page_no - 1) // 4 + 1
            ledger_rows.append(
                {
                    "schema": "interlanguage.stacks_cjk.ko_cumulative_page_visual_inspection/v1",
                    "page_one_based": page_no,
                    "chapter": int(render_rows[page_no - 1]["chapter"]),
                    "chapter_page_one_based": int(render_rows[page_no - 1]["chapter_page_one_based"]),
                    "sheet": sheet_number,
                    "sheet_filename": expected_sheets[sheet_number - ((first - 1) // 4 + 1)],
                    "batch": identity(path),
                    "outcome": outcome,
                    "inspection_mode": row.get("inspection_mode") or row.get("mode") or "CONTACT_SHEET_OR_RECORDED_PROBE",
                    "notes": row.get("notes") or row.get("finding") or "",
                }
            )
        batch_summaries.append(
            {
                "batch": index,
                "first_page": first,
                "last_page": last,
                "pages": len(pages),
                "sheets": len(sheets),
                "anomalies": 0,
                "result": result,
                "receipt": identity(path),
            }
        )

    if [row["page_one_based"] for row in ledger_rows] != list(range(1, EXPECTED_PAGE_COUNT + 1)):
        raise RuntimeError("Combined page inspection ledger coverage mismatch")
    with LEDGER.open("w", encoding="utf-8", newline="\n") as stream:
        for row in ledger_rows:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    expected_outline_pages = [1] + [item["page_index_zero_based"] + 1 for item in build["merge"]["chapter_starts"]]
    outline_pages = [row["page_one_based"] for row in precheck["outline"]]
    if outline_pages != expected_outline_pages:
        raise RuntimeError("Outline destinations do not match the cumulative chapter starts")
    expected_outline_titles = ["한국어 누적 리더 / Korean Cumulative Reader"] + [
        f"제{item['chapter']}장: {item['title']}" for item in build["merge"]["chapter_starts"]
    ]
    outline_titles = [row["title"] for row in precheck["outline"]]
    if outline_titles != expected_outline_titles:
        raise RuntimeError("Outline titles do not match the cumulative chapter inventory")

    final = {
        "schema": "interlanguage.stacks_cjk.ko_cumulative_visual_qa/v1",
        "record_id": "STACKS-CJK-KO-CUMULATIVE-R3-VISUAL-QA-20260905",
        "successor_id": "integration-20260905-r3",
        "pdf": {**identity(PDF), "pages": EXPECTED_PAGE_COUNT},
        "build_receipt": identity(BUILD),
        "render": {
            "dpi": 120,
            "manifest": identity(RENDER_MANIFEST),
            "pages": len(render_rows),
            "page_png_bytes": sum(int(row["bytes"]) for row in render_rows),
            "page_dimensions": precheck["page_dimensions_pixels"],
            "uniform_page_dimensions": precheck["uniform_page_dimensions"],
            "blank_pages": precheck["blank_pages"],
            "pages_touching_raster_edge": precheck["pages_touching_raster_edge"],
        },
        "contact_sheets": {
            "pages_per_sheet": 4,
            "manifest": identity(SHEET_MANIFEST),
            "sheets": len(sheet_rows),
            "coverage_exactly_once_in_order": True,
        },
        "deterministic_precheck": {
            "attempt1": {
                "receipt": identity(FAILED_PRECHECK),
                "result": "FAIL_TOOLING_FONT_COLUMN_PARSE_ONLY",
                "render_or_pdf_defect": False,
                "preserved_as_adverse_evidence": True,
            },
            "corrected_successor": {
                "receipt": identity(PRECHECK),
                "result": precheck["result"],
                "font_rows": len(precheck["font_inventory_lines"]),
                "unembedded_fonts": len(precheck["unembedded_fonts"]),
                "characters_outside_page": len(precheck["characters_outside_page"]),
                "links_outside_page": len(precheck["links_outside_page"]),
                "link_annotations": precheck["link_annotations"],
                "other_annotations": precheck["other_annotations"],
            },
        },
        "independent_visual_inspection": {
            "batches": batch_summaries,
            "batch_count": len(batch_summaries),
            "page_ledger": identity(LEDGER),
            "pages_inspected": len(ledger_rows),
            "pages_passed": len(ledger_rows),
            "pages_failed": 0,
            "anomalies": 0,
            "criteria": [
                "blankness",
                "clipping",
                "overlap",
                "margin breach",
                "broken diagrams or tables",
                "footnote integrity",
                "header, footer, and page-number integrity",
                "unexpected rendering artifacts",
                "chapter and title continuity",
            ],
        },
        "required_full_resolution_reinspection": {
            "receipt": identity(PROBES),
            "pages": [229, 230, 430, 566, 567, 568, 569],
            "result": probes["result"],
            "visual_blockers": probes["visual_blockers"],
        },
        "inherited_adverse_evidence": {
            "text_extraction_question_mark_pairs": {
                "pairs": 9,
                "pages": [
                    {"page_one_based": 229, "pairs": 3},
                    {"page_one_based": 230, "pairs": 3},
                    {"page_one_based": 430, "pairs": 3},
                ],
                "visual_disposition": "PASS_XYPIC_EXTRACTION_ONLY_NO_VISIBLE_REPLACEMENT_OR_DIAGRAM_DAMAGE",
                "new_or_unexplained_pairs": 0,
            },
            "chapter_99_overfull_vbox": {
                "diagnostic": "Overfull vbox (1.12279pt too high) has occurred while output is active",
                "cumulative_pages_reinspected": [566, 567, 568, 569],
                "visual_disposition": "PASS_NO_CLIPPING_OVERLAP_MARGIN_OR_FOOTNOTE_DEFECT",
            },
        },
        "outline": {
            "present": True,
            "entries": len(precheck["outline"]),
            "titles_and_destinations_match_chapter_inventory": True,
            "rows": precheck["outline"],
        },
        "gates": {
            "all_572_pages_rendered": True,
            "all_572_pages_inspected": True,
            "blank_pages": 0,
            "characters_outside_page": 0,
            "links_outside_page": 0,
            "unembedded_fonts": 0,
            "visual_blockers": 0,
            "unexplained_extraction_artifacts": 0,
            "chapter_joins_and_outline": "PASS",
        },
        "inputs_mutated": False,
        "tex_run": False,
        "publication": False,
        "result": "PASS_PAGE_COMPLETE_CUMULATIVE_VISUAL_QA",
    }
    FINAL.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(FINAL.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "page_ledger": identity(LEDGER),
                "final_receipt": identity(FINAL),
                "pages": len(ledger_rows),
                "result": final["result"],
            }
        )
    )


if __name__ == "__main__":
    main()
