# The instrument makes the winner: reconciling two contradictory 2026 head-to-head evaluations of clinical AI

**Author:** Koyar Afrasyab, M.D. — *corresponding author.*
**Affiliation:** Independent researcher; Founder, Kinvectum.
**Correspondence:** Koyar Afrasyab (Kinvectum). ORCID: [to complete before submission].
**Article type:** Brief report / methodological reconciliation.
**Preprint + code:** see *Data and code availability*.

---

## Abstract

**Background.** Two 2026 head-to-head studies reached opposite conclusions about specialized clinical
AI. Real-POCQi (arXiv:2606.28960) found OpenEvidence (OE) beat frontier general-purpose LLMs on
blinded physician **pairwise preference** across 620 real point-of-care queries; a Nature Medicine
study (s41591-026-04431-5) found frontier LLMs beat OE and UpToDate Expert AI under **absolute 1–4
rubric** scoring. Each study also sourced its "real-world" queries from the platform that won
(home-field provenance), and the two used different model versions and evaluation instruments,
confounding any direct comparison.

**Objective.** Test whether the **evaluation instrument alone** — with queries and answers held fixed
— can flip the winner, isolating it from query provenance, model version, and answer content.

**Methods.** We reused Real-POCQi's public data (CC BY 4.0): the same 620 queries, the same four
systems' verbatim answers (Claude Opus 4.8, Gemini 3.1 Pro, GPT-5.5, OpenEvidence), and the same
blinded human pairwise ratings. On a seed-fixed 150-query sample we re-scored every answer with a
**Nature-style absolute 1–4 rubric** administered by a blinded four-model LLM-judge panel (GPT-5.5,
Claude Opus 4.8, Grok-4.3, Gemini-3.5-flash), all at **high reasoning effort with token consumption
verified**. We derived the identical OE-vs-rest win-difference metric under both instruments and
compared them, with 2,000-replicate cluster bootstrap (on `question_id`), per-judge self-preference,
leave-one-judge-out robustness, and inter-judge agreement. To separate the *instrument* effect from a
*rater-population* effect (physicians vs LLMs), we additionally ran the same blinded panel under the
**pairwise** instrument, filling three of the four cells of a {pairwise, rubric} × {human, LLM} design
and decomposing the swing into rater-modality (B−A) and instrument-format (C−B) components.

**Results.** Swapping only the instrument **eliminated OE's advantage on every axis, though not
uniformly**: it reversed OE's sign on two axes, collapsed it to statistical null on two, and shrank it
roughly threefold — while leaving it significantly positive — on the fifth. On accuracy — the marquee
axis — the LLM-rubric panel scored OE **−29.1 pp (95% CI −38.0 to −19.8): a *significantly OE-negative*
verdict on the very answers human raters preferred OE on** (+24.4 pp on the full Real-POCQi data; +10.4
pp, CI −1.6 to +22.2, on the identical 150-question subsample, which is same-signed but underpowered).
The negative sign survived dropping any single judge, including the self-preferring GPT-5.5 (−12.3 pp
without it). Clinical utility also reversed significantly; **source quality kept a significantly positive
but ~3× smaller OE edge (+12.0 pp, CI excluding zero)**; completeness and verifiability collapsed to
statistical null. GPT-5.5 self-preferred (+0.481 points to own family; Opus +0.121; Gemini +0.004),
amplifying but not creating the reversal. Inter-judge agreement was modest (Spearman 0.19–0.47),
mirroring the low rater agreement reported by the Nature study itself. **The 2×2 decomposition (cell A
computed on the *same* questions as B and C) localizes the cause to the instrument, not the rater: LLM
judges administering the *pairwise* instrument reproduce the human verdict — OE wins on four of five axes
— and the instrument-format component (C−B, −30 to −44 pp on every axis) dominates the rater-modality
component (B−A). On accuracy specifically, the instrument component (−32.7 pp) accounts for ~83% of the
human-pairwise→LLM-rubric swing; rater modality contributes only −6.8 pp.** The reversal is also **not a
length artifact**: OE produces the *longest* answers yet loses on accuracy, and length-adjusting the
rubric gap leaves it unchanged within CI.

**Conclusions.** The two studies' disagreement is driven substantially by the **evaluation
instrument** (pairwise preference vs absolute rubric) rather than by whether humans or LLMs do the
rating, independently of query provenance, model version, and answer content. This conclusion is
established *within LLM raters* (cells B and C); bridging it to the human-rated Nature rubric requires
assuming no rater×instrument interaction — i.e. that human raters would show the same pairwise→rubric
shift LLMs do. We could **not** fill the fourth {human, rubric} cell, so we flag this additivity
assumption as the central untested step and the primary target for follow-up (even a small human-rubric
sample would test it). Subject to that caveat, "which clinical AI is best" is not instrument-invariant;
leaderboards must report the instrument as a first-class experimental factor. We additionally document
two under-reported flaws common to both source studies — omission of the actual product clinicians use
(the ChatGPT product), and unreported/uncontrolled reasoning effort — and pre-register a full
provenance × instrument × citation factorial (including the missing human-rubric cell) to estimate each
factor's causal contribution.

---

## 1. Introduction

