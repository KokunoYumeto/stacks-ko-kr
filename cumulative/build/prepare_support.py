from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CUMULATIVE = ROOT / "cumulative"
SUPPORT = CUMULATIVE / "support"
FROZEN = SUPPORT / "frozen-authority"
DEPS = SUPPORT / "dependencies"
PROFILES = SUPPORT / "profiles"
RECEIPT = CUMULATIVE / "receipts" / "SUPPORT_CLOSURE.json"
CHAPTER_INVENTORY = SUPPORT / "CHAPTERS.json"

AUTHORITY_COMMIT = "a04446e57ec1fbc252a871afcec7752fb2807b14"
CANONICAL_ORDER = [17, 60, 61, 62, 63, 64, 65, 66, 67, 68, 71, 99]
EXPECTED_IMPORT_MANIFEST = (10497, "8F5615A1977B3EBFB406CA1F816F5FC75E2CE9E0D1444A8DF8F536B3257DF480")
EXPECTED_IMPORT_VERIFICATION = (3079, "38D6FC9E17D73B3A9AADDB705B3857E162034098391B891BFD7878F165BA8CEC")
EXPECTED_FROZEN_TEX = (119, 27688968, 10371, "DF01764B0EDA52EEF184304E8230D17D10CC206BD21DCC37F4309E51CF73F5F8")
EXPECTED_PREAMBLE = (9107, "CD56A8DB6F80F5D1644F1F94344F7BA3E3A95BD731D4F6FE09E3785B52A50A5E")
EXPECTED_DEPS = {
    "my.bib": (210197, "AE2BA8729BECFD5BAA4FDC9448EB5332ED1EC727BD41CAF0937EBA02E367521E"),
    "stacks-project.cls": (60186, "DBACE0CB163B1B24F2816D89C547A3D487D51D59EDE0303FAD079E8AE3F93254"),
    "hyperref.cfg": (124, "50B882C8244281806C3245AFF3B70FB1577B01A405246896B2AC96A90C9C8307"),
    "tags/tags": (969923, "098F77CCE75F8359F1EACB22B7AA0088099B09E5B3FFCAD2DE513CBD1A8A9F1C"),
}
EXPECTED_NEW_XR_MAPS = {
    17: (7629, "65CC8779B2491DF80F24AB775C3862C8E195AA56C5C907089C2C70C32D69C7EC"),
    71: (18415, "81128170D8943DF38298B8E98DF57DB62A53F3D334D07FE4D0D6A23AD3F1C1C1"),
    99: (22761, "C76AA05A54234CBA2B885205EA5C024831704A347A39D92B1ED918DB320C363D"),
}
EXPECTED_CH62_FALLBACK_XR_MAP = (6387, "C57A7577A6B2C28F834F021629510C1C95888CF42745356061CBBD1881F294C6")
EXPECTED_FONTS = {
    Path("${USER_HOME}/AppData/Local/Programs/MiKTeX/fonts/truetype/public/unfonts-core/UnBatang.ttf"): (6157280, "5066E52D247568ACC6C2984F41D8F7E3C20E28F19F0D8ACDA9D33027BE91E991"),
    Path("${USER_HOME}/AppData/Local/Programs/MiKTeX/fonts/truetype/public/unfonts-core/UnBatangBold.ttf"): (6794692, "4443D5C8CA7F1562EE3B5E22652E2C0D90C360948FC5F8998A98600D25631A8E"),
    Path("${USER_HOME}/AppData/Local/Programs/MiKTeX/fonts/truetype/public/unfonts-core/UnDotum.ttf"): (3656228, "5B8373E126BB61F59105CF7F54A47EB1B089C2B0AACB70C6CD688BD8EA76CDC9"),
    Path("${USER_HOME}/AppData/Local/Programs/MiKTeX/fonts/truetype/public/unfonts-core/UnDotumBold.ttf"): (4093740, "C4BF31B1B74A9C9164B23E1FEAE0D9060B38F4790302DC44E7B1E5051C9AFD78"),
}

