# Stacks CJK manager workflow — 2026-09-04

This is an additive current operating record for the Stacks CJK programme. It does not rewrite the older Noether-era CJK logbooks. Direct user messages and exact primary artifacts control over this file if a conflict is found.

## Current topology

- One manager/canon task owns cumulative integration, correction intake and propagation, reproducible build/QA, public release maintenance, and recoverability records.
- Twelve persistent producer tasks, P01 through P12, retain their existing disjoint Stacks chapter ranges and current language cursors. They continue current work; completed material is not restarted and live cursors are not reassigned wholesale.
- Chinese (mainland Simplified Chinese), Japanese, and Korean are independent target editions. A translation or checkpoint in one language is comparison evidence for another language, never automatic authority or proof of completion.
- English-source defects found during translation are routed to the established Stacks errata registrar/composer. Frozen official upstream at commit `a04446e57ec1fbc252a871afcec7752fb2807b14` is never silently mutated by a locale producer.

## Visible programme organization

- Keep `Stacks — Director · CJK Canon · Errata · Harvest · Releases` pinned as the single programme manager, parallel to the EGA/FGA/SGA director task.
- Keep P01–P12 together in the `Stacks CJK Production` sidebar section, ordered by their immutable chapter ranges from P01 through P12; `Stacks French — Full Corpus · Source Review & Errata Feed` remains the supporting thirteenth Stacks lane rather than displacing a CJK owner.
- Stable producer titles expose both the immutable chapter boundary and the intended locale succession `ZH → JA → KO`. Titles are organizational labels only: the producer's exact durable cursor controls its present locale and position, and a title change never reassigns or restarts work.
- The manager, not a locale producer, admits chapter-complete returns into cumulative language editions, maintains the correction/propagation ledger, and owns the independent public GitHub and Zenodo lineages for each language.

## Finite production and integration loop

1. Each producer continues from its exact durable cursor under its existing exclusive write boundary.
2. At each checkpoint it binds authority, target, structural replay, build, rendered-page review, terminology/decision state, adverse evidence, and next cursor by byte count and SHA-256.
3. The manager independently verifies chapter-complete returns before cumulative admission and records missing/partial chapters without converting them into completed coverage.
4. Cumulative editions are assembled in canonical chapter order from admitted language-specific units only. Generated indexes and support files are rebuilt from the admitted tree.
5. Every TeX build obeys `Global\InterlanguageTeXSlotV1` for the complete captured build tree. A failed or interrupted pass is resumed only from an exact validated snapshot; no duplicate build is launched while state is unknown.
6. Structural/source QA, PDF mechanics, extraction/font/glyph checks, and complete rendered-page visual QA must pass. A predecessor visual inspection may be inherited only for pages proved byte-identical or decoded-pixel-identical under a hash-bound renderer transition; all pixel-different pages are retained and reinspected.
7. Complete worthwhile nonduplicative releases are published promptly into the correct language's existing GitHub and Zenodo lineage. If no such lineage exists, create one language-specific lineage rather than borrowing another language or corpus lineage. Keep every public surface public and anonymously read back every released file by filename, bytes, and SHA-256.
8. Continue the loop until all 116 Stacks chapters and generated index are integrated for each authorized target language. A cumulative checkpoint covering fewer chapters must state its exact coverage and omissions.

## Terminology and difficult-choice evidence

For every substantive term or translation choice, record:

- stable record ID and target language;
- exact authority and target locator;
- source form and relevant sense window;
- chosen target wording and sense;
- actual dictionaries, corpora, editions, or other sources checked, or an honest `not checked` / `not found` statement;
- rationale and rejected alternatives;
- uncertainty, adverse evidence, and any open correction question;
- whether the rationale was contemporaneous or retrospectively backfilled;
- the checkpoint/release in which the choice is embodied.

Missing dictionary entries, experts, or human review never create a gap or hold. Make the best source-grounded provisional choice, mark it as provisional and reversible, and continue through deterministic QA and publication.

## Durable records

- User-directive ledger: `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\00_lane_control\STACKS_CJK_MANAGER_DIRECTIVES_20260904.jsonl`
- Sidebar topology receipts: `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\00_lane_control\SIDEBAR_ORGANIZATION_20260904.json` and additive successors in the same directory.
- Current Japanese cumulative integration: `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\03_working_translations\stacks_cjk_20260821\canon\ja-jp\integration-20260831-r1`
- Producer-local `CONTROL.md`, `DECISIONS.jsonl`, `MANIFEST.jsonl`, terminology ledgers, errata ledgers, QA receipts, and cursor records remain authoritative within each P01-P12 write boundary.

