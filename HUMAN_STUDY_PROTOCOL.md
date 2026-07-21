# Human study protocol: filling the missing rubric×human cell and adjudicating instrument validity

**Status:** pre-registration draft (not yet executed). Requires IRB review and clinician recruitment.
**Relationship to the main paper:** the executed work identifies a *format effect with the LLM rater held
fixed* and a three-cell path decomposition (cells A/B/C). This protocol adds the missing cell **D =
{rubric, human}** and a clinician-adjudicated reference standard, turning the three-cell demonstration into
a **complete 2×2 factorial** and moving the claim from "instruments disagree" to "which instrument better
tracks clinically adjudicated quality."

---

## 1. Background and objectives

On fixed Real-POCQi queries and answers, switching the evaluation **format** (pairwise preference →
absolute rubric) reverses the OpenEvidence-vs-frontier ranking with the *same four-model LLM panel*
(aggregation-matched format effect −16.9 to −45.8 pp; all five axes). Three of the four cells of the
{pairwise, rubric} × {human, LLM} design are populated:

|              | Pairwise | Absolute rubric |
|--------------|----------|-----------------|
| **Human**    | A (Real-POCQi) | **D — MISSING** |
| **LLM**      | B (this work) | C (this work) |

The missing cell D prevents identification of three quantities:

1. **the format effect among humans** (D − A) — do clinicians show the same pairwise→rubric shift LLMs do?
2. **the human-vs-LLM rater effect under rubric scoring** (D − C);
3. **the rater × format interaction** — the single term the main paper flags as unidentified, and the
   assumption on which the bridge to the human-rated Nature rubric rests.

**Objective 1 (cell D).** Have specialty-matched physicians score the same answers under **both** formats,
completing the factorial and estimating the interaction.

**Objective 2 (adjudication).** Have the same physicians produce a **clinically adjudicated reference
standard** (correctness, omissions, harm, qualification, citation support, overall preference), then test
**which instrument — pairwise or rubric — better tracks the adjudicated reference**, overall and within
disagreement strata.

This mirrors the Nature study's rationale for treating blinded clinician RCQ assessment as principal
evidence: automated benchmark and LLM-judge scores carry benchmark- and judge-bias concerns.

---

## 2. Sample

**Frame.** `judge/sample_human_study.py` (seed 62) draws a stratified sample of **90 (question × opponent)
items** from the exact-common-support pool, written to `dataset/human_study_sample.csv`. Achieved balance:

- **6 strata of 15** — instrument-flip {yes, no} × rubric-margin tertile {weak, mid, strong}; this yields
  **strong reversals** (flip × strong margin), **weak-margin reversals** (flip × weak), and **agreement
  controls** (non-flip), as the adjudication arm requires;
- all **five axes** (13–24 items each), all **three opponents** (29–32 each), **23 of 30 specialties**;
- each item additionally tagged high/low **judge dispersion** for the adjudication stratification.

Each of the 90 items is an OE-vs-one-frontier comparison on one axis; the 90 items span 62 distinct
questions. Blinded rating packets are generated from `data/answers.parquet` (answers are public, CC BY 4.0):
for each item present the question and the two verbatim answers in a **randomized, de-identified A/B slot**
order (provider identity never shown), with a fresh randomization per rater.

**Scaling note.** 90 items is a **direction/feasibility** scale (see §7 power). A confirmatory interaction
estimate would enlarge to the ≥250 items/cell derived in `reconciliation_protocol.md`; this protocol is
written so the same instruments and raters scale up without redesign.

---

## 3. Raters

- **2–3 board-certified physicians per item**, **specialty-matched** to the question topic (the Real-POCQi
  `specialty` field), reproducing Real-POCQi's specialty-matching (which the main paper flags as part of the
  A vs B contrast). Target ≥5 physicians total across specialties for the 90-item pilot.
- Raters are **blinded** to system identity, to the study hypothesis, and to the LLM/human results.
- Each rater completes a short **calibration set** (5 non-study items with reference answers) before scoring.

---

## 4. Instruments (identical answers, clinicians, and dimensions across tasks)

**Task R — absolute rubric (populates cell D).** Each answer scored **independently** on the five
Real-POCQi axes (accuracy, clinical utility, source quality, completeness, verifiability), integer **1–4**
(1 unacceptable … 4 excellent) — the exact scale and axes used for cells B/C, so D is directly comparable.

**Task P — pairwise preference (human replicate of A on these items).** For each item, **A/B/tie** per axis,
slot order randomized. Task P is separated from Task R by a **washout** (different session/day, re-blinded,
re-randomized order) so a rater's rubric scores cannot anchor their pairwise choice.

