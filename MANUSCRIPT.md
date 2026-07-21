# Evaluation instrument choice can flip the apparent winner: a secondary analysis reconciling two contradictory 2026 head-to-head evaluations of clinical AI

**Author:** Koyar Afrasyab, M.D. — *corresponding author.*
**Affiliation:** Independent researcher; Founder, Kinvectum AB.
**Funding:** Kinvectum AB.
**Correspondence:** Koyar Afrasyab (Kinvectum AB). ORCID: [0009-0009-3530-4606](https://orcid.org/0009-0009-3530-4606).
**Article type:** Methodological reconciliation and secondary analysis (with critical appraisal and a pre-registered extension).
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
verified**. We re-expressed both instruments through the same OE-vs-rest win-difference summary (a
construct re-expression, not an identity — the rubric win-difference is a thresholded score gap and is
hypersensitive at the decision boundary) and compared them, with a **crossed question × judge bootstrap
that treats the four judges as a random factor** (so CIs reflect panel composition, not just question
sampling), per-judge self-preference, and leave-one-judge-out robustness. To separate the *instrument*
effect from a *rater-population* effect (physicians vs LLMs), we additionally ran the same blinded panel
under the **pairwise** instrument, filling three of the four cells of a {pairwise, rubric} × {human, LLM}
design and decomposing the swing into rater-modality (B−A) and instrument-format (C−B) components with
propagated CIs. A restricted version of this pairwise-LLM cell already exists inside Real-POCQi, so we
frame it as replication-and-extension.

**Results.** Swapping only the instrument **eliminated OE's advantage on every axis**. On accuracy — the
marquee axis — the LLM-rubric panel scored OE **−29.1 pp**, and this stayed significantly negative under
the crossed question × judge bootstrap **(95% CI −37.8 to −4.3): a judge-robust, OE-negative verdict on
the very answers human raters preferred OE on** (+24.4 pp on the full Real-POCQi data; +10.4 pp on the
identical 150-question subsample). The negative sign also survived dropping any single judge, including
the self-preferring GPT-5.5. Once judges are treated as a random factor, the other four per-axis reversals
are **not individually significant** — including a small residual source-quality OE edge (+12.0 pp, crossed
CI −8.2 to +29.5) and the clinical-utility reversal, both of which we explicitly retract from the earlier
draft — so accuracy is the one axis carrying a significant per-axis instrument reversal. GPT-5.5
self-preferred (+0.481 points to own family; Opus +0.121; Gemini-flash +0.004, though flash may simply be
a weak discriminator), amplifying but not creating the reversal. **The stronger, judge-robust result is at
the decomposition level: the instrument-format component (C−B) is negative with a crossed CI excluding
zero on *all five* axes (−30.5 to −44.4 pp), while the rater-modality component (B−A) is indistinguishable
from zero on accuracy (−6.8 pp, CI −27.5 to +14.3).** We therefore downgrade the earlier "instrument does
~83% of the accuracy swing" claim (that ratio's 95% CI is a wide [35%, 206%]) to the CI-supported
statement that the instrument dominates and the rater term is null on accuracy. The reversal is also **not
a length artifact**: OE produces among the *longest* answers yet loses on accuracy, and length-adjusting
the rubric gap leaves it unchanged within CI.

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
conclusions using overlapping systems,[^poc]<sup>,</sup>[^nat] which strongly suggests that at least one
conclusion reflects the evaluation method rather than the systems compared.

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
in the metric is attributable to the instrument. (For transparency, `random_state=62` was fixed once at
the outset and reused for the bootstrap RNG; it coincides with Nature's generation seed but plays no role
in our result — the instrument contrast is computed on the same fixed 150-question draw regardless of
seed, and the full-bank reproductions in §4.4 match Real-POCQi independently of the subsample. We did not
re-draw to obtain a preferred outcome.)

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
question. This re-expresses the rubric scores through the **same one-vs-rest rule** Real-POCQi reports
for human pairwise — a win-ratio-family contrast[^winratio] in the arena-style preference tradition[^arena]
— but the two are **not the identical measurement** (§3.3a), so we treat the win-difference as a common
*summary* applied to both instruments, not as an instrument-invariant quantity.

**Uncertainty — a crossed question × judge bootstrap.** The naïve cluster bootstrap resamples only
*questions* and treats the four judges as a fixed population; its CIs answer "how stable is this across
questions" but say nothing about "how stable is this across the *choice of judges*" — the dimension a
skeptic cares about most here, because three of the four judges are contestant families and GPT-5.5
self-prefers by +0.481 points (§4.2). We therefore make **judges a random factor**: each of 2,000
replicates resamples questions with replacement (cluster on `question_id`) **and** resamples the four
judges with replacement, recomputes the panel mean from the resampled judge multiset, and recomputes the
win-difference (`judge/bootstrap_panel.py`). Judges are resampled once per replicate and applied
consistently to the pairwise and rubric cells (they are the same four judges under both instruments). We
report **both** the question-only CI (comparable to prior work) and this wider **crossed** CI, and treat
the crossed CI as primary. Robustness: **leave-one-judge-out** (recompute dropping each judge). Bias:
**self-preference** = mean own-family minus mean others, paired within (question, axis). **Inter-judge
agreement** = Spearman correlation of per-(question, system) mean scores. Human comparison uses the
`qa_text_only` render mode (matching the citation-free OE answers in the dataset).

**What the crossed bootstrap changes.** Adding judge uncertainty widens every CI, and two previously
"significant" per-axis claims do not survive it: the small **source-quality** OE edge (+12.0 pp) moves
from a question-only CI that excluded zero [+1.3, +22.0] to a crossed CI that **includes** zero
[−8.2, +29.5], and the **clinical-utility** reversal likewise loses significance (crossed CI [−22.4,
+8.3]). The **headline accuracy reversal survives**: crossed CI [−37.8, −4.3], still strictly negative.
We rely only on claims that survive the crossed CI and explicitly retract the two that do not.

### 3.3a The win-difference is a construct re-expression, not an identity
A subtle but important point of honesty: cell A's win-difference comes from a **genuine forced choice** —
a physician picks A, B, or tie. Cell C's win-difference is **synthesized** by thresholding continuous
panel-mean rubric scores (OE panel mean > frontier panel mean ⇒ a "win"). Because the mean of four
integer scores is near-continuous, exact ties almost never occur, so essentially every question is forced
to a win or a loss on a razor-thin margin — which is precisely why a mean rubric gap of only −0.127 of one
point (accuracy) becomes a −29 pp win-difference. The win-difference metric was designed for a paradigm
where ties are real (forced choice with a tie option) and we are applying it to one where we have
engineered ties away; it is therefore **hypersensitive at the decision boundary**. The honest statement is
not "the same metric under two instruments" but "we re-express the rubric means through the same
one-vs-rest rule, whose sign is decisive but whose magnitude is boundary-sensitive." We accordingly report
both the win-difference *and* the native score gap (§4.1), and lean on the *sign and its crossed-CI
significance*, not the raw magnitude.

**Multiplicity.** We test five axes across three cells; we report per-axis 95% crossed-bootstrap CIs
without a formal family-wise correction, so per-axis claims near the null boundary should be read as
descriptive. After the crossed bootstrap only two results are individually significant — the **accuracy**
reversal (crossed CI [−37.8, −4.3]) and the **instrument-format component** of the decomposition (§4.5,
significant on every axis) — and both are far enough from the boundary to survive standard Bonferroni/Holm
adjustment across five axes. We flag every borderline axis explicitly rather than over-claiming per-axis
significance.

### 3.4 The pairwise cell (2×2 decomposition)
To separate the instrument from the rater population we administer a **second instrument to the same LLM
panel**: blinded forced-choice **pairwise** preference (A/B/tie per axis), OpenEvidence vs each of the
three frontier systems, on the same 150-query sample (`judge/pairwise.py`). Slot order is deterministically
randomized per (question, opponent, judge) via a hash and de-blinded at scoring, removing position bias.
We de-blind each A/B/tie verdict to an OE win/loss/tie and compute the OE-vs-rest win-difference (here a
*native* forced choice, not a thresholded score; §3.3a). This yields cell **B = {pairwise, LLM}**,
which — with cell A = {pairwise, human} (Real-POCQi) and cell C = {rubric, LLM} (§3.2) — gives three of
the four cells of the {pairwise, rubric} × {human, LLM} design and identifies the **rater-modality effect
(B−A)** and the **instrument-format effect (C−B)** (§4.5). Judges run at high reasoning effort; all four
judges completed 448–450/450 comparisons (1,798/1,800 overall). We bootstrap the decomposition
components **jointly** under the same crossed question × judge scheme as §3.3 (resampling questions and
judges together across cells A/B/C), so B−A and C−B carry propagated CIs rather than being point-estimate
arithmetic. Because cell B already exists in a restricted form inside Real-POCQi itself, we position it as
a replication-and-extension, not a wholly new measurement (§4.5a).

## 4. Results

### 4.1 The instrument flips the winner (Figure 1, Table 1)

![Figure 1](judge/out/existence_proof.png)

**Figure 1.** Instrument existence proof. OE-vs-rest win-difference (percentage points) per axis under
the human blinded pairwise instrument (same 150 questions) versus the LLM-judge absolute-rubric panel
(n = 150). Error bars show the question-only cluster bootstrap; the wider **crossed question × judge**
CIs that we treat as primary are given in Table 1. Holding queries and answers fixed and changing only
the instrument eliminates OE's advantage on every axis; under the crossed CI the effect is
individually significant on accuracy (a sign reversal) and directionally consistent but not per-axis
significant on the others.

**Table 1.** OE-vs-rest win-difference (pp) by axis under each instrument, **both computed on the same
150-query sample**. For the LLM-rubric cell we give both the question-only cluster bootstrap (comparable
to prior work) and the wider **crossed question × judge** CI (§3.3), which we treat as primary. The human
column is the human pairwise win-difference restricted to the identical questions (86–119 of 150 carry
human text-only ratings, by axis); the "full data" column is the win-difference on Real-POCQi's complete
text-only bank (reproduced in §4.4), shown for reference because the subsample is underpowered. The
native-gap column gives the OE-minus-mean-of-frontier gap on the raw 1–4 rubric (see scale note).

| Axis | Human pairwise, same 150 [95% CI] | Human, full data (ref) | LLM rubric, Q-only CI | **LLM rubric, crossed q×judge CI** | Native gap (pts) | Verdict (crossed CI) |
|---|---:|---:|---:|---:|---:|---|
| Accuracy | +10.4 [−1.8, +22.2] | +24.4 | −29.1 [−37.8, −20.0] | **−29.1 [−37.8, −4.3]** | −0.127 | sign flips; **negative, survives judge resampling** |
| Clinical utility | +14.4 [−1.6, +31.4] | +29.5 | −12.2 [−21.1, −3.3] | −12.2 [−22.4, +8.3] | −0.021 | sign flips, but **not sig under crossed CI** |
| Source quality | +23.2 [+7.6, +38.0] | +38.1 | +12.0 [+1.3, +22.0] | +12.0 [−8.2, +29.5] | +0.103 | attenuated ~3×; **not sig under crossed CI** |
| Completeness | +13.6 [−2.5, +28.7] | +30.3 | −3.6 [−12.7, +5.8] | −3.6 [−14.4, +12.7] | +0.004 | collapses to null |
| Verifiability | +14.4 [+2.2, +27.6] | +25.5 | +0.7 [−9.6, +11.1] | +0.7 [−13.6, +13.8] | +0.003 | collapses to null (see verifiability caveat, §4.3) |

The headline is accuracy. Real-POCQi's central finding is that physicians prefer OE on accuracy (+24.4
pp on the full data; +10.4 pp, CI −1.8 to +22.2, on this 150-query subsample — same sign, but the
subsample carries only 86 accuracy ratings and is underpowered). On the **same answers**, the LLM-rubric
panel scores OE **−29.1 pp**, and — crucially — this stays significantly negative under the crossed
question × judge bootstrap **[−37.8, −4.3]**: the reversal is not an artifact of which judges we happened
to pick. So the instrument swap moves the accuracy verdict from OE-favoring (significantly so at full
power; positive but CI-crossing in this subsample) to *significantly OE-disfavoring*.

