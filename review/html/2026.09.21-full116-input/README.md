# Korean input for the connected Stacks reader

This is a frozen integration input, **not a rendered or deployed HTML reader**.
It binds all 116 chapters of the published Korean edition to immutable
source commit `f6cbc7d7b88d8ab12c2864593a7cbb7ad2fdd4b6`. No translation or mathematical source is
modified by this handoff.

## Read and reuse

- [Frozen source manifest and reading links](INPUT.json)
- [Complete source/translation label crosswalk](LABEL_CROSSWALK.jsonl)
- [Human-readable translation-choice review](https://github.com/KokunoYumeto/stacks-ko-kr/blob/d0d0958de85104bb97c08895c4bd78ee14bbee04/review/translation-choices/README.md)
- [Published reader PDF, direct cumulative LaTeX and complete source ZIP](https://zenodo.org/records/22849667)

All 21,447 chapter labels match exact source labels in source order; 21,437
have tags in the pinned official table. The ten labels without official tags
are explicitly listed and retain exact source/target locations. Label matching
supports navigation; it does not establish translation accuracy or expert review.
The manifest binds each chapter's bytes and the complete source package checked
in this pass. This does not repeat or expand the PDF's recorded visual-QA scope.

Use this snapshot through the existing programme reader, not changing producer
folders. Generate chapter/result links, connect the corresponding English and
available translated passages, and link their translation-choice explanations.
Use actual generated anchors, not guessed HTML routes. Preserve all prose and
mathematics, disclose unsupported rendering, and validate CJK text, formulas,
links/fragments and public reading before reporting online coverage. Keep
translation review, source errata and AI additions as separate statuses.

Unofficial AI-assisted translation; no comprehensive expert human review.
Expert corrections are welcome. The choice index covers selected recorded
choices, not every word of every chapter. Human response is not a release gate.
Browser reading complements the editable LaTeX and complete source ZIP.
