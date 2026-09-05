from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VISUAL = ROOT / "evidence" / "visual-qa-r9"
PRECHECK = VISUAL / "DETERMINISTIC_VISUAL_DELTA_PRECHECK.json"
CLASSIFICATION = VISUAL / "VISUAL_WARNING_CLASSIFICATION_REPAIR_001.json"
SUCCESSOR = VISUAL / "DETERMINISTIC_VISUAL_DELTA_PRECHECK_R1.json"
BUILD = ROOT / "receipts" / "R9_COMPONENT_AND_CUMULATIVE_BUILD.json"

EXPECTED_PRECHECK = {
    "bytes": 7680,
    "sha256": "0E56E11CAA8051E78BDAE64A9FBD4BBF3B2CB4ADAFA3CE1F707E2CC86BCF4386",
}
EXPECTED_BUILD = {
    "bytes": 564017,
    "sha256": "796DC8DB2A01C4CDD007D91302B5BFDC4F07B13B51E962BBBF218732C66A98EC",
}
ALLOWED_WARNING = "LaTeX Warning: You have requested release `2026/06/01' of LaTeX,"
EXPECTED_CHAPTERS = (89, 90, 101)
PASS_RESULT = "PASS_DETERMINISTIC_VISUAL_DELTA_PRECHECK_AFTER_BENIGN_WARNING_CLASSIFICATION_PENDING_161_FRESH_PAGE_REVIEWS"


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


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_once(path: Path, value: object) -> None:
    data = encoded(value)
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"refusing to overwrite nonidentical append-only receipt: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def main() -> None:
    require_identity(PRECHECK, EXPECTED_PRECHECK)
    require_identity(BUILD, EXPECTED_BUILD)
    precheck = load(PRECHECK)
    build = load(BUILD)
    if precheck.get("result") != "FAIL":
        raise RuntimeError("predecessor precheck is no longer the preserved FAIL receipt")
    if build.get("result") != "PASS_BUILD_AND_DETERMINISTIC_CUMULATIVE_ASSEMBLY_PENDING_PAGE_COMPLETE_VISUAL_QA":
        raise RuntimeError("manager build is not the expected PASS pending visual-QA state")

    hard_checks = {
        "pdf_pages_exact": precheck.get("pdf", {}).get("pages") == 2316,
        "page_dimensions_uniform_a4_raster": precheck.get("page_dimensions") == [[1224, 1584]],
        "blank_pages_zero": precheck.get("blank_pages") == [],
        "raster_edge_touch_pages_zero": precheck.get("pages_touching_raster_edge") == [],
        "inherited_pages_exact": precheck.get("inherited_pages") == 2158,
        "inherited_pixel_equivalent_exact": precheck.get("inherited_decoded_pixel_equivalent_pages") == 2158,
        "inherited_pixel_mismatches_zero": precheck.get("inherited_pixel_mismatch_pages") == [],
        "new_chapter_pages_exact": precheck.get("new_chapter_pages") == 158,
        "fresh_review_pages_exact": precheck.get("fresh_review_pages") == 161,
        "fresh_review_sheets_exact": precheck.get("fresh_review_sheets") == 41,
    }
    if not all(hard_checks.values()):
        raise RuntimeError(f"non-warning precheck condition failed: {hard_checks}")

    precheck_warnings = precheck.get("new_manager_warning_chapters")
    if not isinstance(precheck_warnings, list):
        raise RuntimeError("precheck warning inventory is missing")
    if [int(row["chapter"]) for row in precheck_warnings] != list(EXPECTED_CHAPTERS):
        raise RuntimeError("precheck warning chapter inventory changed")

    components = build.get("components")
    if not isinstance(components, list) or [int(row["chapter"]) for row in components] != list(EXPECTED_CHAPTERS):
        raise RuntimeError("component inventory changed")

    classifications: list[dict[str, object]] = []
    for component, reported in zip(components, precheck_warnings, strict=True):
        chapter = int(component["chapter"])
        flags = component.get("log_flags")
        if not isinstance(flags, dict) or any(int(value) != 0 for value in flags.values()):
            raise RuntimeError(f"chapter {chapter} has a nonzero mechanical log flag")
        if component.get("bibtex_warning_lines") != []:
            raise RuntimeError(f"chapter {chapter} has a BibTeX warning")
        policy = component.get("bibtex_warning_policy")
        if not isinstance(policy, dict) or policy.get("unexpected_warning_lines") != []:
            raise RuntimeError(f"chapter {chapter} has an unexpected BibTeX warning policy entry")

        log_path = ROOT / str(component["tex_log"]["path"])
        blg_path = ROOT / str(component["blg"]["path"])
        for path, claim in ((log_path, component["tex_log"]), (blg_path, component["blg"])):
            require_identity(path, {"bytes": int(claim["bytes"]), "sha256": str(claim["sha256"])})
        raw_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        raw_lines.extend(blg_path.read_text(encoding="utf-8", errors="replace").splitlines())
        observed = [
            line.strip()
            for line in raw_lines
            if "Warning:" in line or line.startswith(("Overfull ", "Underfull ", "Warning--"))
        ]
        expected = [ALLOWED_WARNING, ALLOWED_WARNING, ALLOWED_WARNING]
        if observed != expected or reported.get("warning_lines") != expected:
            raise RuntimeError(f"chapter {chapter} warning inventory is not the exact benign three-line notice")
        classifications.append(
            {
                "chapter": chapter,
                "tex_log": identity(log_path),
                "blg": identity(blg_path),
                "warning_line": ALLOWED_WARNING,
                "occurrences": 3,
                "classification": "BENIGN_TOOLCHAIN_RELEASE_AVAILABILITY_NOTICE",
                "layout_locus": None,
                "layout_relevance": False,
                "adverse_evidence_preserved": True,
                "reason": "MiKTeX reports that the source requests a future LaTeX release; the build completed deterministically and every fatal, glyph, box, reference, citation, rerun, duplicate-destination, and multiply-defined-label flag is zero.",
                "mechanical_log_flags": flags,
            }
        )

    classification = {
        "schema": "interlanguage.stacks_cjk.ko_kr_r9_visual_warning_classification_repair/v1",
        "record_id": "STACKS-CJK-KO-KR-R9-VISUAL-WARNING-CLASSIFICATION-REPAIR-001",
        "predecessor_fail_precheck": identity(PRECHECK),
        "build_receipt": identity(BUILD),
        "repair_scope": "append-only classification of the sole failing predicate; no TeX or render rerun and no predecessor mutation",
        "non_warning_hard_checks": hard_checks,
        "warning_occurrences": 9,
        "warning_chapters": list(EXPECTED_CHAPTERS),
        "classifications": classifications,
        "warning_locus_review_required": False,
        "reason_no_warning_locus": "The notice describes requested toolchain release availability and names no page, line, box, glyph, object, or rendered geometry.",
        "predecessor_preserved_as_adverse_evidence": True,
        "result": "PASS_BENIGN_NON_LAYOUT_WARNING_CLASSIFICATION",
    }
    write_once(CLASSIFICATION, classification)

    successor = dict(precheck)
    successor.update(
        {
            "schema": "interlanguage.stacks_cjk.ko_kr_r9_visual_delta_precheck/v2",
            "record_id": "STACKS-CJK-KO-KR-R9-VISUAL-DELTA-PRECHECK-R1",
            "predecessor_fail_precheck": identity(PRECHECK),
            "warning_classification_repair": identity(CLASSIFICATION),
            "new_manager_warning_classification": classifications,
            "unclassified_or_layout_relevant_new_manager_warnings": [],
            "result": PASS_RESULT,
        }
    )
    write_once(SUCCESSOR, successor)
    print(
        json.dumps(
            {
                "classification": identity(CLASSIFICATION),
                "successor": identity(SUCCESSOR),
                "result": PASS_RESULT,
            }
        )
    )


if __name__ == "__main__":
    main()