**Two per-axis claims from the earlier draft do not survive judge uncertainty, and we retract them.**
Once judges are treated as a random factor, the **clinical-utility** reversal (crossed CI [−22.4, +8.3])
and the small residual **source-quality** OE edge (crossed CI [−8.2, +29.5]) both cross zero. The honest
picture is therefore narrower than "reversed on two, positive on one": under the crossed CI, **accuracy is
the one axis with a significant instrument-driven reversal**, and the other four are individually
indistinguishable from null. This is a weaker per-axis result but a more defensible one — and the
decomposition (§4.5) recovers a stronger, judge-robust pattern at the *component* level. We deliberately
avoid framing this as "a significant +24 becomes a significant −29": at the existence-proof scale the
human accuracy estimate is not itself significant, so the clean claim is a **sign reversal to a
significantly-negative rubric verdict on identical content, robust to judge resampling**, corroborated by
the full-data human sign.

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
GPT-5.5-dependent (→ +2.5 pp without it), consistent with the crossed-CI finding that clinical utility is
not judge-robust (§4.1).

**Two honest caveats about the panel itself.** *(i) The Gemini seat is flash-tier, not Pro.* Our Gemini
judge is `gemini-3.5-flash` — a smaller, cheaper, weaker evaluator than the `gemini-3.1-pro` model that is
one of the *contestants*, and it is the seat that stalled on quota mid-run (§4.5). Its self-preference of
**+0.004** should therefore *not* be read as evidence that the Gemini family is unbiased: a flash-tier
judge may simply be a poor discriminator, registering little preference of any kind. Using flash while the
contestant is Pro is an apples-to-oranges asymmetry; re-running the Gemini seat at Pro tier and high
reasoning is a stated follow-up. *(ii) Grok is a single neutral anchor.* Our cleanest causal handle — that
the pro-frontier tilt is instrument-specific because the one family-neutral judge (Grok) still prefers OE
under pairwise (§4.5) — rests on **n = 1 non-contestant model**. One neutral judge cannot separate a true
instrument effect from Grok's own idiosyncrasies; a second genuinely neutral judge (e.g. DeepSeek,
Mistral, Qwen, or Llama) would convert this from a single data point into a pattern, and we flag its
absence as a real limitation rather than leaning on Grok as if it were a clean control.

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

