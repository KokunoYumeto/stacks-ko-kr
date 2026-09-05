from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
STACKS_ROOT = ROOT.parents[2]
R6 = STACKS_ROOT / "canon" / "ko-kr" / "integration-20260905-r6-cumulative-49"
BUILD_RECEIPT = ROOT / "receipts" / "R9_COMPONENT_AND_CUMULATIVE_BUILD.json"
PDF = ROOT / "output" / "pdf" / "stacks-project-ko-kr-cumulative-r9-52-chapters.pdf"
R6_BUILD = R6 / "receipts" / "R6_COMPONENT_AND_CUMULATIVE_BUILD.json"
R6_VISUAL = R6 / "receipts" / "R6_PAGE_COMPLETE_VISUAL_QA.json"
R6_PDF = R6 / "output" / "pdf" / "stacks-project-ko-kr-cumulative-r6-49-chapters.pdf"
R6_PAGE_MANIFEST = R6 / "evidence" / "visual-qa-r6" / "PAGE_RENDER_MANIFEST.json"
R6_PAGE_LEDGER = R6 / "evidence" / "visual-qa-r6" / "PAGE_REVIEW_LEDGER.jsonl"
R6_WARNING_LEDGER = R6 / "evidence" / "visual-qa-r6" / "WARNING_LOCUS_REVIEW_LEDGER.jsonl"
R6_PAGES = R6 / "evidence" / "visual-qa-r6" / "pages-144dpi"

EVIDENCE = ROOT / "evidence" / "visual-qa-r9"
PAGES = EVIDENCE / "pages-144dpi"
SHEETS = EVIDENCE / "fresh-review-contact-sheets"
PAGE_MANIFEST = EVIDENCE / "PAGE_RENDER_MANIFEST.json"
INHERITANCE_MANIFEST = EVIDENCE / "R6_INHERITED_PAGE_EQUIVALENCE.json"
SHEET_MANIFEST = EVIDENCE / "FRESH_REVIEW_CONTACT_SHEET_MANIFEST.json"
REVIEW_LEDGER = EVIDENCE / "FRESH_PAGE_REVIEW_LEDGER.jsonl"
PRECHECK = EVIDENCE / "DETERMINISTIC_VISUAL_DELTA_PRECHECK.json"
RESUME_RECEIPT = EVIDENCE / "RENDER_RESUME_RECEIPT_001.json"
RENDER_FAILURE = EVIDENCE / "RENDER_VALIDATION_FAILURE_001.json"
RENDER_REPAIR = EVIDENCE / "RENDER_SINGLE_PAGE_REPAIR_001.json"

EXPECTED = {
    BUILD_RECEIPT: (564017, "796DC8DB2A01C4CDD007D91302B5BFDC4F07B13B51E962BBBF218732C66A98EC"),
    PDF: (25145874, "CE7ED45FD47C9E1583ECD9B3A3383A03EC511A63D649CF2715BD24F8926C9642"),
    R6_BUILD: (857587, "4B94F5DB1FAF022C9DD40254B00837D5810BDDEEE2E0F7BA19CBDBFFA0059BB5"),
    R6_VISUAL: (214902, "7810B9E3CDC866B43BEEAED9196FA54263B4B7BEDBCD91634A5938576CE25112"),
    R6_PDF: (23566552, "461F8B4881E317D9DD787400E1BBEC5D8EDB46D874C37F82F7AC9EFEBDC06765"),
    R6_PAGE_MANIFEST: (1481755, "1DB580366F4BE907C09D16C7FE7F81CF434815547FC5EBA0FB675154109FCAE0"),
    R6_PAGE_LEDGER: (2617882, "119091FA9327E39BA7B32757A08E5AB1B66DB230D9C76753804DF610A1C97DBA"),
    R6_WARNING_LEDGER: (215627, "769DCCF338661B86F98D3782C711B8902521347D0269877E210225EEC0C1098C"),
}

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
    "korean_glyph_and_word_spacing_integrity",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def identity(path: Path, base: Path = ROOT) -> dict[str, object]:
    return {
        "path": path.resolve().relative_to(base.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def stacks_identity(path: Path) -> dict[str, object]:
    return {
        "path_relative_to_stacks_root": path.resolve().relative_to(STACKS_ROOT.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def require(path: Path, expected: tuple[int, str]) -> dict[str, object]:
    observed = (path.stat().st_size, sha256(path)) if path.is_file() else None
    if observed != expected:
        raise RuntimeError(f"identity mismatch for {path}: expected {expected}, got {observed}")
    return stacks_identity(path) if path.is_relative_to(STACKS_ROOT) and not path.is_relative_to(ROOT) else identity(path)


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if path.exists() or temporary.exists():
        raise RuntimeError(f"refusing to overwrite {path}")
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def atomic_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if path.exists() or temporary.exists():
        raise RuntimeError(f"refusing to overwrite {path}")
    payload = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows).encode("utf-8")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, object]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="strict").splitlines(), 1):
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError(f"JSONL row is not an object: {path}:{line_number}")
        rows.append(value)
    return rows


