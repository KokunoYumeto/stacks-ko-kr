# Deterministic rebuild

1. Extract this ZIP without newline conversion. `.gitattributes` records the byte-preservation rule.
2. Install XeLaTeX, BibTeX, Poppler (`pdftotext`, `pdfinfo`, `pdffonts`, `pdftoppm`), Python 3, and `pypdf`.
3. On Windows, optionally set `STACKS_PYTHON` to the desired Python executable. Otherwise `python` on PATH is used.
4. Run `pwsh -NoProfile -File cumulative/build/run_tex_serialized.ps1`. The wrapper acquires `Global\InterlanguageTeXSlotV1` for the complete TeX process tree.
5. The expected reader is `cumulative/output/pdf/stacks-project-ko-kr-cumulative-r3.pdf`, 6,163,243 bytes, SHA-256 `D16F925E5EAD4BA519D2C5E5F7ED47F022810DE76484183BBAE5108D970190F7`, 572 pages.

The build driver checks the exact Korean targets, the twelve selected authority comparison files, the full reference/AUX support closure, dependency hashes, reference/citation diagnostics, extraction, page geometry, chapter order, and deterministic PDF merge replay. The release copy uses the final compact page-complete visual-QA receipt in place of four excluded diagnostic PNG probes. To regenerate visual evidence, use the supplied visual-QA scripts; regenerated PNG/contact trees are intentionally not part of this source package.
