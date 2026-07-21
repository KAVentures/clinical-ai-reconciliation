# Executable-now results on public Real-POCQi data

Reproducible: `analysis/analyze.py` → `out/results.json`, `out/citation_halo.png`.
Data: `jjfenglab/Real-POCQi` (CC BY 4.0), ratings.parquet (5,780 rows), seed=62, cluster bootstrap on question_id.

## 0. Data correction to the protocol
The **public `ratings` table has no rater identifier** (columns: question_id, axis, choice, slot_a_provider, slot_b_provider, render_mode). The 149 physicians are anonymized and un-linkable across ratings. Consequences:
- Rater random effects / rater-leniency adjustment **cannot** be fit from public data (only question-level clustering is possible).
- Protocol §7 and §8 assumptions about "rater random effects from the public data" are **wrong** and are corrected below. Any instrument that needs rater modeling requires our own rater panel.

## 1. Metric reproduction (validates our pipeline)
Our one-vs-rest win-difference on the **text-only** subset matches the paper to <1 pp on every axis:

| Axis | Ours (text-only) | Paper |
|---|---|---|
| Accuracy | +24.4 [18.4, 30.4] | +24.7 |
| Clinical utility | +29.5 [21.9, 36.7] | +29.6 |
| Source quality | +38.1 [30.8, 45.0] | +38.8 |
| Completeness | +30.3 [22.4, 38.1] | +30.9 |
| Verifiability | +25.5 [18.8, 32.0] | +26.2 |

→ We compute their headline metric correctly; the rest of the analysis is trustworthy.

## 2. Citation halo — the key preliminary result (refined, not confirmed)
Halo = OE win-diff(citations) − OE win-diff(text-only).

**Between-groups (all data):** OE's margin grows on every axis when citations are shown — accuracy +11.4 pp [1.4, 21.0] p=.022; verifiability +34.2 [23.9, 44.3] p<.001; source quality +21.2 p<.001.

**Within-question (n=120 questions rated in BOTH modes) — the honest control:**
| Axis | Between-groups halo | Within-question halo |
|---|---|---|
| Accuracy | **+11.4** (p=.02) | **+1.5 [−13, +16] (p=.83)** |
| Clinical utility | +16.6 (p=.01) | +12.2 [−5, +32] (p=.18) |
| Source quality | +21.2 (p<.001) | +22.5 [8.4, 36] (p=.002) |
| Completeness | +21.2 (p=.001) | +21.3 [3.9, 40] (p=.02) |
| Verifiability | +34.2 (p<.001) | +29.2 [14, 45] (p<.001) |

**Interpretation (careful):**
- The **accuracy** "citation halo" largely **collapses within-question (+11.4 → +1.5, NS)** → the between-groups accuracy effect is substantially a **selection artifact** (which questions happened to be shown with citations), not evidence that citations inflate *perceived correctness*. This *weakens* protocol hypothesis H3 for the accuracy axis.
- The **source-quality / verifiability / completeness** halos are **robust within-question** — but these axes are partly *definitional* (citations literally are "source quality" and "verifiability"), so a genuine effect is expected and less interesting.
- Caveat: n=120 within-question subset is underpowered (CIs ±14 pp), and even the "within-question" set is not comparison-level randomized. This is why the protocol's **citation-halo RCT** (randomize citation display on identical body text) is still needed — the public data can only motivate it, not settle it.

Net: the sharpest version of the citation story is **not** "citations fool physicians about accuracy" (that mostly vanishes under control); it is "the raw between-group contrast overstates the halo, and a randomized test is required." That is a more defensible, more publishable claim.

## 3. Precision / power (replaces protocol §8 hand-waving with real numbers)
Empirical question-level SD of OE's accuracy outcome = 0.598 (over 429 questions with ≥1 accuracy rating).