Point-of-care clinical AI is now evaluated by head-to-head studies whose results directly influence
purchasing and deployment. Medical-AI evaluation has grown rapidly, spanning licensing-exam question
banks,[^medqa] physician-aligned rubric benchmarks,[^healthbench] large language models that encode
clinical knowledge,[^medpalm] specialized and mobile-sized clinical models,[^medmobile]<sup>,</sup>[^cardio]<sup>,</sup>[^obsidian]
health-system-scale prediction and operations models,[^nyutron]<sup>,</sup>[^hospops] sequential
diagnostic reasoning,[^seqdx] retrieval-augmented generation for healthcare,[^rag] and a parallel
literature documenting these systems' failure modes —
susceptibility to distraction,[^distracted] conflict between an LLM's internal prior and retrieved
evidence,[^clasheval] data-poisoning attacks,[^poison] and the need for clinically safe generation.[^noharm]
These benchmarks increasingly characterize their query distributions with topic models.[^bertopic]
Deployment is already at health-system scale.[^jamia] In 2026 two such studies reached **opposite**
conclusions using overlapping systems,[^poc]<sup>,</sup>[^nat] which is the strongest possible signal that at least one
conclusion is an artifact of method rather than of the systems compared.

Both studies contain a symmetric structural feature — each sourced its "real-world" query set from the
platform that ultimately won (Real-POCQi from OpenEvidence traffic; the Nature study's real-clinical-
query benchmark from an NYU Langone GPT deployment) — and each used a **different evaluation
instrument** (blinded human pairwise preference vs absolute rubric scoring). Provenance and instrument
are therefore fully confounded in the published record. This paper isolates the instrument by holding
everything else constant, and then situates that result within a fuller critique and a pre-registered
factorial design.

Our contributions:
1. **An instrument existence proof plus a rater/instrument decomposition** (executed, on public data):
   with queries and answers held fixed, changing the instrument reverses, nullifies, or sharply
   attenuates OE's advantage on every axis (§4.1); and by filling three cells of a {pairwise, rubric} ×
   {human, LLM} design we show the swing is
   driven by the **instrument format**, not by the human-vs-LLM rater change — LLMs given the pairwise
   instrument agree with physicians on four of five axes (§4.5).
2. **Two methodological critiques** of both source studies: the comparator set omits the ChatGPT
   product clinicians actually use, and reasoning effort is unreported or uncontrolled (§5).
3. **A pre-registered 2×2×2** provenance × instrument × citation design (§7) that would estimate each
   factor's causal contribution, with power grounded in measured variance components. This is a
   *proposed design, not an executed result* — we flag it as such to keep the executed contribution
   (#1) cleanly separated from future work.

## 2. The two source studies (verified)

Numbers below were verified for this work from primary sources (Nature PDF Methods; Real-POCQi
abstract + HTML full text).

**Real-POCQi**[^poc] (arXiv:2606.28960; dataset `jjfenglab/Real-POCQi`, CC BY 4.0). 620 real
point-of-care queries sourced from OpenEvidence[^oe] plus 187 HealthBench[^healthbench] items; 149
physicians across 36 states; blinded **pairwise** comparisons — the arena-style preference paradigm[^arena]
— on five axes (accuracy, clinical utility, source quality, completeness, verifiability). Systems: Claude
Opus 4.8, Gemini 3.1 Pro, GPT-5.5, OpenEvidence, all queried via API; temperature 0.0, seed 42, web
search enabled; **"Thinking was automatically determined by the LLM."** OE won by roughly +25 to +39 pp
win-difference. *The data collection was run by the platform under study (conflict of interest).*

**Nature Medicine**[^nat] (s41591-026-04431-5, NYU Langone + UT Austin). MedQA[^medqa] (500) +
HealthBench[^healthbench] (500) + a 100-item real-clinical-question (RCQ) benchmark sampled from NYU's
HIPAA-compliant GPT instance;[^jamia] 12 clinician raters; **absolute 1–4 rubric**. Systems: GPT-5.2
(2025-12-11), Gemini 3.1 Pro Preview, Claude Opus 4.6 (all API), OpenEvidence and UpToDate Expert
AI[^utd] (browser), plus Google Search AI Overview (RCQ). Temperature 0.0, seed 62, search enabled;
**reasoning effort not reported.** Length not normalized (by explicit choice). Frontier LLMs won: e.g.
HealthBench GPT 88.0 / Gemini 79.3 / Claude 77.0 / OE 62.6 / UpToDate 61.3; RCQ Gemini 3.62 / GPT 3.54 /
Claude 3.52 / OE 3.24. HealthBench was graded by an LLM-judge panel (self-preference risk); RCQ
item-level agreement was low (Krippendorff α ≈ 0.10–0.20). License CC BY-NC-ND 4.0.

The two studies thus differ simultaneously in **provenance, instrument, model version, and access
path** — none of which is individually identified by comparing their published leaderboards.

## 3. Methods

### 3.1 Design: hold queries and answers fixed, vary only the instrument
We reuse Real-POCQi's public artifacts unchanged: the 620 queries, the four systems' verbatim answers,
and the blinded human pairwise ratings. On a seed-fixed sample of **150 queries** (`random_state=62`;
600 answers) we administer a **second instrument** — Nature-style absolute 1–4 rubric scoring — to the
*same* answers, then derive the *same* OE-vs-rest win-difference metric from both instruments. Because
queries, answers, provenance, and model versions are identical across the two instruments, any change
in the metric is attributable to the instrument.

### 3.2 The rubric instrument (LLM-judge panel)
Each answer is scored 1–4 (1 unacceptable … 4 excellent) on the five Real-POCQi axes by a blinded
panel of four judges — GPT-5.5, Claude Opus 4.8, Grok-4.3, Gemini-3.5-flash — chosen to span vendors
and to include contestant families (enabling a self-preference measurement) and one family with no
contestant (Grok). We stress that Grok is a *family-neutral* reference, **not a bias-free** one: as an
LLM it may still share the panel's general preference for frontier-style prose (structure, breadth,
hedging), a house effect that leave-one-judge-out cannot remove (§4.2, Limitation iii). Judges see only the question and one answer, are told nothing
about the source system, and return JSON scores only (system prompt in `judge/grade.py`). All judges
run at **high reasoning effort**; we **verify** reasoning-token consumption on a real grading item
(GPT-5.5 3,071; Grok-4.3 1,880; Gemini-3.5-flash 922; Opus-4.8 443 thinking tokens;
`judge/verify_thinking.py`). 2,388 of 2,401 answer-grades completed (0.5% failures — transient
timeouts and a few Gemini truncations — balanced across systems).