### 4.3 The instrument is noisy — and one axis is barely measurable in either study
Inter-judge Spearman agreement was modest (0.19–0.47), closely mirroring the low item-level agreement
the Nature study reports for its own human raters (α ≈ 0.10–0.20). Rubric scoring — whether by humans
or LLMs — is a higher-variance instrument than forced-choice preference; this is part of *why* it can
diverge from pairwise, not a defect unique to our panel.

**A specific caution on verifiability.** Real-POCQi reports that its own physicians' weighted Cohen's κ
was 23–38% on four axes but only **9% on verifiability** — essentially chance agreement. Verifiability is
therefore an axis that *neither instrument reliably measures*: when our rubric cell "collapses to null" on
verifiability, that is unremarkable, because the human pairwise instrument cannot resolve it either. We
accordingly **drop verifiability from any headline framing** and treat its collapse as uninformative
rather than as evidence of an instrument effect; the same discount applies, more softly, to source
quality. This strengthens the general "both instruments are noisy" point while removing any per-axis
weight we might otherwise have placed on verifiability.

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

**Cell B is a replication-and-extension, not a wholly new experiment.** Real-POCQi already ran an
LLM-judge *pairwise* experiment (their §2.4 / Methods §5.7): they took the same questions, answers, and
pairs the physicians saw, blinded and position-randomized them, and had GPT-5.5, Gemini 3.1 Pro, and
Claude Opus 4.8 grade them on the same five axes.[^poc] Our cell B **replicates that design and extends it
in three ways** — a fourth, *family-neutral* judge (Grok), **high** reasoning effort (they ran at minimal
thinking), and propagated crossed-judge CIs. This matters two ways. First, we credit them: we are not the
first to administer an LLM pairwise instrument here. Second, it *strengthens* cell B — because their
judges ran at minimal thinking and ours at high, cell B reproducing across both reasoning regimes is a
genuine robustness point, and their released ratings could in principle be used to triangulate cell B
directly. Their headline is concordant with ours: LLM judges **agreed with human experts on which system
was best** (i.e. OE at the one-vs-rest winner level) while disagreeing on the lower ranks — exactly the
pattern our OvR win-difference is built to surface (see the rank-resolution caveat below).