## Current Simplified-Chinese public edition

The independent public replay on 2026-09-05 proves that mainland Simplified Chinese is complete at R15: all 116 chapters, 5,906 reader pages, authority commit `a04446e57ec1fbc252a871afcec7752fb2807b14`. The public repository is `https://github.com/KokunoYumeto/stacks-zh-hans-cn`, release tag `zh-hans-cn-2026.08.30-r15`, public commit `782bf32b4a74bea784e831d585f7a235ce33638d`, Zenodo version DOI `10.5281/zenodo.22177503`, and stable concept DOI `10.5281/zenodo.22060287`. Anonymous GitHub and Zenodo readback matched all five release files by filename, byte count, and SHA-256. The reconciled publication-state pointer is `canon\control\ZH_HANS_CN_PUBLICATION_STATE_20260831_R15.json` (5,531 bytes; SHA-256 `E3B97CA6B582E8EB8909E3E9651453CE11058CA4C174885A98B444E6BB347321`); the final publication receipt remains `canon\stacks-zh-hans-cn\release\control-r15\R15_PUBLICATION_FINAL_RECEIPT.json` (3,023 bytes; SHA-256 `4191F92211962FB974B0CD2692471DF4192E29FC66532197271031A25A8B457E`). The clean detached public mirror is `canon\stacks-zh-hans-cn-public-r15-782bf32`, at exact commit `782bf32b4a74bea784e831d585f7a235ce33638d` and tree `2218a9a5fc08024f0ebef62dcc9c37ddc29e9b62`, with 278 tracked files and zero tracked changes. No republication is required. The mixed historical/production checkout remains preserved at its R14 head with all later local files untouched; its role is explicitly distinct from the immutable public R15 mirror and later moving producer work.

## Current Japanese integration boundary

The admitted immutable snapshot contains 95 of 116 Japanese chapters: 1–9, 11–28, 34–50, and 60–110. Missing chapters are 10, 29–33, 51–59, and 111–116, plus the generated index. Chapters 10, 29, 51, and 111 are active producer work. The 95-chapter cumulative reader is 5,379 pages / 28,310,875 bytes / SHA-256 `17854FE895725BFD697117E05E9173A8B00CB0E43F889381F9515B8914F2AE51`. Its canonical mechanics receipt `qa\pdf-mechanics.json` is schema v4 `PASS` with zero failures, bound by `qa\PDF_MECHANICS_ADMISSION_20260904.json` (3,412 bytes; SHA-256 `64FC160266A3621EA4A7C539F08D6376446FAFE65FC93C9AABDE0510786B6960`). The remaining release gate is the independently audited same-runtime visual delta plus page-complete aggregate inspection; this is not a claim that all 116 chapters are complete.

## Current P08 admission

The original intake receipt `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\00_lane_control\P08_CANON_INTAKE_ADMISSION_20260904.json` (12,076 bytes; SHA-256 `1B6F2EFD7BEF0F860A1538A3720FE31D7246D2CF0FC8116F50BB1A49AE143258`) remains valid historical evidence for the direct identities and structural replay it actually performed, but its Korean interpretation is append-only corrected by `P08_CANON_INTAKE_ADMISSION_CORRECTION_20260905.json` (6,122 bytes; SHA-256 `8ABE53A25B61B6328E8F0D60B43852AA5FC4E42CBA93D11BD77BF1C3BB8C225F`). Japanese Chapters 60–68 remain byte-identical to the units already present in the immutable Japanese snapshot. Simplified Chinese is already subsumed by the complete public R15 edition.

The Korean P08 tree is now preserved at `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\03_working_translations\stacks_cjk_20260821\canon\ko-kr\integration-20260904-r1` as an `EVIDENCE_SNAPSHOT_ONLY_NOT_CANON_ADMITTED` snapshot. All nine Chapters 60–68 reach their frozen upstream termini and 88/88 manifested identities plus 84/84 producer-to-snapshot identities replay exactly, but nine deterministic defects remain across Chapters 62, 63, 65, and 66. All 486 PNGs named by the nine render inventories are absent, including all 51 checkpoint-inspected PNGs. Therefore the Korean units are complete producer evidence, not clean canon admission or a cumulative reader. The exact next action is an additive canon successor applying only those nine enumerated repairs, followed by structural/protected-math replay and a mutex-guarded rebuild with newly preserved page-complete visual evidence. Producer bytes and the evidence snapshot remain unchanged.

