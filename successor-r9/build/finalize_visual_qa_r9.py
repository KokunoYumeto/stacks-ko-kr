from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
STACKS_ROOT = ROOT.parents[2]
VISUAL = ROOT / "evidence" / "visual-qa-r9"
PDF = ROOT / "output" / "pdf" / "stacks-project-ko-kr-cumulative-r9-52-chapters.pdf"
BUILD = ROOT / "receipts" / "R9_COMPONENT_AND_CUMULATIVE_BUILD.json"
PRECHECK = VISUAL / "DETERMINISTIC_VISUAL_DELTA_PRECHECK_R1.json"
WARNING_REPAIR = VISUAL / "VISUAL_WARNING_CLASSIFICATION_REPAIR_001.json"
PAGE_MANIFEST = VISUAL / "PAGE_RENDER_MANIFEST.json"
INHERITANCE = VISUAL / "R6_INHERITED_PAGE_EQUIVALENCE.json"
SHEET_MANIFEST = VISUAL / "FRESH_REVIEW_CONTACT_SHEET_MANIFEST.json"
INITIAL_LEDGER = VISUAL / "FRESH_PAGE_REVIEW_LEDGER.jsonl"
REVIEWED_LEDGER = VISUAL / "FRESH_PAGE_REVIEW_LEDGER_R1.jsonl"
REVIEW_TRANSITION = VISUAL / "FRESH_PAGE_REVIEW_TRANSITION_001.json"
AGENT_001 = VISUAL / "FRESH_VISUAL_INSPECTION_RECEIPT_AGENT_001.json"
AGENT_002 = VISUAL / "FRESH_VISUAL_INSPECTION_RECEIPT_AGENT_002.json"
FINAL = ROOT / "receipts" / "R9_PAGE_COMPLETE_VISUAL_QA.json"