def page_suffix(path: Path) -> int:
    match = re.search(r"-(\d+)$", path.stem)
    if not match:
        raise RuntimeError(f"bad rendered-page name: {path.name}")
    return int(match.group(1))


def run(command: list[str]) -> None:
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode:
        raise RuntimeError((completed.stdout + completed.stderr).decode("utf-8", errors="replace"))


def render_pages(page_count: int) -> tuple[Path, list[Path], dict[str, object]]:
    found = shutil.which("pdftoppm")
    if not found:
        raise RuntimeError("pdftoppm unavailable")
    tool = Path(found).resolve()
    existing = sorted(PAGES.glob("page-*.png"), key=page_suffix)
    existing_numbers = [page_suffix(path) for path in existing]
    if len(existing_numbers) != len(set(existing_numbers)):
        raise RuntimeError("duplicate rendered-page ordinals exist")
    if existing_numbers != list(range(1, len(existing_numbers) + 1)):
        raise RuntimeError(
            f"existing rendered-page prefix is not contiguous: {len(existing_numbers)}"
        )
    if len(existing_numbers) > page_count:
        raise RuntimeError("existing rendered-page prefix exceeds PDF page count")
    if RESUME_RECEIPT.exists():
        if not RENDER_FAILURE.is_file() or not RENDER_REPAIR.is_file():
            raise RuntimeError("existing resume receipt lacks its required failure/repair successor chain")
        if existing_numbers != list(range(1, page_count + 1)):
            raise RuntimeError("repaired render set is not complete")
        repair = read_json(RENDER_REPAIR)
        if repair.get("result") != "PASS_SINGLE_TRUNCATED_PREFIX_PAGE_REPAIRED_ALL_2316_PNGS_DECODE":
            raise RuntimeError("single-page render repair is not PASS")
        repaired_claim = repair.get("repaired_page")
        repaired_page = PAGES / "page-002200.png"
        if not isinstance(repaired_claim, dict) or identity(repaired_page) != {
            "path": str(repaired_claim.get("path", "")),
            "bytes": int(repaired_claim.get("bytes", -1)),
            "sha256": str(repaired_claim.get("sha256", "")),
        }:
            raise RuntimeError("single-page render repair identity changed")
        return tool, existing, {
            "result": "PASS_RESUMED_2201_2316_AND_REPAIRED_ONLY_TRUNCATED_PAGE_2200",
            "resume_receipt": identity(RESUME_RECEIPT),
            "failure_receipt": identity(RENDER_FAILURE),
            "repair_receipt": identity(RENDER_REPAIR),
        }
    preexisting = [identity(path) for path in existing]
    first_missing = len(existing_numbers) + 1
    command = None
    if first_missing <= page_count:
        command = [
            str(tool),
            "-png",
            "-r",
            "144",
            "-aa",
            "yes",
            "-aaVector",
            "yes",
            "-f",
            str(first_missing),
            "-l",
            str(page_count),
            str(PDF),
            str(PAGES / "page"),
        ]
        run(command)
    raw = sorted(PAGES.glob("page-*.png"), key=page_suffix)
    numbers = [page_suffix(path) for path in raw]
    if numbers != list(range(1, page_count + 1)):
        raise RuntimeError(f"rendered-page coverage changed: {len(numbers)}")
    normalized = []
    for number, source in zip(numbers, raw, strict=True):
        destination = PAGES / f"page-{number:06d}.png"
        if source != destination:
            source.replace(destination)
        normalized.append(destination)
    resume = {
        "schema": "interlanguage.stacks_cjk.ko_kr_r9_render_resume_receipt/v1",
        "record_id": "STACKS-CJK-KO-KR-R9-RENDER-RESUME-001",
        "reason": "The initial bounded Poppler render ended after a contiguous 2200-page prefix; resume without rerendering or replacing any completed page.",
        "pdf": identity(PDF),
        "renderer": str(tool),
        "preexisting_page_count": len(preexisting),
        "preexisting_pages": preexisting,
        "resumed_first_page_one_based": first_missing if first_missing <= page_count else None,
        "resumed_last_page_one_based": page_count if first_missing <= page_count else None,
        "render_command": command,
        "final_page_count": len(normalized),
        "final_ordered_images": [identity(path) for path in normalized],
        "preexisting_bytes_preserved": all(
            int(before["bytes"]) == int(identity(after)["bytes"])
            and str(before["sha256"]) == str(identity(after)["sha256"])
            for before, after in zip(preexisting, normalized[: len(preexisting)], strict=True)
        ),
        "result": "PASS_RESUMED_MISSING_SUFFIX_WITHOUT_RERENDERING_PREFIX",
    }
    atomic_json(RESUME_RECEIPT, resume)
    return tool, normalized, resume