### 3.3 Metric and statistics
For each axis we compute the **panel-mean 1–4 score per (question, system)**, then form the OE-vs-rest
**win-difference** = 100 × (wins − losses) / comparisons across the three frontier systems per
question — the same one-vs-rest statistic Real-POCQi reports for human pairwise, a win-ratio-family
contrast[^winratio] in the arena-style preference tradition.[^arena] Uncertainty: 2,000
cluster-bootstrap replicates resampling **questions** (cluster on `question_id`). Robustness:
**leave-one-judge-out** (recompute dropping each judge). Bias: **self-preference** = mean own-family
minus mean others, paired within (question, axis). **Inter-judge agreement** = Spearman correlation of
per-(question, system) mean scores. Human comparison uses the `qa_text_only` render mode (matching the
citation-free OE answers in the dataset).

**Multiplicity.** We test five axes; we report per-axis 95% cluster-bootstrap CIs without a formal
family-wise correction, so the two axes closest to the null boundary (source quality lower CI +1.6;
clinical utility upper CI −3.6) would not necessarily survive Bonferroni/Holm adjustment across five
tests. The headline accuracy reversal (CI −38.0 to −19.8) is far from the boundary and robust to any
standard correction. We flag the borderline axes explicitly rather than over-claiming per-axis
significance.

### 3.4 The pairwise cell (2×2 decomposition)
To separate the instrument from the rater population we administer a **second instrument to the same LLM
panel**: blinded forced-choice **pairwise** preference (A/B/tie per axis), OpenEvidence vs each of the
three frontier systems, on the same 150-query sample (`judge/pairwise.py`). Slot order is deterministically
randomized per (question, opponent, judge) via a hash and de-blinded at scoring, removing position bias.
We de-blind each A/B/tie verdict to an OE win/loss/tie and compute the identical OE-vs-rest win-difference,
with the same 2,000-replicate `question_id` cluster bootstrap. This yields cell **B = {pairwise, LLM}**,
which — with cell A = {pairwise, human} (Real-POCQi) and cell C = {rubric, LLM} (§3.2) — gives three of
the four cells of the {pairwise, rubric} × {human, LLM} design and identifies the **rater-modality effect
(B−A)** and the **instrument-format effect (C−B)** (§4.5). Judges run at high reasoning effort; all four
judges completed 448–450/450 comparisons (1,798/1,800 overall).

## 4. Results

### 4.1 The instrument flips the winner (Figure 1, Table 1)

![Figure 1](judge/out/existence_proof.png)

**Figure 1.** Instrument existence proof. OE-vs-rest win-difference (percentage points) per axis under
the human blinded pairwise instrument (same 150 questions) versus the LLM-judge absolute-rubric panel
(n = 150), with 95% cluster-bootstrap confidence intervals. Holding queries and answers fixed and
changing only the instrument eliminates OE's advantage on every axis — reversed on two, null on two,
threefold smaller on one.

**Table 1.** OE-vs-rest win-difference (pp) by axis under each instrument, **both computed on the same
150-query sample** (2,000-replicate `question_id` cluster bootstrap). The human column is the human
pairwise win-difference restricted to the identical questions (86–119 of 150 carry human text-only
ratings, by axis); the "full data" column is the win-difference on Real-POCQi's complete text-only bank
(reproduced in §4.4), shown for reference because the subsample is underpowered. The native-gap column
gives the OE-minus-mean-of-frontier gap on the raw 1–4 rubric (see scale note).

