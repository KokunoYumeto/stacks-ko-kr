# Evidence cards: fresh bounded reassessments

[Index and evidence labels](README.md)

**Added 2026-09-21:** [KO-BRAUER-003: 나눗셈환, with consulted Korean scholarly passages and all 31 chapter occurrences](brauer-division-ring.md). This is a source-grounded retention decision; the 2026-09-19 cards below remain historical bounded reassessments with their original evidence limits.

The public chapter was read at commit `f8c8ac86357011c6c0a96e4ebc5a51219d9a8935`, SHA-256 `3A3A3A91A0859C65FC81F445B9FDCBC6BBD72CABA70857048C6C29840F8DCE47`. These cards do not claim a newly rebuilt PDF or a corpus-wide review.

## KO-BRAUER-001: inner automorphism

**Evidence:** direct mathematical-society headword attestation, not a sentence-level scholarly passage.

[대한수학회 mathematical dictionary: inner automorphism](https://www.kms.or.kr/mathdict/list.html?key=ename&keyword=inner+automorphism) gives `inner automorphism → 내부자기동형사상`. The saved 2026-09-06 HTML was freshly read and its SHA-256 verified as `5C6D3C050950CFD801F4F8C72ED639E63C8721E1DC826F13D962ADE7BEE4FC17`. The live site did not return a usable response during this check; no fresh online availability claim is made.

**Occurrence:** [English lemma](https://github.com/stacks/stacks-project/blob/a04446e57ec1fbc252a871afcec7752fb2807b14/brauer.tex#L510-L515); [Korean lemma](https://github.com/KokunoYumeto/stacks-ko-kr/blob/f8c8ac86357011c6c0a96e4ebc5a51219d9a8935/editions/2026-09-19-full116/src/brauer.tex#L471-L475).

**Decision:** use the explicit technical noun `내부자기동형사상` rather than the underspecified adjective `내부적이다`. It names the mathematical automorphism property the source intends. The dictionary attests the noun; it does not by itself validate every part of the Korean sentence or settle all spacing preferences.

**Important separation:** this vocabulary decision does not certify the source theorem as literally stated. The source’s broad “any automorphism” wording has a separate hypothesis issue: the intended assertion concerns k-algebra automorphisms. Source errata and language choices must not be conflated.

**Release status:** the explicit noun is already present in the linked public text. **Confidence:** strong lexical evidence, limited sentence-level attestation. Original audit occurrence: `P02-LSA-KO-CH11-B057`.

## KO-BRAUER-002: 브라우어 군

**Evidence:** provisional, model-informed transliteration; no exact Korean scholarly passage verified in this dossier.

**Occurrence:** [English section heading](https://github.com/stacks/stacks-project/blob/a04446e57ec1fbc252a871afcec7752fb2807b14/brauer.tex#L380-L381); [Korean chapter](https://github.com/KokunoYumeto/stacks-ko-kr/blob/f8c8ac86357011c6c0a96e4ebc5a51219d9a8935/editions/2026-09-19-full116/src/brauer.tex), the Brauer-group section. Original audit record: `P02-LSA-KO-CH11-B043`.

**Decision and reason:** retain the intelligible transliteration `브라우어 군` provisionally because the mathematical name and the group being defined are unambiguous. `Brauer 군` is a meaningful alternative that retains the Latin surname. This is a linguistic/editorial judgment, not evidence that the Hangul form is the uniquely conventional specialist spelling. We do not know which training examples, if any, influenced that judgment.

**Uncertainty:** a verified same-sense Korean paper or textbook passage would strengthen or change the register decision. Failure to find one in this dossier does not establish that none exists. The earlier generic “strongest supported form” rationale should not be read as direct attestation.