### Korean P08 additive canon admission

The preceding r1 paragraph is preserved as historical intake state and is now superseded operationally by the additive corrected successor `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\03_working_translations\stacks_cjk_20260821\canon\ko-kr\integration-20260905-r2`. The nine exact authorized repairs replay from r1 into new successor bytes; only Chapters 62, 63, 65, and 66 changed, while Chapters 60, 61, 64, 67, and 68 remain byte-identical to r1. Ordered structure, protected math, authority termini, serialized builds, PDF mechanics, and page-complete visual evidence all pass. The successor contains nine PDFs / 444 pages and retains 444 page PNGs / 122,946,565 bytes plus 42 survey sheets. Its manifest has 1,776/1,776 matching identities. An independent read-only replay parsed 44 strict JSON files and six JSONL files / 1,886 rows, replayed all nine repairs, opened all nine PDFs, and found no discrepancy. Manager admission is bounded strictly to Korean Chapters 60–68; gaps remain 1–59 and 69–116, `cumulative_reader=false`, and `publication=false`. The manager receipt is `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\00_lane_control\P08_KO_CANON_ADMISSION_20260905.json` (4,591 bytes; SHA-256 `747984F6E31F9C207CB24FD47C1CC6CC3AD34C538D0CA13202F0560E12F7E019`).

### Current Korean P02 prefix intake

The Korean Chapter 15 return from P02 is a verified incomplete prefix, not canon admission. The exact harvested checkpoint covers `more-algebra.tex` source lines 1–18,861 and binds next source line 18,862, section `Perfect complexes`. Required structural replay passes, including 12,579/12,579 math spans; no TeX build or rendered-page gate was claimed. The producer target advanced after the checkpoint bytes were read, so the manager preserves the earlier checkpoint by hash without pretending the live mutable path still has those bytes. The intake receipt is `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\00_lane_control\P02_KO_CH15_PREFIX_18861_MANAGER_INTAKE_20260905.json` (5,896 bytes; SHA-256 `ECAFC952DF73422E48E84AF63E23A7203BE7BA0EF23E1552BDF2F74B1D2379DC`), classification `INCOMPLETE_PREFIX_NOT_CANON_ADMITTED`.

## Current Japanese visual gate execution

The first R3 full-render attempt used source `qa/render-visual-delta-r3.py` at 154,547 bytes / SHA-256 `34EB89CCC6FAD47B08B618B3583FB28EFA7E60F381A450495CFFB9F507BBD681`. Static review proved before completion that its compact runtime snapshot name `.r-17854FE8-3EFC` was rejected by its own teardown routine. The manager stopped the known-doomed process during batch 13, preserved its partial stage without inheriting any visual result, restored and removed the exact stale runtime snapshot, and wrote `qa/visual-delta-r3/ABORTED_R3_TEARDOWN_CONTRACT_20260904/ABORT_RECEIPT.json` (2,031 bytes; SHA-256 `F26E4194E7A08F28F7587F2908DAFE03806CC284FFB0A6A1F53651DAC694475B`).

The additive repair authorizes only exact compact names matching `.r-[A-F0-9]{8}-[A-F0-9]{4}` while retaining the descriptive synthetic-test namespace. Repaired source is 155,052 bytes / SHA-256 `29F5F41685A97250E746B8B91F8F0B7C55DA86A44ED93A9D0B07EDA42270BE05`; repaired tests are 98,711 bytes / SHA-256 `ABBE50F51565236AA3BBE25542C75E1CB248C819B8BE1EA4C11D1BBB46F843C1`. R3 tests pass 45/45, R2 regressions pass 48/48, and the exact 5,379-page production preflight passes without writes.

