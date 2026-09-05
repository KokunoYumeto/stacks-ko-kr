from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
STACK_ROOT = ROOT.parents[2]
KO_ROOT = ROOT.parent
R6 = KO_ROOT / "integration-20260905-r6-cumulative-49"
R7 = KO_ROOT / "integration-20260905-r7-p11-terminal"
R8 = KO_ROOT / "integration-20260905-r8-p10-terminal"
PLAN = ROOT / "BUILD_PLAN.json"

EXPECTED = {
    R6 / "BUILD_PLAN.json": (9719, "E716D41B056E572B77D4FCFDC4D92D548347618CC0C0FF4A63A22A7EB0844F22"),
    R6 / "receipts" / "R6_COMPONENT_AND_CUMULATIVE_BUILD.json": (857587, "4B94F5DB1FAF022C9DD40254B00837D5810BDDEEE2E0F7BA19CBDBFFA0059BB5"),
    R6 / "receipts" / "R6_PAGE_COMPLETE_VISUAL_QA.json": (214902, "7810B9E3CDC866B43BEEAED9196FA54263B4B7BEDBCD91634A5938576CE25112"),
    R6 / "output" / "pdf" / "stacks-project-ko-kr-cumulative-r6-49-chapters.pdf": (23566552, "461F8B4881E317D9DD787400E1BBEC5D8EDB46D874C37F82F7AC9EFEBDC06765"),
    R7 / "IMPORT_MANIFEST.json": (13975, "C834E68626E13BF2055E614848DF484C8B559720CD00CDFB81C907C4B9DEDB42"),
    R7 / "VERIFICATION_RECEIPT.json": (9372, "FC6AB318B2EF15D05739EE86508A9B0F00502A48BCFEFAF9F1A488E78C8B5CE0"),
    R8 / "IMPORT_MANIFEST.json": (21409, "5B4685682D8961D93F978C0D01BCB6DD81674F861042F7EAD934B2AD48918173"),
    R8 / "VERIFICATION_RECEIPT.json": (13470, "9163B9EA1766AF0529C3482BEC7CC0098FFD909AFF41710C747F4D6AD524F209"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def identity(path: Path, base: Path = ROOT) -> dict[str, object]:
    return {
        "path": path.relative_to(base).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


def external_identity(path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(STACK_ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


def require(path: Path, size: int, sha256: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"required file is absent: {path}")
    if path.stat().st_size != size or digest(path) != sha256:
        raise RuntimeError(f"identity mismatch: {path}")


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def tree_identity(root: Path, base: Path = ROOT) -> dict[str, object]:
    rows: list[str] = []
    total = 0
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix(),
    ):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        total += size
        rows.append(f"{relative}\t{size}\t{digest(path)}\n")
    payload = "".join(rows).encode("utf-8")
    return {
        "path": root.relative_to(base).as_posix(),
        "files": len(rows),
        "bytes": total,
        "serialization_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest().upper(),
    }


def copy_file(source: Path, destination: Path) -> dict[str, object]:
    if destination.exists():
        if not destination.is_file():
            raise RuntimeError(f"staged destination is not a file: {destination}")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    if destination.stat().st_size != source.stat().st_size or digest(destination) != digest(source):
        raise RuntimeError(f"copy identity mismatch: {source} -> {destination}")
    return identity(destination)


def copy_tree(source: Path, destination: Path) -> dict[str, object]:
    if destination.exists():
        if not destination.is_dir():
            raise RuntimeError(f"staged destination is not a directory: {destination}")
    else:
        shutil.copytree(source, destination)
    source_tree = tree_identity(source, R6)
    destination_tree = tree_identity(destination)
    for key in ("files", "bytes", "serialization_bytes", "sha256"):
        if source_tree[key] != destination_tree[key]:
            raise RuntimeError(f"tree copy mismatch: {source} -> {destination}")
    return destination_tree


def atomic_json(path: Path, value: object) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite: {path}")
    temporary = path.with_name(path.name + ".tmp")
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def main() -> None:
    if PLAN.exists():
        raise RuntimeError("r9 build plan already exists; inspect rather than restage")
    for path, expected in EXPECTED.items():
        require(path, *expected)

    r6_plan = read_json(R6 / "BUILD_PLAN.json")
    r6_build = read_json(R6 / "receipts" / "R6_COMPONENT_AND_CUMULATIVE_BUILD.json")
    r6_visual = read_json(R6 / "receipts" / "R6_PAGE_COMPLETE_VISUAL_QA.json")
    r7_manifest = read_json(R7 / "IMPORT_MANIFEST.json")
    r7_verification = read_json(R7 / "VERIFICATION_RECEIPT.json")
    r8_manifest = read_json(R8 / "IMPORT_MANIFEST.json")
    r8_verification = read_json(R8 / "VERIFICATION_RECEIPT.json")

    if r6_visual.get("result") != "PASS_PAGE_COMPLETE_CUMULATIVE_VISUAL_QA":
        raise RuntimeError("r6 visual predecessor is not terminal PASS")
    if int(r6_visual["pdf"]["pages"]) != 2158:
        raise RuntimeError("r6 visual predecessor page count changed")
    if r7_verification.get("result") != "pass" or r8_verification.get("result") != "pass":
        raise RuntimeError("r7/r8 import verification is not PASS")
    if r8_verification.get("status") != "PASS_STAGED_ONLY_R6_VISUAL_BASELINE_CLOSED_SUCCESSOR_READY":
        raise RuntimeError("r8 import verification does not authorize the successor")

    added = list(r8_manifest["selection"]["included"]) + list(r7_manifest["selection"]["included"])
    if [int(item["chapter"]) for item in added] != [89, 90, 101]:
        raise RuntimeError("successor addition set changed")
    titles = {
        89: "곡면의 특이점 해소 재론",
        90: "형식 변형 이론",
        101: "대수 스택의 사상",
    }
    added_rows: list[dict[str, object]] = []
    for row in added:
        chapter = int(row["chapter"])
        part = str(row["part"])
        stem = str(row["stem"])
        source_record = row["source"]
        target_record = row["target"]
        producer_pdf_record = row["producer_pdf"]
        qa_record = row["producer_qa"]
        source = STACK_ROOT / str(source_record["path"])
        target = STACK_ROOT / str(target_record["path"])
        producer_pdf = STACK_ROOT / str(producer_pdf_record["path"])
        producer_qa = STACK_ROOT / str(qa_record["path"])
        for path, record in (
            (source, source_record),
            (target, target_record),
            (producer_pdf, producer_pdf_record),
            (producer_qa, qa_record),
        ):
            require(path, int(record["bytes"]), str(record["sha256"]))
        pages = len(PdfReader(producer_pdf, strict=True).pages)
        if pages != int(producer_pdf_record["pages"]):
            raise RuntimeError(f"chapter {chapter}: producer PDF page count changed")
        local_target = ROOT / "inputs" / part / "ko" / f"{stem}.tex"
        local_authority = ROOT / "authority" / "a04446e" / f"{stem}.tex"
        local_target_id = copy_file(target, local_target)
        local_authority_id = copy_file(source, local_authority)
        added_rows.append(
            {
                "chapter": chapter,
                "part": part,
                "stem": stem,
                "title": titles[chapter],
                "source": dict(source_record),
                "target": dict(target_record),
                "producer_pdf": dict(producer_pdf_record),
                "producer_qa": dict(qa_record),
                "producer_additional_evidence": {
                    key: value
                    for key, value in row.items()
                    if key
                    in {
                        "structural_receipt",
                        "formula_receipt",
                        "pdf_object_and_visual_receipt",
                        "complete_structural_receipt",
                        "terminal_prefix_structural_receipt",
                        "structural_replay",
                        "producer_manifest_record",
                    }
                },
                "local_target": local_target_id,
                "local_authority": local_authority_id,
                "producer_pdf_pages_replayed": pages,
            }
        )

    r6_order = [int(value) for value in r6_plan["canonical_cumulative_order"]]
    if len(r6_order) != 49 or r6_order != sorted(r6_order):
        raise RuntimeError("closed r6 order is malformed")
    if set(r6_order) & {89, 90, 101}:
        raise RuntimeError("new chapters overlap closed r6")
    r6_starts = {int(item["chapter"]): item for item in r6_build["merge"]["chapter_starts"]}
    if list(r6_starts) != r6_order:
        raise RuntimeError("r6 build receipt chapter order changed")
    inherited_rows: list[dict[str, object]] = []
    for chapter in r6_order:
        row = r6_starts[chapter]
        source_pdf = R6 / str(row["pdf"]["path"])
        require(source_pdf, int(row["pdf"]["bytes"]), str(row["pdf"]["sha256"]))
        if len(PdfReader(source_pdf, strict=True).pages) != int(row["pages"]):
            raise RuntimeError(f"r6 chapter {chapter}: component page count changed")
        destination = ROOT / "evidence" / "inherited-components" / f"ch{chapter:03d}-{row['stem']}.pdf"
        inherited_rows.append(
            {
                "chapter": chapter,
                "stem": row["stem"],
                "title": row["title"],
                "r6_provenance": row["provenance"],
                "r6_global_page_index_zero_based": int(row["page_index_zero_based"]),
                "pages": int(row["pages"]),
                "r6_pdf": dict(row["pdf"]),
                "local_pdf": copy_file(source_pdf, destination),
            }
        )

    copied_trees = {
        "corrected_korean_profile": copy_tree(R6 / "support" / "profile", ROOT / "support" / "profile"),
        "dependencies": copy_tree(R6 / "support" / "dependencies", ROOT / "support" / "dependencies"),
        "complete_authority_universe": copy_tree(R6 / "support" / "frozen-authority", ROOT / "support" / "frozen-authority"),
        "qa_tools": copy_tree(R6 / "support" / "tools", ROOT / "support" / "tools"),
    }
    for name in (
        "run_tex_serialized.ps1",
        "visual_qa_common.py",
        "record_visual_review.py",
    ):
        copy_file(R6 / "build" / name, ROOT / "build" / name)

    canonical_order = [int(value) for value in r8_manifest["projected_52_chapter_successor"]["canonical_order"]]
    if canonical_order != sorted(r6_order + [89, 90, 101]) or len(canonical_order) != 52:
        raise RuntimeError("projected r9 canonical order mismatch")

    plan = {
        "schema": "interlanguage.stacks_cjk.ko_kr_cumulative_r9_build_plan/v1",
        "record_id": "STACKS-CJK-KO-KR-R9-CUMULATIVE-52-PLAN-20260905",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_STAGED_PENDING_NON_TEX_PREFLIGHT_AND_MUTEX_SERIALIZED_BUILD",
        "locale": "ko-KR",
        "authority_commit": "a04446e57ec1fbc252a871afcec7752fb2807b14",
        "closed_r6_predecessor": {
            "build_plan": external_identity(R6 / "BUILD_PLAN.json"),
            "build_receipt": external_identity(R6 / "receipts" / "R6_COMPONENT_AND_CUMULATIVE_BUILD.json"),
            "page_complete_visual_receipt": external_identity(R6 / "receipts" / "R6_PAGE_COMPLETE_VISUAL_QA.json"),
            "cumulative_pdf": {
                **external_identity(R6 / "output" / "pdf" / "stacks-project-ko-kr-cumulative-r6-49-chapters.pdf"),
                "pages": 2158,
            },
            "chapter_count": 49,
        },
        "terminal_imports": {
            "p10_r8_manifest": external_identity(R8 / "IMPORT_MANIFEST.json"),
            "p10_r8_verification": external_identity(R8 / "VERIFICATION_RECEIPT.json"),
            "p11_r7_manifest": external_identity(R7 / "IMPORT_MANIFEST.json"),
            "p11_r7_verification": external_identity(R7 / "VERIFICATION_RECEIPT.json"),
        },
        "added_chapters": added_rows,
        "inherited_chapters": inherited_rows,
        "canonical_cumulative_order": canonical_order,
        "frozen_local_trees": {
            "added_inputs": tree_identity(ROOT / "inputs"),
            "added_authority": tree_identity(ROOT / "authority" / "a04446e"),
            "inherited_r6_components": tree_identity(ROOT / "evidence" / "inherited-components"),
            **copied_trees,
        },
        "build_contract": {
            "tex_mutex": "Global\\InterlanguageTeXSlotV1",
            "mutex_acquisition_timeout_seconds": 30,
            "component_passes": ["xelatex", "bibtex", "xelatex", "xelatex", "xelatex"],
            "source_date_epoch": "1788562238",
            "added_component_count": 3,
            "inherited_component_count": 49,
            "final_cumulative_chapter_count": 52,
            "xr_aux_files_per_profile": 117,
            "corrected_korean_cjkspace_directive_exact_count": 1,
            "producer_files_mutated": False,
            "predecessor_files_mutated": False,
            "publication_before_cumulative_build_and_visual_qa": False,
        },
        "visual_contract": {
            "renderer": "Poppler pdftoppm at 144 dpi for exact r6 page-image equivalence and new-page review",
            "inherited_pages": 2158,
            "inheritance_rule": "Every r6 component-local page must render byte-identically in r9 after canonical page remapping; otherwise that page requires fresh review.",
            "fresh_units": [89, 90, 101],
            "fresh_review_rule": "Render and explicitly review every new page plus every new warning locus at 288 dpi.",
        },
        "next_exact_action": "Run non-TeX preflight, exact three-unit replay, exact 49-component inheritance replay, and generate three disjoint 117-AUX profiles. Then acquire Global\\InterlanguageTeXSlotV1 once for all three component builds, cumulative merge, deterministic replay, and immediate mechanical checks.",
    }
    atomic_json(PLAN, plan)
    print(json.dumps({"plan": identity(PLAN), "added": 3, "inherited": 49, "result": plan["status"]}))


if __name__ == "__main__":
    main()