- SE of a single win-difference: ~6.0 pp at 100 questions, ~4.2 at 200, ~3.0 at 400, ~2.4 at 620, ~1.9 at 1000.
- **Questions per group for 80% power on an INTERACTION (difference-of-differences), α=.05 two-sided:**
  - 10 pp → **561/group**
  - 12 pp → **390/group**
  - 15 pp → **250/group**
  - 20 pp → **141/group**

→ The reconciliation's primary provenance×instrument interaction should target **~250–400 questions per cell** to resolve a 12–15 pp reversal. The existing 620-item Real-POCQi bank is adequate for one cell but not for a well-powered 3×3 surface; budget accordingly. (These are lower bounds: without rater IDs we cannot add rater-variance inflation, so real N should be padded ~20–30%.)

## 4. What this does to the protocol
- Corrects the rater-ID assumption (§7/§8): rater modeling needs our own panel.
- Grounds §8 power in measured variance.
- Reframes H3: lead with "raw citation contrast is confounded; randomized test required," not "citations inflate perceived accuracy."
- Everything else in the protocol stands.

## 5. Instrument existence proof (the headline result)
Reproducible: `judge/grade.py` (grades) → `judge/analyze_grades.py` + `judge/bootstrap_grades.py`
→ `judge/out/{grades.jsonl, grade_results.json, bootstrap_results.json}`.

**Design.** Hold the queries AND the answers fixed (Real-POCQi's own 150-question sample × 4 systems'
verbatim answers). Change **only the evaluation instrument**: the human blinded pairwise preference
already in the dataset → an absolute 1–4 rubric scored by a 4-judge LLM panel (GPT-5.5, Opus-4.8,
Grok-4.3, Gemini-3.5-flash, all reasoning=high; blinded to system identity). Same OE-vs-rest
win-difference metric derived from both. If OE's advantage moves, the *instrument* — not the queries,
answers, or provenance — is sufficient to produce it. n=150 questions, 2,388 graded answers
(0.5% missing, balanced), 2,000-replicate cluster bootstrap on question_id.

Both instruments are computed on the **same 150-query sample**. The human column is the human pairwise
win-diff restricted to those questions (86–119 of 150 carry human text-only ratings, by axis); the
full-data column is Real-POCQi's complete text-only bank (reproduced in §1), shown because the subsample
is underpowered.

| Axis | HUMAN pairwise, same 150 [95% CI] | HUMAN full data (ref) | LLM-judge panel [95% CI] | Reversal? |
|---|---|---|---|---|
| accuracy | **+10.4 [−1.8, +22.2]** | +24.4 | **−29.1 [−38.0, −19.8]** | **Sign flip; LLM sig. negative** |
| clinical_utility | +14.4 [−1.6, +31.4] | +29.5 | −12.2 [−20.9, −3.6] | Sign flip; LLM sig. negative |
| source_quality | +23.2 [+7.6, +38.0] | +38.1 | +12.0 [+1.6, +22.9] | No — OE edge survives but shrinks 3× |
| completeness | +13.6 [−2.5, +28.7] | +30.3 | −3.6 [−12.4, +6.0] | Collapses to null (CI spans 0) |
| verifiability | +14.4 [+2.2, +27.6] | +25.5 | +0.7 [−10.0, +11.1] | Collapses to null (CI spans 0) |

> **Update — crossed question×judge bootstrap is now the primary inference (`judge/bootstrap_panel.py`
> → `out/panel_bootstrap.json`).** The table above uses the *question-only* cluster bootstrap, which
> treats the 4 judges as fixed. Because 3 of 4 judges are contestant families and GPT-5.5 self-prefers
> +0.481, the honest CI must also resample **judges** as a random factor. Re-running with judges resampled
> per replicate widens every CI, and **two per-axis claims above do not survive** and are retracted:
> clinical_utility crossed CI **[−22.4, +8.3]** (crosses 0 — *not* a significant reversal), source_quality
> crossed CI **[−8.2, +29.5]** (crosses 0 — the residual OE edge is *not* significant). The headline
> **accuracy reversal survives: crossed CI [−37.8, −4.3]** (still strictly negative). Corrected per-axis
> verdict: **accuracy is the one axis carrying a significant instrument-driven reversal**; the other four
> are individually indistinguishable from null once judges are a random factor. The stronger, judge-robust
> result is at the *decomposition* level (§6), not per-axis.

