# Deterministic replay

1. Extract the ZIP without newline conversion; `.gitattributes` preserves bytes.
2. Install Python 3 and `pypdf`.
3. Run `python successor-r9/build/replay_verified_reader.py`.
4. The expected output is 25,145,874 bytes, SHA-256 `CE7ED45FD47C9E1583ECD9B3A3383A03EC511A63D649CF2715BD24F8926C9642`, and 2,316 pages.

The replay combines the 49 exact inherited component PDFs and three newly built component PDFs in canonical 52-chapter order. The package also includes editable Korean TeX and exact comparison authority files for all 52 chapters. TeX is not needed for this byte-identical reader replay.

All 2,158 inherited pages were remapped pixel-for-pixel to the closed r6 visual baseline. Every one of the 158 new pages and the three insertion boundaries was freshly inspected; all 2,316 cumulative pages are covered by terminal page-complete visual QA.