| Axis | Human pairwise, same 150 (pp) [95% CI] | Human, full data (ref) | LLM-judge panel (pp) [95% CI] | Native gap (1–4 pts) | Verdict |
|---|---:|---:|---:|---:|---|
| Accuracy | +10.4 [−1.8, +22.2] | +24.4 | **−29.1 [−38.0, −19.8]** | −0.127 | LLM rubric significantly negative; sign flips |
| Clinical utility | +14.4 [−1.6, +31.4] | +29.5 | −12.2 [−20.9, −3.6] | −0.021 | LLM rubric significantly negative; sign flips |
| Source quality | +23.2 [+7.6, +38.0] | +38.1 | +12.0 [+1.6, +22.9] | +0.103 | OE edge survives, ~3× smaller |
| Completeness | +13.6 [−2.5, +28.7] | +30.3 | −3.6 [−12.4, +6.0] | +0.004 | collapses to null |
| Verifiability | +14.4 [+2.2, +27.6] | +25.5 | +0.7 [−10.0, +11.1] | +0.003 | collapses to null |

The headline is accuracy. Real-POCQi's central finding is that physicians prefer OE on accuracy (+24.4
pp on the full data; +10.4 pp, CI −1.8 to +22.2, on this 150-query subsample — same sign, but the
subsample carries only 86 accuracy ratings and is underpowered). On the **same answers**, the LLM-rubric
panel scores OE **−29.1 pp [−38.0, −19.8] — significantly negative**. So the instrument swap moves the
accuracy verdict from OE-favoring (significantly so at full power; positive but CI-crossing in this
subsample) to *significantly OE-disfavoring*. Two axes flip sign into significantly-negative territory
(accuracy, clinical utility), one retains a much-attenuated but significantly positive OE edge (source
quality), and two collapse to null. Under no axis does OE retain its large human-pairwise advantage. We
deliberately avoid framing this as "a significant +24 becomes a significant −29": at the 150-query
existence-proof scale the human accuracy estimate is not itself significant, so the clean claim is a
**sign reversal to a significantly-negative rubric verdict on identical content**, corroborated by the
full-data human sign.

**Note on scale (native vs win-difference).** The win-difference is a sign-of-the-gap statistic:
because per-question frontier scores cluster tightly, a mean rubric gap as small as **−0.127 of one
point** (accuracy) is enough to flip the majority of head-to-head comparisons and produce a −29 pp
win-difference, while a near-zero gap (completeness +0.004, verifiability +0.003) yields a null
win-difference. We therefore report both scales: the **native gap** shows the *effect size is modest in
absolute terms*, and the **win-difference** shows it is *directionally decisive* under the same
one-vs-rest rule Real-POCQi used. Neither instrument's metric should be read as a large clinical-quality
gulf; the point is that the two instruments order the systems differently on identical content.

### 4.2 The reversal is not merely a self-scoring artifact
LLM-as-judge panels are now a standard evaluation tool[^mtbench] but are known to favor their own
generations,[^selfpref] so we measure this directly. Contestant-family judges self-preferred (GPT-5.5
**+0.481**, Opus **+0.121**, Gemini **+0.004** points, own family minus others). Yet leave-one-judge-out shows the **accuracy reversal survives dropping any
single judge, including GPT-5.5** (−12.3 pp with GPT-5.5 removed — still negative). GPT-5.5 amplifies
the flip roughly fourfold but does not create it. By contrast, the clinical-utility reversal is
GPT-5.5-dependent (→ +2.5 pp without it) and is reported as such.

**A residual house effect remains, however.** Leave-one-judge-out and the self-preference statistic
only address *family-specific* bias — a judge favoring its own vendor's answer. They do **not** remove
the bias all four LLM judges may *share*: a common preference for the structured, comprehensive,
frontier-style prose that general-purpose LLMs produce (and are trained on), against OE's terser
clinician-tuned framing. Because even our family-neutral judge (Grok) is itself an LLM, no judge in the
panel is a clean control for this shared stylistic prior. The frontier "win" under the rubric is
therefore best read as *"frontier answers score higher on an LLM-administered rubric,"* not as a
family-free verdict of clinical superiority — a caution we carry into the Discussion and Limitation (iii).
The LLM-pairwise cell (§4.5) directly tests this house effect and finds it is **specific to the rubric
instrument**: the same judges — including the family-neutral one — prefer OE under pairwise. Human-
administered rubric scoring would be the remaining control (pre-registered, §7).

### 4.3 The instrument is noisy
Inter-judge Spearman agreement was modest (0.19–0.47), closely mirroring the low item-level agreement
the Nature study reports for its own human raters (α ≈ 0.10–0.20). Rubric scoring — whether by humans
or LLMs — is a higher-variance instrument than forced-choice preference; this is part of *why* it can
diverge from pairwise, not a defect unique to our panel.

### 4.4 Public-data reproductions (pipeline validation)
Our one-vs-rest win-difference on the human text-only data reproduces Real-POCQi to <1 pp on every axis
(e.g., accuracy +24.4 vs 24.7 published). A separately reported citation-halo analysis
(`analysis/analyze.py`) finds OE's between-groups accuracy "halo" (+11.4 pp) **collapses to +1.5 pp
(NS)** within questions rated in both render modes — i.e., largely a selection artifact, not a causal
citation effect — motivating the randomized citation arm in §7. Measured question-level SD = 0.598
grounds the power analysis.

### 4.5 Decomposing the swing: it is the instrument, not the rater (Figure 2, Table 2)

