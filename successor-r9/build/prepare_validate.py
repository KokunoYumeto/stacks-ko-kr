from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
STACK_ROOT = ROOT.parents[2]
PLAN_PATH = ROOT / "BUILD_PLAN.json"
PROFILE_BASE = ROOT / "support" / "profile"
PROFILES = ROOT / "support" / "profiles-r9"
FROZEN_AUTHORITY = ROOT / "support" / "frozen-authority"
DEPENDENCIES = ROOT / "support" / "dependencies"
RECEIPT = ROOT / "receipts" / "R9_PREFLIGHT_AND_REFERENCE_PROFILES.json"

EXPECTED_PLAN = (44999, "BF46DA7C4D877687E97982761A96443BD2A97B81A190A91349B0E6DD5BE1DA07")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def identity(path: Path, relative_to: Path = ROOT) -> dict[str, object]:
    return {
        "path": path.relative_to(relative_to).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def require(path: Path, size: int, digest: str, relative_to: Path = ROOT) -> dict[str, object]:
    if not path.is_file():
        raise RuntimeError(f"required file absent: {path}")
    got = identity(path, relative_to)
    if got["bytes"] != size or got["sha256"] != digest:
        raise RuntimeError(f"identity mismatch: {path}; expected {size}/{digest}, got {got['bytes']}/{got['sha256']}")
    return got


def require_record(record: dict[str, object], base: Path) -> dict[str, object]:
    return require(base / str(record["path"]), int(record["bytes"]), str(record["sha256"]), base)


def tree_identity(root: Path) -> dict[str, object]:
    rows: list[str] = []
    total = 0
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        total += size
        rows.append(f"{relative}\t{size}\t{sha256(path)}\n")
    payload = "".join(rows).encode("utf-8")
    return {
        "path": root.relative_to(ROOT).as_posix(),
        "files": len(rows),
        "bytes": total,
        "serialization_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest().upper(),
    }


def require_tree(record: dict[str, object]) -> dict[str, object]:
    observed = tree_identity(ROOT / str(record["path"]))
    keys = ("path", "files", "bytes", "serialization_bytes", "sha256")
    if any(observed[key] != record[key] for key in keys):
        raise RuntimeError(f"tree mismatch: {record['path']}; expected {record}, got {observed}")
    return observed


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if path.exists() or temporary.exists():
        raise RuntimeError(f"refusing to overwrite: {path}")
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def strip_comments(text: str) -> str:
    rows: list[str] = []
    for line in text.splitlines():
        cut = len(line)
        for index, char in enumerate(line):
            if char != "%":
                continue
            slashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                slashes += 1
                cursor -= 1
            if slashes % 2 == 0:
                cut = index
                break
        rows.append(line[:cut])
    return "\n".join(rows) + "\n"


def label_universe() -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    labels: dict[str, tuple[str, str]] = {}
    duplicates: list[str] = []
    for path in sorted(FROZEN_AUTHORITY.glob("*.tex"), key=lambda item: item.name):
        document = path.stem
        clean = strip_comments(path.read_text(encoding="utf-8", errors="strict"))
        for local in re.findall(r"\\label\{([^{}]+)\}", clean):
            full = f"{document}-{local}"
            if full in labels:
                duplicates.append(full)
            labels[full] = (document, local)
    if duplicates:
        raise RuntimeError(f"duplicate full labels in frozen authority: {duplicates[:20]}")
    tags: dict[str, str] = {}
    for line in (DEPENDENCIES / "tags" / "tags").read_text(encoding="utf-8", errors="strict").splitlines():
        if line and not line.startswith("#") and "," in line:
            tag, label = line.split(",", 1)
            if label in tags and tags[label] != tag:
                raise RuntimeError(f"ambiguous permanent tag: {label}")
            tags[label] = tag
    return labels, tags


def fallback_value(document: str, local: str) -> str:
    if (document, local) != ("more-morphisms", "lemma-weighting-specialization"):
        raise RuntimeError(f"no authorized frozen-counter fallback: {document}-{local}")
    clean = strip_comments((FROZEN_AUTHORITY / f"{document}.tex").read_text(encoding="utf-8", errors="strict"))
    section = 0
    item = 0
    theorem = re.compile(r"\\begin\{(?:theorem|proposition|lemma|definition|example|exercise|situation|remark|remarks)\}")
    for line in clean.splitlines():
        if re.match(r"^\\section\{", line):
            section += 1
            item = 0
        if theorem.search(line):
            item += 1
        if f"\\label{{{local}}}" in line:
            value = f"{section}.{item}"
            if value != "75.9":
                raise RuntimeError(f"frozen fallback value changed: {value}")
            return value
    raise RuntimeError("frozen fallback label absent")


def make_profiles(plan: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, object]]:
    if PROFILES.exists():
        raise RuntimeError("profile output already exists; inspect rather than overwrite")
    preamble = PROFILE_BASE / "ko_preamble.tex"
    clean_preamble = strip_comments(preamble.read_text(encoding="utf-8", errors="strict"))
    external_pairs = re.findall(r"\\externaldocument\[([^]]+)\]\{([^}]+)\}", clean_preamble)
    if len(external_pairs) != 117 or len({document for _, document in external_pairs}) != 117:
        raise RuntimeError(f"base profile does not bind exactly 117 external documents: {len(external_pairs)}")
    if any(prefix != f"{document}-" for prefix, document in external_pairs):
        raise RuntimeError("external-document prefix mismatch")
    if clean_preamble.count(r"\xeCJKsetup{CJKspace=true}") != 1:
        raise RuntimeError("corrected Korean CJK-space directive count is not one")
    external_documents = [document for _, document in external_pairs]
    labels, tags = label_universe()
    PROFILES.mkdir()
    chapter_rows: list[dict[str, object]] = []
    for chapter in plan["added_chapters"]:
        number = int(chapter["chapter"])
        part = str(chapter["part"])
        stem = str(chapter["stem"])
        target = ROOT / "inputs" / part / "ko" / f"{stem}.tex"
        clean = strip_comments(target.read_text(encoding="utf-8", errors="strict"))
        local_labels = set(re.findall(r"\\label\{([^{}]+)\}", clean))
        references = re.findall(r"\\(?:ref|eqref|pageref|autoref)\{([^{}]+)\}", clean)
        external = [label for label in references if label not in local_labels]
        missing = sorted({label for label in external if label not in labels})
        if missing:
            raise RuntimeError(f"chapter {number}: external labels absent from frozen authority: {missing[:20]}")
        profile = PROFILES / f"ch{number:03d}-{stem}"
        aux = profile / "xr"
        aux.mkdir(parents=True)
        shutil.copyfile(preamble, profile / "preamble.tex")
        shutil.copyfile(preamble, profile / "ko_preamble.tex")
        for filename in ("chapters.tex", "ko_chapters.tex"):
            (profile / filename).write_text(
                "% Canonical cumulative navigation is supplied by the manager-owned merged PDF outline.\n",
                encoding="utf-8",
                newline="\n",
            )
        mappings: list[dict[str, str]] = []
        grouped: dict[str, list[str]] = defaultdict(list)
        fallback_rows: list[dict[str, object]] = []
        for full in sorted(set(external), key=str.casefold):
            document, local = labels[full]
            value = tags.get(full)
            source = "permanent_tag"
            if value is None:
                value = fallback_value(document, local)
                source = "frozen_counter_fallback"
                fallback_rows.append({"full_label": full, "value": value, "occurrences": external.count(full)})
            mappings.append({"full_label": full, "tag": value, "aux_document": document, "local_label": local, "value_source": source})
            grouped[document].append(f"\\newlabel{{{local}}}{{{{{value}}}{{0}}}}")
        for document in external_documents:
            lines = sorted(set(grouped.get(document, [])))
            (aux / f"{document}.aux").write_text("\\relax\n" + "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")
        map_path = profile / "xr-map.tsv"
        with map_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["full_label", "tag", "aux_document", "local_label", "value_source"], delimiter="\t", lineterminator="\r\n")
            writer.writeheader()
            writer.writerows(mappings)
        if len(list(aux.glob("*.aux"))) != 117:
            raise RuntimeError(f"chapter {number}: generated profile lacks the 117-AUX closure")
        chapter_rows.append({
            "chapter": number,
            "part": part,
            "stem": stem,
            "target": identity(target),
            "reference_occurrences": len(references),
            "external_reference_occurrences": len(external),
            "external_reference_unique": len(mappings),
            "fallback_bindings": fallback_rows,
            "xr_map": identity(map_path),
            "profile": tree_identity(profile),
            "result": "PASS_COMPLETE_117_AUX_REFERENCE_PROFILE",
        })
    return chapter_rows, tree_identity(PROFILES)


