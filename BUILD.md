# Deterministic replay

1. Extract this ZIP without newline conversion. `.gitattributes` records the byte-preservation rule.
2. Install Python 3 and `pypdf`.
3. Run `python successor-r5/build/replay_verified_reader.py`.
4. The expected reader is `successor-r5/output/pdf/stacks-project-ko-kr-cumulative-r5.pdf`, 9,964,389 bytes, SHA-256 `41EBF54DACE5E55CE8BE3E3289192375FC9683AEAB504DF66359BB88EE42C3EC`, 880 pages.

The replay uses the exact twenty-one receipt-bound component PDFs preserved as compact deterministic evidence. Editable Korean TeX and all twenty-one comparison authority files are also included. To rebuild the nine newly admitted component PDFs from TeX, use a clean copy, remove the nine `successor-r5/evidence/components/ch09*`/`ch100*` directories and move the final `successor-r5/receipts/P11_COMPONENT_AND_CUMULATIVE_BUILD.json` aside, install XeLaTeX, BibTeX, Poppler, Python, and `pypdf`, then run `pwsh -NoProfile -File successor-r5/build/run_tex_serialized.ps1`; the wrapper acquires `Global\InterlanguageTeXSlotV1` for the complete process tree.

All 880 pages and every warning locus were rendered and explicitly inspected. Ordered page hashes and review ledgers are under `successor-r5/evidence/visual-qa-r5/`; raster pages, contact sheets, and probes are intentionally omitted because they are deterministically regenerable.