The next foreground execution lost its application command handle after reaching only an unauthenticated partial stage; no renderer process survived and no page result was inherited. Its additive evidence is `qa\visual-delta-r3\ABORTED_R3_FOREGROUND_HANDLE_LOSS_20260905\ABORT_RECEIPT.json` (2,066 bytes; SHA-256 `F7386CCF0418FDA576163D7C086489BA01C63F67884DFAD3D2ED58ED6C4614AE`). The live replacement therefore uses the durable hidden supervisor `qa\run-visual-delta-r3-worker.ps1` (6,278 bytes; SHA-256 `F3995A7E96B300AD9E4F9DF3908C3BFB8B9964DE910F88837B7B432F9ED9E62C`). Its immutable start receipt is `qa\visual-delta-r3\worker-r3-20260905\WORKER_START.json` (3,534 bytes; SHA-256 `BCDCF7342D2CC24C936BC32935CFCC298C4FE80226B414BA2DA254E09ED6D1AE`). At the 2026-09-05 manager check, supervisor PID 45364 and its Python child PID 5752 were both live and the exact stage `.s-17854FE8-3EFC` was advancing. Do not launch a duplicate renderer. Continue read-only polling of that supervisor, stage, and eventual `WORKER_TERMINAL.json`; no result is trusted until the authenticated `COMPLETE` receipt and subsequent fresh-page visual admissions pass.

The offline admission helper is now frozen and independently test-clean but has not been used against the live result. `qa\admit-visual-delta-r3.py` is 126,710 bytes / SHA-256 `5B2337D9B3571CECB67140552F0110C36206001DC6C47D79B097D552151110CC`; `qa\test-admit-visual-delta-r3.py` is 59,840 bytes / SHA-256 `3E60253C8C6B5F8C2EEEB7E3574A34A6021E8B45897EFB0E0515E3D2CAA2A093`. The manager independently reran its 25-test production-shaped suite with all 25 passing and reran the existing R3 renderer suite with all 45 passing. The final helper receipt is `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\00_lane_control\JA_VISUAL_ADMISSION_HELPER_FINAL_20260905.json`. Admission remains fail-closed until the one live worker emits an authenticated complete result and every fresh pixel-different page has a new visual disposition.

## Additive manager update — 2026-09-05 R9

### Manager-style visible organization

The visible organization now matches the manager pattern used for the EGA/FGA/SGA programme without changing any producer's assignment. The single pinned director remains `Stacks — Director · CJK Canon · Errata · Harvest · Releases`. Custom sidebar section `30553d79-cf5a-43d0-880d-516df6160f3d` is now named `Stacks CJK Production`; it contains P01–P12 in canonical chapter-range order followed by the supporting French full-corpus lane. Exact topology receipt: `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\00_lane_control\SIDEBAR_ORGANIZATION_20260905_R8.json`, 4,097 bytes, SHA-256 `B3A667839A9C4A310D79F9B7F21DC3473D2CA2585D4B661AFEA4CC7612ADC539`. No producer was messaged, reassigned, restarted, archived, or moved out of its existing write boundary.

### Ordered canon-admission queue

The current independently re-audited intake is frozen in `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\00_lane_control\STACKS_CJK_CANON_ADMISSION_QUEUE_20260905_R1.json`, 9,940 bytes, SHA-256 `324B562951B342278CB2845E3264D406C2548CE98447B129DD9FF0042BA17B98`. It queues exactly five chapter-complete source targets: Korean Chapter 17 (`modules.tex`) from P03; Japanese Chapter 51 (`local-cohomology.tex`) from P07; Korean Chapter 71 (`spaces-divisors.tex`) from P09; Korean Chapter 99 (`quot.tex`) from P11; and Japanese Chapter 114 (`coding.tex`) from P12.

These are source/target admissions for fresh cumulative successors, not standalone publication authorizations. Japanese Chapter 51's isolated PDF contains 232 visible external-reference `??` pairs; Korean Chapter 71's contains 239. Both source targets pass exact structure/protected-math replay and every referenced external label is recoverable from the frozen upstream corpus, so the defect is missing cumulative AUX context rather than translated-source loss. Their isolated PDFs must not be released. The cumulative successors must load the full cross-chapter label universe and reach zero unresolved ordinary references, zero unresolved navigation references, and zero extracted question-mark pairs before publication. The other three bounded PDFs pass their chapter-level mechanical and visual gates but are not cumulative releases.

Japanese Chapters 51 and 114 are queued for the next additive Japanese successor only after the immutable 95-chapter visual worker terminates. Korean Chapters 17, 71, and 99 are queued around the already admitted P08 Chapters 60–68 in canonical chapter order for the next additive Korean successor. Live incomplete work is expressly excluded: P02 Korean Chapter 15, P07 Japanese Chapter 52, P09 Korean Chapter 72, P11 Korean Chapter 100, and P12 Japanese Chapter 115. The manager does not copy or freeze mutable prefixes merely because a file exists.

