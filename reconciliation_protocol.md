# Why Do Two Head-to-Head Clinical-AI Studies Disagree? A Factorial Reconciliation of Query Provenance, Evaluation Instrument, and Presentation

**Study protocol / pre-registration draft — v0.1**
Sole author: Koyar Afrasyab, M.D. (Kinvectum AB)
Status: design only. No data collected yet. All cited figures verified against source PDFs/HTML (see §11).

---

## 1. The puzzle

Two 2026 studies ran blinded, physician-in-the-loop, head-to-head comparisons of the *same* specialized clinical tool (OpenEvidence, "OE") against frontier general-purpose LLMs, on "real" physician queries — and reached **opposite** conclusions.

| | **Feng, Patel, Heagerty, Mai, Sivaraman, Vossler, Ouyang, Jena** — arXiv:2606.28960 (Real-POCQi) | **Vishwanath, Alyakin, … Oermann** — *Nat Med* s41591-026-04431-5 (RCQ) |
|---|---|---|
| Headline | **OE beats** GPT-5.5, Claude Opus 4.8, Gemini 3.1 Pro on all 5 axes | **Frontier LLMs beat** OE + UpToDate on all 3 stages |
| "Real" query source | 620 queries **from OE platform traffic** (rewritten w/ Opus-4.6) | 100 queries **from NYU Langone's HIPAA-compliant GPT instance** |
| Who built/ran it | **OpenEvidence** ran data collection + survey | NYU academic lab (Oermann); OE not involved |
| Real-query instrument | **Pairwise preference** (A-vs-B, 5-pt Likert), win-difference | **Absolute rubric** 1–4 per model, cumulative-link model |
| Real-query raters | 149 specialty-matched physicians | 12 US clinicians (3/item) |
| Shared benchmark | HealthBench subset (187 items), **physician pairwise** → OE wins all 5 (attenuated) | HealthBench (500 items), **LLM-judge panel** → OE 62.6 vs GPT 88.0 |
| Ground truth on real queries | none (preference only) | none on RCQ (rubric only); MedQA has answer key |
| Length control | none (length-sensitivity reported) | none (deliberately not normalized) |
| Models | Opus 4.8 / GPT-5.5 / Gemini 3.1 / OE | Opus 4.6 / GPT-5.2 / Gemini 3.1 / OE / UpToDate / Google AI Overview |

**Verified magnitudes.** Real-POCQi text-only win-differences (OE vs rest): accuracy +24.7, clinical utility +29.6, source quality +38.8, completeness +30.9, verifiability +26.2 pp (all p≪0.001). With citations shown, OE's accuracy margin *rose* to +35.7. Nature: MedQA Gemini 97.4 / GPT 94.2 / Claude 90.2 / OE 89.6 / UpToDate 88.4; HealthBench GPT 88.0 / Gemini 79.3 / Claude 77.0 / OE 62.6 / UpToDate 61.3; RCQ mean-aggregate Gemini 3.62 / GPT 3.54 / Claude 3.52 / OE 3.24 / UpToDate 3.17 / Google AI 3.27.

**The observation that motivates this study:** the two designs differ on *every* axis at once, and on each axis the choice favors the team that won. The word "real" conceals a provenance decision; the word "accuracy" conceals the absence of ground truth. The disagreement is therefore not (necessarily) about the models — it may be an artifact of benchmark construction. **Nobody has decomposed which design choice actually flips the result.** That decomposition is this paper.

---

## 2. Research questions & hypotheses

- **RQ1 (provenance).** Holding models, raters, and instrument fixed, how much of the OE-vs-frontier gap is explained by whether queries are sourced from OE traffic vs an LLM-platform vs a neutral corpus?
  - **H1:** OE's margin declines monotonically as query provenance moves OE → neutral → LLM-platform. A non-trivial share of each study's headline is provenance, not capability.
- **RQ2 (instrument).** On *identical* queries and answers, does the winner change when the evaluation instrument changes among {pairwise human preference, absolute human rubric, LLM-judge rubric}?
  - **H2:** Ranking reverses across instruments even with query provenance held constant. LLM-judge rubric favors frontier LLMs (self-preference); pairwise human preference favors OE (presentation/citation salience).
- **RQ3 (citation halo).** Does displaying citations raise *perceived* accuracy independent of factual correctness?
  - **H3:** Adding matched citations to frontier answers narrows/erases OE's perceived-accuracy margin; stripping OE's citations reduces it. Effect is largest on "verifiability"/"source quality," present on "accuracy."
- **RQ4 (ground truth).** When correctness is adjudicated against guidelines/literature (not preference), does OE's *perceived* advantage correspond to a *real* one?
  - **H4:** Perceived-accuracy margins overstate adjudicated-correctness margins; the two systems are closer on adjudicated correctness than either study implies.
