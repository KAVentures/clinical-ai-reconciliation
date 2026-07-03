# Reconciling two contradictory 2026 clinical-AI benchmarks — reproducibility package

This repository contains everything needed to reproduce the analyses in `MANUSCRIPT.md`, which
reconciles two mirror-image 2026 studies:

- **Real-POCQi** (arXiv:2606.28960) — OpenEvidence (OE) beats frontier LLMs on blinded human
  **pairwise preference**.
- **Nature Medicine** (s41591-026-04431-5) — frontier LLMs beat OE + UpToDate under **absolute
  1–4 rubric** scoring.

The headline result (`FINDINGS.md` §5) is an **instrument existence proof**: holding the Real-POCQi
queries *and* the four systems' answers fixed and changing **only the evaluation instrument** (human
pairwise → LLM-judge absolute rubric) erases or reverses OE's advantage on every axis. See also
`CRITIQUES.md` for the comparator-set and reasoning-effort critiques of both source studies.

## Repository layout

```
reconciliation/
├── MANUSCRIPT.md            # the paper
├── FINDINGS.md              # detailed results (public-data analyses + existence proof §5)
├── CRITIQUES.md             # comparator + reasoning-setting critiques of both source studies
├── reconciliation_protocol.md   # pre-registration for the full 2x2x2 study
├── requirements.txt
├── run_all.sh               # end-to-end reproduction
├── fetch_data.py            # download Real-POCQi parquet files from HF (CC BY 4.0)
├── data/                    # questions.parquet, answers.parquet, ratings.parquet (vendored + fetchable)
├── analysis/
│   └── analyze.py           # metric reproduction, citation-halo, power sim (NO API keys)
├── judge/
│   ├── providers.py         # unified 4-provider judge interface (stdlib only; keys at runtime)
│   ├── grade.py             # blinded absolute 1–4 rubric grader (resumable)
│   ├── analyze_grades.py    # human-pairwise vs LLM-judge win-diff, self-preference, agreement
│   ├── bootstrap_grades.py  # cluster-bootstrap CIs + leave-one-judge-out
│   ├── pairwise.py          # blinded forced-choice LLM pairwise grader — the {pairwise,LLM} cell (resumable)
│   ├── analyze_pairwise.py  # 2x2 decomposition: rater-modality vs instrument-format effects
│   ├── length_analysis.py   # length-matched sub-study on the rubric cell (no new API calls)
│   ├── make_figure.py       # Figure 1 (existence proof)
│   ├── make_figure2.py      # Figure 2 (2x2 decomposition)
│   ├── verify_thinking.py   # proves each judge ran with reasoning ON (token readout)
│   └── out/                 # grades.jsonl + all judge-analysis outputs + figures
└── out/                     # public-data outputs (results.json, citation_halo.png)
```

## Quick start

```bash
# Public-data analyses only (no API keys, no cost):
SKIP_JUDGES=1 ./run_all.sh

# Full pipeline including LLM-judge grading (requires API keys, spends credits ~1-2 hr):
./run_all.sh
```

## Environment
- Python ≥ 3.9 (developed/tested on CPython 3.9.6). `python3 -m pip install -r requirements.txt`.
- Judge calls use only the Python standard library (`urllib`) — no provider SDKs.

## Data
- Source: Hugging Face `jjfenglab/Real-POCQi`, **CC BY 4.0** (redistribution permitted with
  attribution; the three parquet files are also vendored in `data/`).
- `questions.parquet` (620 real point-of-care queries, 30 specialties), `answers.parquet`
  (2,480 = 620 × 4 systems, verbatim markdown), `ratings.parquet` (5,780 blinded human pairwise
  ratings; **no rater_id** — physicians are unlinkable; `render_mode` ∈ {qa_text_only,
  qa_text_citations}).
- Nature Medicine is **CC BY-NC-ND 4.0** (no derivatives): we cite its published numbers but
  redistribute none of its data. Its RCQ corpus is not public (IRB i23-00510 / DUA).

## API keys (judge steps only)
`judge/providers.py` reads keys at runtime from the path in its `KEYS_PATH` constant and **never
prints or persists key values** (only key names). Point `KEYS_PATH` at a local file containing:

```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
XAI_API_KEY=...
GOOGLE_API_KEY=...
```

Keep that file out of version control. **Rotate any key that has ever been shared.**

## Judge configuration (fixed, and verified)
Four judges, all at **high reasoning effort**, blinded to system identity:

| Judge label | Model | High-effort mechanism | Verified reasoning tokens (real task) |
|---|---|---|---|
| gpt-5.5 | gpt-5.5 | `reasoning_effort=high` | 3,071 |
| opus-4.8 | claude-opus-4-8 | `thinking.type=adaptive` + `output_config.effort=high` | 443 (thinking_tokens) |
| grok-4.3 | grok-4.3 | `reasoning_effort=high` | 1,880 |
| gemini-3.5-flash | gemini-3.5-flash | `thinkingConfig.thinkingBudget` | 922 (thoughts) |

Reproduce this table: `cd judge && python3 verify_thinking.py` → `out/thinking_evidence.json`.
Note Anthropic's only accepted high mode for this model is `adaptive`; it emits ~0 thinking on
trivial items, so verification uses a real (long) clinical answer.

## Determinism & seeds
- Question sampling: `random_state=62` (grade.py) — matches Nature's seed for the shared-benchmark
  spirit; changing `--n` changes the sampled set.
- Bootstrap: `numpy default_rng(62)`, 2,000 replicates, cluster on `question_id`.
- LLM judges are **not** bit-deterministic (reasoning traces sampled); we quantify this via
  inter-judge agreement (Spearman 0.19–0.47) and bootstrap CIs rather than claiming determinism.

## Expected key outputs
- `judge/out/grades.jsonl` — one row per (question, system, judge); resumable.
- `judge/out/grade_results.json` — win-diffs, per-judge breakdown, self-preference, agreement.
- `judge/out/bootstrap_results.json` — 95% CIs + leave-one-judge-out.
- `judge/out/pairwise.jsonl` — one row per (question, opponent, judge) blinded pairwise verdict; resumable.
- `judge/out/pairwise_results.json` — 2x2 decomposition (rater-modality vs instrument-format effects).
- `judge/out/length_results.json` — length-matched sub-study (per-system lengths, length-adjusted intercept/slope, length-stratified win-diffs).
- `judge/out/existence_proof.png` — Figure 1 (instrument existence proof).
- `judge/out/decomposition.png` — Figure 2 (2×2 rater-vs-instrument decomposition).
- `judge/out/thinking_evidence.json` — reasoning-token proof.
- `out/results.json`, `out/citation_halo.png` — public-data reproduction + citation-halo analysis.

## Known limitations (see MANUSCRIPT §Limitations)
No adjudicated ground truth (we show instruments *disagree*, not which is *correct*); length not
normalized; contestant-family judges self-prefer (quantified and controlled via leave-one-judge-out);
LLM rubric scores are noisy (modest inter-judge agreement). ~0.5% of judge calls failed
(transient timeouts + a few Gemini truncations), balanced across systems.