def pixel_identity(path: Path) -> tuple[str, int, int, int, list[int] | None, bool]:
    with Image.open(path) as source:
        source.load()
        rgb = source.convert("RGB")
        gray = rgb.convert("L")
        payload = rgb.width.to_bytes(4, "big") + rgb.height.to_bytes(4, "big") + rgb.tobytes()
        digest = hashlib.sha256(payload).hexdigest().upper()
        histogram = gray.histogram()
        nonwhite = sum(histogram[:250])
        bbox = gray.point(lambda value: 255 if value < 250 else 0).getbbox()
        touching = bool(bbox and (bbox[0] <= 1 or bbox[1] <= 1 or bbox[2] >= gray.width - 1 or bbox[3] >= gray.height - 1))
        return digest, rgb.width, rgb.height, nonwhite, list(bbox) if bbox else None, touching


def start_map(receipt: dict[str, object]) -> dict[int, dict[str, object]]:
    rows = receipt["merge"]["chapter_starts"]
    result = {int(row["chapter"]): row for row in rows}
    if len(result) != len(rows):
        raise RuntimeError("duplicate chapter start")
    offset = 0
    for row in rows:
        if int(row["page_index_zero_based"]) != offset:
            raise RuntimeError("noncontiguous chapter starts")
        offset += int(row["pages"])
    if offset != int(receipt["merge"]["pages"]):
        raise RuntimeError("chapter starts do not cover PDF")
    return result


def chapter_for_page(page: int, starts: dict[int, dict[str, object]]) -> tuple[int, int, str]:
    for chapter, row in starts.items():
        first = int(row["page_index_zero_based"]) + 1
        last = first + int(row["pages"]) - 1
        if first <= page <= last:
            return chapter, page - first + 1, str(row["title"])
    raise RuntimeError(f"page outside chapter map: {page}")


def make_sheets(selected: list[int], page_rows: dict[int, dict[str, object]]) -> list[dict[str, object]]:
    result = []
    for sheet_number, offset in enumerate(range(0, len(selected), 4), 1):
        pages = selected[offset : offset + 4]
        thumbs = []
        for page in pages:
            with Image.open(PAGES / f"page-{page:06d}.png") as source:
                rgb = source.convert("RGB")
                width = 700
                height = round(rgb.height * width / rgb.width)
                thumbs.append(rgb.resize((width, height), Image.Resampling.LANCZOS))
        maximum_height = max(image.height for image in thumbs)
        canvas = Image.new("RGB", (1436, 2 * (maximum_height + 44) + 36), "white")
        draw = ImageDraw.Draw(canvas)
        for position, (page, thumb) in enumerate(zip(pages, thumbs, strict=True)):
            row, column = divmod(position, 2)
            x = 12 + column * 712
            y = 12 + row * (maximum_height + 56)
            info = page_rows[page]
            draw.text((x + 3, y + 8), f"GLOBAL {page:06d} | CH {int(info['chapter']):03d} PAGE {int(info['chapter_page_one_based']):03d}", fill="black")
            canvas.paste(thumb, (x, y + 36))
        destination = SHEETS / f"sheet-{sheet_number:03d}-selected-pages-{'-'.join(f'{page:06d}' for page in pages)}.png"
        canvas.save(destination, format="PNG", compress_level=9)
        result.append({"sheet_one_based": sheet_number, "pages": pages, "image": identity(destination), "width_pixels": canvas.width, "height_pixels": canvas.height})
        canvas.close()
        for thumb in thumbs:
            thumb.close()
    if [page for row in result for page in row["pages"]] != selected:
        raise RuntimeError("fresh-review sheet coverage changed")
    return result