**One component of B−A is a genuine rater confound, not pure "modality," and it lands on accuracy.**
Real-POCQi **specialty-matched** each physician grader to the question topic and argues this matching
optimizes evaluation on the *accuracy* axis specifically.[^poc] Our LLM judges are generalists with no
such matching. So B−A on accuracy conflates the pairwise→pairwise rater-*modality* change with a loss of
**specialty expertise** — a substantive confound that pushes in the direction of making the human cell A
*more* accurate-sensitive. If specialty-matching inflates cell A's accuracy edge, the true rater term
could be larger (more negative) than our −6.8 pp, which would *reduce* the instrument's share — another
reason we no longer quote a precise "83%." We name specialty-matching explicitly as part of B−A rather
than burying it in "protocol differences."

**Rank-resolution caveat: cell B's agreement lives in the winner-friendly OvR regime.** The concordance we
credit — LLM judges reproducing the human pairwise winner — must be read against what Real-POCQi actually
found about LLM-judge *ranking* fidelity: their LLM judges agreed with physicians on **which single system
was best** but their rank correlations across the *full* ordering were low-to-negative (e.g. Kendall
τ ≈ −0.200 for GPT-5.5 and ≈ −0.067 for the jury against the human ranking).[^poc] The one-vs-rest
win-difference is by construction a **winner-resolving, not a rank-resolving** contrast: it asks only
"is OE preferred to the frontier field," which is exactly the question on which LLM and human judges *do*
concur, and it is deliberately blind to the lower-rank disagreements where they diverge. So cell B's
reproduction of cell A is genuine but should be understood as agreement *at the resolution our metric
operates on* — the top of the order — not as evidence that LLM judges recover the physicians' complete
system ranking. This cuts both ways for us: it is why cell B is a fair test of the "do LLMs disagree with
physicians about OE" question (they do not, at winner level), and why we do not over-read cell B as a
general validation of LLM-judge pairwise scoring.

![Figure 2](judge/out/decomposition.png)

**Figure 2.** The 2×2 rater-vs-instrument decomposition (n = 150). *Left:* three cells of the
{pairwise, rubric} × {human, LLM} design per axis — both pairwise cells (A: human; B: LLM) favor
OpenEvidence; only the rubric cell (C) reverses it. *Right:* the human-pairwise→LLM-rubric swing split
into a rater-modality component (B−A) and an instrument-format component (C−B); under the crossed
question × judge bootstrap the instrument component is negative with a CI excluding zero on **every**
axis, while the rater component is not distinguishable from zero on accuracy.

**Table 2.** OE-vs-rest win-difference (pp) across three cells of the 2×2, and the decomposition of the
human-pairwise→LLM-rubric swing **with propagated crossed question × judge 95% CIs** on the two
components (§3.3; `judge/bootstrap_panel.py`). **Cell A is computed on the same 150-query sample as B and
C** (human text-only ratings restricted to those questions), *not* on the full text-only bank — otherwise
B−A would absorb a sample-composition difference into the "rater" term. Cell B: n=150; 8,990 axis-verdicts
(1,798/1,800 comparisons, all four judges 448–450/450).

| Axis | A: pw/human | B: pw/LLM | C: rubric/LLM | Rater (B−A) [crossed CI] | **Instrument (C−B) [crossed CI]** |
|---|---:|---:|---:|---:|---:|
| Accuracy | +10.4 | +3.6 | −29.1 | −6.8 [−27.5, +14.3] | **−32.7 [−42.8, −8.8]** |
| Clinical utility | +14.4 | +18.2 | −12.2 | +3.8 [−22.3, +31.9] | **−30.5 [−42.6, −9.0]** |
| Source quality | +23.2 | +48.8 | +12.0 | +25.6 [−3.4, +54.8] | **−36.8 [−56.9, −22.4]** |
| Completeness | +13.6 | +37.0 | −3.6 | +23.4 [+2.2, +45.4] | **−40.5 [−53.6, −22.0]** |
| Verifiability | +14.4 | +45.1 | +0.7 | +30.7 [+7.9, +53.6] | **−44.4 [−62.0, −29.1]** |

