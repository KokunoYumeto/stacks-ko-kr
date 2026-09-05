from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
R4 = ROOT / "provenance" / "p11-r4"
PLAN = ROOT / "BUILD_PLAN.json"
RECEIPT = ROOT / "receipts" / "P11_REBUILD_PREFLIGHT.json"
P11_CHECKER = ROOT / "support" / "tools" / "tex_structure_qa.py"
P08_CHECKER = ROOT / "support" / "tools" / "structural.ps1"
PROFILE = ROOT / "support" / "profile"
DEPS = ROOT / "support" / "dependencies"

AUTHORITY_COMMIT = "a04446e57ec1fbc252a871afcec7752fb2807b14"
EXPECTED_R4_MANIFEST = (
    17078,
    "7350862F09356D75D8BDBD47167D343931ABB87953D5D17C67CA28770A32505D",
)
EXPECTED_P11_CHECKER = (
    8687,
    "4B000359BCDAFE30C1C80B4A07FC06A844C5EA59427C839DF523C34223D20F50",
)
EXPECTED_P08_CHECKER = (
    6975,
    "EE9EE3C3BC24641B48BF41DE0443D4E6E3C1962671F37EE5B2691A0EFE9EE876",
)

CHAPTERS = [
    (91, "defos", "변형 이론", 226711, "F35CA78D18DE9586FC33C2372A1EA2348A4AB5356DC9242C1C756B0795D23E49", 212669, "F7231DC4ADCD611393F4A1F117055C51882C50237C4F0FF9898C9C92169D6F3A"),
    (92, "cotangent", "코탄젠트 복합체", 181840, "E682AA113DF36F5AFCB3C298EC333924CC94B4DEE28ED2DE2A69FE0C41982026", 172190, "39E7B361912DCCC1F4C1590E9F5F7E79A47D15C5F176E6C3469A32CB4BA4B9F3"),
    (93, "examples-defos", "변형 문제", 132544, "60755AA48B38D92A9BBA7498CD83B370D128B8D3E51AF24B07F262E6A55D4E41", 122896, "AD2948AF00ECCC361DC2E33314C7B1D4B3DCE5E977AA153580589E2F48DE5957"),
    (94, "algebraic", "대수 스택", 102776, "18F7FF75A7E87C920DF6ED7946AE40AA5998EBB313D87AFB907ABB57D9F646FC", 97496, "08445616A6BB3555D25B8B589DAF3FAAF68E8CA5AA0BD7CE85E6332740D7DFCB"),
    (95, "examples-stacks", "스택의 예", 67956, "20C8A486058C42FE16C6FE2610546CE27E9ED6FC48D7800283742726BCE6D156", 65671, "54DBC9D017B82B7C93A6CCD72A0295E5A2C1A3E535187083E4100101CD577976"),
    (96, "stacks-sheaves", "대수 스택 위의 층", 202037, "49C874993F9FFF1B3DC542E52BEA11CA8BDF9F3A6B19DE3B954DF39591BAA02F", 192171, "7E28B1ED25663BF5868C34B99F567E1CE49B0EEBC238D39E4117BA9D5E4C2E36"),
    (97, "criteria", "표현 가능성의 판정 조건", 140151, "CFFDE8A76EA6EF9DB9C8947E10AD3AE5421482DCD0EEEFC7B8E6F391CEACB7CE", 130349, "97F0A5A7060C076A0447F0A813EC9A70F2D75995F5E607C90D64FF32FD0511D1"),
    (98, "artin", "Artin의 공리", 280868, "7D4544BC247CC30CCBCBF6A6EA1681A69ABC266E8792DD60E4B621126E3A440E", 254362, "EBA90A897B08EEBFF451E80925D13381B1A7F6AB883A34118733CD24CF061F47"),
    (100, "stacks-properties", "대수 스택의 성질", 128709, "267947D63266B021224D1F46905C8C728EED8F82A627EF902B4666F2D73E96D1", 120421, "59D6B6DF8F528ED5D3A68D9B9D74622E9B643F3622CC4D381BB46CC27A990016"),
]