EXPECTED = {
    PDF: (25145874, "CE7ED45FD47C9E1583ECD9B3A3383A03EC511A63D649CF2715BD24F8926C9642"),
    BUILD: (564017, "796DC8DB2A01C4CDD007D91302B5BFDC4F07B13B51E962BBBF218732C66A98EC"),
    PRECHECK: (13064, "9BB8E4CF778D3B53A8EAA5B33F30B72F5F2AB12ED5DCC8DD44907866DD0D6062"),
    WARNING_REPAIR: (6285, "70E6268D42DB2C76C7EF23ADEF453F9EE85E7DEF299E6CAA28D10703E5FC1B4A"),
    PAGE_MANIFEST: (1884627, "B4F2A4CD0500F6D8505656AD35010D9EBC30CB3648BC7B945BA21E27A57A5CEE"),
    INHERITANCE: (1999668, "3B153234A18CB464B1C565E643AB2E7609CE30E30144CBCC6A1E8E6DE622983E"),
    SHEET_MANIFEST: (21748, "59A54B861FC52E5ED1245DDA980DD55B866D2DB5CA68B97C42E840E4DA1C09C8"),
    INITIAL_LEDGER: (168604, "7CF8D65B11372DB236464588406BD0C83BBD34569A7E44F13F21AA47F42D47D9"),
    REVIEWED_LEDGER: (224100, "FAEF45C005C4439D47A553A8A7CBB7CF136AC275EF1405CA86773465E124D5FC"),
    REVIEW_TRANSITION: (3127, "AB5E581DBFD774DAFEE269E72402376A548AAD7E4665E7A0EA8274A0645DF30A"),
    AGENT_001: (12215, "27F68106A2B51FDECE2C6D0774B698C5D74678A7B4B962488230557AB3711E3F"),
    AGENT_002: (15379, "4D415E8056ACE0EBC0A7A763AF1C419436F19B37EF3605E42F521463A5455B88"),
}
CRITERIA = {
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
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def identity(path: Path) -> dict[str, object]:
    try:
        rel = path.relative_to(ROOT).as_posix()
        return {"path": rel, "bytes": path.stat().st_size, "sha256": sha256(path)}
    except ValueError:
        rel = path.relative_to(STACKS_ROOT).as_posix()
        return {"path_relative_to_stacks_root": rel, "bytes": path.stat().st_size, "sha256": sha256(path)}


def require_expected() -> None:
    for path, (size, digest) in EXPECTED.items():
        observed = (path.stat().st_size, sha256(path))
        if observed != (size, digest):
            raise RuntimeError(f"identity mismatch for {path}: {observed} != {(size, digest)}")


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError(f"non-object JSONL row in {path}")
    return rows


def resolve_claim(claim: dict[str, object]) -> Path:
    if "path" in claim:
        return ROOT / str(claim["path"])
    return STACKS_ROOT / str(claim["path_relative_to_stacks_root"])


def verify_claim(claim: object) -> dict[str, object]:
    if not isinstance(claim, dict):
        raise RuntimeError("identity claim missing")
    path = resolve_claim(claim)
    if path.stat().st_size != int(claim["bytes"]) or sha256(path) != str(claim["sha256"]):
        raise RuntimeError(f"identity claim failed: {path}")
    return claim


def write_once(path: Path, value: object) -> None:
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"refusing to overwrite nonidentical terminal receipt: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def ordered_identity_digest(claims: list[dict[str, object]]) -> str:
    payload = "".join(
        f"{claim.get('path', claim.get('path_relative_to_stacks_root'))}|{claim['bytes']}|{claim['sha256']}\n"
        for claim in claims
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def main() -> None:
    require_expected()
    build = load(BUILD)
    precheck = load(PRECHECK)
    warning = load(WARNING_REPAIR)
    page_manifest = load(PAGE_MANIFEST)
    inheritance = load(INHERITANCE)
    sheet_manifest = load(SHEET_MANIFEST)
    transition = load(REVIEW_TRANSITION)
    reviewed = load_jsonl(REVIEWED_LEDGER)

    if build.get("result") != "PASS_BUILD_AND_DETERMINISTIC_CUMULATIVE_ASSEMBLY_PENDING_PAGE_COMPLETE_VISUAL_QA":
        raise RuntimeError("manager build receipt is not PASS pending visual QA")
    if precheck.get("result") != "PASS_DETERMINISTIC_VISUAL_DELTA_PRECHECK_AFTER_BENIGN_WARNING_CLASSIFICATION_PENDING_161_FRESH_PAGE_REVIEWS":
        raise RuntimeError("corrected visual precheck is not PASS")
    if warning.get("result") != "PASS_BENIGN_NON_LAYOUT_WARNING_CLASSIFICATION":
        raise RuntimeError("warning classification is not PASS")
    if warning.get("warning_occurrences") != 9 or warning.get("warning_chapters") != [89, 90, 101]:
        raise RuntimeError("warning classification inventory changed")
    if warning.get("warning_locus_review_required") is not False:
        raise RuntimeError("warning classification unexpectedly requires a rendered locus")
    if precheck.get("unclassified_or_layout_relevant_new_manager_warnings") != []:
        raise RuntimeError("unclassified or layout-relevant warning remains")

    pages = page_manifest.get("pages")
    if not isinstance(pages, list) or len(pages) != 2316:
        raise RuntimeError("page manifest does not contain 2316 rows")
    if [int(row["page_one_based"]) for row in pages] != list(range(1, 2317)):
        raise RuntimeError("page manifest coverage is not exact and ordered")
    if page_manifest.get("pdf") != identity(PDF) or page_manifest.get("dpi") != 144:
        raise RuntimeError("page manifest PDF binding or DPI changed")

    encoded_hashes: list[str] = []
    decoded_hashes: list[str] = []
    page_claims: list[dict[str, object]] = []
    dimensions: set[tuple[int, int]] = set()
    blank_pages: list[int] = []
    edge_pages: list[int] = []
    for row in pages:
        page = int(row["page_one_based"])
        claim = verify_claim(row["image"])
        page_claims.append(claim)
        encoded_hashes.append(str(claim["sha256"]))
        image_path = resolve_claim(claim)
        with Image.open(image_path) as image:
            image.load()
            rgb = image.convert("RGB")
            dimensions.add(rgb.size)
            payload = rgb.width.to_bytes(4, "big") + rgb.height.to_bytes(4, "big") + rgb.tobytes()
            digest = hashlib.sha256(payload).hexdigest().upper()
        decoded_hashes.append(digest)
        if digest != row.get("decoded_rgb_sha256"):
            raise RuntimeError(f"decoded RGB hash mismatch on page {page}")
        if int(row.get("nonwhite_pixels_below_250", 0)) <= 0 or row.get("content_bbox") is None:
            blank_pages.append(page)
        if row.get("touches_image_edge") is True:
            edge_pages.append(page)
    if encoded_hashes != page_manifest.get("ordered_encoded_sha256"):
        raise RuntimeError("ordered encoded page hashes changed")
    if decoded_hashes != page_manifest.get("ordered_decoded_rgb_sha256"):
        raise RuntimeError("ordered decoded page hashes changed")
    if dimensions != {(1224, 1584)} or blank_pages or edge_pages:
        raise RuntimeError("page raster dimension, blankness, or edge gate failed")

    mapping = inheritance.get("mapping")
    if not isinstance(mapping, list) or len(mapping) != 2158:
        raise RuntimeError("inheritance mapping does not contain 2158 rows")
    mapped_pages: set[int] = set()
    for row in mapping:
        page = int(row["r9_global_page_one_based"])
        if page in mapped_pages:
            raise RuntimeError(f"duplicate inherited r9 page {page}")
        mapped_pages.add(page)
        verify_claim(row["r6_image"])
        verify_claim(row["r9_image"])
        if row.get("decoded_pixel_equivalent") is not True:
            raise RuntimeError(f"inherited page {page} is not pixel-equivalent")
        if row.get("r6_decoded_rgb_sha256") != row.get("r9_decoded_rgb_sha256"):
            raise RuntimeError(f"inherited page {page} decoded hash differs")
        if row.get("r6_prior_visual_review_outcome") != "PASS":
            raise RuntimeError(f"inherited page {page} lacks prior visual PASS")
    if inheritance.get("decoded_pixel_equivalent_pages") != 2158 or inheritance.get("mismatch_pages") != []:
        raise RuntimeError("inheritance summary changed")
    verify_claim(inheritance["r6_visual_receipt"])
    r6_visual = load(resolve_claim(inheritance["r6_visual_receipt"]))
    if r6_visual.get("result") != "PASS_PAGE_COMPLETE_CUMULATIVE_VISUAL_QA" or r6_visual.get("pdf", {}).get("pages") != 2158:
        raise RuntimeError("r6 visual baseline is not terminal page-complete PASS")

    new_pages = set(range(1803, 1813)) | set(range(1813, 1876)) | set(range(2232, 2317))
    if len(new_pages) != 158 or mapped_pages | new_pages != set(range(1, 2317)) or mapped_pages & new_pages:
        raise RuntimeError("inherited/new page partition is not exact")

    selected = [int(page) for page in sheet_manifest.get("selected_pages", [])]
    expected_selected = list(range(1802, 1877)) + list(range(2231, 2317))
    if selected != expected_selected or len(selected) != 161:
        raise RuntimeError("fresh review selection changed")
    sheets = sheet_manifest.get("sheets")
    if not isinstance(sheets, list) or len(sheets) != 41:
        raise RuntimeError("fresh contact-sheet inventory changed")
    covered: list[int] = []
    sheet_by_page: dict[int, dict[str, object]] = {}
    sheet_claims: list[dict[str, object]] = []
    for index, sheet in enumerate(sheets, 1):
        if int(sheet["sheet_one_based"]) != index:
            raise RuntimeError("contact-sheet numbering changed")
        claim = verify_claim(sheet["image"])
        sheet_claims.append(claim)
        for page in [int(item) for item in sheet["pages"]]:
            if page in sheet_by_page:
                raise RuntimeError(f"page {page} appears on multiple contact sheets")
            covered.append(page)
            sheet_by_page[page] = sheet
    if covered != selected:
        raise RuntimeError("contact sheets do not cover selected pages once in exact order")

    if [int(row["page_one_based"]) for row in reviewed] != selected:
        raise RuntimeError("reviewed ledger does not match selected-page order")
    page_by_number = {int(row["page_one_based"]): row for row in pages}
    for row in reviewed:
        page = int(row["page_one_based"])
        if row.get("page_image") != page_by_number[page].get("image"):
            raise RuntimeError(f"review row {page} page binding changed")
        if row.get("contact_sheet") != sheet_by_page[page].get("image"):
            raise RuntimeError(f"review row {page} sheet binding changed")
        verify_claim(row["inspection_receipt"])
        if row.get("explicitly_reviewed") is not True or row.get("outcome") != "PASS":
            raise RuntimeError(f"review row {page} is not explicit PASS")
        criteria = row.get("criteria")
        if not isinstance(criteria, dict) or set(criteria) != CRITERIA or any(value != "PASS" for value in criteria.values()):
            raise RuntimeError(f"review row {page} criteria are incomplete or non-PASS")
        if not str(row.get("inspection_mode", "")).strip() or not str(row.get("actor", "")).strip() or not str(row.get("notes", "")).strip():
            raise RuntimeError(f"review row {page} lacks provenance")
    if transition.get("result") != "PASS_161_OF_161_FRESH_PAGE_REVIEWS" or transition.get("fail_rows") != 0:
        raise RuntimeError("review transition is not terminal PASS")
    for claim in transition.get("inspection_receipts", []):
        verify_claim(claim)

    gates = {
        "build_receipt_pass": True,
        "pdf_identity_unchanged": True,
        "all_2316_page_images_present_and_hash_bound": True,
        "all_2316_page_images_decode_successfully": True,
        "all_2316_decoded_rgb_hashes_replayed": True,
        "page_dimensions_uniform_1224x1584": True,
        "blank_pages_zero": True,
        "pages_touching_raster_edge_zero": True,
        "r6_inherited_page_mapping_complete": True,
        "r6_inherited_pages_pixel_equivalent_2158_of_2158": True,
        "r6_inherited_pages_prior_visual_pass_2158_of_2158": True,
        "new_pages_fresh_visual_pass_158_of_158": True,
        "insertion_boundary_pages_fresh_visual_pass_3_of_3": True,
        "fresh_selected_pages_explicit_visual_pass_161_of_161": True,
        "contact_sheets_disjoint_exact_selected_page_coverage": True,
        "new_manager_notices_classified_benign_non_layout_9_of_9": True,
        "unclassified_or_layout_relevant_warnings_zero": True,
        "failed_precheck_and_truncated_render_history_preserved": True,
        "tex_rerun_for_visual_qa": False,
    }
    receipt = {
        "schema": "interlanguage.stacks_cjk.ko_kr_r9_page_complete_visual_qa/v1",
        "record_id": "STACKS-CJK-KO-KR-R9-PAGE-COMPLETE-VISUAL-QA",
        "pdf": {**identity(PDF), "pages": 2316},
        "build_receipt": identity(BUILD),
        "corrected_precheck": identity(PRECHECK),
        "warning_classification_repair": identity(WARNING_REPAIR),
        "render_and_repair_history": {
            "resumed_only_missing_pages_2201_2316": verify_claim(precheck["render_resume_receipt"]),
            "preserved_truncated_page_2200_failure": verify_claim(precheck["render_validation_failure_receipt"]),
            "single_page_2200_repair": verify_claim(precheck["render_single_page_repair_receipt"]),
            "original_fail_precheck_preserved": verify_claim(precheck["predecessor_fail_precheck"]),
            "tex_rerun": False,
        },
        "page_render": {
            "manifest": identity(PAGE_MANIFEST),
            "dpi": 144,
            "page_count": 2316,
            "dimensions": [1224, 1584],
            "ordered_encoded_sha256_count": len(encoded_hashes),
            "ordered_decoded_rgb_sha256_count": len(decoded_hashes),
            "ordered_page_identity_sha256": ordered_identity_digest(page_claims),
        },
        "inherited_visual_evidence": {
            "manifest": identity(INHERITANCE),
            "r6_terminal_visual_receipt": inheritance["r6_visual_receipt"],
            "pages": 2158,
            "decoded_pixel_equivalent": 2158,
            "prior_visual_pass": 2158,
            "mismatches": 0,
        },
        "fresh_visual_evidence": {
            "initial_unreviewed_ledger_preserved": identity(INITIAL_LEDGER),
            "inspection_receipts": [identity(AGENT_001), identity(AGENT_002)],
            "transition": identity(REVIEW_TRANSITION),
            "reviewed_ledger": identity(REVIEWED_LEDGER),
            "contact_sheet_manifest": identity(SHEET_MANIFEST),
            "contact_sheet_count": 41,
            "ordered_contact_sheet_identity_sha256": ordered_identity_digest(sheet_claims),
            "new_chapter_pages": 158,
            "fresh_inherited_boundaries": [1802, 1876, 2231],
            "total_fresh_reviews": 161,
            "pass": 161,
            "fail": 0,
            "criteria": sorted(CRITERIA),
        },
        "warning_evidence": {
            "notices": 9,
            "chapters": [89, 90, 101],
            "classification": "BENIGN_TOOLCHAIN_RELEASE_AVAILABILITY_NOTICE",
            "layout_loci": 0,
            "all_mechanical_failure_flags_zero": True,
            "preserved_as_adverse_evidence": True,
        },
        "coverage_equation": "2158 inherited exact and previously visually passed pages + 158 new freshly reviewed pages = 2316 cumulative pages; inherited insertion boundaries 1802, 1876, and 2231 were additionally reviewed fresh",
        "gates": gates,
        "all_gates_pass": all(value is True or (key == "tex_rerun_for_visual_qa" and value is False) for key, value in gates.items()),
        "producer_roots_touched": False,
        "tex_run": False,
        "publication": False,
        "canon_admission": "PASS_PAGE_COMPLETE_VISUAL_QA_READY_FOR_DETERMINISTIC_PACKAGE_AND_PUBLICATION",
        "result": "PASS_PAGE_COMPLETE_CUMULATIVE_VISUAL_QA",
    }
    if receipt["all_gates_pass"] is not True:
        raise RuntimeError("terminal gate aggregation failed")
    write_once(FINAL, receipt)
    print(json.dumps({"receipt": identity(FINAL), "pages": 2316, "fresh_reviews": 161, "result": receipt["result"]}))


if __name__ == "__main__":
    main()