- **RQ5 (length).** How much of every margin is verbosity?
  - **H5:** Length-matching shrinks completeness/accuracy margins but not source-quality margins (consistent with Real-POCQi's own length-stratified finding).

The paper's single deliverable number is the **reversal contrast**: the difference-in-differences in the OE-vs-frontier latent-quality gap across provenance levels and across instrument levels, with its interaction.

---

## 3. Decomposition framework

Model the latent quality gap between OE and a frontier comparator on item *i* as

  δ(OE−frontier) = β0 + β_prov·Provenance + β_instr·Instrument + β_cite·Citations + β_len·LengthMatched + β_prov×instr(interaction) + u_item + u_rater

Each published study is one *cell* of this design:
- Real-POCQi ≈ {Provenance = OE-sourced, Instrument = human-pairwise, Citations = shown, Length = native}
- Nature RCQ ≈ {Provenance = LLM-platform, Instrument = human-rubric, Citations = native, Length = native}
- Nature HealthBench ≈ {Provenance = benchmark, Instrument = LLM-judge, …}

The reconciliation is: estimate the full surface, show each paper is a corner of it, and report which coefficient(s) carry the sign flip.

---

## 4. Systems under test

Frozen, dated snapshots (both papers show version drift matters — Opus 4.6 vs 4.8, GPT-5.2 vs 5.5): OpenEvidence, UpToDate Expert AI, GPT (current), Gemini (current), Claude (current), plus **Google AI Overview as the reality-check floor** (Nature's most damning control — clinical tools ≈ free search). Generation standardized: temperature 0, fixed seed, search enabled, one dated access window, screenshots archived for the browser-only tools (OE/UpToDate have no API — a real constraint both studies hit).

---

## 5. Harmonized query bank (the key asset)

Three provenance strata, **de-confounded from evaluation**, ~200 items each (see §8 power):

- **S1 OE-sourced** — reuse the 620 public Real-POCQi questions (HF `jjfenglab/Real-POCQi`, CC BY 4.0 — reuse permitted with attribution).
- **S2 LLM-platform-sourced** — an *independent* corpus mimicking RCQ provenance. Nature's RCQ is **not public** (IRB/DUA), so it cannot be reused; construct a matched surrogate from an open physician-to-LLM query source (e.g., de-identified queries from an academic clinical-LLM deployment, or a solicited panel) with the *same* inclusion filters both studies used (English, decision-support, no PHI, no mid-conversation turns).
- **S3 Neutral/adjudicable** — items with a defensible gold answer: HealthBench (public), plus guideline-anchored questions (USPSTF/specialty society) where a correct answer is establishable. Enables RQ4.

Balance strata on specialty mix and difficulty. Pre-register the query bank before generation.

---

## 6. Evaluation arms (crossed with query strata)

- **A1 Human pairwise preference** — replicate Real-POCQi's instrument: blinded A-vs-B, 5-pt Likert, 5 axes, specialty-matched physicians, randomized position, citation render-mode toggle.
- **A2 Human absolute rubric** — replicate Nature's instrument: blinded 1–4 per model, 4 axes + harm/hallucination flags, 3 raters/item.
- **A3 LLM-judge rubric** — replicate Nature's HealthBench grading: multi-family judge panel; run in two modes — *self-inclusive* (judges include the contestants) vs *self-excluded* (judge family ≠ any contestant) to directly measure self-preference bias.

Same items and same generated answers flow through A1/A2/A3 → instrument effect is identified *within item*.

**Sub-experiments (nested):**
- **Citation-halo RCT (RQ3):** within A1, randomize each frontier answer to {citations added, none} and each OE answer to {native citations, stripped}, holding body text fixed. Estimate the causal citation effect on perceived accuracy.
- **Length-matching (RQ5):** regenerate a length-controlled answer set; A1/A2 re-rating.
- **Ground-truth adjudication (RQ4):** on S3, an independent expert panel (blinded to system) sets adjudicated correctness + required citations; compare to A1/A2/A3 scores.

---

## 7. Statistical model

Unified latent-quality framework so each published metric is a special case:

- **Pairwise arm (A1):** Bradley–Terry / Davidson (ties) with **crossed random effects** for item and rater; axis-specific. Recovers Real-POCQi's win-difference as a marginal contrast.
- **Absolute arms (A2/A3):** cumulative-link mixed model (proportional-odds) with random rater intercept + random item — exactly Nature's primary CLM, extended with item random effects. Sensitivity: linear mixed model.
- **Cross-instrument bridge:** estimate the OE−frontier gap δ within each (stratum × instrument) cell on a common latent scale; the **estimands** are the main effects β_prov, β_instr and the **interaction β_prov×instr** (the reversal). Bootstrap CIs (≥5,000), clustered on item and rater.
- **Citation RCT:** ATE of citation display on the accuracy-axis rating, within-item randomization.
- **IRR reported for every arm** (Krippendorff α + PABAK) — Nature's α was only 0.10–0.20 item-level; low reliability is itself a finding and must bound interpretation.
- **NOTE (verified against public data):** the public Real-POCQi `ratings` table has **no rater_id** — the 149 physicians are unlinkable. Rater random effects / leniency adjustment therefore require our own rater panels; public-data analyses are limited to question-level clustering. This corrects an earlier assumption.

Multiplicity: pre-register primary contrasts (H1 provenance slope, H2 instrument reversal, H3 citation ATE); Holm–Bonferroni within family; everything else exploratory.

---

## 8. Power / sample size  *(now grounded in measured variance — see reconciliation/FINDINGS.md)*

Estimated empirically from the public Real-POCQi ratings (question-level SD of OE's accuracy outcome = 0.598; cluster bootstrap on question). SE of a single win-difference is ~6.0 pp at 100 questions, ~3.0 at 400, ~2.4 at 620. For the primary **interaction** (difference-of-differences), questions **per cell** for 80% power (α=.05 two-sided): 10 pp → 561; 12 pp → 390; 15 pp → 250; 20 pp → 141. **Target ~250–400 questions per provenance×instrument cell** to resolve a 12–15 pp reversal, padded ~20–30% because the public data lacks rater IDs (so rater-variance inflation is not captured; our own panels will add it). The existing 620-item bank suffices for one cell, not a full 3×3 surface — budget query-bank construction accordingly.

---

## 9. What is executable now vs needs recruitment

**Now, from public data (no recruitment):**
1. **Variance-component estimation + power simulation** from Real-POCQi's public `ratings` split (has rater-level rows, render_mode, axis).
2. **Citation-halo re-analysis (observational):** exploit the public `qa_text_only` vs `qa_text_citations` render-mode contrast to estimate the citation effect on perceived accuracy *before* running the RCT — a strong preliminary result on its own.
3. **Instrument existence-proof on HealthBench:** both papers used HealthBench; re-grade the public HealthBench answers with (a) the LLM-judge panel and (b) a pairwise-preference reduction, and show the ranking flips with provenance held constant. This is the cheapest publishable nugget and de-risks the whole thesis.

**Needs generation + recruitment:** S2 corpus construction, fresh model answers, physician rater panel (A1/A2), adjudication panel (RQ4).

---

## 10. Bias, ethics, licensing safeguards

- **Provenance neutrality:** the whole point is that neither "real" corpus is privileged; report all strata, never collapse to one "real-world" claim.
- **COI transparency:** Real-POCQi was run by OE; Nature's senior author discloses equity + Google consulting (Gemini won). This study is independent (Kinvectum-funded); pre-register and open-source code/data (except any DUA-restricted surrogate).
- **Licensing:** Real-POCQi CC BY 4.0 → reusable w/ attribution. **Nature paper is CC BY-NC-ND → no derivative/adapted material may be redistributed;** cite and reproduce numbers as facts, do not repackage their figures or RCQ items. RCQ is unavailable anyway (IRB/DUA) — hence the S2 surrogate.
- **No PHI:** apply both studies' exclusion filters to any newly sourced queries; IRB/exempt determination for the rater study.

---

## 11. Source verification log

- Nature figures/methods: read directly from `s41591-026-04431-5.pdf` (19 text pages), §Results, Fig 2, Methods, Extended Data. Numbers in §1 table match the PDF verbatim.
- Real-POCQi numbers: arXiv:2606.28960 HTML + HF data card `jjfenglab/Real-POCQi` (620 Q / 2,480 A / 5,780 ratings / 149 raters; render_mode field present).
- Licenses: Real-POCQi CC BY 4.0 (HF card); Nature CC BY-NC-ND 4.0 (PDF p.5).
- COI: PDF p.7 competing-interests statement.

---

## 12. Honest limitations of *this* study

- The S2 surrogate is not Nature's actual RCQ; provenance replication is *approximate*, so RQ1's LLM-platform arm estimates an analog, not the identical distribution. State this loudly.
- Browser-only access to OE/UpToDate reintroduces the same hidden-prompt/formatting confound both prior studies suffered; we can measure it (screenshots, render-mode) but not eliminate it.
- Rater panels are expensive; if underpowered for the 3-way interaction, pre-register a fallback to the 2-way (provenance × instrument) with citations as a nested RCT only.
- Version drift: results are a dated snapshot; freeze and report access dates.
- Low IRR (per Nature) caps how sharply any instrument can resolve differences — a ceiling on all conclusions, ours included.