def main() -> None:
    if RECEIPT.exists():
        raise RuntimeError("preflight receipt already exists; inspect rather than overwrite")
    plan_id = require(PLAN_PATH, *EXPECTED_PLAN)
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8", errors="strict"))
    if plan.get("status") != "PASS_STAGED_PENDING_NON_TEX_PREFLIGHT_AND_MUTEX_SERIALIZED_BUILD":
        raise RuntimeError("build plan is not in the staged state")
    trees = {name: require_tree(record) for name, record in plan["frozen_local_trees"].items()}

    predecessor_records = {
        name: require_record(record, STACK_ROOT)
        for name, record in plan["closed_r6_predecessor"].items()
        if isinstance(record, dict) and {"path", "bytes", "sha256"} <= set(record)
    }
    import_records = {
        name: require_record(record, STACK_ROOT)
        for name, record in plan["terminal_imports"].items()
    }
    r6_visual = json.loads(
        (STACK_ROOT / str(plan["closed_r6_predecessor"]["page_complete_visual_receipt"]["path"])).read_text(
            encoding="utf-8", errors="strict"
        )
    )
    if (
        r6_visual.get("result") != "PASS_PAGE_COMPLETE_CUMULATIVE_VISUAL_QA"
        or int(r6_visual.get("explicit_page_review", {}).get("pages_reviewed", -1)) != 2158
        or int(r6_visual.get("explicit_page_review", {}).get("pages_failed", -1)) != 0
        or int(r6_visual.get("warning_locus_review", {}).get("rows_reviewed", -1)) != 247
        or int(r6_visual.get("warning_locus_review", {}).get("rows_failed", -1)) != 0
    ):
        raise RuntimeError("closed r6 page-complete visual receipt changed")

    for field in ("p10_r8_manifest", "p10_r8_verification", "p11_r7_manifest", "p11_r7_verification"):
        value = json.loads((STACK_ROOT / str(plan["terminal_imports"][field]["path"])).read_text(encoding="utf-8", errors="strict"))
        if field.endswith("verification") and value.get("result") != "pass":
            raise RuntimeError(f"terminal import verification is not PASS: {field}")

    added = [(int(item["chapter"]), str(item["part"]), str(item["stem"])) for item in plan["added_chapters"]]
    if added != [(89, "p10", "spaces-resolve"), (90, "p10", "formal-defos"), (101, "p11", "stacks-morphisms")]:
        raise RuntimeError("r9 addition set or order changed")
    inherited_numbers = [int(item["chapter"]) for item in plan["inherited_chapters"]]
    if len(inherited_numbers) != 49 or len(set(inherited_numbers)) != 49:
        raise RuntimeError("r9 inherited chapter set is not exactly 49 unique chapters")
    if set(plan["canonical_cumulative_order"]) != {item[0] for item in added} | set(inherited_numbers):
        raise RuntimeError("cumulative chapter set mismatch")
    if list(plan["canonical_cumulative_order"]) != sorted(plan["canonical_cumulative_order"]):
        raise RuntimeError("cumulative chapter order is not canonical ascending order")

    source_replay: list[dict[str, object]] = []
    for row in plan["added_chapters"]:
        number = int(row["chapter"])
        part = str(row["part"])
        stem = str(row["stem"])
        producer_source = require_record(row["source"], STACK_ROOT)
        producer_target = require_record(row["target"], STACK_ROOT)
        producer_pdf = require_record(row["producer_pdf"], STACK_ROOT)
        producer_qa = require_record(row["producer_qa"], STACK_ROOT)
        local_target = require_record(row["local_target"], ROOT)
        local_authority = require_record(row["local_authority"], ROOT)
        if local_target["bytes"] != producer_target["bytes"] or local_target["sha256"] != producer_target["sha256"]:
            raise RuntimeError(f"chapter {number}: local target differs from producer")
        if local_authority["bytes"] != producer_source["bytes"] or local_authority["sha256"] != producer_source["sha256"]:
            raise RuntimeError(f"chapter {number}: local authority differs from producer authority")
        pdf_path = STACK_ROOT / str(row["producer_pdf"]["path"])
        pages = len(PdfReader(pdf_path, strict=True).pages)
        if pages != int(row["producer_pdf"]["pages"]):
            raise RuntimeError(f"chapter {number}: producer PDF page count changed")
        qa_value = json.loads((STACK_ROOT / str(row["producer_qa"]["path"])).read_text(encoding="utf-8", errors="strict"))
        qa_disposition = qa_value.get("result", qa_value.get("status", qa_value.get("outcome", "")))
        if "pass" not in str(qa_disposition).casefold():
            raise RuntimeError(f"chapter {number}: producer QA is not PASS")
        additional_receipts = []
        for value in row.get("producer_additional_evidence", {}).values():
            if isinstance(value, dict) and {"path", "bytes", "sha256"} <= set(value):
                additional_receipts.append(require_record(value, STACK_ROOT))
                json.loads((STACK_ROOT / str(value["path"])).read_text(encoding="utf-8", errors="strict"))
        full_authority = FROZEN_AUTHORITY / f"{stem}.tex"
        if identity(ROOT / str(row["local_authority"]["path"]))["sha256"] != identity(full_authority)["sha256"] or full_authority.stat().st_size != int(row["local_authority"]["bytes"]):
            raise RuntimeError(f"chapter {number}: local authority copy differs from frozen authority universe")
        source_replay.append({
            "chapter": number,
            "producer_source": producer_source,
            "producer_target": producer_target,
            "local_target": local_target,
            "producer_qa": producer_qa,
            "producer_additional_receipts": additional_receipts,
            "producer_pdf": producer_pdf,
            "producer_pdf_pages": pages,
            "local_authority": local_authority,
            "result": "PASS_EXACT_TERMINAL_IMPORT_REPLAY",
        })

    r6_build_path = STACK_ROOT / str(plan["closed_r6_predecessor"]["build_receipt"]["path"])
    r6_build = json.loads(r6_build_path.read_text(encoding="utf-8", errors="strict"))
    if r6_build.get("result") != "PASS_BUILD_AND_DETERMINISTIC_CUMULATIVE_ASSEMBLY_PENDING_PAGE_COMPLETE_VISUAL_QA":
        raise RuntimeError("r6 component/cumulative build receipt is not PASS")
    r6_starts = {int(item["chapter"]): item for item in r6_build["merge"]["chapter_starts"]}
    inherited_replay: list[dict[str, object]] = []
    for item in plan["inherited_chapters"]:
        number = int(item["chapter"])
        stem = str(item["stem"])
        prior = r6_starts[number]
        local = ROOT / "evidence" / "inherited-components" / f"ch{number:03d}-{stem}.pdf"
        local_id = identity(local)
        if local_id != item["local_pdf"] or local_id["bytes"] != prior["pdf"]["bytes"] or local_id["sha256"] != prior["pdf"]["sha256"]:
            raise RuntimeError(f"chapter {number}: inherited component differs from r6")
        pages = len(PdfReader(local, strict=True).pages)
        if pages != int(prior["pages"]):
            raise RuntimeError(f"chapter {number}: inherited component page count changed")
        inherited_replay.append({"chapter": number, "stem": stem, "pdf": local_id, "pages": pages, "result": "PASS_EXACT_R6_INHERITANCE"})

    profiles, profile_tree = make_profiles(plan)
    receipt = {
        "schema": "interlanguage.stacks_cjk.ko_kr_r9_preflight_and_reference_profiles/v1",
        "record_id": "STACKS-CJK-KO-KR-R9-PREFLIGHT-XR-20260905",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "build_plan": plan_id,
        "closed_r6_predecessor": predecessor_records,
        "terminal_imports": import_records,
        "frozen_local_trees": trees,
        "added_source_replay": source_replay,
        "inherited_r6_component_replay": inherited_replay,
        "reference_profiles": profiles,
        "reference_profile_tree": profile_tree,
        "counts": {
            "added_sources": len(source_replay),
            "inherited_components": len(inherited_replay),
            "cumulative_chapters": len(plan["canonical_cumulative_order"]),
            "profiles": len(profiles),
            "aux_files_per_profile": 117,
        },
        "gates": {
            "terminal_import_identities": "r8 P10 and r7 P11 manifests plus verification receipts PASS",
            "producer_target_source_pdf_qa_replay": "3/3 PASS",
            "producer_pdf_page_counts": "3/3 PASS",
            "inherited_r6_components": "49/49 PASS",
            "r6_page_complete_visual_qa": "2158/2158 pages and 247/247 warning-locus/page rows PASS",
            "reference_closure": "3/3 profiles with 117 AUX files each PASS",
            "only_chapters_89_90_101_added": True,
            "producer_files_mutated": False,
            "tex_invoked": False,
        },
        "result": "PASS_READY_FOR_SINGLE_MUTEX_SERIALIZED_R9_BUILD",
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps({"receipt": identity(RECEIPT), "profiles": len(profiles), "inherited": len(inherited_replay), "result": receipt["result"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
