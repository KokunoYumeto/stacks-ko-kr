from __future__ import annotations

import hashlib
import json
from pathlib import Path

from build_components import merge_pdf

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BYTES = 9964389
EXPECTED_SHA256 = "41EBF54DACE5E55CE8BE3E3289192375FC9683AEAB504DF66359BB88EE42C3EC"
EXPECTED_PAGES = 880


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_identity(path: Path, row: dict[str, object]) -> None:
    if not path.is_file() or path.stat().st_size != int(row["bytes"]) or digest(path) != str(row["sha256"]):
        raise RuntimeError(f"identity mismatch: {path}")


plan = json.loads((ROOT / "BUILD_PLAN.json").read_text(encoding="utf-8"))
preflight = json.loads((ROOT / "receipts/P11_REBUILD_PREFLIGHT.json").read_text(encoding="utf-8"))
for row in preflight["inherited_components"]:
    require_identity(ROOT / row["pdf"]["path"], row["pdf"])
components = []
for chapter in plan["new_chapters"]:
    job = f"ch{int(chapter['chapter']):03d}-{chapter['stem']}"
    receipt = json.loads((ROOT / "evidence/components" / job / "COMPONENT_BUILD.json").read_text(encoding="utf-8"))
    require_identity(ROOT / "evidence/components" / job / receipt["pdf_filename"], receipt["pdf"])
    components.append(receipt)
destination = ROOT / "output/pdf/stacks-project-ko-kr-cumulative-r5.pdf"
if destination.exists():
    raise RuntimeError(f"refusing to overwrite {destination}")
result = merge_pdf(plan, components, destination)
if result["pages"] != EXPECTED_PAGES or destination.stat().st_size != EXPECTED_BYTES or digest(destination) != EXPECTED_SHA256:
    raise RuntimeError("deterministic cumulative replay mismatch")
print(json.dumps({"result": "PASS_BYTE_IDENTICAL_REPLAY", "pdf": {"path": str(destination.relative_to(ROOT)), "bytes": EXPECTED_BYTES, "sha256": EXPECTED_SHA256, "pages": EXPECTED_PAGES}}, indent=2))
