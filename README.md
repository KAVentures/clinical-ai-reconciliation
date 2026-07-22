# The Instrument Makes the Winner: Reconciling Two Contradictory 2026 Head-to-Head Evaluations of Clinical AI

**Two 2026 studies compared the same class of systems and reached opposite conclusions. This repository shows the disagreement is not about the models — it is about the *measuring instrument*.** Holding the queries *and* the systems' answers fixed and changing **only** the evaluation instrument (blinded human pairwise preference → LLM-judge absolute rubric) erases or reverses the specialist system's advantage on every quality axis. A formal 2×2 {instrument} × {rater} decomposition — with a **crossed question × judge bootstrap** that treats the four judges as a random factor — localizes the swing to the **instrument** component (significantly negative on all five axes), while the **rater** component is indistinguishable from zero on accuracy.

Author: **Koyar Afrasyab, M.D.** — *corresponding author*
Affiliation: **Independent researcher; Founder, Kinvectum AB**
Funding: **Kinvectum AB**

This repository contains the manuscript (Markdown + self-contained PDF), the judging/analysis pipeline, figures, judge-panel votes, bootstrap CIs, and the public rating data needed to reproduce a reconciliation of two mirror-image 2026 clinical-AI evaluations:

- **Real-POCQi** (arXiv:2606.28960) — OpenEvidence (OE) **beats** frontier general-purpose LLMs on blinded physician **pairwise preference** across 620 real point-of-care queries.
- **Nature Medicine** (s41591-026-04431-5) — frontier LLMs **beat** OE and UpToDate Expert AI under an **absolute 1–4 rubric**.

Both studies additionally sourced their "real-world" queries from the platform that went on to win (home-field provenance) and used different model versions — but the decomposition here isolates the **instrument** (pairwise vs rubric) as the dominant driver of the contradiction.

## Quick Links

