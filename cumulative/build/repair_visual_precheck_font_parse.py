from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "output" / "pdf" / "stacks-project-ko-kr-cumulative-r3.pdf"
EVIDENCE = ROOT / "evidence" / "visual-qa-r3"
ATTEMPT1 = EVIDENCE / "DETERMINISTIC_VISUAL_PRECHECK.json"
SUCCESSOR = EVIDENCE / "DETERMINISTIC_VISUAL_PRECHECK_R2.json"

EXPECTED_ATTEMPT1_SHA256 = "C3D7154642D9D79B4041E61BE736C623B2F1E4FF5F87700B77D4CCCD12BB14A1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def identity(path: Path) -> dict:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> None:
    if SUCCESSOR.exists():
        raise RuntimeError("Successor precheck already exists; inspect instead of overwriting")
    if sha256(ATTEMPT1) != EXPECTED_ATTEMPT1_SHA256:
        raise RuntimeError("Attempt-1 precheck identity mismatch")
    attempt1 = json.loads(ATTEMPT1.read_text(encoding="utf-8"))
    if attempt1.get("result") != "FAIL":
        raise RuntimeError("Attempt-1 receipt is not the expected failed precheck")

    tool = shutil.which("pdffonts")
    if not tool:
        raise RuntimeError("pdffonts unavailable")
    result = subprocess.run(
        [tool, str(PDF)], check=True, capture_output=True, text=True, errors="replace"
    )
    lines = [line.rstrip() for line in result.stdout.splitlines()]
    header = next(line for line in lines if line.startswith("name"))
    embed_column_start = header.index("emb")
    data_lines = lines[lines.index(header) + 2 :]
    data_lines = [line for line in data_lines if line.strip()]
    unembedded = [
        line
        for line in data_lines
        if line[embed_column_start : embed_column_start + 3].strip().lower() != "yes"
    ]

    successor = dict(attempt1)
    successor["schema"] = "interlanguage.stacks_cjk.ko_cumulative_visual_precheck/v2"
    successor["record_id"] = "STACKS-CJK-KO-CUMULATIVE-R3-VISUAL-PRECHECK-R2-20260905"
    successor["supersedes_failed_precheck"] = identity(ATTEMPT1)
    successor["font_parse_correction"] = {
        "attempt1_error": "Whitespace token index 3 selected the encoding field for CID fonts instead of the emb field.",
        "corrected_method": "Read the fixed-width emb column start from the pdffonts header and slice each data row at that column.",
        "pdffonts_header": header,
        "embed_column_start_zero_based": embed_column_start,
        "font_rows": len(data_lines),
        "unembedded_font_rows": len(unembedded),
        "render_and_contact_sheet_bytes_changed": False,
    }
    successor["font_tool"] = str(Path(tool).resolve()).replace("\\", "/")
    successor["font_inventory_lines"] = data_lines
    successor["unembedded_fonts"] = unembedded
    required_pass = (
        not successor["blank_pages"]
        and not successor["pages_touching_raster_edge"]
        and successor["uniform_page_dimensions"]
        and not successor["characters_outside_page"]
        and not successor["links_outside_page"]
        and not unembedded
        and successor["contact_sheet_page_coverage_exactly_once"]
        and successor["page_numbers_exactly_1_through_572"]
        and successor["pages_rendered"] == successor["pages_expected"] == 572
    )
    successor["result"] = (
        "PASS_DETERMINISTIC_PRECHECK_PENDING_INDEPENDENT_VISUAL_INSPECTION"
        if required_pass
        else "FAIL"
    )
    SUCCESSOR.write_text(
        json.dumps(successor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    json.loads(SUCCESSOR.read_text(encoding="utf-8"))
    print(json.dumps({"successor": identity(SUCCESSOR), "result": successor["result"]}))
    if not required_pass:
        raise RuntimeError("Corrected deterministic visual precheck still fails")


if __name__ == "__main__":
    main()