Two results stand out, and both are now stated at the level the crossed CIs actually support. **First, LLM
judges administering the *pairwise* instrument largely reproduce the human pairwise verdict**: OE wins on
four of five axes (source quality +48.8, verifiability +45.1, completeness +37.0, clinical utility +18.2),
with only accuracy attenuating to a null +3.6. The much-feared "LLMs simply disagree with physicians"
story is therefore false for four of five axes — given the *same* forced-choice instrument, LLMs and
physicians agree that OE's answers are preferred. **Second, and this is the robust core of the paper, the
instrument-format component (C−B) is negative and its crossed CI excludes zero on *every* axis (−30.5 to
−44.4 pp), whereas the rater-modality component (B−A) is indistinguishable from zero on the marquee
accuracy axis** (−6.8 pp, CI −27.5 to +14.3) and on clinical utility and source quality. The swing from
"OE wins" to "OE loses" is thus attributable to the **pairwise→rubric instrument change**; the human→LLM
rater change is not a significant contributor where it matters most.

**We deliberately downgrade the earlier "~83%" claim.** The point estimate for accuracy is indeed
instrument −32.7 pp vs rater −6.8 pp (an 83% instrument share), but this is a ratio of two noisy
differences: bootstrapping it jointly gives a 95% CI of **[35%, 206%]** (the upper tail exceeds 100%
whenever the rater term resamples to the *opposite* sign). We therefore do not put a precise fraction on
the accuracy split. The defensible, judge-robust statement is the one above: **the instrument component is
significantly negative on all five axes; the rater component is not distinguishable from zero on
accuracy.** (With cell A taken on the full text-only bank instead, the accuracy rater term would appear as
−20.8 pp; that larger value is an artifact of comparing the LLM cells against a different, larger question
sample, and we do not use it.)

**Multiplicity of the decomposition.** The decomposition adds implicit comparisons (three cells × five
axes × two components); we do not apply a family-wise correction to the component CIs, but note that the
one claim we rely on — a negative instrument component on every axis — is significant on all five
independently, so it is robust to any standard correction, while we make no per-axis rater claims.

This also sharpens the house-effect discussion (§4.2). Under the pairwise instrument, the **family-neutral
judge (Grok) prefers OE on all five axes** (+11 to +65 win-diff) and the contestant **GPT-5.5 is the
*least* OE-favorable** judge — the *opposite* of what a shared pro-frontier stylistic bias would predict.
The pro-frontier tilt is therefore specific to the **rubric** instrument, not a blanket LLM prejudice
against OE. (One robustness note: Gemini-3.5-flash initially stalled at 297/450 pairwise verdicts when the
Google API account exhausted its credit quota mid-run; after credits were restored we completed the cell
to 448/450, and the point estimates shifted <3 pp from the partial-coverage run — i.e., the conclusion
never depended on the missing data.)

### 4.6 The rubric reversal is not a length artifact (Table 3)

Answer length is the most-cited confound in both source studies. A precise word on how it is handled:
Real-POCQi does not leave length wholly uncontrolled — it **reports and stratifies** by length (their
Table D3 / Fig D6, OE ≈ 3,584 vs Gemini ≈ 3,516 characters) but does not **normalize** generation to
equal length; so the accurate statement is "length is stratified and reported, not equalized," not
"uncontrolled." The natural worry is that the rubric rewards longer, more comprehensive answers. We test
this on the rubric cell without regenerating any answers (`judge/length_analysis.py`). The premise fails
at the first step: **OpenEvidence is among the *longest* providers** — median 3,600 chars, essentially
**tied with Gemini (3,586)** and well above Opus (3,294) and GPT-5.5 (2,232) — so OE is decisively longer
only than GPT, but it is never the *short* answer, and it still *loses* the accuracy rubric. A "longer
answers win" mechanism therefore runs *backwards* against the finding: the co-longest provider loses. We
confirm this three ways (Table 3): (i) the per-axis length **slope** is tiny
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

The critiques below are **independent of the instrument existence proof** (§4): they hold whether
or not the instrument drives the disagreement, and they apply symmetrically to both source studies. We
include them because they bound how far *either* published leaderboard can be trusted for procurement,
but a reader interested only in the instrument result can treat this section as standalone context.
Full detail in `CRITIQUES.md`. Points (a)–(b) concern the systems and settings compared; points (c)–(e)
concern the instruments themselves and bear directly on interpretation:

**(a) The comparator set omits the AI clinicians actually use.** Both studies benchmark **bare frontier
API models**; neither includes the **ChatGPT product** (consumer or clinician deployment), whose system
prompt, retrieval/browsing, memory, and safety guardrails move the very axes under test. This is
especially asymmetric because OE is itself a curated clinical *product*; Nature further queries clinical
tools via browser but frontier models via API. A fair benchmark should include a **product arm** distinct
from the raw model endpoint.

**(b) Reasoning effort is unreported or uncontrolled.** Nature reports temperature 0.0 and a seed but
**never states reasoning effort** (its cost table confirms reasoning tokens were spent, at an
unspecified level); Real-POCQi reports only that "thinking was automatically determined by the LLM."
These are two *distinct* undisclosed knobs — whether extended thinking is **on at all**, and if so at
what **level (high/medium/low or an explicit token budget)** — and reasoning effort is the largest
controllable performance lever for these models, able to swing double digits on exactly the benchmarks
in play. Two consequences follow. *Across studies*, neither head-to-head is reproducible on this axis,
and their absolute numbers are not comparable. *Within* a study, "automatic" or unstated effort is worse
than merely non-reproducible: if a study's thinking setting is auto-determined per query or per model, it
may **not be held constant across the very systems it is comparing** — so even that study's internal
ranking may reflect an uncontrolled effort difference rather than a capability difference. (Note, too,
that temperature 0.0 is largely inert for reasoning models, which sample the reasoning trace regardless;
reporting it can create a false impression of determinism.) Our study instead pins effort = high for all
four judges and **verifies** token consumption on the real task (§3.2), so the instrument comparison here
is not vulnerable to this confound.

