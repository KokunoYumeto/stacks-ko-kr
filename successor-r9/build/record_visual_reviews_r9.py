from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VISUAL = ROOT / "evidence" / "visual-qa-r9"
INITIAL_LEDGER = VISUAL / "FRESH_PAGE_REVIEW_LEDGER.jsonl"
REVIEWED_LEDGER = VISUAL / "FRESH_PAGE_REVIEW_LEDGER_R1.jsonl"
PAGE_MANIFEST = VISUAL / "PAGE_RENDER_MANIFEST.json"
SHEET_MANIFEST = VISUAL / "FRESH_REVIEW_CONTACT_SHEET_MANIFEST.json"
PRECHECK_R1 = VISUAL / "DETERMINISTIC_VISUAL_DELTA_PRECHECK_R1.json"
AGENT_001 = VISUAL / "FRESH_VISUAL_INSPECTION_RECEIPT_AGENT_001.json"
AGENT_002 = VISUAL / "FRESH_VISUAL_INSPECTION_RECEIPT_AGENT_002.json"
TRANSITION = VISUAL / "FRESH_PAGE_REVIEW_TRANSITION_001.json"

EXPECTED_INITIAL = {
    "bytes": 168604,
    "sha256": "7CF8D65B11372DB236464588406BD0C83BBD34569A7E44F13F21AA47F42D47D9",
}
EXPECTED_PAGE_MANIFEST = {
    "bytes": 1884627,
    "sha256": "B4F2A4CD0500F6D8505656AD35010D9EBC30CB3648BC7B945BA21E27A57A5CEE",
}
EXPECTED_SHEET_MANIFEST = {
    "bytes": 21748,
    "sha256": "59A54B861FC52E5ED1245DDA980DD55B866D2DB5CA68B97C42E840E4DA1C09C8",
}
EXPECTED_PRECHECK_R1 = {
    "bytes": 13064,
    "sha256": "9BB8E4CF778D3B53A8EAA5B33F30B72F5F2AB12ED5DCC8DD44907866DD0D6062",
}

CRITERIA = (
    "blankness",
    "clipping",
    "overlap",
    "margin_breach",
    "broken_diagrams_or_tables",
    "footnote_integrity",
    "header_footer_page_number_integrity",
    "unexpected_rendering_artifacts",
    "chapter_and_title_continuity",
    "korean_glyph_and_word_spacing_integrity",
)