A natural objection to §4.1 is that swapping {human pairwise} → {LLM rubric} changes **two** things at
once — the *rater population* (physicians → LLMs) and the *instrument format* (forced-choice preference
→ absolute rubric) — so the reversal could be a human-vs-LLM effect rather than an instrument effect.
The two source studies share exactly this confound. We break it by filling the missing cell of the
2×2 {pairwise, rubric} × {human, LLM} design: we ran the **same four-judge LLM panel, blinded, at high
reasoning effort, on the same 150 queries and answers**, but administered the **pairwise** instrument
(forced A/B/tie per axis, slot order deterministically randomized and de-blinded at scoring;
`judge/pairwise.py`). This gives three of four cells — A = {pairwise, human} (Real-POCQi), B = {pairwise,
LLM} (new), C = {rubric, LLM} (§4.1) — and lets us attribute the A→C swing to a **rater-modality
component (B−A)** and an **instrument-format component (C−B)**.

![Figure 2](judge/out/decomposition.png)

**Figure 2.** The 2×2 rater-vs-instrument decomposition (n = 150). *Left:* three cells of the
{pairwise, rubric} × {human, LLM} design per axis — both pairwise cells (A: human; B: LLM) favor
OpenEvidence; only the rubric cell (C) reverses it. *Right:* the human-pairwise→LLM-rubric swing split
into a rater-modality component (B−A) and an instrument-format component (C−B); the instrument component
dominates on every axis.

**Table 2.** OE-vs-rest win-difference (pp) across three cells of the 2×2, and the decomposition of the
human-pairwise→LLM-rubric swing. **Cell A is computed on the same 150-query sample as B and C** (human
text-only ratings restricted to those questions), *not* on the full text-only bank — otherwise B−A would
absorb a sample-composition difference into the "rater" term. Cell B: n=150, 2,000-replicate cluster
bootstrap; 8,990 axis-verdicts (1,798/1,800 comparisons, all four judges 448–450/450).

| Axis | A: pairwise/human (same 150) | B: pairwise/LLM [95% CI] | C: rubric/LLM | Total (C−A) | Rater (B−A) | **Instrument (C−B)** |
|---|---:|---:|---:|---:|---:|---:|
| Accuracy | +10.4 | +3.6 [−2.5, +9.6] | −29.1 | −39.5 | −6.8 | **−32.7** |
| Clinical utility | +14.4 | +18.2 [+10.4, +25.9] | −12.2 | −26.6 | +3.8 | **−30.4** |
| Source quality | +23.2 | +48.8 [+42.1, +55.4] | +12.0 | −11.2 | +25.6 | **−36.8** |
| Completeness | +13.6 | +37.0 [+29.2, +44.5] | −3.6 | −17.2 | +23.4 | **−40.6** |
| Verifiability | +14.4 | +45.1 [+38.1, +51.9] | +0.7 | −13.7 | +30.7 | **−44.4** |

Two results stand out. **First, LLM judges administering the *pairwise* instrument largely reproduce the
human pairwise verdict**: OE wins on four of five axes (source quality +48.8, verifiability +45.1,
completeness +37.0, clinical utility +18.2), with only accuracy attenuating to a null +3.6. The
much-feared "LLMs simply disagree with physicians" story is therefore false for four of five axes — given
the *same* forced-choice instrument, LLMs and physicians agree that OE's answers are preferred.
**Second, the instrument-format component (C−B) is large, negative, and consistent on every axis (−30.4
to −44.4 pp), and it dominates the rater-modality component (B−A, which is small on accuracy and positive
on three axes).** The swing from "OE wins" to "OE loses" is thus attributable primarily to the
**pairwise→rubric instrument change**, not to the human→LLM rater change. Accuracy is the one axis where
both components push in the same (negative) direction, but even there the instrument does the
overwhelming majority of the work: **−32.7 pp instrument vs only −6.8 pp rater — ~83% of the swing is the
instrument.** (With cell A taken instead on the full text-only bank, the accuracy rater term would appear
as −20.8 pp; that larger value is an artifact of comparing the LLM cells against a different, larger
question sample, and we do not use it.)

This also sharpens the house-effect discussion (§4.2). Under the pairwise instrument, the **family-neutral
judge (Grok) prefers OE on all five axes** (+11 to +65 win-diff) and the contestant **GPT-5.5 is the
*least* OE-favorable** judge — the *opposite* of what a shared pro-frontier stylistic bias would predict.
The pro-frontier tilt is therefore specific to the **rubric** instrument, not a blanket LLM prejudice
against OE. (One robustness note: Gemini-3.5-flash initially stalled at 297/450 pairwise verdicts when the
Google API account exhausted its credit quota mid-run; after credits were restored we completed the cell
to 448/450, and the point estimates shifted <3 pp from the partial-coverage run — i.e., the conclusion
never depended on the missing data.)

### 4.6 The rubric reversal is not a length artifact (Table 3)