NEW_CHAPTERS = {
    17: {
        "part": "p03", "stem": "modules", "title": "가군층",
        "target": "inputs/p03/ko/modules.tex", "target_bytes": 215587,
        "target_sha256": "CD1A00FC6C765DBCACFDE4F73C9FF6AD2DD18C1382A8DB2513DCEA130EE82981",
        "source": "upstream/a04446e/modules.tex", "source_bytes": 204133,
        "source_sha256": "7BD3E9E096717EF6FD458492D8AD91FC9FFE428CFD7DD80E386FAE377BB7CB0D",
        "receipt": "evidence/manager-intake/P03_KO_CH17_MANAGER_INTAKE_20260905.json",
        "receipt_bytes": 8239, "receipt_sha256": "4313E1F86FADCB78111394134BFF86F82BEE43703EC0FE283D313AA9C8F0F9E8",
        "replay_kind": "p03_manager_intake_exact_hash_replay",
    },
    71: {
        "part": "p09", "stem": "spaces-divisors", "title": "대수공간 위의 제수",
        "target": "inputs/p09/ko/spaces-divisors.tex", "target_bytes": 181000,
        "target_sha256": "6972AF02CE516BF7B08794CE14873FD4D05402328F866FB8C85F920F73C6C2FF",
        "source": "upstream/a04446e/spaces-divisors.tex", "source_bytes": 165539,
        "source_sha256": "B31B315F2946BC9C06FEE6322A2FA9117D9DDA9CDCA5726625FCD5BDA280CE58",
        "receipt": "evidence/manager-intake/P09_KO_CH71_MANAGER_INTAKE_20260905_R2.json",
        "receipt_bytes": 16955, "receipt_sha256": "225401C16A1538E290FBCA2009B4CFC7CFF82D2E8DA8AED311390B2BAB238A1C",
        "replay_kind": "p09_manager_intake_exact_hash_replay",
    },
    99: {
        "part": "p11", "stem": "quot", "title": "Quot 공간과 Hilbert 공간",
        "target": "inputs/p11/ko/quot.tex", "target_bytes": 248709,
        "target_sha256": "22EFE1453C4F0CC4C44AAB065E57D5C20A3B65C11A0FE9E33F2F0DCFAC01F3CC",
        "source": "upstream/a04446e/quot.tex", "source_bytes": 225563,
        "source_sha256": "DD8E6FE1C77FBC372252ABBFC7F449A5D9A344D1E83ACABCC55A53EDF3F750E0",
        "receipt": "evidence/manager-intake/P11_KO_CH99_MANAGER_INTAKE_20260905_R2.json",
        "receipt_bytes": 14584, "receipt_sha256": "E9BA559A0943748D6DC4D51849B67567F168BAD0650AF61BB24195144EE1A9D0",
        "replay_kind": "p11_manager_intake_exact_hash_replay",
    },
}

