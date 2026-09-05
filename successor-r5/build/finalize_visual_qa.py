from __future__ import annotations

import argparse
import json

from visual_qa_common import (
    BUILD_RECEIPT,
    FINAL_PASS_RESULT,
    FINAL_RECEIPT,
    LOCUS_LEDGER,
    LOCUS_MANIFEST,
    PAGE_CRITERIA,
    PAGE_LEDGER,
    PAGE_MANIFEST,
    PRECHECK,
    PRECHECK_PASS_RESULT,
    SHEET_MANIFEST,
    WARNING_CRITERIA,
    atomic_json,
    bind_build,
    contact_sheet_ranges,
    identity,
    ordered_identity_digest,
    read_json,
    read_jsonl,
    require_identity,
    root_path,
    self_test_common,
)


def manifest(path, claim: object) -> dict[str, object]:
    if not isinstance(claim, dict):
        raise RuntimeError(f"precheck identity is missing for {path}")
    require_identity(path, claim)
    value = read_json(path)
    if not isinstance(value, dict):
        raise RuntimeError(f"manifest is not an object: {path}")
    return value


def require_review(
    row: dict[str, object], criteria_names: tuple[str, ...], label: str
) -> None:
    if row.get("explicitly_reviewed") is not True:
        raise RuntimeError(f"{label} is not explicitly reviewed")
    if row.get("outcome") != "PASS":
        raise RuntimeError(f"{label} review outcome is not PASS")
    if row.get("inspection_mode") in (None, "", "UNREVIEWED"):
        raise RuntimeError(f"{label} has no inspection mode")
    if not str(row.get("actor", "")).strip() or not str(row.get("notes", "")).strip():
        raise RuntimeError(f"{label} has no actor or review notes")
    criteria = row.get("criteria")
    if not isinstance(criteria, dict) or set(criteria) != set(criteria_names):
        raise RuntimeError(f"{label} review criteria are incomplete")
    if any(criteria[name] != "PASS" for name in criteria_names):
        raise RuntimeError(f"{label} has a non-PASS review criterion")


def verify_page_manifest(
    value: dict[str, object], pdf_identity: dict[str, object], page_count: int
) -> list[dict[str, object]]:
    if value.get("pdf") != pdf_identity or int(value.get("page_count", -1)) != page_count:
        raise RuntimeError("page manifest PDF binding or page count changed")
    rows = value.get("pages")
    if not isinstance(rows, list) or [int(row["page_one_based"]) for row in rows] != list(
        range(1, page_count + 1)
    ):
        raise RuntimeError("page manifest is not exact ordered page coverage")
    identities = []
    for row in rows:
        claimed = row.get("image")
        if not isinstance(claimed, dict):
            raise RuntimeError("page image identity is missing")
        identities.append(require_identity(root_path(str(claimed["path"])), claimed))
    if [item["sha256"] for item in identities] != value.get("ordered_page_sha256"):
        raise RuntimeError("ordered page hashes changed")
    if ordered_identity_digest(identities) != value.get("ordered_identity_sha256"):
        raise RuntimeError("ordered page identity digest changed")
    return rows


def verify_sheet_manifest(
    value: dict[str, object], pdf_identity: dict[str, object], page_count: int
) -> list[dict[str, object]]:
    if value.get("pdf") != pdf_identity or int(value.get("page_count", -1)) != page_count:
        raise RuntimeError("contact-sheet PDF binding or page count changed")
    rows = value.get("sheets")
    ranges = contact_sheet_ranges(page_count)
    if not isinstance(rows, list) or len(rows) != len(ranges):
        raise RuntimeError("contact-sheet count mismatch")
    identities = []
    coverage = []
    for index, (row, expected) in enumerate(zip(rows, ranges, strict=True), 1):
        pages = [int(page) for page in row["pages"]]
        if int(row["sheet_one_based"]) != index or pages != list(
            range(expected[0], expected[1] + 1)
        ):
            raise RuntimeError(f"contact sheet {index} is not its exact disjoint range")
        coverage.extend(pages)
        claimed = row.get("image")
        if not isinstance(claimed, dict):
            raise RuntimeError("contact-sheet image identity is missing")
        identities.append(require_identity(root_path(str(claimed["path"])), claimed))
    if coverage != list(range(1, page_count + 1)):
        raise RuntimeError("contact sheets do not cover each page exactly once in order")
    if [item["sha256"] for item in identities] != value.get("ordered_sheet_sha256"):
        raise RuntimeError("ordered contact-sheet hashes changed")
    if ordered_identity_digest(identities) != value.get("ordered_identity_sha256"):
        raise RuntimeError("ordered contact-sheet identity digest changed")
    return rows


