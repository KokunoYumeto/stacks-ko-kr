from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pdfplumber
from PIL import Image, ImageChops, ImageDraw
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "output" / "pdf" / "stacks-project-ko-kr-cumulative-r3.pdf"
BUILD_RECEIPT = ROOT / "receipts" / "CUMULATIVE_BUILD.json"
EVIDENCE = ROOT / "evidence" / "visual-qa-r3"
PAGES = EVIDENCE / "pages-120dpi"
SHEETS = EVIDENCE / "contact-sheets"
RENDER_MANIFEST = EVIDENCE / "CUMULATIVE_RENDER_MANIFEST.csv"
SHEET_MANIFEST = EVIDENCE / "CONTACT_SHEET_MANIFEST.csv"
PRECHECK = EVIDENCE / "DETERMINISTIC_VISUAL_PRECHECK.json"

EXPECTED_PDF_BYTES = 6_163_243
EXPECTED_PDF_SHA256 = "D16F925E5EAD4BA519D2C5E5F7ED47F022810DE76484183BBAE5108D970190F7"
EXPECTED_BUILD_BYTES = 86_487
EXPECTED_BUILD_SHA256 = "5EE1878B27DAB2E1E937F5E8EB728D5927D39330610F85260FC25ED412C93CD9"
EXPECTED_PAGES = 572
RENDER_DPI = 120
SHEET_PAGE_WIDTH = 600
SHEET_COLUMNS = 2
SHEET_ROWS = 2
SHEET_PAGE_COUNT = SHEET_COLUMNS * SHEET_ROWS
LABEL_HEIGHT = 30
GUTTER = 10


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


def numeric_page(path: Path) -> int:
    match = re.search(r"-(\d+)$", path.stem)
    if not match:
        raise RuntimeError(f"Cannot parse rendered page number: {path}")
    return int(match.group(1))


def chapter_for_page(global_page: int, starts: list[dict]) -> tuple[int, int, str]:
    selected = None
    for start in starts:
        if start["page_index_zero_based"] + 1 <= global_page:
            selected = start
        else:
            break
    if selected is None:
        raise RuntimeError(f"No chapter mapping for page {global_page}")
    chapter_page = global_page - selected["page_index_zero_based"]
    return int(selected["chapter"]), chapter_page, str(selected["title"])


def flatten_outline(reader: PdfReader) -> list[dict]:
    rows: list[dict] = []

    def walk(items, depth: int) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
                continue
            title = getattr(item, "title", str(item))
            try:
                page = reader.get_destination_page_number(item) + 1
            except Exception:
                page = None
            rows.append({"depth": depth, "title": title, "page_one_based": page})

    walk(reader.outline, 0)
    return rows


def parse_fonts(pdf: Path) -> tuple[list[str], list[str], str]:
    tool = shutil.which("pdffonts")
    if not tool:
        raise RuntimeError("pdffonts is unavailable")
    result = subprocess.run(
        [tool, str(pdf)], check=True, capture_output=True, text=True, errors="replace"
    )
    lines = [line.rstrip() for line in result.stdout.splitlines()]
    data = [line for line in lines[2:] if line.strip()]
    unembedded = []
    for line in data:
        fields = line.split()
        if len(fields) < 7 or fields[3].lower() != "yes":
            unembedded.append(line)
    return data, unembedded, str(Path(tool).resolve()).replace("\\", "/")


def renderer_metadata() -> dict:
    tool = shutil.which("pdftoppm")
    if not tool:
        raise RuntimeError("pdftoppm is unavailable")
    version = subprocess.run(
        [tool, "-v"], capture_output=True, text=True, errors="replace"
    )
    text = (version.stderr or version.stdout).strip().splitlines()
    return {
        "path": str(Path(tool).resolve()).replace("\\", "/"),
        "version": text[0] if text else "unavailable",
        "dpi": RENDER_DPI,
        "command": "pdftoppm -png -r 120",
    }


