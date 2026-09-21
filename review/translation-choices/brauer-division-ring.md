# KO-BRAUER-003: why retain 나눗셈환 for Stacks' “skew field”?

[Translation-choice index](README.md) · [Every occurrence](brauer-division-ring-occurrences.md) · [Machine-readable occurrence records](brauer-division-ring-occurrences.jsonl) · [Consulted source identities](brauer-division-ring-sources.json)

**Decision, 2026-09-21:** retain `나눗셈환` in all 31 occurrences in the released
Korean Brauer chapter. This is a newly source-grounded retention decision, not
31 corrected errors. The scholarly passages were consulted retrospectively;
this record does not claim that the original translator consulted them.

## Start with the mathematical definition, not the English word

[Stacks' definition](https://github.com/stacks/stacks-project/blob/a04446e57ec1fbc252a871afcec7752fb2807b14/brauer.tex#L45-L50)
includes **both commutative and noncommutative** rings with a nonzero identity
and inverses for all nonzero elements. The [released Korean definition](https://github.com/KokunoYumeto/stacks-ko-kr/blob/f6cbc7d7b88d8ab12c2864593a7cbb7ad2fdd4b6/editions/2026-09-19-full116/src/brauer.tex#L43-L47)
preserves those conditions explicitly. In particular, its wording permits
noncommutativity; it does not require it.

## The Korean passages actually read

1. **채갑병, 원광대학교 수학과, _추상대수학 3장_, Definition 3.1.5,
   printed slide 21 (PDF page 6, upper left).** The definition names
   `나눗셈환(division ring)`, requires a nonzero identity and both inverse
   equations for every nonzero element, and then distinguishes the commutative
   case as a field. This supports precisely the inclusive concept needed here.
   [Read the university teaching material on KOCW](http://contents.kocw.or.kr/document/Algebra-chapter03-Print.pdf#page=6).

2. **안상욱, 한경대학교 응용수학과, _대수학(환론과 체론) 강의 노트_,
   Definition 1.1.4, printed/PDF page 5.** This passage likewise uses
   `나눗셈환` for division ring, but calls the specifically noncommutative
   case `사체(skew field)`. The convention therefore differs from Stacks'
   inclusive use of the English phrase. [Read the passage](http://contents2.kocw.or.kr/KOCW/document/2017/hankyong/ansangyook2/1.pdf#page=5).
   The consulted PDF footer says 2017-2; the [KOCW course catalogue](https://www.kocw.net/home/search/kemView.do?kemId=1259576)
   says 2017 first semester. The document identity and page, not an inferred
   semester equivalence, bind this citation.

These are actual Korean university algebra teaching passages, not AI-translated
web summaries. Their relevant complete PDF pages were rendered and visually
read. Text extraction alone was inadequate for the second PDF. The first
provides the explicit nonzero-identity clause; the second is additionally useful
for showing a competing terminology convention. Neither source is claimed to
settle every phrase of Brauer-group exposition.

## Why the choice fits the chapter

The chapter uses the concept for endomorphism rings of simple modules, the
coefficient rings in Wedderburn's theorem, their centres and opposite rings,
Brauer-class representatives, and splitting-field arguments. In each case the
object is a division ring in the inclusive sense defined at the beginning;
none of these 31 occurrences adds a requirement of strict noncommutativity.
The occurrence table records the source and target locations and the particular
context checked, rather than treating matching search counts as an audit.

The strongest immediate countercheck is the zero Brauer class: its representative
can be the base field itself. In the algebraically closed case the argument
explicitly concludes that the division ring is the base field. Wording that
necessarily excluded commutative fields would misdescribe those passages.

**Meaningful alternative:** `사체` is not declared universally wrong. It could
be used with a clear inclusive convention, and other authors may use it that
way. But the consulted teaching passage shows that readers can encounter a
narrower convention. Keeping the already defined, directly attested
`나눗셈환` avoids that ambiguity. No claim is made that it is the only acceptable
Korean term. The compound modifiers “finite”, “central” and “extension” were
checked for their local mathematical referents, not independently certified as
the uniquely idiomatic Korean phrasing by these two citations.

## Scope and uncertainty

- **Evidence class:** direct passage attestation plus explicit source/target
  contextual comparison. Qualitative confidence is strong for this lexical
  choice and its inclusive meaning, not a calibrated probability.
- **Coverage:** 31/31 occurrences of this one term in this one immutable chapter.
  Not every translation choice, sentence, chapter or language has been audited.
- **Outcome:** no source text, formula, PDF or source archive changed. All
  consulted source/target chapter hashes are bound in the occurrence records.
- **Separate concerns:** English-source hypothesis errors and other wording
  choices remain separate. For example, the existing zero-module issue in
  `lemma-simple-module-unique` is not validated by this vocabulary decision.
- **Expert review welcome:** a same-sense Korean specialist publication can
  refine this preference. No comprehensive human expert review is claimed,
  and no response is required before continuing evidenced work.

The public witness record contains URLs, exact PDF hashes, locators and short
attestations, not copies of the third-party PDFs. The original PDF endpoints
were consulted anonymously over HTTP after HTTPS hostname verification failed;
TLS verification was not disabled. Hashes identify the consulted bytes, not
authenticated transport. The first PDF renderer emitted font-substitution
warnings; the cited definition and mathematical conditions were visually
legible. These limitations are retained rather than silently omitted.
