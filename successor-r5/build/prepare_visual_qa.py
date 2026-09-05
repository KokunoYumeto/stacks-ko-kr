from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfReader

from visual_qa_common import (
    BOX_KINDS,
    BUILD_RECEIPT,
    EVIDENCE,
    FINAL_RECEIPT,
    INHERITED_LOCI,
    LOCUS_LEDGER,
    LOCUS_MANIFEST,
    PAGE_CRITERIA,
    PAGE_LEDGER,
    PAGE_MANIFEST,
    PAGES,
    PDF,
    PRECHECK,
    PRECHECK_PASS_RESULT,
    PROBES,
    ROOT,
    SHEET_MANIFEST,
    SHEETS,
    WARNING_CRITERIA,
    atomic_json,
    atomic_jsonl,
    bind_build,
    chapter_for_global_page,
    contact_sheet_ranges,
    identity,
    iter_warning_blocks,
    ordered_identity_digest,
    page_candidates_for_locus,
    poppler_tool,
    read_json,
    relative,
    require_identity,
    root_path,
    self_test_common,
    tool_version,
)


RENDER_DPI = 144
PROBE_DPI = 288
PAGES_PER_SHEET = 4
SHEET_COLUMNS = 2
SHEET_ROWS = 2
THUMB_WIDTH = 620
LABEL_HEIGHT = 32
GUTTER = 12


def page_suffix(path: Path) -> int:
    match = re.search(r"-(\d+)$", path.stem)
    if not match:
        raise RuntimeError(f"cannot parse Poppler page suffix: {path.name}")
    return int(match.group(1))


def run(command: list[str]) -> None:
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode:
        output = (completed.stdout + completed.stderr).decode("utf-8", errors="replace")
        raise RuntimeError(f"command failed ({completed.returncode}): {command}\n{output}")


def render_all_pages(pdftoppm: Path, page_count: int) -> list[Path]:
    prefix = PAGES / "page"
    run(
        [
            str(pdftoppm),
            "-png",
            "-r",
            str(RENDER_DPI),
            "-aa",
            "yes",
            "-aaVector",
            "yes",
            str(PDF),
            str(prefix),
        ]
    )
    raw = sorted(PAGES.glob("page-*.png"), key=page_suffix)
    numbers = [page_suffix(path) for path in raw]
    if numbers != list(range(1, page_count + 1)):
        raise RuntimeError(
            f"Poppler output is not exact page coverage 1..{page_count}: "
            f"count={len(numbers)}, first={numbers[:3]}, last={numbers[-3:]}"
        )
    normalized: list[Path] = []
    for number, source in zip(numbers, raw, strict=True):
        destination = PAGES / f"page-{number:06d}.png"
        if source != destination:
            source.replace(destination)
        normalized.append(destination)
    return normalized


def inspect_page_renders(
    paths: list[Path], starts: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[int], list[int], set[tuple[int, int]]]:
    rows: list[dict[str, object]] = []
    blank_pages: list[int] = []
    touching_pages: list[int] = []
    dimensions: set[tuple[int, int]] = set()
    for page, path in enumerate(paths, 1):
        with Image.open(path) as source:
            source.load()
            rgb = source.convert("RGB")
            gray = rgb.convert("L")
            dimensions.add(gray.size)
            histogram = gray.histogram()
            nonwhite = sum(histogram[:250])
            mask = gray.point(lambda value: 255 if value < 250 else 0)
            bbox = mask.getbbox()
            if nonwhite == 0 or bbox is None:
                blank_pages.append(page)
            touches = bool(
                bbox
                and (
                    bbox[0] <= 1
                    or bbox[1] <= 1
                    or bbox[2] >= gray.width - 1
                    or bbox[3] >= gray.height - 1
                )
            )
            if touches:
                touching_pages.append(page)
            chapter, chapter_page, title = chapter_for_global_page(page, starts)
            rows.append(
                {
                    "page_one_based": page,
                    "chapter": chapter,
                    "chapter_page_one_based": chapter_page,
                    "chapter_title": title,
                    "image": identity(path),
                    "width_pixels": gray.width,
                    "height_pixels": gray.height,
                    "nonwhite_pixels_below_250": nonwhite,
                    "nonwhite_fraction": f"{nonwhite / (gray.width * gray.height):.8f}",
                    "content_bbox": list(bbox) if bbox else None,
                    "touches_image_edge": touches,
                }
            )
    return rows, blank_pages, touching_pages, dimensions