**Reading.** Swapping only the instrument **eliminates OE's advantage on every axis.** Under the primary
crossed question×judge bootstrap, only **accuracy** carries an individually-significant sign reversal
(crossed CI [−37.8, −4.3]); clinical_utility, source_quality, completeness, and verifiability all move
toward or past null but their crossed CIs include 0. (Under the narrower question-only bootstrap,
accuracy and clinical_utility both read as significantly negative and source_quality keeps a shrunken
positive edge — but those are not judge-robust and we do not rely on them.)
The headline, stated honestly: on the same answers physicians prefer OE on accuracy (+24.4 pp full data;
+10.4 pp, CI −1.8 to +22.2, same-signed but underpowered in this 150-question subsample), the **LLM
rubric scores OE −29.1 pp [−38.0, −19.8] — significantly negative.** So the instrument swap flips the
accuracy sign to a *significantly OE-disfavoring* verdict on identical content. We deliberately do **not**
claim "a significant +24 becomes a significant −29": at the 150-query existence-proof scale the human
accuracy estimate is not itself significant (the full-data one is). This is a clean existence proof that
the two papers' disagreement is driven substantially by the evaluation instrument, independent of query
provenance.

**Not a judge artifact.** GPT-5.5 self-preferred (+0.481 own-family minus others, paired; Opus +0.121,
Gemini +0.004). But leave-one-judge-out shows the accuracy reversal survives dropping **any** single
judge, including GPT-5.5 (−12.3 with GPT-5.5 removed — still negative). GPT-5.5 *amplifies* the flip
~4× but does not create it. clinical_utility's flip, by contrast, is GPT-5.5-dependent (→ +2.5 without it).

**Caveats to carry into the paper.** (i) Inter-judge Spearman agreement is modest (0.19–0.47), mirroring
Nature's own low RCQ IRR (Krippendorff α 0.10–0.20) — LLM rubric scores are noisy. (ii) No adjudicated
ground truth: we show the instruments *disagree*, not which is *correct*. (iii) Length is not normalized
(OE 3.8k vs GPT 2.6k chars) — a confound to break in the length-matched sub-study. (iv) Self-scoring by
contestant-family judges is a known bias; the frontier win here is partly a house effect and must be
reported as such — but §6 localizes it to the rubric instrument.

## 6. Rater-vs-instrument decomposition (breaks the human-vs-LLM confound)
Reproducible: `judge/pairwise.py` (blinded forced-choice pairwise, OE vs each frontier, 4 judges, same
150 questions) → `judge/analyze_pairwise.py` → `judge/out/{pairwise.jsonl, pairwise_results.json}`.

**Why.** §5 swaps {human, pairwise} → {LLM, rubric}, changing the *rater population* and the *instrument
format* at once (the same confound both source studies carry). Filling the third 2×2 cell — B =
{LLM, pairwise} — isolates the two. Cells: **A** = {pairwise, human} (Real-POCQi), **B** = {pairwise,
LLM} (new), **C** = {rubric, LLM} (§5). Decomposition of the A→C swing: rater-modality = B−A; instrument-
format = C−B.

**Cell A is on the same 150-query sample as B and C** (human text-only ratings restricted to those
questions) — *not* the full text-only bank — so B−A does not absorb a sample-composition difference.

| Axis | A pairwise/human (same 150) | B pairwise/LLM [95% CI] | C rubric/LLM | Total (C−A) | Rater (B−A) | **Instrument (C−B)** |
|---|---:|---:|---:|---:|---:|---:|
| accuracy | +10.4 | +3.6 [−2.5, +9.6] | −29.1 | −39.5 | −6.8 | **−32.7** |
| clinical_utility | +14.4 | +18.2 [+10.4, +25.9] | −12.2 | −26.6 | +3.8 | **−30.4** |
| source_quality | +23.2 | +48.8 [+42.1, +55.4] | +12.0 | −11.2 | +25.6 | **−36.8** |
| completeness | +13.6 | +37.0 [+29.2, +44.5] | −3.6 | −17.2 | +23.4 | **−40.6** |
| verifiability | +14.4 | +45.1 [+38.1, +51.9] | +0.7 | −13.7 | +30.7 | **−44.4** |

