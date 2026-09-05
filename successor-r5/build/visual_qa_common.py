from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Iterator, Sequence


ROOT = Path(__file__).resolve().parents[1]
PDF_RELATIVE = "output/pdf/stacks-project-ko-kr-cumulative-r5.pdf"
BUILD_RECEIPT_RELATIVE = "receipts/P11_COMPONENT_AND_CUMULATIVE_BUILD.json"
PLAN_RELATIVE = "BUILD_PLAN.json"
INHERITED_LOCI_RELATIVE = "support/visual-qa/inherited_visual_loci.json"

PDF = ROOT / Path(PDF_RELATIVE)
BUILD_RECEIPT = ROOT / Path(BUILD_RECEIPT_RELATIVE)
PLAN = ROOT / Path(PLAN_RELATIVE)
INHERITED_LOCI = ROOT / Path(INHERITED_LOCI_RELATIVE)

EVIDENCE = ROOT / "evidence" / "visual-qa-r5"
PAGES = EVIDENCE / "pages-144dpi"
SHEETS = EVIDENCE / "contact-sheets"
PROBES = EVIDENCE / "warning-probes-288dpi"
PAGE_MANIFEST = EVIDENCE / "PAGE_RENDER_MANIFEST.json"
SHEET_MANIFEST = EVIDENCE / "CONTACT_SHEET_MANIFEST.json"
LOCUS_MANIFEST = EVIDENCE / "WARNING_LOCUS_MANIFEST.json"
PRECHECK = EVIDENCE / "DETERMINISTIC_VISUAL_PRECHECK.json"
PAGE_LEDGER = EVIDENCE / "PAGE_REVIEW_LEDGER.jsonl"
LOCUS_LEDGER = EVIDENCE / "WARNING_LOCUS_REVIEW_LEDGER.jsonl"
FINAL_RECEIPT = ROOT / "receipts" / "P11_PAGE_COMPLETE_VISUAL_QA.json"

BUILD_PASS_RESULT = (
    "PASS_BUILD_AND_DETERMINISTIC_CUMULATIVE_ASSEMBLY_PENDING_PAGE_COMPLETE_VISUAL_QA"
)
PRECHECK_PASS_RESULT = (
    "PASS_DETERMINISTIC_PRECHECK_PENDING_EXPLICIT_PAGE_AND_WARNING_LOCUS_REVIEW"
)
FINAL_PASS_RESULT = "PASS_PAGE_COMPLETE_CUMULATIVE_VISUAL_QA"

PAGE_CRITERIA = (
    "blankness",
    "clipping",
    "overlap",
    "margin_breach",
    "broken_diagrams_or_tables",
    "footnote_integrity",
    "header_footer_page_number_integrity",
    "unexpected_rendering_artifacts",
    "chapter_and_title_continuity",
)

WARNING_CRITERIA = (
    "diagnostic_region_legibility",
    "glyph_and_diagram_integrity",
    "clipping",
    "overlap",
    "margin_breach",
    "footnote_integrity",
)

BOX_KINDS = {
    "overfull_hbox": "overfull_hboxes",
    "overfull_vbox": "overfull_vboxes",
    "underfull_hbox": "underfull_hboxes",
    "underfull_vbox": "underfull_vboxes",
}