AGENT_001_PAGES = list(range(1802, 1858))
AGENT_002_PAGES = list(range(1858, 1877)) + list(range(2231, 2317))
AGENT_001_FULL = [1802, 1803, 1804, 1812, 1813, 1817, 1836, 1837, 1841, 1849, 1856, 1857]
AGENT_002_FULL = [1876, 2231]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def identity(path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def require_identity(path: Path, expected: dict[str, object]) -> None:
    observed = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    if observed != expected:
        raise RuntimeError(f"identity mismatch for {path}: {observed} != {expected}")


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError(f"expected object at {path}:{number}")
        rows.append(value)
    return rows


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def jsonl_bytes(rows: list[dict[str, object]]) -> bytes:
    return b"".join(
        (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )


def write_once(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"refusing to overwrite nonidentical append-only artifact: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def verify_claim(claim: object) -> dict[str, object]:
    if not isinstance(claim, dict):
        raise RuntimeError("identity claim missing")
    path = ROOT / str(claim["path"])
    require_identity(path, {"bytes": int(claim["bytes"]), "sha256": str(claim["sha256"])})
    return claim


def page_identities(page_by_number: dict[int, dict[str, object]], pages: list[int]) -> list[dict[str, object]]:
    result = []
    for page in pages:
        claim = verify_claim(page_by_number[page]["image"])
        result.append({"page_one_based": page, "image": claim})
    return result


def make_inspection_receipt(
    record_id: str,
    actor: str,
    pages: list[int],
    sheet_numbers: list[int],
    full_pages: list[int],
    observations: list[str],
    page_by_number: dict[int, dict[str, object]],
    sheet_by_number: dict[int, dict[str, object]],
) -> dict[str, object]:
    sheets = []
    covered: list[int] = []
    for number in sheet_numbers:
        row = sheet_by_number[number]
        claim = verify_claim(row["image"])
        selected = [int(page) for page in row["pages"]]
        covered.extend(selected)
        sheets.append({"sheet_one_based": number, "pages": selected, "image": claim})
    if covered != pages:
        raise RuntimeError(f"{record_id} sheet coverage does not exactly equal assigned pages")
    return {
        "schema": "interlanguage.stacks_cjk.ko_kr_r9_fresh_visual_inspection_receipt/v1",
        "record_id": record_id,
        "actor": actor,
        "precheck": identity(PRECHECK_R1),
        "page_render_manifest": identity(PAGE_MANIFEST),
        "contact_sheet_manifest": identity(SHEET_MANIFEST),
        "inspection_scope": {
            "pages": pages,
            "page_count": len(pages),
            "sheets": sheets,
            "sheet_count": len(sheets),
            "all_contact_sheets_inspected_at_original_sheet_resolution": True,
            "supplemental_full_page_original_resolution": page_identities(page_by_number, full_pages),
        },
        "criteria": list(CRITERIA),
        "criterion_results": {criterion: "PASS" for criterion in CRITERIA},
        "observations": observations,
        "suspected_defects": [],
        "pages_passed": len(pages),
        "pages_failed": 0,
        "result": "PASS_EXPLICIT_VISUAL_INSPECTION",
    }


def main() -> None:
    require_identity(INITIAL_LEDGER, EXPECTED_INITIAL)
    require_identity(PAGE_MANIFEST, EXPECTED_PAGE_MANIFEST)
    require_identity(SHEET_MANIFEST, EXPECTED_SHEET_MANIFEST)
    require_identity(PRECHECK_R1, EXPECTED_PRECHECK_R1)
    initial = load_jsonl(INITIAL_LEDGER)
    page_manifest = load(PAGE_MANIFEST)
    sheet_manifest = load(SHEET_MANIFEST)
    pages = page_manifest.get("pages")
    sheets = sheet_manifest.get("sheets")
    if not isinstance(pages, list) or len(pages) != 2316:
        raise RuntimeError("page manifest does not cover 2316 pages")
    if not isinstance(sheets, list) or len(sheets) != 41:
        raise RuntimeError("sheet manifest does not contain 41 sheets")
    page_by_number = {int(row["page_one_based"]): row for row in pages}
    sheet_by_number = {int(row["sheet_one_based"]): row for row in sheets}
    expected_pages = AGENT_001_PAGES + AGENT_002_PAGES
    if [int(row["page_one_based"]) for row in initial] != expected_pages or len(set(expected_pages)) != 161:
        raise RuntimeError("initial review ledger is not exact 161-page fresh coverage")
    if [int(page) for page in sheet_manifest.get("selected_pages", [])] != expected_pages:
        raise RuntimeError("sheet manifest selected-page order changed")

    receipt_001 = make_inspection_receipt(
        "STACKS-CJK-KO-KR-R9-FRESH-VISUAL-INSPECTION-AGENT-001",
        "/root/ko_r9_visual_resume/r9_visual_sheets_001_014",
        AGENT_001_PAGES,
        list(range(1, 15)),
        AGENT_001_FULL,
        [
            "All 56 pages and sheets 001-014 passed; no suspected visual defect.",
            "Large white areas on pages 1802 and 1812 are legitimate chapter-ending whitespace.",
            "Boundary continuity is correct from Chapter 88 page 65 through Chapter 89 pages 1-10 and Chapter 90 pages 1-45.",
            "Running heads, alternating page numbers, chapter-opening title treatment, contents alignment, diagrams, formulas, and proof-end markers are intact.",
            "Chapter 90 footnotes on pages 1817, 1841, and 1849 are complete, separated by intact rules, and unclipped.",
            "A read-only trim-boundary check found consistent margins and no content approaching a canvas edge abnormally.",
        ],
        page_by_number,
        sheet_by_number,
    )
    write_once(AGENT_001, json_bytes(receipt_001))

    receipt_002 = make_inspection_receipt(
        "STACKS-CJK-KO-KR-R9-FRESH-VISUAL-INSPECTION-AGENT-002",
        "/root/ko_r9_visual_resume",
        AGENT_002_PAGES,
        list(range(15, 42)),
        AGENT_002_FULL,
        [
            "All 105 pages and sheets 015-041 passed; no suspected visual defect.",
            "Boundary continuity is correct at Chapter 90 terminal pages 1874-1875, Chapter 91 opening page 1876, Chapter 100 terminal page 2231, and Chapter 101 opening page 2232.",
            "All text blocks, Korean glyphs and spacing, formulas, commutative diagrams, proof-end markers, headers, footers, page numbers, bibliography, and final page are intact and within bounds.",
            "No blank page, clipping, overlap, margin breach, broken diagram or table, footnote defect, rendering artifact, or continuity failure was observed.",
        ],
        page_by_number,
        sheet_by_number,
    )
    write_once(AGENT_002, json_bytes(receipt_002))

    receipt_by_page = {
        **{page: identity(AGENT_001) for page in AGENT_001_PAGES},
        **{page: identity(AGENT_002) for page in AGENT_002_PAGES},
    }
    full_pages = set(AGENT_001_FULL + AGENT_002_FULL)
    reviewed: list[dict[str, object]] = []
    for row in initial:
        page = int(row["page_one_based"])
        verify_claim(row["page_image"])
        verify_claim(row["contact_sheet"])
        updated = dict(row)
        sheet_pages = next(int(sheet["sheet_one_based"]) for sheet in sheets if page in [int(item) for item in sheet["pages"]])
        sheet_size = len(sheet_by_number[sheet_pages]["pages"])
        mode = f"CONTACT_SHEET_{sheet_size}UP_ORIGINAL_SHEET_RESOLUTION"
        if page in full_pages:
            mode += "_PLUS_FULL_PAGE_ORIGINAL_144DPI"
        updated.update(
            {
                "explicitly_reviewed": True,
                "inspection_mode": mode,
                "criteria": {criterion: "PASS" for criterion in CRITERIA},
                "outcome": "PASS",
                "actor": receipt_by_page[page]["path"],
                "notes": "Explicit visual PASS; exact inspection observations and reviewer provenance are bound by the named immutable receipt.",
                "inspection_receipt": receipt_by_page[page],
            }
        )
        reviewed.append(updated)
    write_once(REVIEWED_LEDGER, jsonl_bytes(reviewed))

    transition = {
        "schema": "interlanguage.stacks_cjk.ko_kr_r9_fresh_page_review_transition/v1",
        "record_id": "STACKS-CJK-KO-KR-R9-FRESH-PAGE-REVIEW-TRANSITION-001",
        "precheck": identity(PRECHECK_R1),
        "initial_unreviewed_ledger_preserved": identity(INITIAL_LEDGER),
        "inspection_receipts": [identity(AGENT_001), identity(AGENT_002)],
        "reviewed_successor_ledger": identity(REVIEWED_LEDGER),
        "page_count": 161,
        "new_chapter_pages": 158,
        "fresh_inherited_boundary_pages": [1802, 1876, 2231],
        "reviewed_pages": [int(row["page_one_based"]) for row in reviewed],
        "explicit_reviews": sum(row["explicitly_reviewed"] is True for row in reviewed),
        "pass_rows": sum(row["outcome"] == "PASS" for row in reviewed),
        "fail_rows": sum(row["outcome"] != "PASS" for row in reviewed),
        "all_criteria_pass": all(
            isinstance(row["criteria"], dict)
            and set(row["criteria"]) == set(CRITERIA)
            and all(value == "PASS" for value in row["criteria"].values())
            for row in reviewed
        ),
        "result": "PASS_161_OF_161_FRESH_PAGE_REVIEWS",
    }
    write_once(TRANSITION, json_bytes(transition))
    print(
        json.dumps(
            {
                "agent_001": identity(AGENT_001),
                "agent_002": identity(AGENT_002),
                "reviewed_ledger": identity(REVIEWED_LEDGER),
                "transition": identity(TRANSITION),
                "result": transition["result"],
            }
        )
    )


if __name__ == "__main__":
    main()