def main() -> None:
    unexpected = [
        path
        for path in (PAGE_MANIFEST, INHERITANCE_MANIFEST, SHEET_MANIFEST, REVIEW_LEDGER, PRECHECK)
        if path.exists()
    ]
    if unexpected:
        raise RuntimeError(f"terminal or resume evidence already exists; inspect rather than overwrite: {unexpected}")
    bound = {str(path): require(path, expected) for path, expected in EXPECTED.items()}
    r9_build = read_json(BUILD_RECEIPT)
    r6_build = read_json(R6_BUILD)
    r6_visual = read_json(R6_VISUAL)
    r6_manifest = read_json(R6_PAGE_MANIFEST)
    if r9_build.get("result") != "PASS_BUILD_AND_DETERMINISTIC_CUMULATIVE_ASSEMBLY_PENDING_PAGE_COMPLETE_VISUAL_QA":
        raise RuntimeError("r9 build is not visual-QA ready")
    if r6_visual.get("result") != "PASS_PAGE_COMPLETE_CUMULATIVE_VISUAL_QA":
        raise RuntimeError("r6 visual baseline is not terminal PASS")
    r6_reviews = read_jsonl(R6_PAGE_LEDGER)
    if len(r6_reviews) != 2158 or [int(row["page_one_based"]) for row in r6_reviews] != list(range(1, 2159)):
        raise RuntimeError("r6 page-review coverage changed")
    if any(row.get("explicitly_reviewed") is not True or row.get("outcome") != "PASS" for row in r6_reviews):
        raise RuntimeError("r6 page-review baseline contains a non-PASS row")
    r6_warnings = read_jsonl(R6_WARNING_LEDGER)
    if len(r6_warnings) != 247 or any(row.get("explicitly_reviewed") is not True or row.get("outcome") != "PASS" for row in r6_warnings):
        raise RuntimeError("r6 warning-review baseline changed")
    r9_starts = start_map(r9_build)
    r6_starts = start_map(r6_build)
    if set(r9_starts) - set(r6_starts) != {89, 90, 101} or set(r6_starts) - set(r9_starts):
        raise RuntimeError("r9 chapter delta changed")
    for chapter, old in r6_starts.items():
        new = r9_starts[chapter]
        if int(old["pages"]) != int(new["pages"]):
            raise RuntimeError(f"inherited chapter page count changed: {chapter}")
        if old["pdf"]["bytes"] != new["pdf"]["bytes"] or old["pdf"]["sha256"] != new["pdf"]["sha256"]:
            raise RuntimeError(f"inherited component bytes changed: {chapter}")
    page_count = int(r9_build["merge"]["pages"])
    if page_count != 2316 or len(PdfReader(PDF, strict=True).pages) != page_count:
        raise RuntimeError("r9 PDF page count changed")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    PAGES.mkdir(exist_ok=True)
    SHEETS.mkdir(exist_ok=True)
    tool, paths, resume = render_pages(page_count)
    print(json.dumps({"rendered_pages": len(paths), "tool": str(tool)}), flush=True)
    page_rows: list[dict[str, object]] = []
    page_by_number: dict[int, dict[str, object]] = {}
    blanks = []
    touching = []
    dimensions = set()
    for page, path in enumerate(paths, 1):
        pixel_sha, width, height, nonwhite, bbox, edge = pixel_identity(path)
        chapter, local, title = chapter_for_page(page, r9_starts)
        row = {"page_one_based": page, "chapter": chapter, "chapter_page_one_based": local, "chapter_title": title, "image": identity(path), "decoded_rgb_sha256": pixel_sha, "width_pixels": width, "height_pixels": height, "nonwhite_pixels_below_250": nonwhite, "content_bbox": bbox, "touches_image_edge": edge}
        page_rows.append(row)
        page_by_number[page] = row
        dimensions.add((width, height))
        if nonwhite == 0 or bbox is None:
            blanks.append(page)
        if edge:
            touching.append(page)
    atomic_json(PAGE_MANIFEST, {"schema": "interlanguage.stacks_cjk.ko_kr_r9_page_render_manifest/v1", "pdf": identity(PDF), "dpi": 144, "page_count": page_count, "ordered_encoded_sha256": [row["image"]["sha256"] for row in page_rows], "ordered_decoded_rgb_sha256": [row["decoded_rgb_sha256"] for row in page_rows], "pages": page_rows})
    old_manifest_rows = r6_manifest.get("pages")
    if not isinstance(old_manifest_rows, list) or len(old_manifest_rows) != 2158:
        raise RuntimeError("r6 page manifest coverage changed")
    old_by_number = {int(row["page_one_based"]): row for row in old_manifest_rows}
    equivalence = []
    mismatches = []
    for chapter in r6_starts:
        old = r6_starts[chapter]
        new = r9_starts[chapter]
        for local in range(1, int(old["pages"]) + 1):
            old_page = int(old["page_index_zero_based"]) + local
            new_page = int(new["page_index_zero_based"]) + local
            old_path = R6_PAGES / f"page-{old_page:06d}.png"
            old_claim = old_by_number[old_page]["image"]
            if old_path.stat().st_size != int(old_claim["bytes"]) or sha256(old_path) != str(old_claim["sha256"]):
                raise RuntimeError(f"r6 page image identity changed: {old_page}")
            old_pixel, old_width, old_height, _n, _b, _e = pixel_identity(old_path)
            new_row = page_by_number[new_page]
            same = old_pixel == new_row["decoded_rgb_sha256"] and (old_width, old_height) == (new_row["width_pixels"], new_row["height_pixels"])
            record = {"chapter": chapter, "chapter_page_one_based": local, "r6_global_page_one_based": old_page, "r9_global_page_one_based": new_page, "r6_image": stacks_identity(old_path), "r9_image": new_row["image"], "r6_decoded_rgb_sha256": old_pixel, "r9_decoded_rgb_sha256": new_row["decoded_rgb_sha256"], "decoded_pixel_equivalent": same, "r6_prior_visual_review_outcome": r6_reviews[old_page - 1]["outcome"]}
            equivalence.append(record)
            if not same:
                mismatches.append(new_page)
    if len(equivalence) != 2158:
        raise RuntimeError("inherited-page mapping is not complete")
    atomic_json(INHERITANCE_MANIFEST, {"schema": "interlanguage.stacks_cjk.ko_kr_r9_r6_inherited_page_equivalence/v1", "r6_pdf": stacks_identity(R6_PDF), "r6_visual_receipt": stacks_identity(R6_VISUAL), "r6_page_manifest": stacks_identity(R6_PAGE_MANIFEST), "r6_page_review_ledger": stacks_identity(R6_PAGE_LEDGER), "r6_warning_review_ledger": stacks_identity(R6_WARNING_LEDGER), "r9_pdf": identity(PDF), "inherited_pages": len(equivalence), "decoded_pixel_equivalent_pages": sum(bool(row["decoded_pixel_equivalent"]) for row in equivalence), "mismatch_pages": sorted(mismatches), "mapping": equivalence})
    new_pages = []
    for chapter in (89, 90, 101):
        row = r9_starts[chapter]
        new_pages.extend(range(int(row["page_index_zero_based"]) + 1, int(row["page_index_zero_based"]) + int(row["pages"]) + 1))
    boundary_pages = sorted({1802, 1876, 2231})
    fresh_pages = sorted(set(new_pages) | set(boundary_pages) | set(mismatches))
    sheets = make_sheets(fresh_pages, page_by_number)
    atomic_json(SHEET_MANIFEST, {"schema": "interlanguage.stacks_cjk.ko_kr_r9_fresh_review_contact_sheet_manifest/v1", "pdf": identity(PDF), "selected_pages": fresh_pages, "new_chapter_pages": sorted(new_pages), "inherited_boundary_pages": boundary_pages, "inherited_pixel_mismatch_pages": sorted(mismatches), "pages_per_sheet_maximum": 4, "sheet_count": len(sheets), "sheets": sheets})
    sheet_by_page = {int(page): row for row in sheets for page in row["pages"]}
    review_rows = []
    for page in fresh_pages:
        info = page_by_number[page]
        review_rows.append({"schema": "interlanguage.stacks_cjk.ko_kr_r9_fresh_page_visual_review/v1", "page_one_based": page, "chapter": info["chapter"], "chapter_page_one_based": info["chapter_page_one_based"], "reason": "new_chapter_page" if page in new_pages else "fresh_inherited_boundary_review", "page_image": info["image"], "contact_sheet": sheet_by_page[page]["image"], "explicitly_reviewed": False, "inspection_mode": "UNREVIEWED", "criteria": {criterion: "UNREVIEWED" for criterion in PAGE_CRITERIA}, "outcome": "UNREVIEWED", "actor": "", "notes": ""})
    atomic_jsonl(REVIEW_LEDGER, review_rows)
    all_new_warnings = []
    for component in r9_build["components"]:
        flags = component["log_flags"]
        log_path = ROOT / str(component["tex_log"]["path"])
        blg_path = ROOT / str(component["blg"]["path"])
        raw_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        raw_lines.extend(blg_path.read_text(encoding="utf-8", errors="replace").splitlines())
        warning_lines = [line.strip() for line in raw_lines if "Warning:" in line or line.startswith(("Overfull ", "Underfull ", "Warning--"))]
        if any(int(flags[name]) for name in ("overfull_hboxes", "overfull_vboxes", "underfull_hboxes", "underfull_vboxes")) or component.get("bibtex_warning_lines") or warning_lines:
            all_new_warnings.append({"chapter": int(component["chapter"]), "warning_lines": warning_lines})
    passes = not blanks and not touching and len(dimensions) == 1 and not mismatches and not all_new_warnings and len(new_pages) == 158 and len(fresh_pages) == 161
    atomic_json(PRECHECK, {"schema": "interlanguage.stacks_cjk.ko_kr_r9_visual_delta_precheck/v1", "record_id": "STACKS-CJK-KO-KR-R9-VISUAL-DELTA-PRECHECK", "bound_inputs": bound, "pdf": {**identity(PDF), "pages": page_count}, "build_receipt": identity(BUILD_RECEIPT), "render_resume_receipt": identity(RESUME_RECEIPT), "render_validation_failure_receipt": identity(RENDER_FAILURE), "render_single_page_repair_receipt": identity(RENDER_REPAIR), "render_resume_result": resume["result"], "r6_visual_baseline": stacks_identity(R6_VISUAL), "page_render_manifest": identity(PAGE_MANIFEST), "inheritance_manifest": identity(INHERITANCE_MANIFEST), "fresh_contact_sheet_manifest": identity(SHEET_MANIFEST), "fresh_review_ledger": identity(REVIEW_LEDGER), "page_dimensions": [list(item) for item in sorted(dimensions)], "blank_pages": blanks, "pages_touching_raster_edge": touching, "inherited_pages": len(equivalence), "inherited_decoded_pixel_equivalent_pages": sum(bool(row["decoded_pixel_equivalent"]) for row in equivalence), "inherited_pixel_mismatch_pages": sorted(mismatches), "new_chapter_pages": len(new_pages), "fresh_review_pages": len(fresh_pages), "fresh_review_sheets": len(sheets), "new_manager_warning_chapters": all_new_warnings, "coverage_equation": "2158 inherited exact pages + 158 new pages = 2316 cumulative pages; 3 inherited insertion boundaries are additionally reviewed fresh", "result": "PASS_DETERMINISTIC_VISUAL_DELTA_PRECHECK_PENDING_161_FRESH_PAGE_REVIEWS" if passes else "FAIL"})
    print(json.dumps({"precheck": identity(PRECHECK), "rendered_pages": page_count, "inherited_exact": len(equivalence) - len(mismatches), "mismatches": mismatches, "fresh_pages": len(fresh_pages), "sheets": len(sheets), "result": read_json(PRECHECK)["result"]}), flush=True)


if __name__ == "__main__":
    main()