def main() -> None:
    if identity(PDF)["bytes"] != EXPECTED_PDF_BYTES or sha256(PDF) != EXPECTED_PDF_SHA256:
        raise RuntimeError("Locked cumulative PDF identity mismatch")
    if identity(BUILD_RECEIPT)["bytes"] != EXPECTED_BUILD_BYTES or sha256(BUILD_RECEIPT) != EXPECTED_BUILD_SHA256:
        raise RuntimeError("Locked build receipt identity mismatch")
    build = json.loads(BUILD_RECEIPT.read_text(encoding="utf-8"))
    if build.get("result") != "PASS_CUMULATIVE_BUILD_PENDING_PAGE_COMPLETE_VISUAL_QA":
        raise RuntimeError("Build result is not the required pending-visual state")
    if build.get("reader_pdf", {}).get("pages") != EXPECTED_PAGES:
        raise RuntimeError("Build receipt page count mismatch")

    page_files = sorted(PAGES.glob("page-*.png"), key=numeric_page)
    page_numbers = [numeric_page(path) for path in page_files]
    if page_numbers != list(range(1, EXPECTED_PAGES + 1)):
        raise RuntimeError("Rendered page coverage is not exactly 1..572")
    if RENDER_MANIFEST.exists() or SHEET_MANIFEST.exists() or PRECHECK.exists():
        raise RuntimeError("Visual evidence receipts already exist; inspect instead of overwriting")
    if any(SHEETS.iterdir()):
        raise RuntimeError("Contact-sheet directory is not empty")

    starts = build["merge"]["chapter_starts"]
    render_rows = []
    dimensions = set()
    blank_pages = []
    touching_pages = []
    page_images: list[tuple[Path, int, int]] = []
    for page_number, path in enumerate(page_files, 1):
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            gray = rgb.convert("L")
            dimensions.add(gray.size)
            mask = gray.point(lambda value: 255 if value < 250 else 0)
            bbox = mask.getbbox()
            histogram = gray.histogram()
            nonwhite = sum(histogram[:250])
            pixels = gray.width * gray.height
            if nonwhite == 0 or bbox is None:
                blank_pages.append(page_number)
            touches = False
            if bbox is not None:
                touches = bbox[0] <= 1 or bbox[1] <= 1 or bbox[2] >= gray.width - 1 or bbox[3] >= gray.height - 1
                if touches:
                    touching_pages.append(page_number)
            chapter, chapter_page, title = chapter_for_page(page_number, starts)
            render_rows.append(
                {
                    "page_one_based": page_number,
                    "chapter": chapter,
                    "chapter_page_one_based": chapter_page,
                    "chapter_title": title,
                    "path": path.relative_to(ROOT).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "width": gray.width,
                    "height": gray.height,
                    "nonwhite_pixels_below_250": nonwhite,
                    "nonwhite_fraction": f"{nonwhite / pixels:.8f}",
                    "content_bbox": "" if bbox is None else ",".join(str(value) for value in bbox),
                    "touches_image_edge": str(touches).lower(),
                }
            )
            page_images.append((path, rgb.width, rgb.height))

    with RENDER_MANIFEST.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(render_rows[0]))
        writer.writeheader()
        writer.writerows(render_rows)

    sheet_rows = []
    for sheet_number, start in enumerate(range(0, EXPECTED_PAGES, SHEET_PAGE_COUNT), 1):
        selected = page_files[start : start + SHEET_PAGE_COUNT]
        thumbs = []
        thumb_height = None
        for path in selected:
            with Image.open(path) as image:
                rgb = image.convert("RGB")
                height = round(rgb.height * SHEET_PAGE_WIDTH / rgb.width)
                if thumb_height is None:
                    thumb_height = height
                elif thumb_height != height:
                    raise RuntimeError("Nonuniform page dimensions while assembling contact sheets")
                thumbs.append(rgb.resize((SHEET_PAGE_WIDTH, height), Image.Resampling.LANCZOS))
        assert thumb_height is not None
        canvas = Image.new(
            "RGB",
            (
                SHEET_COLUMNS * SHEET_PAGE_WIDTH + (SHEET_COLUMNS + 1) * GUTTER,
                SHEET_ROWS * (LABEL_HEIGHT + thumb_height) + (SHEET_ROWS + 1) * GUTTER,
            ),
            "white",
        )
        draw = ImageDraw.Draw(canvas)
        pages = []
        for offset, thumb in enumerate(thumbs):
            page_number = start + offset + 1
            chapter, chapter_page, _title = chapter_for_page(page_number, starts)
            row, column = divmod(offset, SHEET_COLUMNS)
            x = GUTTER + column * (SHEET_PAGE_WIDTH + GUTTER)
            y = GUTTER + row * (LABEL_HEIGHT + thumb_height + GUTTER)
            label = f"GLOBAL {page_number:03d} | CHAPTER {chapter} PAGE {chapter_page:03d}"
            draw.text((x + 4, y + 7), label, fill="black")
            canvas.paste(thumb, (x, y + LABEL_HEIGHT))
            pages.append(page_number)
        sheet_path = SHEETS / f"sheet-{sheet_number:03d}-pages-{pages[0]:03d}-{pages[-1]:03d}.png"
        canvas.save(sheet_path, format="PNG", compress_level=9)
        sheet_rows.append(
            {
                "sheet": sheet_number,
                "first_page": pages[0],
                "last_page": pages[-1],
                "pages": ";".join(str(page) for page in pages),
                "path": sheet_path.relative_to(ROOT).as_posix(),
                "bytes": sheet_path.stat().st_size,
                "sha256": sha256(sheet_path),
                "width": canvas.width,
                "height": canvas.height,
            }
        )
    with SHEET_MANIFEST.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(sheet_rows[0]))
        writer.writeheader()
        writer.writerows(sheet_rows)

    characters_outside_page = []
    page_geometry = []
    with pdfplumber.open(PDF) as document:
        if len(document.pages) != EXPECTED_PAGES:
            raise RuntimeError("pdfplumber page count mismatch")
        for page_number, page in enumerate(document.pages, 1):
            chars = [char for char in page.chars if char.get("text", "").strip()]
            outside = [
                char
                for char in chars
                if char["x0"] < -0.5
                or char["x1"] > page.width + 0.5
                or char["top"] < -0.5
                or char["bottom"] > page.height + 0.5
            ]
            if outside:
                characters_outside_page.append(
                    {"page_one_based": page_number, "count": len(outside)}
                )
            page_geometry.append(
                {
                    "page_one_based": page_number,
                    "width_points": float(page.width),
                    "height_points": float(page.height),
                    "nonspace_characters": len(chars),
                    "outside_page_characters": len(outside),
                }
            )

    reader = PdfReader(PDF, strict=True)
    if len(reader.pages) != EXPECTED_PAGES:
        raise RuntimeError("pypdf page count mismatch")
    link_annotations = 0
    links_outside_page = []
    other_annotations = 0
    for page_number, page in enumerate(reader.pages, 1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        for reference in page.get("/Annots", []):
            annotation = reference.get_object()
            if annotation.get("/Subtype") != "/Link":
                other_annotations += 1
                continue
            link_annotations += 1
            rect = [float(value) for value in annotation.get("/Rect", [0, 0, 0, 0])]
            if len(rect) == 4 and (
                min(rect[0], rect[2]) < -0.5
                or max(rect[0], rect[2]) > width + 0.5
                or min(rect[1], rect[3]) < -0.5
                or max(rect[1], rect[3]) > height + 0.5
            ):
                links_outside_page.append({"page_one_based": page_number, "rect": rect})

    fonts, unembedded_fonts, font_tool = parse_fonts(PDF)
    outline = flatten_outline(reader)
    all_sheet_pages = [
        int(page)
        for row in sheet_rows
        for page in row["pages"].split(";")
    ]
    precheck = {
        "schema": "interlanguage.stacks_cjk.ko_cumulative_visual_precheck/v1",
        "record_id": "STACKS-CJK-KO-CUMULATIVE-R3-VISUAL-PRECHECK-20260905",
        "successor_id": "integration-20260905-r3",
        "pdf": identity(PDF),
        "build_receipt": identity(BUILD_RECEIPT),
        "renderer": renderer_metadata(),
        "render_manifest": identity(RENDER_MANIFEST),
        "contact_sheet_manifest": identity(SHEET_MANIFEST),
        "pages_expected": EXPECTED_PAGES,
        "pages_rendered": len(page_files),
        "page_numbers_exactly_1_through_572": page_numbers == list(range(1, EXPECTED_PAGES + 1)),
        "page_dimensions_pixels": [list(value) for value in sorted(dimensions)],
        "uniform_page_dimensions": len(dimensions) == 1,
        "page_png_bytes": sum(path.stat().st_size for path in page_files),
        "blank_pages": blank_pages,
        "pages_touching_raster_edge": touching_pages,
        "contact_sheets": len(sheet_rows),
        "contact_sheet_page_coverage_exactly_once": all_sheet_pages == list(range(1, EXPECTED_PAGES + 1)),
        "page_geometry": page_geometry,
        "characters_outside_page": characters_outside_page,
        "link_annotations": link_annotations,
        "links_outside_page": links_outside_page,
        "other_annotations": other_annotations,
        "font_tool": font_tool,
        "font_inventory_lines": fonts,
        "unembedded_fonts": unembedded_fonts,
        "outline": outline,
        "required_full_resolution_reinspection_pages": [229, 230, 430, 566, 567, 568, 569],
        "result": "PASS_DETERMINISTIC_PRECHECK_PENDING_HUMAN_INDEPENDENT_VISUAL_INSPECTION"
        if not blank_pages
        and not touching_pages
        and len(dimensions) == 1
        and not characters_outside_page
        and not links_outside_page
        and not unembedded_fonts
        and all_sheet_pages == list(range(1, EXPECTED_PAGES + 1))
        else "FAIL",
    }
    PRECHECK.write_text(json.dumps(precheck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(PRECHECK.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "render_manifest": identity(RENDER_MANIFEST),
                "contact_sheet_manifest": identity(SHEET_MANIFEST),
                "precheck": identity(PRECHECK),
                "pages": len(page_files),
                "sheets": len(sheet_rows),
                "result": precheck["result"],
            },
            ensure_ascii=False,
        )
    )
    if precheck["result"] == "FAIL":
        raise RuntimeError("Deterministic visual precheck failed")


if __name__ == "__main__":
    main()