### Japanese visual-worker successor state

The earlier supervisor/Python pair recorded in the preceding section subsequently ended before a trustworthy complete result and is historical only. Its partial batch-56 stage was preserved under `qa\visual-delta-r3\ABORTED_R3_ORPHANED_PARTIAL_BATCH56_20260905`; the additive receipt is 3,172 bytes, SHA-256 `AB66989BD398564DC657CF1667E4AF54F97CCDFDD9972307146DC1E10857854B`. No page result from that partial stage is admitted.

The sole live retry is the bounded wrapper `qa\run-visual-delta-r3-retry1.ps1`, 6,589 bytes, SHA-256 `660EA089917C3A6A54EC5263F1CE12CC33551CB917AF9E412062633575EAE59F`, invoking the unchanged repaired runner `qa\render-visual-delta-r3.py`, 155,052 bytes, SHA-256 `29F5F41685A97250E746B8B91F8F0B7C55DA86A44ED93A9D0B07EDA42270BE05`. Its start receipt is `qa\visual-delta-r3\worker-r3-retry1-20260905\WORKER_START.json`, 3,723 bytes, SHA-256 `20B2A0298129FEE977EF8A8EF71FB4DEE772F406568874F0DBD6AA19537F6C75`. At `2026-09-05T00:43:11Z`, wrapper PID 36912 and Python PID 50428 were live; the Python process advanced 1.96875 CPU seconds over a two-second sample and held 65,687,552 bytes working set. Therefore no duplicate renderer or cumulative Japanese mutation may begin while these exact processes remain live or their terminal state is unknown. Continue bounded polling of the exact handles and eventual terminal receipt; only an authenticated `COMPLETE` result followed by the frozen admission helper and visual review of every fresh pixel-different page can release this gate.

### Latest incomplete P02 Korean cursor

The earlier P02 line-18,861 intake remains historical evidence but is superseded as the live progress locator by a direct producer checkpoint through frozen `more-algebra.tex` source line 21,917. The current target identity at that checkpoint is 933,797 bytes / SHA-256 `164B0919DE494F5CF0BCDA26ED2444D7D6CEF05F4496D9B22BDC3F0D275E7E08`; QA receipt `p02\control\QA_KO_CH15_PREFIX_21917.json` is 4,161 bytes / SHA-256 `A492A89B46521ECE7661D37F8F45048A02290E85A49F36F4989F473CD8670317`; next exact source line is 21,918, section `Relatively perfect modules`. This remains an incomplete prefix with no build or canon admission. Do not harvest it until the complete Chapter 15 terminal and its final receipt exist.

### Durable boundary

This R9 update changes organization and manager intake only. It does not alter the frozen official authority, any producer target, any producer ledger, or the live Japanese integration snapshot. Complete units are copied only into fresh manager-owned successor roots. Every future public Japanese or Korean checkpoint remains language-specific, openly downloadable, and independently replayed on both GitHub and Zenodo; a partial cumulative release must state its exact included and missing chapters.

## Additive manager update — 2026-09-05 R10

The manager-style sidebar organization and the five-entry canon-admission queue remain unchanged. Their next-stage destinations are now represented by two fresh, manager-owned, strict-JSON import manifests rather than by edits to any producer tree or immutable cumulative snapshot.

Japanese successor staging is bound by `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\03_working_translations\stacks_cjk_20260821\canon\ja-jp\integration-20260905-r2\IMPORT_MANIFEST.json` (8,141 bytes; SHA-256 `0ADDF253EBE4A85B325785F201CC5507582487A2B272B45F72BA52051C57AC2A`). It queues only Japanese Chapters 51 and 114, producing a 97-chapter successor after the immutable 95-chapter predecessor completes its independent visual gate. Chapters 52 and 115 remain active/incomplete and excluded. The manifest records the required append-only P07 terminology/errata repairs and the P12 legacy-record crosswalk; it has copied no source, invoked no TeX, and altered no producer byte. At the 2026-09-05 03:01+02 manager observation, the sole authenticated predecessor renderer remained live in batch 16, pages 481–512, under wrapper PID 36912 and Python PID 50428; its terminal receipt was absent. No duplicate renderer is allowed.