def verify_locus_manifest(
    value: dict[str, object], pdf_identity: dict[str, object]
) -> tuple[list[dict[str, object]], dict[int, dict[str, object]]]:
    if value.get("pdf") != pdf_identity:
        raise RuntimeError("warning-locus manifest PDF binding changed")
    loci = value.get("loci")
    probes = value.get("probes")
    if not isinstance(loci, list) or not isinstance(probes, list):
        raise RuntimeError("warning-locus manifest arrays are missing")
    if int(value.get("locus_count", -1)) != len(loci):
        raise RuntimeError("warning-locus count mismatch")
    probe_by_page: dict[int, dict[str, object]] = {}
    identities = []
    for row in probes:
        page = int(row["global_page_one_based"])
        if page in probe_by_page:
            raise RuntimeError(f"duplicate warning probe page: {page}")
        claimed = row.get("image")
        if not isinstance(claimed, dict):
            raise RuntimeError("warning probe identity is missing")
        require_identity(root_path(str(claimed["path"])), claimed)
        probe_by_page[page] = row
        identities.append(claimed)
    expected_pages = sorted(
        {int(page) for locus in loci for page in locus["global_page_candidates"]}
    )
    if list(probe_by_page) != expected_pages:
        raise RuntimeError("warning probe page inventory is incomplete or unordered")
    if [item["sha256"] for item in identities] != value.get("ordered_probe_sha256"):
        raise RuntimeError("ordered warning-probe hashes changed")
    if ordered_identity_digest(identities) != value.get("ordered_probe_identity_sha256"):
        raise RuntimeError("ordered warning-probe identity digest changed")
    return loci, probe_by_page


def verify_page_reviews(
    pages: list[dict[str, object]], sheets: list[dict[str, object]], page_count: int
) -> list[dict[str, object]]:
    rows = read_jsonl(PAGE_LEDGER)
    if [int(row["page_one_based"]) for row in rows] != list(range(1, page_count + 1)):
        raise RuntimeError("page review ledger is not exact ordered page coverage")
    sheet_by_page = {int(page): row for row in sheets for page in row["pages"]}
    for expected, row in zip(pages, rows, strict=True):
        page = int(expected["page_one_based"])
        if row.get("page_image") != expected.get("image"):
            raise RuntimeError(f"page {page} review is bound to the wrong page image")
        if row.get("contact_sheet") != sheet_by_page[page].get("image"):
            raise RuntimeError(f"page {page} review is bound to the wrong contact sheet")
        require_review(row, PAGE_CRITERIA, f"page {page}")
    return rows


def verify_locus_reviews(
    loci: list[dict[str, object]], probe_by_page: dict[int, dict[str, object]]
) -> list[dict[str, object]]:
    rows = read_jsonl(LOCUS_LEDGER)
    expected = [
        (str(locus["locus_id"]), int(page))
        for locus in loci
        for page in locus["global_page_candidates"]
    ]
    observed = [
        (str(row["locus_id"]), int(row["global_page_one_based"])) for row in rows
    ]
    if observed != expected:
        raise RuntimeError("warning-locus review ledger coverage or order mismatch")
    for locus_id, page in expected:
        row = rows[observed.index((locus_id, page))]
        if row.get("probe_image") != probe_by_page[page].get("image"):
            raise RuntimeError(f"warning review {locus_id} page {page} has the wrong probe")
        require_review(row, WARNING_CRITERIA, f"warning locus {locus_id} page {page}")
    return rows