**(c) The winning margin sits inside the rubric's own noise floor, and the 1–4 scale compresses it.**
Two linked problems undercut how decisively Nature's rubric separates the systems. *First, a noise-floor
problem.* On the real-clinical-question benchmark the frontier systems finish at Gemini 3.62 / GPT 3.54 /
Claude 3.52 — a spread of **0.10 of one point across the top three** — with OE at 3.24, i.e. roughly
0.3 point below an essentially indistinguishable frontier cluster, on n = 100 questions graded at
Krippendorff α ≈ 0.10–0.20. At that agreement level and sample size the between-frontier ordering is
within measurement noise (the "winner" among Gemini/GPT/Claude is not robustly identified), and even the
OE gap is a fraction of a rubric point; the study's own low α makes the fine-grained leaderboard order
fragile. *Second, a ceiling/compression problem that is also a mechanism for our reversal.* A 1–4 integer
rubric has almost no headroom for strong answers — competent clinical responses pile up at 3–4, so the
instrument cannot express *how much* better one good answer is than another, and small stylistic
preferences (structure, breadth, hedging) get magnified into rank order because the usable dynamic range
is one or two points. This compression is exactly why a mean gap of −0.127 point becomes a −29 pp
win-difference in our cell C (§3.3a): the rubric floor/ceiling turns near-ties into decisive-looking
orderings. A coarse absolute rubric is therefore a **low-resolution instrument for near-parity systems**,
and both the Nature leaderboard and our rubric re-expression inherit that low resolution. This is not a
reason to prefer pairwise uncritically — §5(d) levels a symmetric charge at the preference instrument —
but it bounds how much weight the Nature rubric ordering can carry.

**(d) The pairwise instrument has symmetric, opposite biases — it is not the "true" instrument either.**
Nothing here should be read as vindicating forced-choice preference as ground truth. Pairwise preference
is known to reward surface features — answer length, formatting, citation presence, confident tone —
independently of correctness, and Real-POCQi's own data show the mechanism: OE's between-groups accuracy
"halo" of +11.4 pp **collapses to +1.5 pp (NS)** once we condition on questions rated both with and
without citations (§4.4), i.e. much of the measured preference edge tracks the *presence of citations*
rather than answer accuracy. A preference instrument that can be moved 10 pp by attaching references is
as construct-contaminated, in the opposite direction, as a compressed rubric. The honest position is that
**neither instrument is a clean measure of clinical quality**: the rubric over-rewards frontier-style
breadth and compresses near-ties; pairwise over-rewards citations and verbosity. Our claim is the
*relative* one — that switching between these two biased instruments is sufficient to flip the winner —
not that either endpoint is correct.

**(e) The five rubric axes are not independent, so "reversed on k axes" overstates the evidence.**
Source quality and verifiability both essentially ask *"are there citations, and are they real,"* and
accuracy, completeness, and clinical utility are strongly co-scored; the axes are near-collinear rather
than five independent measurements. Two consequences: per-axis "significance" counts should not be read
as five independent confirmations (a single latent "cited, thorough, frontier-style" factor drives much
of the axis structure in both instruments), and this non-independence is *why* we lean on the accuracy
axis and the decomposition rather than tallying axes. It also tempers Real-POCQi's own multi-axis sweep:
OE winning "on all five axes" is closer to winning on **one or two underlying constructs** measured five
ways. We treat the axis set as a small number of correlated constructs throughout, not as five degrees of
freedom.

**(f) Both studies' data pipelines are run by an interested party, with symmetric — not one-sided —
confounds.** We have stressed the provenance symmetry (each sourced queries from the platform that won);
three further data-pipeline facts deserve naming because they cut in *different* directions and a fair
reconciliation must not weaponize only the ones that suit its thesis. *(i) End-to-end control by the
winner.* Real-POCQi's pipeline was run by OpenEvidence: OE selected the query pool (≈3,600 → 620 after
filtering) from its **own** platform traffic, paraphrased queries via an LLM (Opus 4.6) for de-
identification, and paid the physician raters — a chain in which the party under study controls sampling,
wording, and rater incentives end to end. Nature's RCQ pipeline is analogously insider-run (NYU Langone's
own GPT deployment). Neither is neutral. *(ii) A rater-familiarity confound that actually supports the
instrument thesis.* Roughly **half of Real-POCQi's raters were themselves OpenEvidence users**, and the
reported OE accuracy edge is **larger among OE-users (≈+33.8 pp) than non-users (≈+22.6 pp)** — a
habituation/familiarity gradient that inflates the human-pairwise cell (cell A) for reasons unrelated to
answer correctness. This *strengthens* our reading: part of cell A's OE edge is rater familiarity with
OE's house format, exactly the kind of preference-instrument artifact that an absolute rubric does not
reward. *(iii) Very low response and completion rates.* Real-POCQi's physician recruitment yielded low
single-digit response and completion fractions (on the order of ~1–2%), so the rating panel is a
self-selected slice of clinicians; combined with (ii), cell A's preference signal carries a
selection/familiarity component we cannot remove from public data. None of this shows OE's answers are
worse — it shows the *human-pairwise* cell is itself confounded, which is why we do not treat cell A as
ground truth and lean instead on the *within-panel* instrument decomposition (§4.5).