Korean successor staging is bound by `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\03_working_translations\stacks_cjk_20260821\canon\ko-kr\integration-20260905-r3\IMPORT_MANIFEST.json` (10,497 bytes; SHA-256 `8F5615A1977B3EBFB406CA1F816F5FC75E2CE9E0D1444A8DF8F536B3257DF480`). It preserves the admitted P08 base Chapters 60–68 and queues exact Chapters 17, 71, and 99 in canonical order `[17,60,61,62,63,64,65,66,67,68,71,99]`. The fresh root has been materialized from the base and exact receipt-bound imports, but the manager keeps it outside the build gate until the complete cross-chapter dependency/reference universe closes deterministically. No Korean TeX build or publication claim exists yet.

The live P02 Korean Chapter 15 cursor has advanced beyond the earlier prefixes to frozen source line 23,554; the next exact line is 23,555, section `Rlim of modules`. The target at that checkpoint is 1,006,225 bytes / SHA-256 `4F0D29688D77C2CE6FD1266C67AC9BEBAEE7AF01664424C0F33B7A7DF8D7571B`; QA receipt `p02\control\QA_KO_CH15_PREFIX_23554.json` is 4,356 bytes / SHA-256 `7242ED5C38BC79789DFAE5FA950A9B7CFA3906167765C0C7C70064594A4D0B6E`. It remains an incomplete, unbuilt prefix and is excluded from canon admission.

Current durable activation: `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\00_lane_control\STACKS_CJK_MANAGER_ACTIVATION_20260905_R5.json` (6,099 bytes; SHA-256 `8083370536D75DBAECF31CC5E39B5D6A7A91FE10BF36FC3C74BDA5EF683E9452`).

## Additive manager update — 2026-09-05 R11

### Live organization readback

The manager pattern remains active without producer reassignment. The app now reports the correctly named and ordered `Stacks CJK Production` section under section ID `4e011bbf-2739-4385-8920-75cc82027f95`, not the older ID recorded by R8. All twelve P01–P12 tasks and the French source-review feed are active in canonical order, and the pinned director remains `Stacks — Director · CJK Canon · Errata · Harvest · Releases`. No producer was restarted, interrupted, or sent a new assignment. The append-only correction is `${USER_HOME}\Documents\interlanguage\03_projects\language_management\cjk\00_lane_control\SIDEBAR_ORGANIZATION_20260905_R9.json` (2,586 bytes; SHA-256 `E83918793A8FA3343FF243D5AA73C154EC590BE54B2FEC9F52B20E0CA30ECD78`).

### Japanese immutable-base visual replay

The retry1 worker ended without a terminal receipt after completing comparisons only through page 655 in memory. Its unauthenticated partial batch-21 stage was preserved byte-for-byte under `qa\visual-delta-r3\ABORTED_R3_RETRY1_ORPHANED_PARTIAL_BATCH21_20260905`; the retained stage is 34 files / 3,025,008 bytes / ordinal-tree SHA-256 `9CA668BD619CF8F25240666EF0482AB55B4F4BE8BAD0C27F417D81AC884FFA2B`. Its interruption receipt is 7,665 bytes / SHA-256 `902B64CDDD95823A85B64505845E322C0BF4655EF22AD421B9F1019194937C0F`. No partial comparison result is admitted.

One clean full replay is now active under `qa\visual-delta-r3\worker-r3-retry2-20260905`. Wrapper `qa\run-visual-delta-r3-retry2.ps1` is 6,557 bytes / SHA-256 `F6FD7ED92AAF53990A7CA4422485A0EBD0F64384F012FECF624E1EA1F97AD58F`; immutable `WORKER_START.json` is 3,707 bytes / SHA-256 `91DE382250446728400214B1228D4A6B11FC39954B2B6FC892E1C315EAC3ADCB`. The manager launch receipt is 2,334 bytes / SHA-256 `7D41424D77DEEFDA814C77D191F1190B47A8B9DD6340707494D279AA0FFA4572`. This worker invokes no TeX. Poll only this exact worker and its eventual terminal receipt; never launch a duplicate while its state is unknown.

### Korean cumulative reader

The Korean r3 successor has passed exact import replay, complete reference-support closure, all twelve serialized chapter builds, cumulative merge, mechanics, extraction, and byte-identical deterministic merge replay. Canonical order is `[17,60,61,62,63,64,65,66,67,68,71,99]`. The cumulative reader is 572 pages / 6,163,243 bytes / SHA-256 `D16F925E5EAD4BA519D2C5E5F7ED47F022810DE76484183BBAE5108D970190F7`; its build receipt is 86,487 bytes / SHA-256 `5EE1878B27DAB2E1E937F5E8EB728D5927D39330610F85260FC25ED412C93CD9` with result `PASS_CUMULATIVE_BUILD_PENDING_PAGE_COMPLETE_VISUAL_QA`.