INHERITED = [
    (17, "modules", "가군층", 455035, "ED937E030164B10C0AC9FD95C7C623F36320B640B4627533563C6454F36AEB09"),
    (60, "crystalline", "크리스탈린 코호몰로지", 534509, "686FEA3D0024D59A75AA5A54A67A37A819812376EB549BD03985C56885A0A06D"),
    (61, "proetale", "프로에탈 코호몰로지", 581844, "59FE6A64AB17D8C627866ECA09D4FB93D5043C31E4C38F7F0EEE4DDB03076416"),
    (62, "relative-cycles", "상대 사이클", 374010, "586561D0FE3F4F293FAC78C80DF3C239270B4C7518D60C122656FE9607173995"),
    (63, "more-etale", "에탈 코호몰로지 심화", 490053, "7120A4B6899B05D50824F641C18DB6B14BECE23B7F211FDAB377E1D1832C72CC"),
    (64, "trace", "트레이스 공식", 460260, "5812F48AD935ED0A53DDBF17CA46AFE2F705B6F3B72CE05B00D6CEB91118178D"),
    (65, "spaces", "대수공간", 350905, "11A26DDD221AE652CAB06728DB86D21CC9461960DC8B1AB1A384AD5F3C56607C"),
    (66, "spaces-properties", "대수공간의 성질", 520942, "AD36B81E719E67448B9E195DE8062697E85A22367B4D57C24FF728387030F5AD"),
    (67, "spaces-morphisms", "대수공간의 사상", 753628, "1D4843C12DD4D91AE46D9468B45C0187C6682331A9C3736D401DCAE9C24F4868"),
    (68, "decent-spaces", "양호한 대수공간", 507493, "CC17F2FE8D094AB7266EA4104F7E296A54411536D458B4C57B370655793E3039"),
    (71, "spaces-divisors", "대수공간 위의 제수", 413496, "C2612D39BC27A670D70E6E99964EFC155F3F7C0DB5933C166F46273D4E12BE29"),
    (99, "quot", "Quot 공간과 Hilbert 공간", 528709, "67EC18E567BB6FC10815AAE5CA1FA487472E70D7EE9B5047A1CD223FA8C7E0BF"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def identity(path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def require(path: Path, size: int, digest: str) -> dict[str, object]:
    got = identity(path)
    if got["bytes"] != size or got["sha256"] != digest:
        raise RuntimeError(f"identity mismatch: {path}")
    return got


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        import os
        os.fsync(stream.fileno())
    temporary.replace(path)


def tree_identity(root: Path) -> dict[str, object]:
    rows = []
    total = 0
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        size = path.stat().st_size
        digest = sha256(path)
        total += size
        rows.append(f"{rel}\t{size}\t{digest}\n")
    serialized = "".join(rows).encode("utf-8")
    return {
        "path": root.relative_to(ROOT).as_posix(),
        "files": len(rows),
        "bytes": total,
        "serialization_bytes": len(serialized),
        "sha256": hashlib.sha256(serialized).hexdigest().upper(),
    }


def p08_gate(checks: list[dict[str, object]]) -> tuple[bool, dict[str, object]]:
    exact_required = {"labels", "references", "citations", "begin", "end", "align_star", "equation"}
    exact = [entry for entry in checks if entry.get("check") in exact_required]
    inline = next(entry for entry in checks if entry.get("check") == "inline_math")
    display = next(entry for entry in checks if entry.get("check") == "display")
    topology = next(entry for entry in checks if entry.get("check") == "topology_and_hazards")
    passed = (
        all(entry.get("exact") is True for entry in exact)
        and inline.get("difference_count") == 0
        and display.get("source") == display.get("target")
        and topology.get("source_items") == topology.get("target_items")
        and topology.get("source_xymatrix") == topology.get("target_xymatrix")
        and topology.get("double_escaped_ref_or_cite") == 0
        and topology.get("unicode_replacement_characters") == 0
        and topology.get("vertical_tabs") == 0
    )
    return passed, {
        "required_exact_checks": sorted(exact_required),
        "display_policy": "count exact; any content delta is independently bounded by sectionwise inline-math multisets and preserved producer target hash; reader-text/layout-only display adaptations remain visible in the raw checker evidence",
        "checks": checks,
    }


def main() -> None:
    if PLAN.exists() or RECEIPT.exists():
        raise RuntimeError("preflight artifacts already exist; inspect rather than overwrite")
    r4_manifest = R4 / "IMPORT_MANIFEST.json"
    external_r4 = {
        "path": r4_manifest.as_posix(),
        "bytes": r4_manifest.stat().st_size,
        "sha256": sha256(r4_manifest),
    }
    if (external_r4["bytes"], external_r4["sha256"]) != EXPECTED_R4_MANIFEST:
        raise RuntimeError("R4 intake manifest identity mismatch")
    checker_ids = {
        "sectionwise": require(P11_CHECKER, *EXPECTED_P11_CHECKER),
        "ordinal": require(P08_CHECKER, *EXPECTED_P08_CHECKER),
    }
    preamble = PROFILE / "ko_preamble.tex"
    preamble_text = preamble.read_text(encoding="utf-8")
    cjkspace_count = preamble_text.count(r"\xeCJKsetup{CJKspace=true}")
    if cjkspace_count != 1:
        raise RuntimeError("corrected Korean CJK-space preamble gate failed")
    aux_files = sorted((PROFILE / "xr").glob("*.aux"))
    if len(aux_files) != 117:
        raise RuntimeError(f"expected 117 AUX files, found {len(aux_files)}")

    new_chapters = []
    all_pass = True
    for chapter, stem, title, target_bytes, target_sha, source_bytes, source_sha in CHAPTERS:
        target = ROOT / "inputs" / "p11" / "ko" / f"{stem}.tex"
        source = ROOT / "authority" / "a04446e" / f"{stem}.tex"
        target_id = require(target, target_bytes, target_sha)
        source_id = require(source, source_bytes, source_sha)
        p11_done = subprocess.run(
            [sys.executable, "-B", str(P11_CHECKER), str(source), str(target)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        sectionwise = json.loads(p11_done.stdout)
        p08_done = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(P08_CHECKER), "-Source", str(source), "-Target", str(target)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        ordinal_checks = json.loads(p08_done.stdout)
        ordinal_pass, ordinal = p08_gate(ordinal_checks)
        title_exact = f"\\title{{{title}}}" in target.read_text(encoding="utf-8")
        passed = bool(sectionwise.get("pass")) and ordinal_pass and title_exact
        all_pass = all_pass and passed
        new_chapters.append({
            "chapter": chapter,
            "stem": stem,
            "title": title,
            "target": target_id,
            "authority": source_id,
            "title_exact": title_exact,
            "sectionwise_structure_and_inline_math": sectionwise,
            "ordinal_structure_and_math": ordinal,
            "result": "PASS" if passed else "FAIL",
        })

    inherited = []
    for chapter, stem, title, size, digest in INHERITED:
        path = ROOT / "evidence" / "inherited-components" / f"ch{chapter:03d}-{stem}.pdf"
        inherited.append({"chapter": chapter, "stem": stem, "title": title, "pdf": require(path, size, digest)})

    if not all_pass:
        failed = [
            {
                "chapter": entry["chapter"],
                "sectionwise_pass": entry["sectionwise_structure_and_inline_math"].get("pass"),
                "ordinal_gate": p08_gate(entry["ordinal_structure_and_math"]["checks"])[0],
                "title_exact": entry["title_exact"],
            }
            for entry in new_chapters
            if entry["result"] != "PASS"
        ]
        raise RuntimeError(f"one or more P11 structural replay gates failed: {failed}")
    plan = {
        "schema": "interlanguage.stacks_cjk.ko_p11_rebuild_plan/v1",
        "record_id": "STACKS-CJK-KO-P11-R5-PLAN-20260905",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "authority_commit": AUTHORITY_COMMIT,
        "source_intake_manifest": external_r4,
        "classification": "PASS_READY_FOR_MUTEX_SERIALIZED_COMPONENT_BUILD",
        "new_chapters": [
            {
                "chapter": entry[0],
                "stem": entry[1],
                "title": entry[2],
                "target": f"inputs/p11/ko/{entry[1]}.tex",
                "authority": f"authority/a04446e/{entry[1]}.tex",
            }
            for entry in CHAPTERS
        ],
        "inherited_chapters": [
            {
                "chapter": entry[0],
                "stem": entry[1],
                "title": entry[2],
                "pdf": f"evidence/inherited-components/ch{entry[0]:03d}-{entry[1]}.pdf",
            }
            for entry in INHERITED
        ],
        "cumulative_order": [17, 60, 61, 62, 63, 64, 65, 66, 67, 68, 71, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100],
        "adapter": {
            "profile": tree_identity(PROFILE),
            "dependencies": tree_identity(DEPS),
            "preamble": identity(preamble),
            "cjkspace_directive_exact_count": cjkspace_count,
            "xr_aux_files": len(aux_files),
        },
        "build_contract": {
            "tex_mutex": r"Global\InterlanguageTeXSlotV1",
            "component_passes": ["xelatex", "bibtex", "xelatex", "xelatex", "xelatex"],
            "source_date_epoch": "1788562238",
            "new_component_count": 9,
            "inherited_component_count": 12,
            "final_cumulative_chapter_count": 21,
            "producer_files_mutated": False,
            "predecessor_files_mutated": False,
            "publication_before_build_and_visual_qa": False,
        },
    }
    atomic_json(PLAN, plan)
    receipt = {
        "schema": "interlanguage.stacks_cjk.ko_p11_rebuild_preflight/v1",
        "record_id": "STACKS-CJK-KO-P11-R5-PREFLIGHT-20260905",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "build_plan": identity(PLAN),
        "source_intake_manifest": external_r4,
        "checkers": checker_ids,
        "adapter": plan["adapter"],
        "new_chapter_replay": new_chapters,
        "inherited_components": inherited,
        "checks": {
            "nine_target_hashes": "PASS",
            "nine_authority_hashes": "PASS",
            "nine_sectionwise_structure_and_inline_math": "PASS",
            "nine_ordinal_label_ref_cite_environment_and_math_topology": "PASS",
            "corrected_korean_cjk_space_adapter": "PASS",
            "complete_117_chapter_aux_universe": "PASS",
            "twelve_inherited_component_hashes": "PASS",
        },
        "result": "PASS_READY_FOR_MUTEX_SERIALIZED_COMPONENT_BUILD",
        "canon_admission": "NOT_YET_ADMITTED_PENDING_BUILD_CUMULATIVE_ASSEMBLY_AND_PAGE_COMPLETE_VISUAL_QA",
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps({"plan": identity(PLAN), "receipt": identity(RECEIPT), "chapters": len(new_chapters), "result": receipt["result"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