**(g) On the fine-grained order, both leaderboards agree more than they disagree.** Stripped to what is
*robust*, both studies essentially resolve only the extremes: OE is top under pairwise and GPT-class
models are strong under rubric, but the middle of each ranking is within noise (§5c). Real-POCQi's frontier
trio is near-parity behind OE; Nature's frontier trio (Gemini 3.62 / GPT 3.54 / Claude 3.52) is near-parity
ahead of OE. The genuine, reproducible cross-study disagreement is therefore narrow — **where OE sits
relative to a tightly-bunched frontier cluster** — and it is precisely that one placement that the
instrument flips. This bounds the stakes: we are not reconciling two wildly different capability
orderings, but one contested boundary between OE and a frontier pack that both studies otherwise order
similarly.

A corroborating confound: Real-POCQi tested **newer** frontier weights (GPT-5.5, Opus 4.8) than Nature
(GPT-5.2, Opus 4.6) and still found them losing on human pairwise — a pattern more consistent with an
instrument effect than a model-version effect.

## 6. Discussion

Holding queries and answers fixed, the instrument alone is sufficient to reverse the central claim of a
published clinical-AI benchmark. The 2×2 decomposition (§4.5) makes this attribution explicit rather than
inferential: because the *same* LLM panel that reverses OE under the rubric **reproduces the human
pairwise verdict when it uses the pairwise instrument** (OE winning on four of five axes), the swing
localizes to the pairwise→rubric change (C−B, −30.5 to −44.4 pp) and not to the human→LLM change (B−A).

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

**We are not the first to suspect the instrument — Real-POCQi says so itself.** Real-POCQi explicitly
hypothesizes that its divergence from rubric-style benchmarks is *instrument-driven*, and cites
JudgmentBench[^judgmentbench] — which reports that in a high-expertise professional (legal) domain **head-to-head preference
recovers expert judgment more faithfully than absolute rubric scoring** — to argue that its own pairwise
design is the more valid one. We credit this: our contribution is not the *idea* that the instrument
matters but an **executed, controlled demonstration** of it (queries and answers held fixed) plus a
decomposition separating instrument from rater. But we also engage the directional claim honestly, because
it cuts against our symmetric "neither instrument is truth" framing (§5d): if JudgmentBench is right that
head-to-head is the higher-fidelity instrument in expert domains, then the pairwise (OE-favoring) result
deserves *more* evidential weight than the rubric (frontier-favoring) result, and our finding would be not
merely "the instruments disagree" but "the more valid instrument favors OE." We do **not** assert this —
JudgmentBench's generalization to point-of-care clinical answers is untested, our rubric is LLM- rather
than human-administered, and a compressed 1–4 scale is a weak version of rubric scoring — but we flag it
as the key open question the missing human-rubric cell (D) would help settle: if physicians administering
a rubric still down-rank OE, the disagreement is instrument-intrinsic; if they do not, it localizes to
LLM-administered rubrics specifically. Either way, adjudicating *which* instrument is closer to clinical
truth (not merely that they differ) is the natural next study, and JudgmentBench gives a prior that
pairwise may win that contest.

This does not show OE is worse (or better) than frontier models in the clinic — we have **no adjudicated
ground truth** — but it shows that "which system is best" is a function of the measuring instrument, and
that pairwise-preference and absolute-rubric instruments encode materially different value functions
(preference rewards OE's clinician-tuned framing and citations; rubric scoring rewards frontier models'
breadth and structure). It also reframes the "LLM-judge self-preference" worry: the pro-frontier tilt is
a property of the **rubric instrument**, not of LLM judges per se, since those same judges favor OE under
pairwise — including the family-neutral judge. Benchmarks that do not
report the instrument as an experimental factor — and that do not control reasoning effort, comparator
product-vs-endpoint status, and length — are under-specified for procurement decisions.

## 7. Pre-registered extension (proposed design, not an executed result)