def main() -> None:
    if FINAL_RECEIPT.exists():
        raise RuntimeError("final visual-QA receipt already exists; inspect rather than overwrite")
    _build, pdf_identity, page_count, _starts = bind_build()
    precheck = read_json(PRECHECK)
    if not isinstance(precheck, dict) or precheck.get("result") != PRECHECK_PASS_RESULT:
        raise RuntimeError("deterministic visual precheck is not PASS")
    precheck_pdf = dict(precheck.get("pdf", {}))
    precheck_pages = int(precheck_pdf.pop("pages", -1))
    if precheck_pdf != pdf_identity or precheck_pages != page_count:
        raise RuntimeError("precheck is bound to a different PDF identity or page count")

    page_manifest = manifest(PAGE_MANIFEST, precheck.get("page_render_manifest"))
    sheet_manifest = manifest(SHEET_MANIFEST, precheck.get("contact_sheet_manifest"))
    locus_manifest = manifest(LOCUS_MANIFEST, precheck.get("warning_locus_manifest"))
    pages = verify_page_manifest(page_manifest, pdf_identity, page_count)
    sheets = verify_sheet_manifest(sheet_manifest, pdf_identity, page_count)
    loci, probe_by_page = verify_locus_manifest(locus_manifest, pdf_identity)
    page_reviews = verify_page_reviews(pages, sheets, page_count)
    locus_reviews = verify_locus_reviews(loci, probe_by_page)

    receipt = {
        "schema": "interlanguage.stacks_cjk.ko_r5_page_complete_visual_qa/v1",
        "record_id": "STACKS-CJK-KO-P11-R5-PAGE-COMPLETE-VISUAL-QA",
        "pdf": {**pdf_identity, "pages": page_count},
        "build_receipt": identity(BUILD_RECEIPT),
        "deterministic_precheck": identity(PRECHECK),
        "page_render": {
            "manifest": identity(PAGE_MANIFEST),
            "dpi": page_manifest["dpi"],
            "page_count": page_count,
            "ordered_page_sha256": page_manifest["ordered_page_sha256"],
            "ordered_identity_sha256": page_manifest["ordered_identity_sha256"],
        },
        "contact_sheets": {
            "manifest": identity(SHEET_MANIFEST),
            "sheet_count": len(sheets),
            "pages_per_sheet": sheet_manifest["pages_per_sheet"],
            "disjoint_exact_ordered_page_coverage": True,
            "ordered_sheet_sha256": sheet_manifest["ordered_sheet_sha256"],
        },
        "warning_loci": {
            "manifest": identity(LOCUS_MANIFEST),
            "locus_count": len(loci),
            "probe_page_count": len(probe_by_page),
            "ordered_probe_sha256": locus_manifest["ordered_probe_sha256"],
            "locus_page_reviews": len(locus_reviews),
            "all_original_resolution_probe_reviews_passed": True,
        },
        "explicit_page_review": {
            "ledger": identity(PAGE_LEDGER),
            "pages_reviewed": len(page_reviews),
            "pages_passed": len(page_reviews),
            "pages_failed": 0,
            "criteria": list(PAGE_CRITERIA),
        },
        "warning_locus_review": {
            "ledger": identity(LOCUS_LEDGER),
            "rows_reviewed": len(locus_reviews),
            "rows_passed": len(locus_reviews),
            "rows_failed": 0,
            "criteria": list(WARNING_CRITERIA),
        },
        "gates": {
            "all_pages_rendered": True,
            "all_pages_explicitly_reviewed": True,
            "every_page_passed": True,
            "contact_sheets_disjoint_exact_ordered_coverage": True,
            "every_warning_locus_original_resolution_probe_explicitly_reviewed": True,
            "every_warning_locus_probe_passed": True,
            "pdf_identity_unchanged_since_preparation": True,
            "ordered_render_hashes_reverified": True,
        },
        "tex_run": False,
        "publication": False,
        "result": FINAL_PASS_RESULT,
    }
    atomic_json(FINAL_RECEIPT, receipt)
    print(
        json.dumps(
            {
                "receipt": identity(FINAL_RECEIPT),
                "pages": page_count,
                "warning_locus_page_reviews": len(locus_reviews),
                "result": FINAL_PASS_RESULT,
            }
        )
    )


def self_test() -> None:
    self_test_common()
    good = {
        "explicitly_reviewed": True,
        "outcome": "PASS",
        "inspection_mode": "CONTACT_SHEET",
        "actor": "test-agent",
        "notes": "fixture reviewed",
        "criteria": {criterion: "PASS" for criterion in PAGE_CRITERIA},
    }
    require_review(good, PAGE_CRITERIA, "fixture")
    bad = dict(good)
    bad["explicitly_reviewed"] = False
    try:
        require_review(bad, PAGE_CRITERIA, "fixture")
    except RuntimeError:
        pass
    else:
        raise AssertionError("unreviewed fixture was accepted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args()
    if arguments.self_test:
        self_test()
        print("finalize_visual_qa self-test: PASS")
    else:
        main()

