from __future__ import annotations
import hashlib, json
from pathlib import Path
from build_components import merge_pdf
ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BYTES = 25145874
EXPECTED_SHA256 = "CE7ED45FD47C9E1583ECD9B3A3383A03EC511A63D649CF2715BD24F8926C9642"
EXPECTED_PAGES = 2316
def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest().upper()
plan=json.loads((ROOT/"BUILD_PLAN.json").read_text(encoding="utf-8"))
components=[]
for chapter, stem in ((89,"spaces-resolve"),(90,"formal-defos"),(101,"stacks-morphisms")):
    p=ROOT/"evidence"/"components"/f"ch{chapter:03d}-{stem}"/"COMPONENT_BUILD.json"
    components.append(json.loads(p.read_text(encoding="utf-8")))
destination=ROOT/"output"/"pdf"/"stacks-project-ko-kr-cumulative-r9-52-chapters.pdf"
if destination.exists(): raise RuntimeError(f"refusing to overwrite {destination}")
destination.parent.mkdir(parents=True,exist_ok=True)
result=merge_pdf(plan,components,destination)
if int(result["pages"])!=EXPECTED_PAGES or destination.stat().st_size!=EXPECTED_BYTES or digest(destination)!=EXPECTED_SHA256:
    raise RuntimeError("deterministic cumulative replay mismatch")
print(json.dumps({"result":"PASS_BYTE_IDENTICAL_REPLAY","pdf":{"bytes":EXPECTED_BYTES,"sha256":EXPECTED_SHA256,"pages":EXPECTED_PAGES}},indent=2))