Nine extracted `??` pairs are exactly inherited Xy-pic diagram-text extraction artifacts: three each on cumulative pages 229, 230, and 430, corresponding to already page-complete-inspected Chapter 64 pages 2–3 and Chapter 67 page 86. There are zero new or unexplained pairs. Chapter 99 has one 1.12279-point overfull-vbox diagnostic; fresh full-resolution inspection of its affected pages passes with no clipping, overlap, or margin breach. The append-only gate receipt is `cumulative\receipts\CUMULATIVE_BUILD_EXCEPTIONS_ADJUDICATION.json` (3,633 bytes; SHA-256 `020D79297E90409B93D17E58CFA0AF41BA20101D610C8D7FA8E6485E134CBFBB`). Attempt-6 failure evidence remains preserved under its attempt directory, while the stale root-level failure marker was removed after the successful build.

The independent page-complete cumulative visual gate is active. It has rendered all 572 pages at 120 dpi and is inspecting every page in disjoint batches, including fresh full-resolution checks of every inherited extraction-exception page and the Chapter 99 box-warning locus. Publication and the first Korean-specific public lineage remain gated only by this deterministic visual receipt and final release-package replay.

### Terminology and English-source errata propagation

The Korean terminology manager export is `STACKS_KO_TERMINOLOGY_EXPORT_20260905_R1.json` (10,922 bytes; SHA-256 `BD3E4DCD4A5CB0C0BFCCB1E4D5A33DEFEEC6424318B2B228B09A78F60DDFC639`). Its additive EGA/FGA cross-corpus return is `STACKS_KO_TERMINOLOGY_CROSS_CORPUS_RECEIPT_20260905_R2.json` (3,292 bytes; SHA-256 `9115BA730AD903078AFC50D46AFAF74DD32B186BA18F014F53CE93F9BE4788D0`). This evidence confirms the finite-type versus finitely-generated distinction, fills the provisional `prescheme` choice with established `준스킴`, and preserves legacy spelling/spacing variants as review candidates rather than automatic replacements. It mutates no producer or canon source.

Seven new `descent.tex` corrections have been independently deduplicated against 1,137 R1–R39 registry records and accepted as exact once-only preimages: five grammar repairs plus the missing smooth case at lines 5337–5343 and `finite type` to `finite presentation` at line 5775. Strict receipts are `STACKS_DESCENT_GRAMMAR_INTAKE_20260905_R1.json` (11,695 bytes; SHA-256 `2B4AEBA9C29C923CAA3E143782D189E7482BDBE17ABEECAC2A751B639007830B`), `STACKS_DESCENT_MATHEMATICAL_OMISSION_INTAKE_20260905_R2.json` (8,142 bytes; SHA-256 `18AB70FB6D6E200BBA35F309397CECAE169109A6359F61D82E92BA2DFC8FD609`), and `STACKS_DESCENT_FINITE_PRESENTATION_INTAKE_20260905_R3.json` (7,214 bytes; SHA-256 `2B2298169C8425B5F0DEF84FDF51D77E2E07B8495CF85CC010536B3AAD1630CD`). All three were routed once to the persistent English Stacks registrar/composer task. They are intake evidence only until that task allocates permanent stable IDs and admits manifest-bound overlays; frozen CJK targets remain diplomatic.

### Latest incomplete producer cursor

P02 Korean Chapter 15 has advanced through frozen `more-algebra.tex` source line 25,827, completing `The Beauville-Laszlo theorem`; next is line 25,828, `Derived Completion`. The live target at that checkpoint is 1,101,622 bytes / SHA-256 `34319E7A3C9D095BCAF85E6E217718FC4324010FBE6D08765F0E67DC0C13351E`; QA receipt is 4,658 bytes / SHA-256 `B525654F9CAB96B8BD2E3E6A332BA797BE89EBC23595C9B4855B5FF6E223B017`. This remains an incomplete prefix, has not been built, and is excluded from cumulative admission. All other producers continue on their own durable cursors; a separate manager snapshot is being reconstructed from primary control artifacts without interrupting them.