The executed existence proof identifies the instrument; a full **2×2×2 provenance × instrument ×
citations** factorial (protocol in `reconciliation_protocol.md`) estimates each factor's causal
share, including a randomized citation-halo arm (motivated by §4.4), a length-matched *generation*
sub-study (to confirm causally what §4.6 shows observationally — that length does not drive the
reversal), a product-vs-endpoint arm (§5a), and reasoning-effort sweeps (§5b). Power is grounded in the measured question-level SD (0.598): ≈250 questions/cell for a
15 pp interaction, ≈390/cell for 12 pp. Because the Nature RCQ corpus is not public, the provenance arm
uses a constructed surrogate LLM-platform query corpus; Real-POCQi is directly reusable. **This surrogate
is itself a threat to validity:** a corpus we assemble to *stand in* for NYU's HIPAA-restricted RCQ
distribution may not reproduce its topic mix, difficulty, or phrasing, so the provenance-arm estimate is
only as trustworthy as the surrogate's fidelity to the true LLM-platform query stream. We therefore treat
the provenance factor as the **weakest-identified** arm of the proposed factorial and would pre-register
the surrogate-construction procedure and a sensitivity analysis over plausible corpus definitions rather
than reporting a single provenance estimate as if the corpus were the real thing.

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
Nature-copyrighted data were redistributed (CC BY-NC-ND). **Conflicts of interest:** The author is
the founder of Kinvectum AB, an independent medical-AI research venture. The author declares no
financial interest in, and no commercial or consulting relationship with, any of the evaluated
systems or their providers (OpenEvidence, OpenAI, Anthropic, xAI, Google, or Wolters Kluwer/UpToDate).
For transparency we note the source studies' own disclosed conflicts, symmetrically: Real-POCQi's data
collection was run by OpenEvidence (the platform under study, which also won it), and the Nature Medicine
senior author reports disclosed industry equity/consulting including **Google** — whose Gemini model is
the top scorer on that study's headline RCQ leaderboard. Both disclosures are proper and neither implies
misconduct; we flag them only because in each study the disclosed interest overlaps the declared winner,
which is exactly the kind of provenance/COI symmetry this reconciliation is built to treat even-handedly. **Funding:** This work was funded by Kinvectum AB, which covered
the LLM-judge API costs; the funder had no role in study design, analysis, or the decision to publish.
**Author contributions:** K.A. designed the study, wrote the analysis and judging code, performed all
analyses, and wrote the manuscript (sole author).

## 10. Data and code availability

All code and outputs are in this repository; `run_all.sh` reproduces every result end to end
(`SKIP_JUDGES=1` for the no-API-key public-data subset). Real-POCQi data: Hugging Face
`jjfenglab/Real-POCQi` (CC BY 4.0), fetched by `fetch_data.py` and vendored in `data/`. Judge
configuration, reasoning-token verification, grades, bootstrap CIs, and figures are regenerable as
documented in `README.md`. A machine-readable **per-item instrument-disagreement export**
(`judge/export_disagreement.py` → `judge/out/instrument_disagreement.csv`) gives, for every
(question, axis, comparator) triple, the rubric and pairwise winners/margins, the number of
contributing judges, judge dispersion, and an `instrument_flip` flag, so readers can inspect
*where* reversals concentrate; re-aggregating it reproduces the sign of every reported
win-difference (a deterministic unit test pins the flip definition). This is a descriptive audit
layer, not adjudicated clinical truth. Nature Medicine numbers are cited from the published article
(s41591-026-04431-5); its RCQ corpus is not public (IRB i23-00510).

## References

Citations appear as numbered footnotes at the point of use and are collected in full below. Numbering
follows order of first appearance (Vancouver style); author lists of six or more are abbreviated with
*et al.* per Vancouver convention.

[^poc]: Feng, J. J., Patel, V., Heagerty, P., Mai, Y., Sivaraman, V., Vossler, P., Ouyang, J. & Jena, A. B. *Expert evaluation of clinical AI tools on real point-of-care clinical queries (Real-POCQi).* arXiv:2606.28960 (2026). Dataset: huggingface.co/datasets/jjfenglab/Real-POCQi (CC BY 4.0).

[^nat]: Vishwanath, K., Alyakin, A., Stryker, J., Alber, D. A., … Oermann, E. K. *Head-to-head evaluation of frontier general-purpose LLMs and specialized clinical AI tools.* Nature Medicine s41591-026-04431-5 (2026). CC BY-NC-ND 4.0.

[^healthbench]: Arora, R. K. et al. *HealthBench: evaluating large language models towards improved human health.* Preprint at https://doi.org/10.48550/arXiv.2505.08775 (2025).

[^medqa]: Jin, D. et al. *What disease does this patient have? A large-scale open domain question answering dataset from medical exams (MedQA).* Applied Sciences 11, 6421 (2021).

[^medpalm]: Singhal, K. et al. *Large language models encode clinical knowledge.* Nature 620, 172–180 (2023).

[^arena]: Chiang, W.-L. et al. *Chatbot Arena: an open platform for evaluating LLMs by human preference.* Proceedings of the 41st International Conference on Machine Learning (ICML) (2024). Preprint arXiv:2403.04132.

[^mtbench]: Zheng, L. et al. *Judging LLM-as-a-judge with MT-Bench and Chatbot Arena.* Advances in Neural Information Processing Systems 36 (2023). Preprint arXiv:2306.05685.

[^selfpref]: Panickssery, A., Bowman, S. R. & Feng, S. *LLM evaluators recognize and favor their own generations.* Advances in Neural Information Processing Systems 37 (2024). Preprint arXiv:2404.13076.

[^judgmentbench]: Yang, R., Chen, R., Kelaita, P., Ranjan, R., Ma, S., Dickens, C., Guillod, M., Ma, M. & Nyarko, J. *JudgmentBench: comparing rubric and preference evaluation for quality assessment.* Preprint at https://doi.org/10.48550/arXiv.2605.25240 (2026). (In a high-expertise legal domain with practicing-attorney annotations, pairwise comparative judgments recovered the intended quality ordering far better than absolute rubric scoring: mean Spearman ρ ≈ 0.91 vs ≈ 0.15.)

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
