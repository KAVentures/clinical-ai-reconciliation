"""Draw a stratified (question x opponent) sample for the human cell-D + adjudication study.

Selects ~90 OE-vs-frontier items from the exact-common-support pool, stratified to span:
  * all five axes;
  * instrument flips vs non-flips (rubric winner != / == LLM-pairwise winner);
  * small vs large |rubric margin| (decision-boundary vs decisive);
  * the three frontier opponents;
  * a spread of clinical specialties.

Deterministic (seed 62). Writes ../dataset/human_study_sample.csv (the sampling frame the blinded
rating packets are built from — see HUMAN_STUDY_PROTOCOL.md) and prints the achieved stratum balance.
No API calls; reads out/instrument_disagreement.csv + data/questions.parquet.
"""
import os, csv
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
DATA = os.path.join(HERE, '..', 'data')
DATASET = os.path.join(HERE, '..', 'dataset')
OE = 'openevidence'
FRONTIER = ['gpt-5.5', 'claude-opus-4-8', 'gemini-3.1-pro']
TARGET = 90
SEED = 62


def main():
    os.makedirs(DATASET, exist_ok=True)
    df = pd.read_csv(os.path.join(OUT, 'instrument_disagreement.csv'))
    # decidable items only (both instruments pick a side) -> flip is defined
    df = df[df.rubric_winner.isin([OE] + FRONTIER) & df.pw_llm_winner.isin([OE] + FRONTIER)].copy()
    spec = pd.read_parquet(os.path.join(DATA, 'questions.parquet')).set_index('question_id')['specialty']
    df['specialty'] = df.question_id.map(spec)
    df['abs_margin'] = df.rubric_margin.abs()
    df['flip'] = df.instrument_flip_llm.astype(bool)
    df['dispersion'] = pd.to_numeric(df.rubric_judge_diff_sd, errors='coerce')
    # margin TERTILES (the raw margin is concentrated near the 0.25 quarter-point grid, so a
    # median split is degenerate; tertiles give a usable weak/mid/strong spread)
    df['margin_bin'] = pd.qcut(df.abs_margin, 3, labels=['weak', 'mid', 'strong'], duplicates='drop')

    rng = np.random.default_rng(SEED)
    # 6 strata: flip x margin tertile. flip=strong -> strong reversals; flip=weak -> weak-margin
    # reversals; non-flip -> agreement controls. Take up to TARGET/6 per cell.
    per = max(1, TARGET // 6)
    picks = []
    for f in (True, False):
        for m in ['weak', 'mid', 'strong']:
            sub = df[(df.flip == f) & (df.margin_bin == m)]
            if len(sub) == 0:
                continue
            take = min(per, len(sub))
            picks.append(sub.iloc[rng.choice(len(sub), take, replace=False)])
    sample = pd.concat(picks).drop_duplicates(subset=['question_id', 'axis', 'opponent'])
    # mark dispersion split for the adjudication arm (high/low judge disagreement)
    sample['dispersion_bin'] = np.where(sample.dispersion.fillna(0) >= sample.dispersion.median(),
                                        'high_disp', 'low_disp')

    cols = ['question_id', 'specialty', 'axis', 'opponent', 'flip', 'margin_bin', 'dispersion_bin',
            'rubric_margin', 'rubric_winner', 'pw_llm_winner', 'pw_llm_agreement']
    sample[cols].to_csv(os.path.join(DATASET, 'human_study_sample.csv'), index=False, quoting=csv.QUOTE_MINIMAL)

    print(f"selected {len(sample)} (question x opponent) items across {sample.question_id.nunique()} questions\n")
    print("flip x margin:", {f"{k[0]}|{k[1]}": v for k, v in sample.groupby(['flip', 'margin_bin'], observed=True).size().items()})
    print("by axis:      ", sample.axis.value_counts().to_dict())
    print("by opponent:  ", sample.opponent.value_counts().to_dict())
    print("dispersion:   ", sample.dispersion_bin.value_counts().to_dict())
    print("specialties covered:", sample.specialty.nunique(), "of", spec.nunique())
    print("\nwrote ../dataset/human_study_sample.csv")


if __name__ == '__main__':
    main()
