"""Minimal reproducibility quickstart for the dual-instrument dataset.

Loads the tidy tables and (1) prints the instrument-flip rate on the question-level test split, (2)
reproduces the SIGN of the aggregate OE-vs-frontier win-difference under each instrument, and (3) fits a
trivial baseline for the flip-prediction benchmark task. Pure pandas/numpy; run after build_dataset.py:

    python3 build_dataset.py && python3 quickstart.py
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, 'tables')
OE = 'openevidence'
FRONTIER = ['gpt-5.5', 'claude-opus-4-8', 'gemini-3.1-pro']
AXES = ['accuracy', 'clinical_utility', 'source_quality', 'completeness', 'verifiability']


def windiff(winner_col, df):
    w = df[winner_col]
    W = (w == OE).sum(); L = w.isin(FRONTIER).sum(); N = W + L
    return 100 * (W - L) / N if N else float('nan')


def main():
    items = pd.read_csv(os.path.join(T, 'items.csv'))
    splits = pd.read_csv(os.path.join(T, 'splits.csv')).set_index('question_id')['split']
    items['split'] = items.question_id.map(splits)

    print("=== (1) instrument-flip rate (LLM rubric vs LLM pairwise), by split ===")
    dec = items[items.rubric_winner.isin([OE] + FRONTIER) & items.pw_llm_winner.isin([OE] + FRONTIER)]
    for s in ['train', 'dev', 'test']:
        d = dec[dec.split == s]
        print(f"  {s:5s}  n={len(d):4d}  flip_rate={d.instrument_flip_llm.mean():.3f}")

    print("\n=== (2) aggregate OE-vs-frontier win-difference SIGN, by instrument x axis ===")
    print(f"  {'axis':16s}{'rubric(C)':>11s}{'llm_pw(B)':>11s}{'human(A)':>11s}")
    for ax in AXES:
        d = items[items.axis == ax]
        print(f"  {ax:16s}{windiff('rubric_winner', d):>+11.1f}"
              f"{windiff('pw_llm_winner', d):>+11.1f}{windiff('pw_human_winner', d):>+11.1f}")

    print("\n=== (3) flip-prediction baseline: threshold on |rubric margin| (train-fit, test-eval) ===")
    dec = dec.assign(abs_margin=dec.rubric_margin.abs())
    tr, te = dec[dec.split == 'train'], dec[dec.split == 'test']
    # pick the |margin| cutoff on train that best separates flips, evaluate accuracy on test
    best = max(np.linspace(0, 2, 41),
               key=lambda c: ((tr.abs_margin < c) == tr.instrument_flip_llm).mean())
    acc = ((te.abs_margin < best) == te.instrument_flip_llm).mean()
    base = max(te.instrument_flip_llm.mean(), 1 - te.instrument_flip_llm.mean())
    print(f"  cutoff |margin|<{best:.2f} -> test accuracy {acc:.3f}  (majority-class baseline {base:.3f})")
    print("\nSee ../judge/flip_predictors.py for the full question-clustered GEE model.")


if __name__ == '__main__':
    main()