- [Manuscript (Markdown)](MANUSCRIPT.md) · [Manuscript (PDF)](MANUSCRIPT.pdf)
- [Detailed findings — public-data analyses + existence proof](FINDINGS.md)
- [Critiques of both source studies](CRITIQUES.md)
- [Pre-registration for the full 2×2×2 study](reconciliation_protocol.md)
- [Figure 1 — instrument existence proof](judge/out/existence_proof.png)
- [Figure 2 — 2×2 rater-vs-instrument decomposition](judge/out/decomposition.png)
- [Real-POCQi data (Hugging Face, CC BY 4.0)](https://huggingface.co/datasets/jjfenglab/Real-POCQi)

## Study Question

Two blinded, physician-facing evaluations of the *same* specialist-vs-frontier match-up reached opposite verdicts. This study asks:

> When you hold the clinical queries and the systems' verbatim answers fixed and change **only** the evaluation instrument — from forced-choice human pairwise preference to an absolute 1–4 rubric — does the winner change? And if it does, is that swing driven by the *rater* (physicians vs LLMs) or by the *instrument format* (pairwise vs rubric)?

## Design — filling the missing cell of a 2×2

The two source studies differ on two things at once, confounding any direct comparison: the **rater population** (physicians → LLMs) *and* the **instrument format** (pairwise → rubric). We break the confound by running the same blinded, high-reasoning four-judge LLM panel on the **same 150 queries and answers** under *both* instruments, yielding three of four cells:

| | Pairwise instrument | Rubric instrument |
|---|---|---|
| **Human rater** | **A** — Real-POCQi (OE wins) | *D* — not run (pre-registered, §7) |
| **LLM rater** | **B** — new here (OE mostly wins) | **C** — new here (OE reverses) |

The A→C swing (the published contradiction) is then split into a **rater component (B−A)** and an **instrument component (C−B)**.

## Model / Judge Panel

Four judges, all at **high reasoning effort**, blinded to system identity. Reasoning was verified per judge on a real (long) clinical answer.

| Judge label | Configured identifier | High-effort mechanism | Verified reasoning tokens |
|---|---|---|---:|
| gpt-5.5 | `gpt-5.5` | `reasoning_effort=high` | 3,071 |
| opus-4.8 | `claude-opus-4-8` | `thinking.type=adaptive` + `output_config.effort=high` | 443 (thinking) |
| grok-4.3 | `grok-4.3` | `reasoning_effort=high` | 1,880 |
| gemini-3.5-flash | `gemini-3.5-flash` | `thinkingConfig.thinkingBudget` | 922 (thoughts) |

The four graded systems (answers held fixed from Real-POCQi): **OpenEvidence**, plus frontier general-purpose LLMs.

## Main Results

### 1. The instrument flips the winner (n = 150, same queries + answers, 2,000-replicate cluster bootstrap)

OE-vs-rest win-difference (percentage points; positive = OE preferred) under each instrument on the **identical** 150-query sample. The rubric CI shown is the **crossed question × judge bootstrap** (judges treated as a random factor) — the primary, judge-robust interval:

| Axis | Human pairwise [95% CI] | LLM-judge rubric [crossed q×judge CI] | Verdict (crossed) |
|---|---:|---:|---|
| Accuracy | +10.4 [−1.8, +22.2] | **−29.1 [−37.8, −4.3]** | sign flips; **negative, survives judge resampling** |
| Clinical utility | +14.4 [−1.6, +31.4] | −12.2 [−22.4, +8.3] | sign flips, but **not sig under crossed CI** |
| Source quality | +23.2 [+7.6, +38.0] | +12.0 [−8.2, +29.5] | attenuated ~3×; **not sig under crossed CI** |
| Completeness | +13.6 [−2.5, +28.7] | −3.6 [−14.4, +12.7] | collapses to null |
| Verifiability | +14.4 [+2.2, +27.6] | +0.7 [−13.6, +13.8] | collapses to null |

On the full Real-POCQi text-only bank the human accuracy edge is +24.4 pp (reproduces the published +24.7 to <1 pp); on this 150-query subsample it is +10.4 pp (same sign, underpowered). On the **same answers**, the panel-level LLM rubric scores OE **−29.1 pp** — but this cell-C number is inflated by averaging four judges and *then* thresholding; the aggregation-matched value is −16.9 pp and a ±0.25 tie-band gives −13.8 pp (native gap only −0.125 on the 1–4 scale). **The robust, rater-fixed result is the format effect in §2 below**, which is significant on all five axes; accuracy is its weakest instance.

### 2. Primary: the format effect with the rater held **fixed** (aggregation-matched, same judge)

For each judge we threshold **that judge's own** rubric scores into win/tie/loss and pool them exactly as **that same judge's** pairwise votes, then average the per-judge format change (C_j − B_j). This holds the rater fixed, isolating evaluation **format**. Fixed-judge question-cluster bootstrap CIs; Holm-adjusted *p*; simultaneous max-|T| CIs (`judge/robust_analysis.py`):

| Axis | Format effect (pp) | 95% CI (fixed-judge) | Simultaneous CI | Holm *p* | 4/4 judges same sign |
|---|---:|---:|---:|---:|:--:|
| Accuracy | −16.9 | [−22.3, −11.4] | [−23.9, −9.9] | 0.003 | ✓ |
| Clinical utility | −21.3 | [−28.1, −14.3] | [−30.2, −12.4] | 0.003 | ✓ |
| Source quality | −40.6 | [−45.8, −34.9] | [−47.6, −33.6] | 0.003 | ✓ |
| Completeness | −37.4 | [−43.9, −30.1] | [−46.2, −28.6] | 0.003 | ✓ |
| Verifiability | −45.8 | [−51.5, −40.3] | [−53.1, −38.5] | 0.003 | ✓ |

**With the same LLM judge, switching pairwise→rubric moves the OE-vs-frontier verdict negative on all five axes** — sign-consistent across every judge, surviving simultaneous inference, judge-resampling (crossed CIs still exclude zero), and restriction to citation-free OE answers. Largest on the evidence axes (source quality, verifiability); **smallest and most aggregation-sensitive on accuracy** (native 1–4 gap only −0.125; a ±0.25 tie-band cuts the panel accuracy figure from −29.1 to −13.8).

**Exact common-support decomposition (identical keys for A, B, C; 108 q×opp/axis).** The format component (C−B) is negative on all five axes (−17.8 to −43.1 pp, CIs exclude zero). The human→LLM **protocol contrast (B−A)** — which changes *both* rater population and answer rendering (physicians saw text-only; LLM judges saw citation-bearing Markdown) — is **null on accuracy (−7.9 pp [−23.5, +7.1], tail p=0.30)** and clinical utility, but significantly **positive** on source quality (+25.1), completeness (+17.6) and verifiability (+30.0). Those are the axes most sensitive to citation presence, so B−A is a rater+rendering contrast, not evidence about rater population alone. Robust to **equal-key weighting** (accuracy −5.8 NS; evidence axes +18.8…+29.5; format unchanged). So we do **not** claim "instrument, not the rater," nor that B−A is large-and-negative on accuracy — an earlier revision's "−24.0 pp, significant" was an analysis error (unmatched cell A), now fixed. **Both matter, but the format carries the reversal.** Three-cell path decomposition, not a factorial; "~83% instrument share" withdrawn.

### 3. Not merely a self-scoring artifact

Contestant-family judges self-preferred, and this survives a **difference-in-differences** that removes the "the family's answers are simply better" confound (how much more a judge favors its own family than the *other* judges do: GPT-5.5 **+0.42**, Gemini **+0.25**, Opus **+0.14** beyond panel consensus). Nonetheless the format effect **survives dropping any single judge** and is sign-consistent across all four. Under the *pairwise* instrument the family-neutral judge (Grok) prefers OE on **all five axes** and GPT-5.5 is the *least* OE-favorable judge — the opposite of a blanket pro-frontier prejudice. The pro-frontier tilt is **specific to the rubric format**.

### 4. Not a length artifact

OpenEvidence is among the **longest** providers (median 3,600 chars — essentially tied with Gemini's 3,586 and well above GPT-5.5's 2,232) yet *loses* the accuracy rubric, so a "longer wins" mechanism runs backwards against the finding. Length-adjusted gaps are indistinguishable from raw (accuracy −0.12 adjusted vs −0.127 raw), and OE loses accuracy whether it is the longer (−34.3) or shorter (−19.9) answer.

## Key Conclusions

- **The evaluation *format* alone can flip the ranking, with the rater held fixed.** With the same LLM judge, switching pairwise→rubric moves the OE-vs-frontier verdict negative on all five axes (aggregation-matched −16.9 to −45.8 pp; Holm-significant; sign-consistent across all four judges). This is the robust, assumption-light core.
- **Both the format and the human→LLM protocol contrast matter — we do *not* claim "instrument, not the rater," but the format carries the reversal.** On exact common support the protocol contrast B−A (rater population *and* text-only→Markdown rendering) is null on accuracy (−7.9 pp, tail p=0.30) and significantly *positive* on the evidence axes (+18 to +30); it does not explain the rubric reversal. Three-cell path decomposition (missing the human-rubric cell), not a factorial.
- **Accuracy is the weakest, most aggregation-sensitive axis**, not the headline: the earlier −29.1/−32.7 pp figures were inflated by averaging judges then thresholding (native gap only −0.125 on the 1–4 scale). The large, robust format effects are on the evidence-presentation axes.
- **Not Nature's exact rubric.** We score the five Real-POCQi axes with an LLM panel — a general absolute-vs-comparative contrast, not a transport of Nature's RCQ instrument.
- **Self-preference exists but does not create the effect.** The accuracy reversal survives leave-one-judge-out, and the family-neutral judge favors OE under pairwise.
- **This is an existence proof of instrument sensitivity, not an adjudication of clinical truth.** We show the instruments *disagree* on identical content — not which one is *correct*. The missing human-rubric cell (D) is pre-registered as the decisive control.

## Limitations

- **No adjudicated ground truth.** We demonstrate instruments disagree, not which verdict is clinically correct.
- **Existence-proof scale (n = 150).** The human accuracy estimate on the subsample is not itself significant; the clean claim is a sign reversal to a significantly-negative rubric verdict on identical content, corroborated by the full-data human sign.
- **Shared LLM house effect.** Leave-one-judge-out removes *family-specific* bias but not a bias all four LLM judges might *share*; no LLM judge is a clean control for a common stylistic prior. Human-administered rubric scoring (cell D) is the remaining control.
- **Noisy instrument.** Inter-judge Spearman agreement is modest (0.19–0.47), mirroring the low human-rater agreement the Nature study reports (α ≈ 0.10–0.20).
- **Provenance confound in the sources.** Each source study drew queries from the platform that won; we hold answers fixed but cannot remove provenance from the original datasets.

## Repository Contents

| Path | Contents |
|---|---|
| `MANUSCRIPT.md` / `MANUSCRIPT.pdf` | Full manuscript (abstract → methods → results → discussion → limitations → references), self-contained PDF with embedded figures |
| `FINDINGS.md` | Detailed results: public-data analyses + the instrument existence proof |
| `CRITIQUES.md` | Critiques of both source studies: comparator-set, reasoning-effort, instrument construct problems (rubric noise-floor/compression, pairwise citation bias, axis non-independence), and data-pipeline/COI confounds |
| `reconciliation_protocol.md` | Pre-registration for the full 2×2×2 study (incl. missing human-rubric cell) |
| `run_all.sh` | End-to-end reproduction (`SKIP_JUDGES=1` for the no-API-key public-data subset) |
| `fetch_data.py`, `data/` | Real-POCQi parquet fetch + vendored copies (CC BY 4.0) |
| `analysis/analyze.py` | Metric reproduction, citation-halo, power simulation (no API keys) |
| `judge/providers.py` | Unified 4-provider judge interface (stdlib only; keys loaded at runtime, never persisted) |
| `judge/grade.py`, `judge/pairwise.py` | Blinded rubric grader (cell C) and blinded pairwise grader (cell B); both resumable |
| `judge/analyze_*.py`, `judge/bootstrap_grades.py`, `judge/length_analysis.py` | Win-diffs, 2×2 decomposition, self-preference, bootstrap CIs, length sub-study |
| `judge/bootstrap_panel.py` | Crossed question × judge bootstrap (primary inference); writes `judge/out/panel_bootstrap.json` |
| `judge/rubric_anchors.py` | **Canonical rubric** (five-axis 1–4 definitions + per-score anchors) shared by the physician workbooks and the LLM regrade, so cells C and D use identical instructions |
| `judge/grade_expanded.py` | Ready-to-run LLM cell-C **regrade** with the expanded anchors (makes C ≡ D's rubric); ~2,400 calls (~$40–90) — **not run** (needs keys/spend) |
| `judge/export_disagreement.py` (+ `test_export_disagreement.py`) | Per-item instrument-disagreement audit export → `judge/out/instrument_disagreement.csv` + `_by_axis.json`; deterministic test pins the flip definition (issue #1) |
| `judge/judge_subsets.py` | Finite-panel sensitivity: format effect over all 15 non-empty judge subsets → `judge/out/judge_subsets.json` (every subset negative on every axis) |
| `judge/flip_predictors.py` | Question-clustered GEE logistic for what predicts a per-item instrument flip → `judge/out/flip_predictors.json` (flips concentrate at small margin / low agreement) |
| `judge/sample_human_study.py` | Stratified 90-item (question×opponent) sampling frame for the human study → `dataset/human_study_sample.csv` |
| `HUMAN_STUDY_PROTOCOL.md` | Pre-registration draft: fill the missing {rubric, human} cell D + clinician adjudication (completes the 2×2 factorial; needs IRB + clinicians) |
| `dataset/` | Reusable dual-instrument dataset: `build_dataset.py`, tidy `tables/`, `DATASET_CARD.md`, `quickstart.py` (benchmark task: predict instrument disagreement) |
| `dataset/physician/` | **Primary physician study** (completes the 2×2), `build_physician_study.py` (+ `test_physician_study.py` assertions): `PHYSICIAN_ABSOLUTE_RUBRIC.xlsx` — Nature-format, **one blinded answer per row** (no competing answer), **160 response-items** (80 pairs × 2, un-deduped), 5 Real-POCQi axes 1–4 + competence/confidence; `PHYSICIAN_PAIRWISE.xlsx` — blinded A/B (randomized per item **and** reviewer), 5 A/B/tie + overall. Pairs sampled directly at (question, opponent) level, disagreement-enriched **with tie/near-tie + agreement controls**. Each workbook: Instructions / Rubric-anchors / Worked-example / **Data-dictionary** / Ratings, protected, drop-down-validated, provider-scrubbed, completion counter (all fields), randomized item order. `packets/` (git-ignored) = 24 reviewer-specific single-arm files (15–25 items, ≥2 raters/item); `author_only/` (git-ignored) = un-blinding + assignment + data dictionary. See `HUMAN_STUDY_PROTOCOL.md` |
| `dataset/adjudication/` | `CLINICIAN_DISAGREEMENT_ADJUDICATION_PACKET.xlsx` — the fuller adjudication instrument (rubric + pairwise + per-answer correctness/harm/omission/citation), **reserved for a later, smaller sample of clinically important instrument-flip cases**; not the primary factorial instrument. Built by `build_adjudication_packet.py` + `make_adjudication_xlsx.py`; `blinding_key.csv` git-ignored/private |
| `judge/make_figure*.py`, `judge/verify_thinking.py` | Figure generation and per-judge reasoning-token verification |
| `judge/out/`, `out/` | Grades, pairwise verdicts, result JSON, bootstrap CIs, figures |

## Reproducing the Study

```bash
python3 -m pip install -r requirements.txt

# Public-data analyses only (no API keys, no cost):
SKIP_JUDGES=1 ./run_all.sh

# Full pipeline including LLM-judge grading (requires API keys, spends credits, ~1–2 hr):
./run_all.sh
```

- Python ≥ 3.9 (developed on CPython 3.9.6). Judge calls use only the standard library (`urllib`) — no provider SDKs.
- Determinism: question sampling `random_state=62`; bootstrap `numpy default_rng(62)`, 2,000 replicates clustered on `question_id`. LLM judges are not bit-deterministic (reasoning traces sampled); variance is quantified via inter-judge agreement and bootstrap CIs rather than asserted away.

## Data & Licensing

- **Real-POCQi** — Hugging Face `jjfenglab/Real-POCQi`, **CC BY 4.0**: 620 point-of-care queries (30 specialties), 2,480 verbatim answers (620 × 4 systems), 5,780 blinded human pairwise ratings (no `rater_id` — physicians unlinkable). Redistribution permitted with attribution; the three parquet files are vendored in `data/`.
- **Nature Medicine** — **CC BY-NC-ND 4.0** (no derivatives): we cite its published numbers only and redistribute none of its data. Its RCQ corpus is not public (IRB i23-00510 / DUA).

## API Keys (judge steps only)

`judge/providers.py` reads keys at runtime from a **git-ignored local file** and **never prints or persists key values** (only key names). The path defaults to `API_KEYS.local.md` at the repo root and can be overridden with the `MEDROBUST_KEYS_PATH` environment variable. Create a local file (kept out of version control) containing:

```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
XAI_API_KEY=...
GOOGLE_API_KEY=...
```

**Rotate any key that has ever been shared.** No secret values are committed to this repository.

## Citation

> Afrasyab K. *Evaluation instrument choice can flip the apparent winner: a secondary analysis reconciling two contradictory 2026 head-to-head evaluations of clinical AI.* Independent researcher / Kinvectum AB, 2026. https://github.com/KAVentures/clinical-ai-reconciliation