(Full coverage: 1,798/1,800 comparisons, all four judges 448–450/450; 8,990 axis-verdicts. If cell A is
taken on the full text-only bank instead, the accuracy rater term inflates to −20.8 — an artifact of
comparing against a different question sample; we use the same-sample value −6.8.)

**Propagated crossed question×judge CIs on the two components (`judge/bootstrap_panel.py`).** The
components are bootstrapped *jointly* (questions and judges resampled together across cells A/B/C), so
B−A and C−B carry real CIs, not point-estimate arithmetic:

| Axis | Rater (B−A) [crossed CI] | **Instrument (C−B) [crossed CI]** |
|---|---:|---:|
| accuracy | −6.8 [−27.5, +14.3] | **−32.7 [−42.8, −8.8]** |
| clinical_utility | +3.8 [−22.3, +31.9] | **−30.5 [−42.6, −9.0]** |
| source_quality | +25.6 [−3.4, +54.8] | **−36.8 [−56.9, −22.4]** |
| completeness | +23.4 [+2.2, +45.4] | **−40.5 [−53.6, −22.0]** |
| verifiability | +30.7 [+7.9, +53.6] | **−44.4 [−62.0, −29.1]** |

The instrument component (C−B) is negative with a crossed CI excluding zero on all five axes at the
**panel level**. **⚠️ CORRECTION (this revision):** the panel-level table above is retained for
transparency but is **superseded** on two points by the aggregation-matched and common-support analyses
(`judge/robust_analysis.py`):

1. **Primary is now the aggregation-matched, same-judge format component** (each judge's own rubric
   thresholded and pooled like its own pairwise votes): accuracy −16.9, clinical_utility −21.3,
   source_quality −40.6, completeness −37.4, verifiability −45.8 pp — all Holm-significant, all
   sign-consistent across four judges, simultaneous CIs exclude zero. The panel-level −29.1/−32.7 accuracy
   figures were inflated by averaging judges **then** thresholding (a ±0.25 tie-band gives −13.8; native
   1–4 gap only −0.125). Accuracy is the **weakest** axis, not the headline.
2. **The rater term is NOT null — we retract "instrument, not the rater."** On **exact common support**
   (matching every question×opponent×axis with a human rating), the accuracy rater term B−A is **−24.0 pp
   [−35.7, −12.5]**: LLM pairwise judges reproduce only +0.5 pp of physicians' +24.4 pp OE accuracy edge on
   the same questions. The panel-level "−6.8, null" was a support-mismatch artifact. **Both** the rater
   change and the format change contribute; the "~83% instrument share" is withdrawn.

**Result (corrected).** The robust, assumption-light claim is **format-with-rater-fixed**: the same LLM
judge, switched pairwise→rubric, moves OE-vs-frontier negative on all five axes. It is a **three-cell path
decomposition, not a factorial** — both components matter, and the bridge to the human-rated Nature rubric
assumes a small (untested) rater×format interaction.

**Scope caveat (the missing fourth cell).** This decomposition is identified *within LLM raters*: we have
A = {pairwise, human}, B = {pairwise, LLM}, C = {rubric, LLM}, but **not** D = {rubric, human}.
Generalizing the instrument effect (C−B) to explain the *human-rated* Nature rubric therefore assumes **no
rater×instrument interaction** — that humans doing a rubric would show the same pairwise→rubric shift LLMs
do. Untested, and plausibly the direction where interaction lives (humans may not share the frontier-prose
prior an LLM rubric rewards). Proven claim = "with the rater held fixed, the evaluation format shifts the
ranking on all five axes"; we do **not** claim the format acts instead of the rater (both matter, §above);
bridge to Nature = conditional on a small rater×format interaction. Filling cell D (even small-n human rubric) is the top
follow-up. Minor: B−A also absorbs protocol differences (tie handling, pair structure) between Real-POCQi's
human pairwise and our LLM pairwise, so it is "rater modality + protocol," not pure rater.