Answer length is the most-cited uncontrolled confound in both source studies (neither normalizes length).
The natural worry is that the rubric rewards longer, more comprehensive answers. We test this on the
rubric cell without regenerating any answers (`judge/length_analysis.py`). The premise fails at the first
step: **OpenEvidence produces the *longest* answers** (median 3,600 chars vs GPT-5.5 2,232, Opus 3,294,
Gemini 3,586), yet it *loses* the accuracy rubric — so a "longer answers win" mechanism runs *backwards*
against the finding. We confirm this three ways (Table 3): (i) the per-axis length **slope** is tiny
(−0.015 to +0.042 rubric points per 1,000 characters); (ii) the **length-adjusted intercept** — the
expected OE-minus-frontier score gap at *equal length* — is statistically indistinguishable from the raw
gap on every axis (accuracy −0.12 [−0.17, −0.08] adjusted vs −0.127 raw); and (iii) the accuracy
win-difference stays negative **whether OE's answer is longer (−34.3) or shorter (−19.9) than its
opponent's** — OE loses on accuracy even when it is the longer answer.

**Table 3.** Length sensitivity of the rubric cell (n=150; 2,000-replicate cluster bootstrap). Native-scale
OE-minus-frontier score gap: raw vs length-adjusted (intercept at equal length); and the accuracy
win-difference split by whether OE is the longer or shorter answer.

| Axis | Raw gap (pts) | Length-adjusted gap [95% CI] | Slope (pts / +1k chars) | Win-diff: OE longer | Win-diff: OE shorter |
|---|---:|---:|---:|---:|---:|
| Accuracy | −0.127 | −0.12 [−0.17, −0.08] | −0.015 | −34.3 | −19.9 |
| Clinical utility | −0.021 | −0.03 [−0.06, +0.01] | +0.016 | −14.1 | −8.4 |
| Source quality | +0.103 | +0.09 [+0.03, +0.15] | +0.042 | +15.9 | +6.0 |
| Completeness | +0.004 | −0.01 [−0.05, +0.03] | +0.039 | +0.7 | −10.8 |
| Verifiability | +0.003 | −0.01 [−0.06, +0.05] | +0.025 | +1.4 | +0.0 |

Length has a small positive association with source-quality/completeness/verifiability scores (slopes
+0.03 to +0.04 per 1,000 chars) but essentially none with accuracy, and adjusting for it leaves every
axis's OE-vs-frontier gap unchanged within CI. The accuracy reversal is therefore **not** explained by
length. (This does not make length irrelevant in general — a fully length-matched *generation* study is
still pre-registered, §7 — but it removes length as an alternative explanation for the observed reversal.)

## 5. Critiques of both source studies

The two critiques below are **independent of the instrument existence proof** (§4): they hold whether
or not the instrument drives the disagreement, and they apply symmetrically to both source studies. We
include them because they bound how far *either* published leaderboard can be trusted for procurement,
but a reader interested only in the instrument result can treat this section as standalone context.
Full detail in `CRITIQUES.md`. Two points bear directly on interpretation:

**(a) The comparator set omits the AI clinicians actually use.** Both studies benchmark **bare frontier
API models**; neither includes the **ChatGPT product** (consumer or clinician deployment), whose system
prompt, retrieval/browsing, memory, and safety guardrails move the very axes under test. This is
especially asymmetric because OE is itself a curated clinical *product*; Nature further queries clinical
tools via browser but frontier models via API. A fair benchmark should include a **product arm** distinct
from the raw model endpoint.

**(b) Reasoning effort is unreported or uncontrolled.** Nature reports temperature 0.0 and a seed but
**never states reasoning effort** (its cost table confirms reasoning tokens were spent, at an
unspecified level); Real-POCQi reports only that "thinking was automatically determined by the LLM."
Reasoning effort is the largest controllable performance lever for these models and can reorder
leaderboards, so neither head-to-head is reproducible on this axis. Our study pins high effort and
verifies token consumption (§3.2).

A corroborating confound: Real-POCQi tested **newer** frontier weights (GPT-5.5, Opus 4.8) than Nature
(GPT-5.2, Opus 4.6) and still found them losing on human pairwise — a pattern more consistent with an
instrument effect than a model-version effect.

## 6. Discussion

Holding queries and answers fixed, the instrument alone is sufficient to reverse the central claim of a
published clinical-AI benchmark. The 2×2 decomposition (§4.5) makes this attribution explicit rather than
inferential: because the *same* LLM panel that reverses OE under the rubric **reproduces the human
pairwise verdict when it uses the pairwise instrument** (OE winning on four of five axes), the swing
localizes to the pairwise→rubric change (C−B, −30.4 to −44.4 pp) and not to the human→LLM change (B−A).