COMMANDS = {
    "labels": re.compile(r"\\label\{([^{}]+)\}"),
    "refs": re.compile(r"\\(?:ref|eqref|pageref|autoref)\{([^{}]+)\}"),
    "cites": re.compile(r"\\cite(?:\[[^]]*\])?\{([^{}]+)\}"),
    "begins": re.compile(r"\\begin\{([^{}]+)\}"),
    "ends": re.compile(r"\\end\{([^{}]+)\}"),
    "inputs": re.compile(r"\\input\{([^{}]+)\}"),
}
COUNT_PATTERNS = {
    "items": re.compile(r"\\item(?:\s|\[)"),
    "xymatrix": re.compile(r"\\xymatrix\b"),
    "sections": re.compile(r"\\section\{"),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def identity(path: Path, relative: bool = True) -> dict:
    data = path.read_bytes()
    display = path.relative_to(ROOT).as_posix() if relative and path.is_relative_to(ROOT) else path.as_posix()
    return {"path": display, "bytes": len(data), "sha256": sha256_bytes(data)}


def require_identity(path: Path, size: int, sha: str) -> dict:
    got = identity(path)
    if got["bytes"] != size or got["sha256"] != sha:
        raise RuntimeError(f"identity mismatch: {path}")
    return got


def strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        cut = len(line)
        for index, char in enumerate(line):
            if char != "%":
                continue
            slashes = 0
            pos = index - 1
            while pos >= 0 and line[pos] == "\\":
                slashes += 1
                pos -= 1
            if slashes % 2 == 0:
                cut = index
                break
        out.append(line[:cut])
    return "\n".join(out) + "\n"


def ordered_structure(path: Path) -> dict:
    clean = strip_comments(path.read_text(encoding="utf-8"))
    sequences = {name: pattern.findall(clean) for name, pattern in COMMANDS.items()}
    counts = {name: len(pattern.findall(clean)) for name, pattern in COUNT_PATTERNS.items()}
    return {"clean": clean, "sequences": sequences, "counts": counts}


def frozen_tex_inventory() -> dict:
    rows = []
    total = 0
    for path in sorted(FROZEN.glob("*.tex"), key=lambda item: item.name):
        data = path.read_bytes()
        total += len(data)
        rows.append(f"{path.name}\t{len(data)}\t{sha256_bytes(data)}")
    inventory = ("\n".join(rows) + "\n").encode("utf-8")
    result = {
        "files": len(rows), "bytes": total, "inventory_text_bytes": len(inventory),
        "inventory_sha256": sha256_bytes(inventory),
    }
    expected = EXPECTED_FROZEN_TEX
    observed = (result["files"], result["bytes"], result["inventory_text_bytes"], result["inventory_sha256"])
    if observed != expected:
        raise RuntimeError(f"frozen TeX universe identity mismatch: {observed}")
    return result


def verify_replay_receipt(chapter: int, descriptor: dict) -> dict:
    if chapter in range(60, 69):
        path = ROOT / "receipts" / "CORRECTION_AND_STRUCTURE_VALIDATION.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if receipt.get("result") != "PASS_STRUCTURAL_SUCCESSOR_READY_FOR_SERIALIZED_BUILD":
            raise RuntimeError("P08 inherited source/math replay receipt is not PASS")
        row = next(item for item in receipt["chapter_replay"] if item["chapter"] == chapter)
        if row.get("result") != "PASS":
            raise RuntimeError(f"P08 chapter {chapter} inherited replay is not PASS")
        return {"kind": "p08_r2_hash_bound_exact_replay", "receipt": identity(path), "chapter_result": row["result"]}

    path = ROOT / descriptor["receipt"]
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if chapter == 17:
        replay = receipt["independent_source_replay"]
        passed = (replay["source_lock_match"] and replay["inline_math"]["case_sensitive_multiset_equal"]
                  and replay["display_math"]["symbolic_skeleton_mismatches"] == 0)
    elif chapter == 71:
        passed = receipt["source_target_replay"]["passed"]
    else:
        passed = receipt["independent_source_target_replay"]["pass"]
    if not passed:
        raise RuntimeError(f"Chapter {chapter} manager replay receipt is not PASS")
    return {"kind": descriptor["replay_kind"], "receipt": identity(path), "manager_replay_pass": True}


def load_chapters() -> list[dict]:
    p08_index = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
    p08_provenance = [json.loads(line) for line in (ROOT / "provenance.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    by_chapter = {row["chapter"]: row for row in p08_provenance}
    title_by_chapter = {row["chapter"]: row["title"] for row in p08_index["entries"]}
    chapters = []
    for chapter in CANONICAL_ORDER:
        if chapter in NEW_CHAPTERS:
            item = {"chapter": chapter, **NEW_CHAPTERS[chapter]}
        else:
            row = by_chapter[chapter]
            item = {
                "chapter": chapter,
                "part": "p08",
                "stem": row["stem"],
                "title": title_by_chapter[chapter],
                "target": row["canon_successor_target"]["path"],
                "target_bytes": row["canon_successor_target"]["bytes"],
                "target_sha256": row["canon_successor_target"]["sha256"],
                "source": row["upstream_source"]["path"],
                "source_bytes": row["upstream_source"]["bytes"],
                "source_sha256": row["upstream_source"]["sha256"],
                "inherited_xr_map": row["support"]["xr_map"],
                "replay_kind": "p08_r2_hash_bound_exact_replay",
            }
        item["profile"] = f"ch{chapter:03d}-{item['stem']}"
        chapters.append(item)
    if [item["chapter"] for item in chapters] != CANONICAL_ORDER:
        raise RuntimeError("canonical chapter order mismatch")
    return chapters


def build_label_universe() -> tuple[dict[str, tuple[str, str]], dict, list[str]]:
    label_index: dict[str, tuple[str, str]] = {}
    duplicates = []
    doc_labels: dict[str, list[str]] = {}
    for path in sorted(FROZEN.glob("*.tex"), key=lambda item: item.name):
        doc = path.stem
        labels = COMMANDS["labels"].findall(strip_comments(path.read_text(encoding="utf-8")))
        doc_labels[doc] = labels
        for local_label in labels:
            full = f"{doc}-{local_label}"
            if full in label_index:
                duplicates.append(full)
            label_index[full] = (doc, local_label)
    if duplicates:
        raise RuntimeError(f"ambiguous frozen labels: {duplicates[:10]}")

    tags = {}
    for line in (DEPS / "tags" / "tags").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "," in line:
            tag, label = line.split(",", 1)
            if label in tags and tags[label] != tag:
                raise RuntimeError(f"ambiguous permanent tag for {label}")
            tags[label] = tag
    return label_index, tags, sorted(doc_labels)


def external_documents() -> list[str]:
    clean = strip_comments((SUPPORT / "korean-preamble.tex").read_text(encoding="utf-8"))
    docs = re.findall(r"\\externaldocument\[([^]]+)\]\{([^}]+)\}", clean)
    if any(prefix != f"{doc}-" for prefix, doc in docs):
        raise RuntimeError("unexpected external-document prefix")
    names = [doc for _, doc in docs]
    if len(names) != len(set(names)) or len(names) != 117:
        raise RuntimeError(f"external-document inventory mismatch: {len(names)}")
    return names


def frozen_counter_value(doc: str, local_label: str) -> str:
    if doc != "more-morphisms" or local_label != "lemma-weighting-specialization":
        raise RuntimeError(f"no authorized untagged-label fallback for {doc}-{local_label}")
    clean = strip_comments((FROZEN / f"{doc}.tex").read_text(encoding="utf-8"))
    section = 0
    item = 0
    theorem = re.compile(r"\\begin\{(?:theorem|proposition|lemma|definition|example|exercise|situation|remark|remarks)\}")
    for line in clean.splitlines():
        if re.match(r"^\\section\{", line):
            section += 1
            item = 0
        if theorem.search(line):
            item += 1
        if f"\\label{{{local_label}}}" in line:
            value = f"{section}.{item}"
            if value != "75.9":
                raise RuntimeError(f"frozen counter fallback changed: {value}")
            return value
    raise RuntimeError("authorized untagged label missing from frozen authority")


def main() -> None:
    require_identity(ROOT / "IMPORT_MANIFEST.json", *EXPECTED_IMPORT_MANIFEST)
    import_verification = require_identity(ROOT / "IMPORT_VERIFICATION.json", *EXPECTED_IMPORT_VERIFICATION)
    if json.loads((ROOT / "IMPORT_VERIFICATION.json").read_text(encoding="utf-8"))["result"] != "PASS_EXACT_IMPORT_COMPLETE_BUILD_NOT_STARTED":
        raise RuntimeError("exact import gate not satisfied")
    frozen_inventory = frozen_tex_inventory()
    preamble_identity = require_identity(SUPPORT / "korean-preamble.tex", *EXPECTED_PREAMBLE)
    dependency_identities = [require_identity(DEPS / rel, *expected) for rel, expected in EXPECTED_DEPS.items()]
    font_identities = [require_identity(path, *expected) for path, expected in EXPECTED_FONTS.items()]

    if RECEIPT.exists() or CHAPTER_INVENTORY.exists() or PROFILES.exists():
        raise RuntimeError("support outputs already exist; inspect instead of overwriting")

    chapters = load_chapters()
    label_index, tags, frozen_documents = build_label_universe()
    external_docs = external_documents()
    frozen_chapter_documents = [doc for doc in frozen_documents if doc not in {"preamble", "chapters"}]
    missing = sorted(set(frozen_chapter_documents) - set(external_docs))
    extra = sorted(set(external_docs) - set(frozen_chapter_documents))
    if missing != ["bibliography"] or extra != ["index"]:
        raise RuntimeError(f"preamble/frozen document mismatch: missing={missing}, extra={extra}")

    PROFILES.mkdir()
    chapter_receipts = []
    inventory_rows = []
    all_fallbacks = []
    for ordinal, descriptor in enumerate(chapters, 1):
        chapter = descriptor["chapter"]
        target = ROOT / descriptor["target"]
        source = ROOT / descriptor["source"]
        target_identity = require_identity(target, descriptor["target_bytes"], descriptor["target_sha256"])
        source_identity = require_identity(source, descriptor["source_bytes"], descriptor["source_sha256"])
        replay_proof = verify_replay_receipt(chapter, descriptor)

        target_structure = ordered_structure(target)
        source_structure = ordered_structure(source)
        comparisons = {}
        for name in ("labels", "refs", "cites", "begins", "ends"):
            comparisons[name] = {
                "source": len(source_structure["sequences"][name]),
                "target": len(target_structure["sequences"][name]),
                "ordered_exact": source_structure["sequences"][name] == target_structure["sequences"][name],
            }
        source_inputs = ["preamble" if value == "ko_preamble" else value for value in source_structure["sequences"]["inputs"]]
        target_inputs = ["preamble" if value == "ko_preamble" else value for value in target_structure["sequences"]["inputs"]]
        comparisons["inputs"] = {"source": source_inputs, "target": target_inputs, "ordered_exact_after_locale_adapter_normalization": source_inputs == target_inputs}
        for name in COUNT_PATTERNS:
            comparisons[name] = {
                "source": source_structure["counts"][name],
                "target": target_structure["counts"][name],
                "exact": source_structure["counts"][name] == target_structure["counts"][name],
            }
        if any(not row.get("ordered_exact", row.get("ordered_exact_after_locale_adapter_normalization", row.get("exact", False))) for row in comparisons.values()):
            raise RuntimeError(f"Chapter {chapter} independent ordered structure replay failed")

        local_labels = set(target_structure["sequences"]["labels"])
        ref_occurrences = target_structure["sequences"]["refs"]
        external_occurrences = [label for label in ref_occurrences if label not in local_labels]
        missing = sorted({label for label in external_occurrences if label not in label_index})
        if missing:
            raise RuntimeError(f"Chapter {chapter} external labels missing or ambiguous: {missing[:20]}")

        profile = PROFILES / descriptor["profile"]
        aux_dir = profile / "xr"
        aux_dir.mkdir(parents=True)
        shutil.copyfile(SUPPORT / "korean-preamble.tex", profile / "preamble.tex")
        shutil.copyfile(SUPPORT / "korean-preamble.tex", profile / "ko_preamble.tex")
        (profile / "chapters.tex").write_text(
            "% Canonical cumulative navigation is supplied by the merged PDF outline.\n",
            encoding="utf-8", newline="\n",
        )
        (profile / "ko_chapters.tex").write_text(
            "% Canonical cumulative navigation is supplied by the merged PDF outline.\n",
            encoding="utf-8", newline="\n",
        )

        mappings = []
        by_doc: dict[str, list[str]] = defaultdict(list)
        fallbacks = []
        for full_label in sorted(set(external_occurrences), key=str.casefold):
            doc, local_label = label_index[full_label]
            tag = tags.get(full_label)
            source_kind = "permanent_tag"
            if tag is None:
                tag = frozen_counter_value(doc, local_label)
                source_kind = "frozen_counter_fallback"
                fallback = {
                    "full_label": full_label, "doc": doc, "local_label": local_label, "value": tag,
                    "occurrences": external_occurrences.count(full_label), "authority_commit": AUTHORITY_COMMIT,
                }
                fallbacks.append(fallback)
                all_fallbacks.append({"chapter": chapter, **fallback})
            mappings.append({"full_label": full_label, "tag": tag, "aux_document": doc, "local_label": local_label, "value_source": source_kind})
            by_doc[doc].append(f"\\newlabel{{{local_label}}}{{{{{tag}}}{{0}}}}")

        for doc in external_docs:
            lines = sorted(set(by_doc.get(doc, [])))
            (aux_dir / f"{doc}.aux").write_text("\\relax\n" + "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")

        map_path = profile / "xr-map.tsv"
        with map_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["full_label", "tag", "aux_document", "local_label"], delimiter="\t", lineterminator="\r\n", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(mappings)

        if chapter in EXPECTED_NEW_XR_MAPS:
            require_identity(map_path, *EXPECTED_NEW_XR_MAPS[chapter])
        elif chapter == 62:
            require_identity(map_path, *EXPECTED_CH62_FALLBACK_XR_MAP)
        else:
            inherited = descriptor["inherited_xr_map"]
            require_identity(map_path, inherited["bytes"], inherited["sha256"])

        generated_files = sorted([path for path in profile.rglob("*") if path.is_file()])
        generated_inventory = [identity(path) for path in generated_files]
        chapter_receipts.append({
            "ordinal": ordinal,
            "chapter": chapter,
            "part": descriptor["part"],
            "stem": descriptor["stem"],
            "title": descriptor["title"],
            "target": target_identity,
            "source": source_identity,
            "source_math_replay_proof": replay_proof,
            "independent_ordered_structure_replay": comparisons,
            "references": {
                "total_occurrences": len(ref_occurrences),
                "local_occurrences": len(ref_occurrences) - len(external_occurrences),
                "external_occurrences": len(external_occurrences),
                "external_unique": len(mappings),
                "missing_or_ambiguous": 0,
                "permanent_tag_mappings": sum(item["value_source"] == "permanent_tag" for item in mappings),
                "frozen_counter_fallbacks": fallbacks,
            },
            "profile": descriptor["profile"],
            "xr_map": identity(map_path),
            "aux_documents": len(external_docs),
            "generated_files": len(generated_files),
            "generated_inventory": generated_inventory,
            "result": "PASS_EXACT_REPLAY_AND_REFERENCE_CLOSURE",
        })
        inventory_rows.append({
            "ordinal": ordinal, "chapter": chapter, "part": descriptor["part"], "stem": descriptor["stem"],
            "title": descriptor["title"], "target": target_identity, "source": source_identity,
            "profile": descriptor["profile"],
        })

    inventory_document = {
        "schema": "interlanguage.stacks_cjk.ko_cumulative_chapter_inventory/v1",
        "successor_id": "integration-20260905-r3",
        "authority_commit": AUTHORITY_COMMIT,
        "canonical_order": CANONICAL_ORDER,
        "chapters": inventory_rows,
    }
    CHAPTER_INVENTORY.write_text(json.dumps(inventory_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(CHAPTER_INVENTORY.read_text(encoding="utf-8"))

    receipt = {
        "schema": "interlanguage.stacks_cjk.ko_cumulative_support_closure/v1",
        "record_id": "STACKS-CJK-KO-CUMULATIVE-R3-SUPPORT-20260905",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "successor_id": "integration-20260905-r3",
        "authority": {"repository": "stacks/stacks-project", "commit": AUTHORITY_COMMIT},
        "import_gate": import_verification,
        "frozen_tex_universe": frozen_inventory,
        "frozen_label_index": {"documents": len(frozen_documents), "labels": len(label_index), "ambiguous_full_labels": 0},
        "active_external_documents": len(external_docs),
        "preamble": preamble_identity,
        "dependencies": dependency_identities,
        "korean_font_inputs": font_identities,
        "chapter_inventory": identity(CHAPTER_INVENTORY),
        "canonical_order": CANONICAL_ORDER,
        "chapters": chapter_receipts,
        "totals": {
            "chapters": len(chapter_receipts),
            "reference_occurrences": sum(item["references"]["total_occurrences"] for item in chapter_receipts),
            "external_reference_occurrences": sum(item["references"]["external_occurrences"] for item in chapter_receipts),
            "external_unique_sum": sum(item["references"]["external_unique"] for item in chapter_receipts),
            "missing_or_ambiguous": 0,
            "frozen_counter_fallback_occurrences": sum(
                fallback["occurrences"]
                for item in chapter_receipts
                for fallback in item["references"]["frozen_counter_fallbacks"]
            ),
            "fallback_bindings": all_fallbacks,
        },
        "class_resolution_policy": {
            "class": "stacks-project.cls",
            "identity": identity(DEPS / "stacks-project.cls"),
            "reason": "Uniform cumulative-reader mechanics; P03/P09 producer amsart fallback is not replayed. Imported target bytes and source/math replay remain exact.",
        },
        "navigation_policy": "Per-chapter chapters.tex is intentionally empty; the merged PDF receives canonical chapter outline navigation. This prevents links to unadmitted chapter PDFs.",
        "build_authorized": True,
        "result": "PASS_COMPLETE_EXACT_SUPPORT_TREE_AND_AUX_CLOSURE",
    }
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(RECEIPT.read_text(encoding="utf-8"))
    print(json.dumps({
        "result": receipt["result"], "receipt": identity(RECEIPT), "chapter_inventory": identity(CHAPTER_INVENTORY),
        "chapters": len(chapter_receipts), "labels": len(label_index), "external_refs": receipt["totals"]["external_reference_occurrences"],
        "missing": 0, "fallback_bindings": all_fallbacks,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