**Task J — adjudicated reference standard.** For each answer, blinded structured judgments:

- **factual correctness** (correct / minor error / major error);
- **clinically material omission** (yes / no; free-text);
- **potential harm** if followed (none / low / moderate / high);
- **recommendations appropriately qualified** (yes / partially / no);
- **cited evidence supports the claims** (supported / partially / unsupported / no citations);
- **overall preferred answer** for this item (A / B / tie), with rationale.

Task order across raters is **counterbalanced** (R→P→J and J→R→P arms) to detect ordering effects.

---

## 5. Procedures

- **Randomization:** per-rater slot assignment and item order via a fixed seed recorded in the pre-registration.
- **Blinding:** provider identity removed from all packets; citation formatting **retained** (so the human
  rubric is scored on the same rendering the LLM judges saw — this is deliberate, to make D vs C a clean
  *rater* contrast on identical presentation, unlike the A vs B/C rendering mismatch noted in the main paper).
- **Reliability:** every item scored by ≥2 raters; a third adjudicates disagreements beyond a pre-set
  threshold. Report Krippendorff's α / Fleiss' κ per axis and per adjudication field.
- **Stopping rule:** none for the fixed 90-item pilot; a confirmatory extension would pre-register interim
  looks with alpha spending.

---

## 6. Primary analyses

**6.1 Completed 2×2 factorial (Objective 1).** With A, B, C (existing) and D (new) on the matched items,
fit a mixed-effects model of the OE-vs-opponent signed outcome with fixed effects **rater type** (human/LLM),
**format** (pairwise/rubric), their **interaction**, and **axis**, with **question** (and rater) random
intercepts. Report:

- **format effect among humans** = D − A;
- **rater effect under rubric** = C − D;
- **rater × format interaction** = (C − D) − (B − A) — the key previously unidentified term. A small
  interaction supports transporting the LLM format effect to human rubric scoring (and thus to Nature);
  a large one localizes the effect to LLM-administered rubrics.

**6.2 Which instrument tracks adjudicated quality (Objective 2).** Treat Task J as the reference. For each
item compute the adjudicated preference and an adjudicated quality gap (correctness/harm-weighted). Then:

- correlate the **pairwise** verdict and the **rubric** verdict (both human and LLM) with the adjudicated
  preference; report agreement (κ), and rank concordance;
- **stratify** by reversal type: strong reversals, weak-margin reversals, agreement controls, and
  high/low judge dispersion (columns already in the sample). The question of interest: *when the two
  instruments disagree, which one agrees with the clinical adjudication, and does that depend on margin or
  dispersion?*
- report harm and hallucination flag rates by system as a safety-relevant secondary outcome (as Nature did).

**6.3 Combined-design efficiency.** Because the same clinicians provide R, P, and J on the same items,
every reviewed item contributes to both objectives, maximizing scientific value per clinician-hour.

---

## 7. Power and honest scope

The measured question-level SD of the per-question score is **0.598**. The pre-registered confirmatory
design (`reconciliation_protocol.md`) requires **≈250 questions/cell** to detect a 15 pp interaction at 80%
power (≈390/cell for 12 pp). The 90-item pilot with 2–3 raters yields ~180–270 human ratings per rubric arm
— adequate to **estimate the human format effect (D − A) with useful precision and to detect a *large*
rater×format interaction and large adjudication-tracking differences**, but **underpowered for a small
interaction**. Per the reviewer's caution, results from the 90-item cell will be reported as
**directional/feasibility**, not definitive, unless the confirmatory scale is reached.

---

## 8. Ethics, consent, data handling

- **IRB:** required before any clinician data collection; this document is the protocol to submit.
- **Consent:** clinician raters consent to participation; no patient data are involved (queries and answers
  are already public, CC BY 4.0).
- **Compensation:** clinician time compensated at a fair professional rate (budget out of scope here).
- **Data:** rater identifiers pseudonymized; ratings released in aggregate with the dataset (see
  `dataset/DATASET_CARD.md`); free-text adjudication rationales released only after PII screening.

---

## 9. Pre-registration and outputs

- Pre-register this protocol (OSF or equivalent) with the fixed sample manifest hash before recruitment.
- Deliverables: cell-D rubric and pairwise ratings, adjudication table, the completed-factorial model, the
  instrument-vs-adjudication analysis, and reliability statistics — added to the repository and dataset
  release as a versioned update.