**House effect localized.** Per-judge cell B: the *family-neutral* judge **Grok prefers OE on all 5 axes**
(+11 to +65); the contestant **GPT-5.5 is the least OE-favorable** — the opposite of a blanket pro-frontier
LLM prejudice. The pro-frontier tilt is therefore **specific to the rubric instrument**, not to LLM judges.

**Coverage note (resolved).** Gemini-3.5-flash initially stalled at 297/450 (Google API HTTP 429 — prepaid
credits exhausted); after credits were restored the cell was completed to 448/450 (99.9% overall). Point
estimates moved <3 pp from the partial run — the conclusion never depended on the missing data.

## 7. Length is not the driver of the rubric reversal (the last unbroken confound, tested observationally)
Reproducible: `judge/length_analysis.py` → `judge/out/length_results.json` (+ figure). No new API calls —
this reuses the existing 150-question rubric grades and the verbatim answer lengths.

**Why.** Answer length is the most-cited uncontrolled confound in both source studies (neither normalizes
length), and the intuitive worry is that an absolute rubric rewards longer, more comprehensive answers. If
so, the rubric reversal could be a length artifact rather than an instrument effect.

**The premise fails at step one.** OpenEvidence produces the **longest** answers on the graded set (median
3,600 chars vs GPT-5.5 2,232, Opus 3,294, Gemini 3,586) — yet it **loses** the accuracy rubric. A "longer
answers win" mechanism therefore runs *backwards* against the finding.

**Three confirmations (n=150, 2,000-replicate cluster bootstrap on question_id).** Native-scale
OE-minus-frontier rubric-score gap (points, 1–4 scale); slope = points bought per +1,000 chars; win-diff
split by whether OE's answer was longer/shorter than its opponent's.

| Axis | Raw gap (pts) | Length-adjusted gap [95% CI] | Slope (pts / +1k chars) | Win-diff: OE longer | Win-diff: OE shorter |
|---|---:|---:|---:|---:|---:|
| Accuracy | −0.127 | −0.12 [−0.17, −0.08] | −0.015 | −34.3 | −19.9 |
| Clinical utility | −0.021 | −0.03 [−0.06, +0.01] | +0.016 | −14.1 | −8.4 |
| Source quality | +0.103 | +0.09 [+0.03, +0.15] | +0.042 | +15.9 | +6.0 |
| Completeness | +0.004 | −0.01 [−0.05, +0.03] | +0.039 | +0.7 | −10.8 |
| Verifiability | +0.003 | −0.01 [−0.06, +0.05] | +0.025 | +1.4 | +0.0 |

**Reading.** (i) The per-axis length **slope** is tiny (−0.015 to +0.042 pts/1k chars); accuracy's is
essentially zero and slightly negative. (ii) The **length-adjusted intercept** — expected OE-vs-frontier
gap at *equal length* — is statistically indistinguishable from the raw gap on every axis (accuracy −0.12
[−0.17, −0.08] adjusted vs −0.127 raw). (iii) The accuracy win-difference stays negative **whether OE is
the longer answer (−34.3) or the shorter (−19.9)** — OE loses on accuracy even in the stratum where it
wrote *more*. Length has a small positive association with source-quality/completeness/verifiability scores
but essentially none with accuracy, and adjusting for it leaves every axis unchanged within CI.

**Net.** Length does **not** explain the rubric reversal. This is observational (same answers, not
regenerated), so it removes length as an alternative explanation for *this* result but does not replace the
still-pre-registered fully length-matched *generation* study (§4 protocol) — it just shows that study is
unlikely to overturn the finding.
