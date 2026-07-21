# Dual-Instrument Clinical-AI Evaluation Dataset

A dataset for studying **evaluation-instrument sensitivity on identical model outputs**: the same clinical
questions and the same four systems' verbatim answers, scored under **two evaluation formats** (blinded
human/LLM **pairwise preference** and absolute **1–4 rubric**), with per-item instrument-disagreement labels.

> **Status.** Derived-data release built by `build_dataset.py` from the reconciliation repository. Not yet
> assigned a DOI — mint one via Zenodo (or similar) from the repository owner's account before citing as a
> versioned dataset.

## Motivation

Two 2026 head-to-head studies reached opposite conclusions about specialized clinical AI (OpenEvidence)
versus frontier LLMs, using different evaluation instruments. This dataset holds the queries and answers
fixed and varies only the instrument, enabling direct study of how **evaluation format** shapes which system
appears best — including a benchmark task (predict when two instruments disagree). To our knowledge it is the
first reusable clinical dataset built specifically to study evaluation-instrument sensitivity on identical
outputs.

## Composition (`tables/`)

| File | Grain | Key columns |
|---|---|---|
| `questions.csv` | question | `question_id`, `specialty`, `question_text` |
| `answers.csv` | question × provider | `provider`, `char_len`, `has_citation` (verbatim text in `../data/answers.parquet`) |
| `human_pairwise.csv` | question × opponent × axis | `n_votes`, `mean_vote` (+1 OE … −1 opponent), `qa_text_only` render |
| `llm_pairwise.csv` | question × opponent × judge × axis | `vote` ∈ {+1, 0, −1} |
| `llm_rubric.csv` | question × provider × judge × axis | `score_1to4` |
| `items.csv` | **question × axis × opponent** | rubric & pairwise winners/margins, judge counts, `rubric_judge_diff_sd`, `instrument_flip_llm`, `instrument_flip_vs_human` |
| `splits.csv` | question | `split` ∈ {train, dev, test} |

- **Systems:** OpenEvidence + Claude Opus 4.8, Gemini 3.1 Pro, GPT-5.5 (answers verbatim from Real-POCQi).
- **Axes (5):** accuracy, clinical utility, source quality, completeness, verifiability.
- **LLM judge panel (4):** GPT-5.5, Claude Opus 4.8, Grok-4.3, Gemini-3.5-flash (blinded, high reasoning).
- **Size:** 150 questions · 600 answers · 3,865 (question×axis×opponent) items · 11,940 rubric grades ·
  8,990 LLM pairwise verdicts · 2,170 aggregated human pairwise cells.

## Benchmark task

**Predict `instrument_flip_llm`** (do the rubric and LLM-pairwise winners disagree?) from item features
(axis, opponent, rubric margin, pairwise agreement, judge dispersion, citation/length metadata). Baselines and
the reference mechanism model are in `../judge/flip_predictors.py` (flips concentrate at small margin / low
agreement). **Use the question-level `splits.csv`** so no question leaks across train/dev/test.

## Provenance and licensing

- **Real-POCQi–derived content** (questions, answers, human ratings; `question_id`, `answer_markdown`,
  human pairwise) originates from the Real-POCQi dataset (`huggingface.co/datasets/jjfenglab/Real-POCQi`),
  **CC BY 4.0** — attribute Real-POCQi (arXiv:2606.28960). Derived tables here inherit **CC BY 4.0**.
- **LLM judgments** (rubric grades, LLM pairwise verdicts, per-item flip labels) are **original to this work**
  and released under the same terms.
- **Nature Medicine numbers are NOT included**; its RCQ corpus is private (IRB i23-00510).

## Intended use and limitations

- **Intended:** studying evaluation-format sensitivity, judge behavior, and instrument-disagreement
  prediction on fixed clinical answers.
- **No adjudicated ground truth:** the data show which system each *instrument* prefers, **not** which answer
  is clinically correct. Do not use to rank clinical systems as if validated. (A clinician-adjudicated
  reference is proposed in `../HUMAN_STUDY_PROTOCOL.md`.)
- **Known biases/caveats:** LLM-judge self-preference (quantified); a finite four-judge panel (not a random
  sample); human ratings used the `qa_text_only` render while LLM judges saw `answer_markdown` (citation
  presentation differs); questions are OE-originated point-of-care queries (no independent-corpus split).

## Citation

> Afrasyab K. *Evaluation instrument choice can flip the apparent winner: a secondary analysis reconciling
> two contradictory 2026 head-to-head evaluations of clinical AI.* Kinvectum AB, 2026.
> https://github.com/KAVentures/clinical-ai-reconciliation

Please also cite Real-POCQi (arXiv:2606.28960) as the source of the underlying questions, answers, and human
ratings.

## Versioning

Regenerate with `python3 build_dataset.py`. Record the git commit and (once minted) the DOI here for each
released version.
