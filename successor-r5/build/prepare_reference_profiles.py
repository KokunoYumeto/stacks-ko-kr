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


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "support" / "frozen-authority"
DEPS = ROOT / "support" / "dependencies"
BASE_PROFILE = ROOT / "support" / "profile"
PROFILES = ROOT / "support" / "profiles-r2"
RECEIPT = ROOT / "receipts" / "P11_REFERENCE_CLOSURE_REPAIR.json"
FAILURE = ROOT / "receipts" / "P11_COMPONENT_BUILD_FAILURE_001.json"
AUTHORITY_COMMIT = "a04446e57ec1fbc252a871afcec7752fb2807b14"

EXPECTED_FROZEN_TREE = (119, 27688968, 10371, "DF01764B0EDA52EEF184304E8230D17D10CC206BD21DCC37F4309E51CF73F5F8")
EXPECTED_FAILED_BUILD = (2403, "7EBD435058624B6337EB9915A25942E286EFAC22C64FD68E2F6F35BCD73AB9AA")
EXPECTED_PREAMBLE = (9107, "CD56A8DB6F80F5D1644F1F94344F7BA3E3A95BD731D4F6FE09E3785B52A50A5E")

CHAPTERS = [
    (91, "defos"),
    (92, "cotangent"),
    (93, "examples-defos"),
    (94, "algebraic"),
    (95, "examples-stacks"),
    (96, "stacks-sheaves"),
    (97, "criteria"),
    (98, "artin"),
    (100, "stacks-properties"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def identity(path: Path) -> dict[str, object]:
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}


def require(path: Path, size: int, digest: str) -> dict[str, object]:
    got = identity(path)
    if got["bytes"] != size or got["sha256"] != digest:
        raise RuntimeError(f"identity mismatch: {path}")
    return got


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
    rows = []
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


def frozen_tree() -> dict[str, object]:
    rows = []
    total = 0
    for path in sorted(FROZEN.glob("*.tex"), key=lambda item: item.name):
        size = path.stat().st_size
        total += size
        rows.append(f"{path.name}\t{size}\t{sha256(path)}\n")
    serialized = "".join(rows).encode("utf-8")
    result = {
        "files": len(rows),
        "bytes": total,
        "serialization_bytes": len(serialized),
        "sha256": hashlib.sha256(serialized).hexdigest().upper(),
    }
    observed = (result["files"], result["bytes"], result["serialization_bytes"], result["sha256"])
    if observed != EXPECTED_FROZEN_TREE:
        raise RuntimeError(f"frozen authority universe mismatch: {observed}")
    return result


def build_label_universe() -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    labels: dict[str, tuple[str, str]] = {}
    duplicates = []
    for path in sorted(FROZEN.glob("*.tex"), key=lambda item: item.name):
        document = path.stem
        for local in re.findall(r"\\label\{([^{}]+)\}", strip_comments(path.read_text(encoding="utf-8"))):
            full = f"{document}-{local}"
            if full in labels:
                duplicates.append(full)
            labels[full] = (document, local)
    if duplicates:
        raise RuntimeError(f"duplicate full labels in frozen universe: {duplicates[:10]}")
    tags: dict[str, str] = {}
    for line in (DEPS / "tags" / "tags").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "," in line:
            tag, label = line.split(",", 1)
            if label in tags and tags[label] != tag:
                raise RuntimeError(f"ambiguous tag: {label}")
            tags[label] = tag
    return labels, tags


def fallback_value(document: str, local: str) -> str:
    if (document, local) != ("more-morphisms", "lemma-weighting-specialization"):
        raise RuntimeError(f"no authorized permanent-tag fallback: {document}-{local}")
    clean = strip_comments((FROZEN / f"{document}.tex").read_text(encoding="utf-8"))
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
                raise RuntimeError(f"frozen fallback changed: {value}")
            return value
    raise RuntimeError("fallback label absent")


def profile_tree(root: Path) -> dict[str, object]:
    rows = []
    total = 0
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        size = path.stat().st_size
        total += size
        rows.append(f"{rel}\t{size}\t{sha256(path)}\n")
    serialized = "".join(rows).encode("utf-8")
    return {
        "path": root.relative_to(ROOT).as_posix(),
        "files": len(rows),
        "bytes": total,
        "serialization_bytes": len(serialized),
        "sha256": hashlib.sha256(serialized).hexdigest().upper(),
    }


def main() -> None:
    if PROFILES.exists() or RECEIPT.exists():
        raise RuntimeError("reference repair output already exists; inspect rather than overwrite")
    frozen = frozen_tree()
    failure = require(FAILURE, *EXPECTED_FAILED_BUILD)
    preamble = BASE_PROFILE / "ko_preamble.tex"
    preamble_id = require(preamble, *EXPECTED_PREAMBLE)
    preamble_text = strip_comments(preamble.read_text(encoding="utf-8"))
    external_pairs = re.findall(r"\\externaldocument\[([^]]+)\]\{([^}]+)\}", preamble_text)
    if len(external_pairs) != 117 or len({document for _, document in external_pairs}) != 117:
        raise RuntimeError(f"external-document inventory mismatch: {len(external_pairs)}")
    if any(prefix != f"{document}-" for prefix, document in external_pairs):
        raise RuntimeError("external-document prefix mismatch")
    external_documents = [document for _, document in external_pairs]
    labels, tags = build_label_universe()
    PROFILES.mkdir()
    chapter_receipts = []
    total_external_occurrences = 0
    total_unique = 0
    fallbacks = []
    for chapter, stem in CHAPTERS:
        target = ROOT / "inputs" / "p11" / "ko" / f"{stem}.tex"
        clean = strip_comments(target.read_text(encoding="utf-8"))
        local_labels = set(re.findall(r"\\label\{([^{}]+)\}", clean))
        references = re.findall(r"\\(?:ref|eqref|pageref|autoref)\{([^{}]+)\}", clean)
        external = [label for label in references if label not in local_labels]
        missing = sorted({label for label in external if label not in labels})
        if missing:
            raise RuntimeError(f"chapter {chapter}: missing or ambiguous external labels: {missing[:20]}")
        profile = PROFILES / f"ch{chapter:03d}-{stem}"
        aux = profile / "xr"
        aux.mkdir(parents=True)
        shutil.copyfile(preamble, profile / "preamble.tex")
        shutil.copyfile(preamble, profile / "ko_preamble.tex")
        for filename in ("chapters.tex", "ko_chapters.tex"):
            (profile / filename).write_text(
                "% Canonical cumulative navigation is supplied by the merged PDF outline.\n",
                encoding="utf-8",
                newline="\n",
            )
        mappings = []
        by_document: dict[str, list[str]] = defaultdict(list)
        local_fallbacks = []
        for full in sorted(set(external), key=str.casefold):
            document, local = labels[full]
            tag = tags.get(full)
            source = "permanent_tag"
            if tag is None:
                tag = fallback_value(document, local)
                source = "frozen_counter_fallback"
                row = {"chapter": chapter, "full_label": full, "document": document, "local_label": local, "value": tag, "occurrences": external.count(full)}
                local_fallbacks.append(row)
                fallbacks.append(row)
            mappings.append({"full_label": full, "tag": tag, "aux_document": document, "local_label": local, "value_source": source})
            by_document[document].append(f"\\newlabel{{{local}}}{{{{{tag}}}{{0}}}}")
        for document in external_documents:
            lines = sorted(set(by_document.get(document, [])))
            (aux / f"{document}.aux").write_text("\\relax\n" + "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")
        map_path = profile / "xr-map.tsv"
        with map_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["full_label", "tag", "aux_document", "local_label"], delimiter="\t", lineterminator="\r\n", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(mappings)
        if len(list(aux.glob("*.aux"))) != 117:
            raise RuntimeError(f"chapter {chapter}: generated AUX universe incomplete")
        total_external_occurrences += len(external)
        total_unique += len(mappings)
        chapter_receipts.append({
            "chapter": chapter,
            "stem": stem,
            "target": identity(target),
            "references": {
                "total_occurrences": len(references),
                "local_occurrences": len(references) - len(external),
                "external_occurrences": len(external),
                "external_unique": len(mappings),
                "missing_or_ambiguous": 0,
                "frozen_counter_fallbacks": local_fallbacks,
            },
            "xr_map": identity(map_path),
            "profile": profile_tree(profile),
            "result": "PASS_COMPLETE_EXACT_REFERENCE_CLOSURE",
        })
    receipt = {
        "schema": "interlanguage.stacks_cjk.ko_p11_reference_closure_repair/v1",
        "record_id": "STACKS-CJK-KO-P11-R5-XR-REPAIR-20260905",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "authority_commit": AUTHORITY_COMMIT,
        "trigger_failure": failure,
        "diagnosis": "The initial preflight counted 117 AUX files but inherited the Chapter 99 profile, whose files intentionally contained only Chapter 99's required labels. Chapter 91 consequently completed five TeX passes with unresolved external references.",
        "repair": "Generate one disjoint profile per new P11 chapter from the exact target's external reference set, the complete frozen 119-file authority label universe, and the permanent tag registry; preserve the original failed attempt and original preflight as adverse history.",
        "frozen_authority_tree": frozen,
        "preamble": preamble_id,
        "external_documents": len(external_documents),
        "label_universe": {"full_labels": len(labels), "ambiguous": 0},
        "chapters": chapter_receipts,
        "totals": {
            "chapters": len(chapter_receipts),
            "external_reference_occurrences": total_external_occurrences,
            "external_unique_sum": total_unique,
            "missing_or_ambiguous": 0,
            "fallback_bindings": fallbacks,
        },
        "profile_tree": profile_tree(PROFILES),
        "producer_files_mutated": False,
        "failed_attempt_mutated": False,
        "original_plan_or_preflight_rewritten": False,
        "result": "PASS_APPEND_ONLY_REFERENCE_CLOSURE_REPAIR_READY_FOR_NEW_SERIALIZED_ATTEMPT",
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps({"receipt": identity(RECEIPT), "profiles": len(chapter_receipts), "external_occurrences": total_external_occurrences, "unique_sum": total_unique, "fallbacks": len(fallbacks), "result": receipt["result"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