def make_contact_sheets(
    page_paths: list[Path],
    page_count: int,
    starts: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for sheet, (first, last) in enumerate(contact_sheet_ranges(page_count), 1):
        page_numbers = list(range(first, last + 1))
        thumbs: list[Image.Image] = []
        for page in page_numbers:
            with Image.open(page_paths[page - 1]) as source:
                rgb = source.convert("RGB")
                height = round(rgb.height * THUMB_WIDTH / rgb.width)
                thumbs.append(
                    rgb.resize((THUMB_WIDTH, height), Image.Resampling.LANCZOS)
                )
        max_height = max(image.height for image in thumbs)
        canvas = Image.new(
            "RGB",
            (
                SHEET_COLUMNS * THUMB_WIDTH + (SHEET_COLUMNS + 1) * GUTTER,
                SHEET_ROWS * (LABEL_HEIGHT + max_height) + (SHEET_ROWS + 1) * GUTTER,
            ),
            "white",
        )
        draw = ImageDraw.Draw(canvas)
        for offset, (page, thumb) in enumerate(zip(page_numbers, thumbs, strict=True)):
            row, column = divmod(offset, SHEET_COLUMNS)
            x = GUTTER + column * (THUMB_WIDTH + GUTTER)
            y = GUTTER + row * (LABEL_HEIGHT + max_height + GUTTER)
            chapter, chapter_page, _title = chapter_for_global_page(page, starts)
            label = f"GLOBAL {page:06d} | CHAPTER {chapter:03d} PAGE {chapter_page:04d}"
            draw.text((x + 4, y + 8), label, fill="black")
            canvas.paste(thumb, (x, y + LABEL_HEIGHT))
        destination = SHEETS / f"sheet-{sheet:04d}-pages-{first:06d}-{last:06d}.png"
        canvas.save(destination, format="PNG", compress_level=9)
        rows.append(
            {
                "sheet_one_based": sheet,
                "first_page": first,
                "last_page": last,
                "pages": page_numbers,
                "image": identity(destination),
                "width_pixels": canvas.width,
                "height_pixels": canvas.height,
            }
        )
        for thumb in thumbs:
            thumb.close()
        canvas.close()
    coverage = [page for row in rows for page in row["pages"]]
    if coverage != list(range(1, page_count + 1)):
        raise RuntimeError("contact sheets are not disjoint exact ordered page coverage")
    return rows


def parse_fonts(pdffonts: Path) -> tuple[list[str], list[str]]:
    completed = subprocess.run(
        [str(pdffonts), str(PDF)], check=True, capture_output=True, text=True, errors="replace"
    )
    lines = [line.rstrip() for line in completed.stdout.splitlines()]
    header_index = next(
        (index for index, line in enumerate(lines) if line.lower().startswith("name")), None
    )
    if header_index is None:
        raise RuntimeError("pdffonts output has no header")
    header = lines[header_index]
    embed_start = header.lower().find("emb")
    if embed_start < 0:
        raise RuntimeError("pdffonts output has no fixed-width emb column")
    data = [line for line in lines[header_index + 2 :] if line.strip()]
    unembedded = [
        line
        for line in data
        if line[embed_start : embed_start + 3].strip().lower() != "yes"
    ]
    return data, unembedded


def flatten_outline(reader: PdfReader) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    def walk(items: object, depth: int) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
                continue
            try:
                page = reader.get_destination_page_number(item) + 1
            except Exception:
                page = None
            rows.append(
                {
                    "depth": depth,
                    "title": str(getattr(item, "title", item)),
                    "page_one_based": page,
                }
            )

    walk(reader.outline, 0)
    return rows


def start_by_chapter(
    starts: list[dict[str, object]], chapter: int
) -> dict[str, object]:
    matches = [item for item in starts if int(item["chapter"]) == chapter]
    if len(matches) != 1:
        raise RuntimeError(f"chapter {chapter} does not have exactly one cumulative start")
    return matches[0]


def global_pages(start: dict[str, object], local_pages: list[int]) -> list[int]:
    pages = int(start["pages"])
    if not local_pages or local_pages[0] < 1 or local_pages[-1] > pages:
        raise RuntimeError(
            f"component page candidates outside 1..{pages}: {local_pages}"
        )
    offset = int(start["page_index_zero_based"])
    return [offset + page for page in local_pages]


def collect_manager_loci(
    build: dict[str, object], starts: list[dict[str, object]]
) -> list[dict[str, object]]:
    components = build.get("components")
    if not isinstance(components, list):
        raise RuntimeError("build receipt components are missing")
    loci: list[dict[str, object]] = []
    for component in components:
        if not isinstance(component, dict):
            raise RuntimeError("component receipt is not an object")
        chapter = int(component["chapter"])
        start = start_by_chapter(starts, chapter)
        component_pages = int(start["pages"])
        component_pdf_claim = component.get("pdf")
        if not isinstance(component_pdf_claim, dict):
            raise RuntimeError(f"chapter {chapter} component PDF identity is missing")
        component_pdf = root_path(str(component_pdf_claim["path"]))
        require_identity(component_pdf, component_pdf_claim)
        if int(component.get("pdf_validation", {}).get("pages", -1)) != component_pages:
            raise RuntimeError(f"chapter {chapter} component page count mismatch")

        tex_claim = component.get("tex_log")
        if not isinstance(tex_claim, dict):
            raise RuntimeError(f"chapter {chapter} TeX log identity is missing")
        tex_log = root_path(str(tex_claim["path"]))
        tex_identity = require_identity(tex_log, tex_claim)
        text = tex_log.read_text(encoding="utf-8", errors="replace")
        parsed = list(iter_warning_blocks(text))
        actual_box_counts = {value: 0 for value in BOX_KINDS.values()}
        for item in parsed:
            if item["kind"] in BOX_KINDS:
                actual_box_counts[BOX_KINDS[str(item["kind"])]] += 1
        flags = component.get("log_flags")
        if not isinstance(flags, dict):
            raise RuntimeError(f"chapter {chapter} log flags are missing")
        expected_box_counts = {
            name: int(flags.get(name, -1)) for name in actual_box_counts
        }
        if actual_box_counts != expected_box_counts:
            raise RuntimeError(
                f"chapter {chapter} parsed box diagnostics disagree with receipt: "
                f"{actual_box_counts} != {expected_box_counts}"
            )
        for index, item in enumerate(parsed, 1):
            local = page_candidates_for_locus(text, item, component_pages)
            loci.append(
                {
                    "locus_id": f"manager-ch{chapter:03d}-tex-{index:03d}",
                    "chapter": chapter,
                    "origin": "manager_component_final_tex_log",
                    "kind": item["kind"],
                    "diagnostic": item["diagnostic"],
                    "source_line_one_based": item["source_line_one_based"],
                    "source": tex_identity,
                    "component_pdf": identity(component_pdf),
                    "component_page_candidates": local,
                    "global_page_candidates": global_pages(start, local),
                }
            )

        blg_claim = component.get("blg")
        expected_bib = [str(value) for value in component.get("bibtex_warning_lines", [])]
        if not isinstance(blg_claim, dict):
            raise RuntimeError(f"chapter {chapter} BibTeX log identity is missing")
        blg = root_path(str(blg_claim["path"]))
        blg_identity = require_identity(blg, blg_claim)
        observed_bib = re.findall(
            r"^Warning--.*$", blg.read_text(encoding="utf-8", errors="replace"), re.MULTILINE
        )
        if observed_bib != expected_bib:
            raise RuntimeError(
                f"chapter {chapter} BibTeX warning lines disagree with receipt"
            )
        for index, diagnostic in enumerate(observed_bib, 1):
            local = list(range(max(1, component_pages - 1), component_pages + 1))
            loci.append(
                {
                    "locus_id": f"manager-ch{chapter:03d}-bibtex-{index:03d}",
                    "chapter": chapter,
                    "origin": "manager_component_final_bibtex_log",
                    "kind": "bibtex_warning",
                    "diagnostic": diagnostic,
                    "source_line_one_based": None,
                    "source": blg_identity,
                    "component_pdf": identity(component_pdf),
                    "component_page_candidates": local,
                    "global_page_candidates": global_pages(start, local),
                }
            )
    return loci


def collect_inherited_loci(
    starts: list[dict[str, object]], build: dict[str, object]
) -> list[dict[str, object]]:
    catalog = read_json(INHERITED_LOCI)
    if not isinstance(catalog, dict) or not isinstance(catalog.get("chapters"), list):
        raise RuntimeError("inherited visual-locus catalog is malformed")
    manager_chapters = {
        int(item["chapter"])
        for item in build.get("components", [])
        if isinstance(item, dict)
    }
    inherited_starts = [
        item for item in starts if int(item["chapter"]) not in manager_chapters
    ]
    catalog_by_chapter = {
        int(item["chapter"]): item
        for item in catalog["chapters"]
        if isinstance(item, dict)
    }
    if set(catalog_by_chapter) != {
        int(item["chapter"]) for item in inherited_starts
    }:
        raise RuntimeError("inherited catalog chapter inventory does not match the build")
    rows: list[dict[str, object]] = []
    for start in inherited_starts:
        chapter = int(start["chapter"])
        catalog_row = catalog_by_chapter[chapter]
        claimed = catalog_row.get("component_pdf")
        start_claimed = start.get("pdf")
        if not isinstance(claimed, dict) or not isinstance(start_claimed, dict):
            raise RuntimeError(f"chapter {chapter} inherited PDF identity is missing")
        path = root_path(str(start_claimed["path"]))
        observed = require_identity(path, start_claimed)
        if observed != {
            "path": str(claimed.get("path", "")).replace("\\", "/"),
            "bytes": int(claimed.get("bytes", -1)),
            "sha256": str(claimed.get("sha256", "")).upper(),
        }:
            raise RuntimeError(
                f"chapter {chapter} inherited locus catalog is stale for the current PDF"
            )
        catalog_loci = catalog_row.get("loci", [])
        if not isinstance(catalog_loci, list):
            raise RuntimeError(f"chapter {chapter} inherited loci are malformed")
        for item in catalog_loci:
            if not isinstance(item, dict):
                raise RuntimeError(f"chapter {chapter} inherited locus is not an object")
            local = sorted({int(value) for value in item["component_page_candidates"]})
            rows.append(
                {
                    "locus_id": str(item["locus_id"]),
                    "chapter": chapter,
                    "origin": "identity_bound_inherited_component_catalog",
                    "kind": str(item["kind"]),
                    "diagnostic": str(item["diagnostic"]),
                    "source_line_one_based": item.get("source_line_one_based"),
                    "source": catalog.get("provenance"),
                    "component_pdf": observed,
                    "component_page_candidates": local,
                    "global_page_candidates": global_pages(start, local),
                }
            )
    return rows


def render_warning_probes(
    pdftoppm: Path, loci: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    target_pages = sorted(
        {
            int(page)
            for locus in loci
            for page in locus["global_page_candidates"]
        }
    )
    probes: list[dict[str, object]] = []
    for page in target_pages:
        destination_prefix = PROBES / f"page-{page:06d}"
        run(
            [
                str(pdftoppm),
                "-png",
                "-r",
                str(PROBE_DPI),
                "-f",
                str(page),
                "-l",
                str(page),
                "-singlefile",
                str(PDF),
                str(destination_prefix),
            ]
        )
        destination = destination_prefix.with_suffix(".png")
        with Image.open(destination) as image:
            image.load()
            width, height = image.size
        probes.append(
            {
                "global_page_one_based": page,
                "image": identity(destination),
                "width_pixels": width,
                "height_pixels": height,
            }
        )
    probe_by_page = {int(row["global_page_one_based"]): row for row in probes}
    bound_loci: list[dict[str, object]] = []
    for locus in loci:
        bound = dict(locus)
        bound["probes"] = [
            probe_by_page[int(page)] for page in locus["global_page_candidates"]
        ]
        bound_loci.append(bound)
    return bound_loci, probes


def initialize_ledgers(
    page_rows: list[dict[str, object]],
    sheet_rows: list[dict[str, object]],
    loci: list[dict[str, object]],
) -> None:
    sheet_by_page = {
        int(page): row for row in sheet_rows for page in row["pages"]
    }
    page_ledger_rows = []
    for row in page_rows:
        page = int(row["page_one_based"])
        sheet = sheet_by_page[page]
        page_ledger_rows.append(
            {
                "schema": "interlanguage.stacks_cjk.ko_r5_page_visual_review/v1",
                "page_one_based": page,
                "chapter": row["chapter"],
                "chapter_page_one_based": row["chapter_page_one_based"],
                "page_image": row["image"],
                "contact_sheet": sheet["image"],
                "explicitly_reviewed": False,
                "inspection_mode": "UNREVIEWED",
                "criteria": {criterion: "UNREVIEWED" for criterion in PAGE_CRITERIA},
                "outcome": "UNREVIEWED",
                "actor": "",
                "notes": "",
            }
        )
    locus_rows = []
    for locus in loci:
        probe_by_page = {
            int(row["global_page_one_based"]): row for row in locus["probes"]
        }
        for page in locus["global_page_candidates"]:
            probe = probe_by_page[int(page)]
            locus_rows.append(
                {
                    "schema": "interlanguage.stacks_cjk.ko_r5_warning_locus_review/v1",
                    "locus_id": locus["locus_id"],
                    "chapter": locus["chapter"],
                    "global_page_one_based": page,
                    "probe_image": probe["image"],
                    "explicitly_reviewed": False,
                    "inspection_mode": "UNREVIEWED",
                    "criteria": {
                        criterion: "UNREVIEWED" for criterion in WARNING_CRITERIA
                    },
                    "outcome": "UNREVIEWED",
                    "actor": "",
                    "notes": "",
                }
            )
    atomic_jsonl(PAGE_LEDGER, page_ledger_rows)
    atomic_jsonl(LOCUS_LEDGER, locus_rows)


def main() -> None:
    if EVIDENCE.exists() or FINAL_RECEIPT.exists():
        raise RuntimeError(
            "r5 visual-QA evidence already exists; inspect it rather than overwriting it"
        )
    build, pdf_identity, page_count, starts = bind_build()
    reader = PdfReader(PDF, strict=True)
    if reader.is_encrypted or len(reader.pages) != page_count:
        raise RuntimeError("strict PDF open/page-count gate failed")

    pdftoppm = poppler_tool("pdftoppm")
    pdfinfo = poppler_tool("pdfinfo", pdftoppm)
    pdffonts = poppler_tool("pdffonts", pdftoppm)
    EVIDENCE.mkdir(parents=True)
    PAGES.mkdir()
    SHEETS.mkdir()
    PROBES.mkdir()

    info = subprocess.run(
        [str(pdfinfo), str(PDF)], check=True, capture_output=True, text=True, errors="replace"
    ).stdout
    match = re.search(r"^Pages:\s+(\d+)\s*$", info, re.MULTILINE)
    if not match or int(match.group(1)) != page_count:
        raise RuntimeError("pdfinfo page count disagrees with the build receipt")

    paths = render_all_pages(pdftoppm, page_count)
    page_rows, blank_pages, touching_pages, dimensions = inspect_page_renders(paths, starts)
    page_manifest = {
        "schema": "interlanguage.stacks_cjk.ko_r5_page_render_manifest/v1",
        "pdf": pdf_identity,
        "dpi": RENDER_DPI,
        "page_count": page_count,
        "ordered_page_sha256": [row["image"]["sha256"] for row in page_rows],
        "ordered_identity_sha256": ordered_identity_digest(
            [row["image"] for row in page_rows]
        ),
        "pages": page_rows,
    }
    atomic_json(PAGE_MANIFEST, page_manifest)

    sheet_rows = make_contact_sheets(paths, page_count, starts)
    sheet_manifest = {
        "schema": "interlanguage.stacks_cjk.ko_r5_contact_sheet_manifest/v1",
        "pdf": pdf_identity,
        "pages_per_sheet": PAGES_PER_SHEET,
        "page_count": page_count,
        "sheet_count": len(sheet_rows),
        "coverage_exactly_once_in_order": True,
        "ordered_sheet_sha256": [row["image"]["sha256"] for row in sheet_rows],
        "ordered_identity_sha256": ordered_identity_digest(
            [row["image"] for row in sheet_rows]
        ),
        "sheets": sheet_rows,
    }
    atomic_json(SHEET_MANIFEST, sheet_manifest)

    loci = collect_manager_loci(build, starts) + collect_inherited_loci(starts, build)
    chapter_order = {int(item["chapter"]): index for index, item in enumerate(starts)}
    loci.sort(key=lambda row: (chapter_order[int(row["chapter"])], str(row["locus_id"])))
    bound_loci, probe_rows = render_warning_probes(pdftoppm, loci)
    locus_manifest = {
        "schema": "interlanguage.stacks_cjk.ko_r5_warning_locus_manifest/v1",
        "pdf": pdf_identity,
        "probe_dpi": PROBE_DPI,
        "locus_count": len(bound_loci),
        "probe_page_count": len(probe_rows),
        "ordered_probe_sha256": [row["image"]["sha256"] for row in probe_rows],
        "ordered_probe_identity_sha256": ordered_identity_digest(
            [row["image"] for row in probe_rows]
        ),
        "loci": bound_loci,
        "probes": probe_rows,
    }
    atomic_json(LOCUS_MANIFEST, locus_manifest)
    initialize_ledgers(page_rows, sheet_rows, bound_loci)

    font_rows, unembedded_fonts = parse_fonts(pdffonts)
    annotations = sum(len(page.get("/Annots", [])) for page in reader.pages)
    outline = flatten_outline(reader)
    expected_outline = [
        {"title": "한국어 누적 리더 / Korean Cumulative Reader", "page": 1}
    ] + [
        {
            "title": f"제{int(item['chapter'])}장: {item['title']}",
            "page": int(item["page_index_zero_based"]) + 1,
        }
        for item in starts
    ]
    observed_outline = [
        {"title": row["title"], "page": row["page_one_based"]} for row in outline
    ]
    outline_matches = observed_outline == expected_outline
    passes = (
        not blank_pages
        and not touching_pages
        and len(dimensions) == 1
        and not unembedded_fonts
        and annotations == 0
        and outline_matches
    )
    precheck = {
        "schema": "interlanguage.stacks_cjk.ko_r5_visual_precheck/v1",
        "record_id": "STACKS-CJK-KO-P11-R5-VISUAL-PRECHECK",
        "pdf": {**pdf_identity, "pages": page_count},
        "build_receipt": identity(BUILD_RECEIPT),
        "tools": {
            "pdftoppm": tool_version(pdftoppm),
            "pdfinfo": tool_version(pdfinfo),
            "pdffonts": tool_version(pdffonts),
            "pillow": Image.__version__,
        },
        "page_render_manifest": identity(PAGE_MANIFEST),
        "contact_sheet_manifest": identity(SHEET_MANIFEST),
        "warning_locus_manifest": identity(LOCUS_MANIFEST),
        "page_count": page_count,
        "pages_rendered": len(page_rows),
        "ordered_page_identity_sha256": page_manifest["ordered_identity_sha256"],
        "page_dimensions_pixels": [list(value) for value in sorted(dimensions)],
        "uniform_page_dimensions": len(dimensions) == 1,
        "blank_pages": blank_pages,
        "pages_touching_raster_edge": touching_pages,
        "contact_sheet_count": len(sheet_rows),
        "contact_sheets_disjoint_exact_ordered_coverage": True,
        "warning_locus_count": len(bound_loci),
        "warning_probe_page_count": len(probe_rows),
        "font_inventory_lines": font_rows,
        "unembedded_fonts": unembedded_fonts,
        "annotations": annotations,
        "outline": outline,
        "outline_matches_build_chapter_starts": outline_matches,
        "review_ledgers": {
            "pages": relative(PAGE_LEDGER),
            "warning_loci": relative(LOCUS_LEDGER),
            "initial_state": "ALL_UNREVIEWED",
        },
        "result": PRECHECK_PASS_RESULT if passes else "FAIL",
    }
    atomic_json(PRECHECK, precheck)
    print(
        json.dumps(
            {
                "pdf": pdf_identity,
                "pages": page_count,
                "sheets": len(sheet_rows),
                "warning_loci": len(bound_loci),
                "warning_probe_pages": len(probe_rows),
                "precheck": identity(PRECHECK),
                "result": precheck["result"],
            },
            ensure_ascii=False,
        )
    )
    if not passes:
        raise RuntimeError("deterministic visual precheck failed")


def self_test() -> None:
    self_test_common()
    assert page_suffix(Path("page-123.png")) == 123
    fake_starts = [
        {"chapter": 1, "title": "a", "page_index_zero_based": 0, "pages": 2},
        {"chapter": 2, "title": "b", "page_index_zero_based": 2, "pages": 3},
    ]
    assert global_pages(fake_starts[1], [1, 3]) == [3, 5]
    assert chapter_for_global_page(4, fake_starts) == (2, 2, "b")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args()
    if arguments.self_test:
        self_test()
        print("prepare_visual_qa self-test: PASS")
    else:
        main()

