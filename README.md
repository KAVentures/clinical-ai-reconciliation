# The Instrument Makes the Winner: Reconciling Two Contradictory 2026 Head-to-Head Evaluations of Clinical AI

**Two 2026 studies compared the same class of systems and reached opposite conclusions. This repository shows the disagreement is not about the models — it is about the *measuring instrument*.** Holding the queries *and* the systems' answers fixed and changing **only** the evaluation instrument (blinded human pairwise preference → LLM-judge absolute rubric) erases or reverses the specialist system's advantage on every quality axis. A formal 2×2 {instrument} × {rater} decomposition attributes ~83% of the accuracy swing to the instrument, not the rater.

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

OE-vs-rest win-difference (percentage points; positive = OE preferred) under each instrument on the **identical** 150-query sample:

| Axis | Human pairwise [95% CI] | LLM-judge rubric [95% CI] | Verdict |
|---|---:|---:|---|
| Accuracy | +10.4 [−1.8, +22.2] | **−29.1 [−38.0, −19.8]** | sign flips to significantly negative |
| Clinical utility | +14.4 [−1.6, +31.4] | −12.2 [−20.9, −3.6] | sign flips to significantly negative |
| Source quality | +23.2 [+7.6, +38.0] | +12.0 [+1.6, +22.9] | OE edge survives, ~3× smaller |
| Completeness | +13.6 [−2.5, +28.7] | −3.6 [−12.4, +6.0] | collapses to null |
| Verifiability | +14.4 [+2.2, +27.6] | +0.7 [−10.0, +11.1] | collapses to null |

On the full Real-POCQi text-only bank the human accuracy edge is +24.4 pp (reproduces the published +24.7 to <1 pp); on this 150-query subsample it is +10.4 pp (same sign, underpowered). On the **same answers**, the LLM rubric scores OE **−29.1 pp**. Under no axis does OE retain its large human-pairwise advantage.

### 2. It is the instrument, not the rater (2×2 decomposition)

Splitting the human-pairwise→LLM-rubric swing into rater (B−A) and instrument (C−B) components:

| Axis | A: pairwise/human | B: pairwise/LLM | C: rubric/LLM | Rater (B−A) | **Instrument (C−B)** |
|---|---:|---:|---:|---:|---:|
| Accuracy | +10.4 | +3.6 | −29.1 | −6.8 | **−32.7** |
| Clinical utility | +14.4 | +18.2 | −12.2 | +3.8 | **−30.4** |
| Source quality | +23.2 | +48.8 | +12.0 | +25.6 | **−36.8** |
| Completeness | +13.6 | +37.0 | −3.6 | +23.4 | **−40.6** |
| Verifiability | +14.4 | +45.1 | +0.7 | +30.7 | **−44.4** |

**LLM judges administering the *pairwise* instrument reproduce the human pairwise verdict** — OE wins on four of five axes. The instrument component (C−B) is large, negative, and consistent (−30.4 to −44.4 pp) and dominates the rater component on every axis. On accuracy — the one axis where both push negative — the instrument still does **~83% of the swing (−32.7 pp instrument vs −6.8 pp rater)**.

### 3. Not merely a self-scoring artifact

Contestant-family judges self-preferred (GPT-5.5 **+0.481**, Opus **+0.121**, Gemini **+0.004** points, own family minus others), but the accuracy reversal **survives dropping any single judge**, including GPT-5.5 (−12.3 pp without it). Under the *pairwise* instrument the family-neutral judge (Grok) prefers OE on **all five axes** and GPT-5.5 is the *least* OE-favorable judge — the opposite of a blanket pro-frontier prejudice. The pro-frontier tilt is **specific to the rubric instrument**.

### 4. Not a length artifact

OpenEvidence produces the **longest** answers (median 3,600 chars vs GPT-5.5 2,232) yet *loses* the accuracy rubric, so a "longer wins" mechanism runs backwards against the finding. Length-adjusted gaps are indistinguishable from raw (accuracy −0.12 adjusted vs −0.127 raw), and OE loses accuracy whether it is the longer (−34.3) or shorter (−19.9) answer.

## Key Conclusions

- **The measuring instrument, not the model, is the first-order driver of the contradiction.** Pairwise and rubric instruments order the same fixed answers differently; ~83% of the accuracy swing is instrument-attributable.
- **LLMs are not the problem — the rubric is.** Given the *same* forced-choice instrument, LLM judges agree with physicians (OE preferred on 4/5 axes). The reversal appears only under absolute rubric scoring.
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
| `CRITIQUES.md` | Comparator-set and reasoning-effort critiques of both source studies |
| `reconciliation_protocol.md` | Pre-registration for the full 2×2×2 study (incl. missing human-rubric cell) |
| `run_all.sh` | End-to-end reproduction (`SKIP_JUDGES=1` for the no-API-key public-data subset) |
| `fetch_data.py`, `data/` | Real-POCQi parquet fetch + vendored copies (CC BY 4.0) |
| `analysis/analyze.py` | Metric reproduction, citation-halo, power simulation (no API keys) |
| `judge/providers.py` | Unified 4-provider judge interface (stdlib only; keys loaded at runtime, never persisted) |
| `judge/grade.py`, `judge/pairwise.py` | Blinded rubric grader (cell C) and blinded pairwise grader (cell B); both resumable |
| `judge/analyze_*.py`, `judge/bootstrap_grades.py`, `judge/length_analysis.py` | Win-diffs, 2×2 decomposition, self-preference, bootstrap CIs, length sub-study |
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

> Afrasyab K. *The instrument makes the winner: reconciling two contradictory 2026 head-to-head evaluations of clinical AI.* Independent researcher / Kinvectum AB, 2026. https://github.com/KAVentures/clinical-ai-reconciliation