BOX_START = re.compile(r"^(Overfull|Underfull) \\(hbox|vbox)\b", re.IGNORECASE)
GENERAL_WARNING_START = re.compile(
    r"^(?:LaTeX|Package\s+\S+|Class\s+\S+) Warning:", re.IGNORECASE
)
PAGE_MARKER = re.compile(r"(?<![A-Za-z0-9])\[(\d+)\](?![A-Za-z0-9])")
EXPLICIT_PAGE = re.compile(r"\bon page\s+(\d+)\b", re.IGNORECASE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def identity(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise RuntimeError(f"required file is missing: {path}")
    return {
        "path": relative(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def root_path(relative_path: str) -> Path:
    candidate = (ROOT / Path(relative_path)).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError(f"path escapes r5 root: {relative_path}") from exc
    return candidate


def require_identity(path: Path, expected: dict[str, object]) -> dict[str, object]:
    observed = identity(path)
    normalized_expected = {
        "path": str(expected.get("path", "")).replace("\\", "/"),
        "bytes": int(expected.get("bytes", -1)),
        "sha256": str(expected.get("sha256", "")).upper(),
    }
    if observed != normalized_expected:
        raise RuntimeError(
            f"identity mismatch for {path}: observed={observed}, expected={normalized_expected}"
        )
    return observed


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: object, *, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise RuntimeError(f"stale temporary file blocks atomic write: {temporary}")
    if path.exists() and not overwrite:
        raise RuntimeError(f"refusing to overwrite: {path}")
    payload = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError(f"JSONL row {line_number} is not an object: {path}")
        rows.append(value)
    return rows


def atomic_jsonl(
    path: Path, rows: Iterable[dict[str, object]], *, overwrite: bool = False
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise RuntimeError(f"stale temporary file blocks atomic write: {temporary}")
    if path.exists() and not overwrite:
        raise RuntimeError(f"refusing to overwrite: {path}")
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def ordered_identity_digest(entries: Sequence[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for index, entry in enumerate(entries, 1):
        line = (
            f"{index}\t{entry['path']}\t{int(entry['bytes'])}\t"
            f"{str(entry['sha256']).upper()}\n"
        )
        digest.update(line.encode("utf-8"))
    return digest.hexdigest().upper()


def contact_sheet_ranges(page_count: int, pages_per_sheet: int = 4) -> list[tuple[int, int]]:
    if page_count < 1 or pages_per_sheet < 1:
        raise ValueError("page_count and pages_per_sheet must be positive")
    return [
        (first, min(first + pages_per_sheet - 1, page_count))
        for first in range(1, page_count + 1, pages_per_sheet)
    ]


def parse_page_spec(specification: str, page_count: int) -> list[int]:
    selected: set[int] = set()
    for token in specification.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            left, right = token.split("-", 1)
            first, last = int(left), int(right)
            if first > last:
                raise ValueError(f"descending page range: {token}")
            selected.update(range(first, last + 1))
        else:
            selected.add(int(token))
    pages = sorted(selected)
    if not pages:
        raise ValueError("page selection is empty")
    if pages[0] < 1 or pages[-1] > page_count:
        raise ValueError(f"page selection is outside 1..{page_count}: {specification}")
    return pages


def poppler_tool(name: str, anchor: Path | None = None) -> Path:
    candidates: list[Path] = []
    executable_name = name + (".exe" if os.name == "nt" else "")
    if anchor is not None:
        candidates.append(anchor.parent / executable_name)
    found = shutil.which(name)
    if found:
        candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise RuntimeError(f"required Poppler tool is unavailable: {name}")


def tool_version(tool: Path) -> dict[str, str]:
    completed = subprocess.run(
        [str(tool), "-v"], capture_output=True, text=True, errors="replace"
    )
    text = (completed.stdout + completed.stderr).splitlines()
    first = next((line.strip() for line in text if line.strip()), "unavailable")
    return {"path": tool.as_posix(), "version": first}


def bind_build() -> tuple[dict[str, object], dict[str, object], int, list[dict[str, object]]]:
    if not BUILD_RECEIPT.is_file():
        raise RuntimeError(
            "the cumulative build receipt does not exist yet; run visual QA only after the build passes"
        )
    if not PDF.is_file():
        raise RuntimeError(
            "the r5 cumulative PDF does not exist yet; no PDF identity is assumed by this tooling"
        )
    build = read_json(BUILD_RECEIPT)
    if not isinstance(build, dict):
        raise RuntimeError("build receipt is not a JSON object")
    if build.get("result") != BUILD_PASS_RESULT:
        raise RuntimeError(f"build receipt is not in the visual-QA pending state: {build.get('result')}")
    claimed_pdf = build.get("cumulative_pdf")
    if not isinstance(claimed_pdf, dict):
        raise RuntimeError("build receipt has no cumulative_pdf identity")
    if str(claimed_pdf.get("path", "")).replace("\\", "/") != PDF_RELATIVE:
        raise RuntimeError("build receipt names an unexpected cumulative PDF path")
    pdf_identity = require_identity(PDF, claimed_pdf)

    merge = build.get("merge")
    verification = build.get("cumulative_verification")
    if not isinstance(merge, dict) or not isinstance(verification, dict):
        raise RuntimeError("build receipt is missing merge or verification data")
    page_counts = {
        int(merge.get("pages", -1)),
        int(verification.get("pages", -2)),
    }
    if len(page_counts) != 1 or next(iter(page_counts)) < 1:
        raise RuntimeError(f"build receipt page counts disagree: {sorted(page_counts)}")
    page_count = next(iter(page_counts))
    starts = merge.get("chapter_starts")
    if not isinstance(starts, list) or not starts:
        raise RuntimeError("build receipt has no chapter starts")
    expected_offset = 0
    normalized_starts: list[dict[str, object]] = []
    for item in starts:
        if not isinstance(item, dict):
            raise RuntimeError("chapter start is not an object")
        offset = int(item.get("page_index_zero_based", -1))
        pages = int(item.get("pages", -1))
        if offset != expected_offset or pages < 1:
            raise RuntimeError(f"chapter starts are not contiguous at {item}")
        expected_offset += pages
        normalized_starts.append(item)
    if expected_offset != page_count:
        raise RuntimeError(
            f"chapter starts cover {expected_offset} pages, build receipt declares {page_count}"
        )
    return build, pdf_identity, page_count, normalized_starts


def chapter_for_global_page(
    global_page: int, starts: Sequence[dict[str, object]]
) -> tuple[int, int, str]:
    if global_page < 1:
        raise ValueError("global page must be positive")
    for item in starts:
        first = int(item["page_index_zero_based"]) + 1
        last = first + int(item["pages"]) - 1
        if first <= global_page <= last:
            return (
                int(item["chapter"]),
                global_page - first + 1,
                str(item["title"]),
            )
    raise RuntimeError(f"global page {global_page} is not in the chapter map")


def normalize_warning_block(lines: Sequence[str]) -> str:
    return " ".join(line.strip() for line in lines if line.strip())


def iter_warning_blocks(text: str) -> Iterator[dict[str, object]]:
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        box = BOX_START.match(stripped)
        general = GENERAL_WARNING_START.match(stripped)
        if not box and not general:
            index += 1
            continue
        block = [lines[index].rstrip("\r\n")]
        following = index + 1
        while following < len(lines) and len(block) < 16:
            candidate = lines[following].rstrip("\r\n")
            if not candidate.strip():
                break
            if BOX_START.match(candidate.strip()) or GENERAL_WARNING_START.match(candidate.strip()):
                break
            if PAGE_MARKER.fullmatch(candidate.strip()):
                break
            block.append(candidate)
            following += 1
        if box:
            kind = f"{box.group(1).lower()}_{box.group(2).lower()}"
        else:
            kind = "tex_warning"
        yield {
            "kind": kind,
            "source_line_one_based": index + 1,
            "character_offset": offsets[index],
            "diagnostic": normalize_warning_block(block),
        }
        index = max(index + 1, following)


def page_candidates_for_locus(
    text: str,
    locus: dict[str, object],
    page_count: int,
    *,
    expand_box_context: bool = True,
) -> list[int]:
    diagnostic = str(locus["diagnostic"])
    explicit = EXPLICIT_PAGE.search(diagnostic)
    if explicit:
        page = int(explicit.group(1))
        return [min(max(page, 1), page_count)]

    offset = int(locus["character_offset"])
    markers = [(match.start(), int(match.group(1))) for match in PAGE_MARKER.finditer(text)]
    previous = [page for position, page in markers if position < offset and 1 <= page <= page_count]
    following = [page for position, page in markers if position > offset and 1 <= page <= page_count]
    previous_page = previous[-1] if previous else None
    next_page = following[0] if following else None
    seeds = {page for page in (previous_page, next_page) if page is not None}
    if not seeds:
        seeds = {1}
    if str(locus["kind"]) in BOX_KINDS and expand_box_context:
        expanded: set[int] = set()
        for page in seeds:
            expanded.update(range(max(1, page - 1), min(page_count, page + 1) + 1))
        seeds = expanded
    return sorted(seeds)


def self_test_common() -> None:
    assert contact_sheet_ranges(10) == [(1, 4), (5, 8), (9, 10)]
    assert parse_page_spec("1-3,5,3", 5) == [1, 2, 3, 5]
    fixture = "[1]\nOverfull \\hbox (2pt too wide) at lines 9--10\n detail\n\n[2]\n"
    loci = list(iter_warning_blocks(fixture))
    assert len(loci) == 1 and loci[0]["kind"] == "overfull_hbox"
    assert page_candidates_for_locus(fixture, loci[0], 3) == [1, 2, 3]
    fixture = "LaTeX Warning: item on page 4 on input line 2.\n"
    locus = next(iter_warning_blocks(fixture))
    assert page_candidates_for_locus(fixture, locus, 9) == [4]
    digest_a = ordered_identity_digest(
        [{"path": "a", "bytes": 1, "sha256": "A" * 64}]
    )
    digest_b = ordered_identity_digest(
        [{"path": "a", "bytes": 1, "sha256": "B" * 64}]
    )
    assert digest_a != digest_b

