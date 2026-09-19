# Rebuilding the complete Korean source

The `src/` directory contains all 116 translated chapters, the generated index,
the complete English GFDL text, the class, bibliography, preamble and tag references.
The direct cumulative `.tex` contains the full reader text, not a thin master.
Its lossless expansion map is `DIRECT_SOURCE_MAP.json`.

Use current XeLaTeX and BibTeX (TeX Live or MiKTeX), with `xeCJK`, `fontspec`,
`xypic`, `hyperref`, and the packages loaded by `src/preamble.tex` and the class.
Fonts: TeX Gyre Termes, TeX Gyre Heros, Latin Modern Mono, plus
UnBatang and UnDotum.
Font binaries and standard distribution packages are not duplicated in this archive.

On Windows with PowerShell 7, run `pwsh -NoProfile -File ./build.ps1` in this
directory. The script takes the machine-wide TeX mutex, runs XeLaTeX/BibTeX,
requires exact PDF/auxiliary convergence, and records consumed source files.
It never runs another build over an existing receipt. For a fresh rebuild,
extract this source archive to a new empty directory.

On other systems, work in `src/`: run `xelatex reader.tex`, `bibtex reader`,
then repeat `xelatex reader.tex` until references and auxiliary files stabilize.
To compile the direct cumulative source instead, copy it beside the `.cls`
and `my.bib` in `src/` and use its basename in the same commands.

At this source publication checkpoint, the cumulative PDF is still undergoing
build/layout validation. The source corpus itself is complete; no previously
published PDF is replaced by an unverified new PDF.
