from __future__ import annotations

import argparse
import json

from visual_qa_common import (
    LOCUS_LEDGER,
    PAGE_CRITERIA,
    PAGE_LEDGER,
    PRECHECK,
    PRECHECK_PASS_RESULT,
    WARNING_CRITERIA,
    atomic_jsonl,
    parse_page_spec,
    read_json,
    read_jsonl,
    self_test_common,
)


def require_prepared() -> int:
    value = read_json(PRECHECK)
    if not isinstance(value, dict) or value.get("result") != PRECHECK_PASS_RESULT:
        raise RuntimeError("visual-QA preparation has not passed")
    return int(value["page_count"])


def criterion_results(
    names: tuple[str, ...], outcome: str, failed: str | None
) -> dict[str, str]:
    failed_names = {
        value.strip() for value in (failed or "").split(",") if value.strip()
    }
    unknown = failed_names - set(names)
    if unknown:
        raise RuntimeError(f"unknown failed criteria: {sorted(unknown)}")
    if outcome == "PASS" and failed_names:
        raise RuntimeError("a PASS review cannot have failed criteria")
    if outcome == "FAIL" and not failed_names:
        raise RuntimeError("a FAIL review must name at least one failed criterion")
    return {name: "FAIL" if name in failed_names else "PASS" for name in names}


def review_pages(arguments: argparse.Namespace) -> None:
    page_count = require_prepared()
    selected = set(parse_page_spec(arguments.pages, page_count))
    rows = read_jsonl(PAGE_LEDGER)
    if [int(row["page_one_based"]) for row in rows] != list(range(1, page_count + 1)):
        raise RuntimeError("page ledger coverage is malformed")
    criteria = criterion_results(PAGE_CRITERIA, arguments.outcome, arguments.failed_criteria)
    for row in rows:
        if int(row["page_one_based"]) not in selected:
            continue
        if row.get("explicitly_reviewed") is True and not arguments.replace:
            raise RuntimeError(
                f"page {row['page_one_based']} was already reviewed; use --replace deliberately"
            )
        row.update(
            {
                "explicitly_reviewed": True,
                "inspection_mode": "CONTACT_SHEET_AND_FULL_PAGE_RENDER",
                "criteria": criteria,
                "outcome": arguments.outcome,
                "actor": arguments.actor.strip(),
                "notes": arguments.notes.strip(),
            }
        )
    atomic_jsonl(PAGE_LEDGER, rows, overwrite=True)
    print(json.dumps({"updated_pages": sorted(selected), "outcome": arguments.outcome}))


def review_locus(arguments: argparse.Namespace) -> None:
    require_prepared()
    rows = read_jsonl(LOCUS_LEDGER)
    key = (arguments.locus_id, arguments.page)
    matches = [
        row
        for row in rows
        if (str(row["locus_id"]), int(row["global_page_one_based"])) == key
    ]
    if len(matches) != 1:
        raise RuntimeError(f"warning locus/page pair does not exist exactly once: {key}")
    row = matches[0]
    if row.get("explicitly_reviewed") is True and not arguments.replace:
        raise RuntimeError("warning locus/page pair was already reviewed; use --replace deliberately")
    row.update(
        {
            "explicitly_reviewed": True,
            "inspection_mode": "ORIGINAL_RESOLUTION_288DPI_WARNING_PROBE",
            "criteria": criterion_results(
                WARNING_CRITERIA, arguments.outcome, arguments.failed_criteria
            ),
            "outcome": arguments.outcome,
            "actor": arguments.actor.strip(),
            "notes": arguments.notes.strip(),
        }
    )
    atomic_jsonl(LOCUS_LEDGER, rows, overwrite=True)
    print(json.dumps({"updated_locus": arguments.locus_id, "page": arguments.page, "outcome": arguments.outcome}))


def status() -> None:
    page_count = require_prepared()
    pages = read_jsonl(PAGE_LEDGER)
    loci = read_jsonl(LOCUS_LEDGER)
    print(
        json.dumps(
            {
                "pages": {
                    "total": page_count,
                    "reviewed": sum(row.get("explicitly_reviewed") is True for row in pages),
                    "pass": sum(row.get("outcome") == "PASS" for row in pages),
                    "fail": sum(row.get("outcome") == "FAIL" for row in pages),
                },
                "warning_locus_pages": {
                    "total": len(loci),
                    "reviewed": sum(row.get("explicitly_reviewed") is True for row in loci),
                    "pass": sum(row.get("outcome") == "PASS" for row in loci),
                    "fail": sum(row.get("outcome") == "FAIL" for row in loci),
                },
            },
            ensure_ascii=False,
        )
    )


def add_review_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--outcome", choices=("PASS", "FAIL"), required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--notes", required=True)
    parser.add_argument("--failed-criteria")
    parser.add_argument("--replace", action="store_true")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    subparsers = parser.add_subparsers(dest="command")
    pages = subparsers.add_parser("pages")
    pages.add_argument("--pages", required=True)
    add_review_options(pages)
    locus = subparsers.add_parser("warning-locus")
    locus.add_argument("--locus-id", required=True)
    locus.add_argument("--page", required=True, type=int)
    add_review_options(locus)
    subparsers.add_parser("status")
    arguments = parser.parse_args()
    if arguments.self_test:
        self_test_common()
        assert criterion_results(PAGE_CRITERIA, "PASS", None)["clipping"] == "PASS"
        print("record_visual_review self-test: PASS")
    elif arguments.command == "pages":
        review_pages(arguments)
    elif arguments.command == "warning-locus":
        review_locus(arguments)
    elif arguments.command == "status":
        status()
    else:
        parser.error("choose pages, warning-locus, or status")


if __name__ == "__main__":
    main()