**Two scoping caveats bound this claim.** *First*, the decomposition is established **within LLM raters**:
we have cells A = {pairwise, human}, B = {pairwise, LLM}, and C = {rubric, LLM}, but **not** the fourth
cell D = {rubric, human}. The two-study reconciliation is ultimately a claim about a *human-rated* rubric
study (Nature), so generalizing our within-LLM instrument effect (C−B) to explain Nature requires
assuming **no rater×instrument interaction** — that physicians administering a rubric would show the same
pairwise→rubric shift LLMs do. That assumption is plausible but untested, and this is precisely the
direction where interaction is likely: humans may not share the frontier-prose prior that an LLM-scored
rubric appears to reward, so the human-rubric cell could differ materially from our LLM-rubric cell. We
therefore state the proven claim narrowly ("the instrument dominates the rater *modality* among LLM
raters") and treat the bridge to Nature as conditional on additivity; filling cell D — even with a small
human-rubric sample — is the single highest-value follow-up. *Second*, the axis where our headline lives,
accuracy, is also the axis where the rater term is not negligible in the same direction: instrument −32.7
pp and rater −6.8 pp (≈83% instrument), cleaner than before once cell A is put on the same sample, but not
a pure instrument effect. The clean "instrument, not rater" statement is strongest for source
quality/verifiability/completeness and merely dominant — not exclusive — for accuracy.

This does not show OE is worse (or better) than frontier models in the clinic — we have **no adjudicated
ground truth** — but it shows that "which system is best" is a function of the measuring instrument, and
that pairwise-preference and absolute-rubric instruments encode materially different value functions
(preference rewards OE's clinician-tuned framing and citations; rubric scoring rewards frontier models'
breadth and structure). It also reframes the "LLM-judge self-preference" worry: the pro-frontier tilt is
a property of the **rubric instrument**, not of LLM judges per se, since those same judges favor OE under
pairwise — including the family-neutral judge. Benchmarks that do not
report the instrument as an experimental factor — and that do not control reasoning effort, comparator
product-vs-endpoint status, and length — are under-specified for procurement decisions.

## 7. Pre-registered extension

The executed existence proof identifies the instrument; a full **2×2×2 provenance × instrument ×
citations** factorial (protocol in `reconciliation_protocol.md`) estimates each factor's causal
share, including a randomized citation-halo arm (motivated by §4.4), a length-matched *generation*
sub-study (to confirm causally what §4.6 shows observationally — that length does not drive the
reversal), a product-vs-endpoint arm (§5a), and reasoning-effort sweeps (§5b). Power is grounded in the measured question-level SD (0.598): ≈250 questions/cell for a
15 pp interaction, ≈390/cell for 12 pp. Because the Nature RCQ corpus is not public, the provenance arm
uses a constructed surrogate LLM-platform query corpus; Real-POCQi is directly reusable.

## 8. Limitations

(i) **No ground truth** — we show instruments disagree, not which is correct. (ii) **Length not
normalized** (OE 3.8k vs GPT 2.6k chars) — we show *observationally* (§4.6) that the reversal is not a
length artifact (OE is the longest provider yet loses; length-adjusted gaps match raw gaps within CI),
but a fully length-matched *generation* study is still pre-registered to settle it causally. (iii)
**House effects** — contestant-family judges self-prefer (quantified; controlled via leave-one-judge-out),
and the panel may share a rubric-specific pro-frontier stylistic prior that leave-one-judge-out cannot
remove; the pairwise cell (§4.5) shows this prior is instrument-specific (the same judges favor OE under
pairwise), and the remaining control — human-administered rubric scoring — is pre-registered. (iv)
**Noisy instrument** — modest inter-judge agreement. (v) **Missing fourth cell and the additivity
assumption** — we have three of the four 2×2 cells; the decomposition is therefore identified *within LLM
raters*, and bridging the instrument effect to the human-rated Nature rubric assumes **no rater×instrument
interaction** (that physicians doing a rubric would show the same pairwise→rubric shift LLMs do). This is
untested and is the likely direction of interaction (humans may not share the frontier-prose prior);
filling cell D = {rubric, human}, even at small n, is the top follow-up. Relatedly, cell A is Real-POCQi's
human pairwise protocol while cell B is our LLM pairwise reimplementation, so the rater term B−A absorbs
minor **protocol** differences (tie handling, pair structure) as well as rater modality — it is "rater
modality + protocol," not pure rater. Both cell A and cell B are computed on the identical 150-query
sample, so B−A is at least free of sample-composition confounding. The n=150 existence-proof scale is
decisive for the LLM-rubric verdict (cell C significantly negative on accuracy and clinical utility) but
underpowers the same-sample human baseline (three axes' human CIs cross zero in the subsample, though the
full-data values are significant and same-signed); the null-collapsing axes await the full run. (vi)
**No rater-level modeling** — the
public ratings table has no rater identifier, so human-side rater random effects cannot be fit from public
data. (vii) **LLM judges are not bit-deterministic**; we quantify rather than assume stability.

## 9. Ethics, conflicts, funding

No human subjects or PHI were used; all human ratings are de-identified public data (CC BY 4.0). No
Nature-copyrighted data were redistributed (CC BY-NC-ND). **Conflicts:** [author to declare;
Kinvectum AB affiliation]. We note the source studies' own conflicts: Real-POCQi's data collection was
run by OpenEvidence; the Nature senior author reports industry equity/consulting including Google.
**Funding / compute:** LLM-judge API costs [to complete]. **Author contributions / acknowledgements:**
[to complete].

## 10. Data and code availability

All code and outputs are in this repository; `run_all.sh` reproduces every result end to end
(`SKIP_JUDGES=1` for the no-API-key public-data subset). Real-POCQi data: Hugging Face
`jjfenglab/Real-POCQi` (CC BY 4.0), fetched by `fetch_data.py` and vendored in `data/`. Judge
configuration, reasoning-token verification, grades, bootstrap CIs, and figures are regenerable as
documented in `README.md`. Nature Medicine numbers are cited from the published article
(s41591-026-04431-5); its RCQ corpus is not public (IRB i23-00510).

## References

Citations appear as numbered footnotes at the point of use and are collected in full below. Numbering
follows order of first appearance (Vancouver style). Full author lists and target-journal formatting to
be finalized before submission.

[^poc]: Feng, J. J., Patel, V., Heagerty, P., Mai, Y., Sivaraman, V., Vossler, P., Ouyang, J. & Jena, A. B. *Expert evaluation of clinical AI tools on real point-of-care clinical queries (Real-POCQi).* arXiv:2606.28960 (2026). Dataset: huggingface.co/datasets/jjfenglab/Real-POCQi (CC BY 4.0).

[^nat]: Vishwanath, K., Alyakin, A., Stryker, J., Alber, D. A., … Oermann, E. K. *Head-to-head evaluation of frontier general-purpose LLMs and specialized clinical AI tools.* Nature Medicine s41591-026-04431-5 (2026). CC BY-NC-ND 4.0.

[^healthbench]: Arora, R. K. et al. *HealthBench: evaluating large language models towards improved human health.* Preprint at https://doi.org/10.48550/arXiv.2505.08775 (2025).

[^medqa]: Jin, D. et al. *What disease does this patient have? A large-scale open domain question answering dataset from medical exams (MedQA).* Applied Sciences 11, 6421 (2021).

[^medpalm]: Singhal, K. et al. *Large language models encode clinical knowledge.* Nature 620, 172–180 (2023).

[^arena]: Chiang, W.-L. et al. *Chatbot Arena: an open platform for evaluating LLMs by human preference.* Proceedings of the 41st International Conference on Machine Learning (ICML) (2024). Preprint arXiv:2403.04132.

[^mtbench]: Zheng, L. et al. *Judging LLM-as-a-judge with MT-Bench and Chatbot Arena.* Advances in Neural Information Processing Systems 36 (2023). Preprint arXiv:2306.05685.

[^selfpref]: Panickssery, A., Bowman, S. R. & Feng, S. *LLM evaluators recognize and favor their own generations.* Advances in Neural Information Processing Systems 37 (2024). Preprint arXiv:2404.13076.

[^winratio]: Pocock, S. J., Ariti, C. A., Collier, T. J. & Wang, D. *The win ratio: a new approach to the analysis of composite endpoints in clinical trials based on clinical priorities.* European Heart Journal 33, 176–182 (2012).

[^rag]: Amugongo, L. M., Mascheroni, P., Brooks, S., Doering, S. & Seidel, J. *Retrieval augmented generation for large language models in healthcare: a systematic review.* PLOS Digital Health 4, e0000877 (2025).

[^clasheval]: Wu, E., Wu, K. & Zou, J. *ClashEval: quantifying the tug-of-war between an LLM's internal prior and external evidence.* Advances in Neural Information Processing Systems 37, 33402–33422 (2024).

[^distracted]: Vishwanath, K. et al. *Medical large language models are easily distracted.* Preprint at https://doi.org/10.48550/arXiv.2504.01201 (2025).

[^medmobile]: Vishwanath, K., Stryker, J., Alyakin, A., Alber, D. A. & Oermann, E. K. *MedMobile: a mobile-sized language model with clinical capabilities.* BMJ Digital Health & AI 1, e000068 (2025).

[^cardio]: O'Sullivan, J. W. et al. *A large language model for complex cardiology care.* Nature Medicine 32, 616–623 (2026).

[^seqdx]: Nori, H. et al. *Sequential diagnosis with language models.* Preprint at https://doi.org/10.48550/arXiv.2506.22405 (2025).

[^noharm]: Wu, D. et al. *First, do NOHARM: towards clinically safe large language models.* Preprint at https://doi.org/10.48550/arXiv.2512.01241 (2025).

[^hospops]: Jiang, L. Y. et al. *Generalist foundation models are not clinical enough for hospital operations.* Preprint at https://doi.org/10.48550/arXiv.2511.13703 (2025).

[^nyutron]: Jiang, L. Y. et al. *Health system-scale language models are all-purpose prediction engines.* Nature 619, 357–362 (2023).

[^poison]: Alber, D. A. et al. *Medical large language models are vulnerable to data-poisoning attacks.* Nature Medicine 31, 618–626 (2025).

[^jamia]: Malhotra, K. et al. *Health system-wide access to generative artificial intelligence: the New York University Langone Health experience.* Journal of the American Medical Informatics Association 32, 268–274 (2025).

[^obsidian]: Alyakin, A. et al. *CNS-Obsidian: a neurosurgical vision-language model built from scientific publications.* Neurosurgery (2026). https://doi.org/10.1227/neu.0000000000004070.

[^bertopic]: Grootendorst, M. *BERTopic: neural topic modeling with a class-based TF-IDF procedure.* Preprint at https://doi.org/10.48550/arXiv.2203.05794 (2022).

[^oe]: *OpenEvidence, the fastest-growing application for physicians in history, announces $210 million round at $3.5 billion valuation.* Cision PR Newswire (2025).

[^utd]: Wolters Kluwer. *HLTH 2025: Wolters Kluwer showcases UpToDate Expert AI and workflow innovations.* wolterskluwer.com (2025).
