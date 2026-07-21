"""Assemble the dual-instrument clinical-AI evaluation dataset from repository outputs.

Produces tidy tables under dataset/tables/ plus a group-wise (question-level) train/dev/test split, so the
package can be released (e.g. Zenodo) and used to study evaluation-instrument sensitivity on IDENTICAL model
outputs. No API calls; reads ../judge/out/{grades,pairwise}.jsonl, ../judge/out/instrument_disagreement.csv,
and ../data/{questions,answers,ratings}.parquet.

Tables:
  questions.csv       question_id, specialty, question_text
  answers.csv         question_id, provider, char_len, has_citation   (verbatim text stays in data/*.parquet)
  human_pairwise.csv  question_id, opponent, axis, n_votes, mean_vote  (qa_text_only; +1 OE .. -1 opp)
  llm_pairwise.csv    question_id, opponent, judge, axis, vote
  llm_rubric.csv      question_id, provider, judge, axis, score_1to4
  items.csv           one row per (question_id, axis, opponent): rubric & pairwise winners/margins,
                      judge counts, dispersion, instrument_flip  (the benchmark table)
  splits.csv          question_id, split  (group split; no question leaks across splits)
"""
import os, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'judge', 'out')
DATA = os.path.join(HERE, '..', 'data')
TABLES = os.path.join(HERE, 'tables')
OE = 'openevidence'
FRONTIER = ['gpt-5.5', 'claude-opus-4-8', 'gemini-3.1-pro']
AXES = ['accuracy', 'clinical_utility', 'source_quality', 'completeness', 'verifiability']
import re
_CIT = re.compile(r'\[[0-9]+\]|\]\(https?://|\bdoi\b|PMID|https?://', re.I)


def _jsonl(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def main():
    os.makedirs(TABLES, exist_ok=True)
    q = pd.read_parquet(os.path.join(DATA, 'questions.parquet'))
    a = pd.read_parquet(os.path.join(DATA, 'answers.parquet'))
    r = pd.read_parquet(os.path.join(DATA, 'ratings.parquet'))

    # graded question universe (the 150 with LLM ratings)
    graded = sorted({row['question_id'] for row in _jsonl(os.path.join(OUT, 'grades.jsonl'))})

    # questions
    q[q.question_id.isin(graded)].to_csv(os.path.join(TABLES, 'questions.csv'), index=False)

    # answers (metadata; verbatim text remains in data/answers.parquet, CC BY 4.0)
    ans = a[a.question_id.isin(graded)].copy()
    ans['char_len'] = ans.answer_markdown.str.len()
    ans['has_citation'] = ans.answer_markdown.map(lambda s: int(bool(_CIT.search(str(s)))))
    ans.rename(columns={'provider_key': 'provider'})[['question_id', 'provider', 'char_len', 'has_citation']] \
        .to_csv(os.path.join(TABLES, 'answers.csv'), index=False)

    # llm_rubric (long)
    rows = []
    for x in _jsonl(os.path.join(OUT, 'grades.jsonl')):
        if x.get('scores'):
            for ax in AXES:
                if ax in x['scores']:
                    rows.append((x['question_id'], x['provider_key'], x['judge'], ax, x['scores'][ax]))
    pd.DataFrame(rows, columns=['question_id', 'provider', 'judge', 'axis', 'score_1to4']) \
        .to_csv(os.path.join(TABLES, 'llm_rubric.csv'), index=False)

    # llm_pairwise (long)
    rows = []
    for x in _jsonl(os.path.join(OUT, 'pairwise.jsonl')):
        res = x.get('oe_result')
        if res:
            for ax in AXES:
                if ax in res:
                    rows.append((x['question_id'], x['opponent'], x['judge'], ax,
                                 1 if res[ax] == 'oe' else (-1 if res[ax] == 'opp' else 0)))
    pd.DataFrame(rows, columns=['question_id', 'opponent', 'judge', 'axis', 'vote']) \
        .to_csv(os.path.join(TABLES, 'llm_pairwise.csv'), index=False)

    # human_pairwise (qa_text_only, aggregated per q x opponent x axis)
    pref = {'strongly_a': 1, 'slightly_a': 1, 'strongly_b': -1, 'slightly_b': -1, 'tie': 0}
    hrows = []
    rt = r[(r.render_mode == 'qa_text_only') & (r.axis.isin(AXES))]
    for _, x in rt.iterrows():
        if x.slot_a_provider != OE and x.slot_b_provider != OE:
            continue
        p = pref.get(x.choice)
        if p is None:
            continue
        opp = x.slot_b_provider if x.slot_a_provider == OE else x.slot_a_provider
        if opp not in FRONTIER:
            continue
        o = 0 if p == 0 else (1 if (x.slot_a_provider if p == 1 else x.slot_b_provider) == OE else -1)
        hrows.append((x.question_id, opp, x.axis, o))
    hp = pd.DataFrame(hrows, columns=['question_id', 'opponent', 'axis', 'vote'])
    hp.groupby(['question_id', 'opponent', 'axis']).vote.agg(['size', 'mean']).reset_index() \
        .rename(columns={'size': 'n_votes', 'mean': 'mean_vote'}) \
        .to_csv(os.path.join(TABLES, 'human_pairwise.csv'), index=False)

    # items = the benchmark table (per question x axis x opponent)
    items = pd.read_csv(os.path.join(OUT, 'instrument_disagreement.csv'))
    items = items.merge(q[['question_id', 'specialty']], on='question_id', how='left')
    items.to_csv(os.path.join(TABLES, 'items.csv'), index=False)

    # group split by question (no leakage): deterministic by sorted question index
    qids = sorted(graded)
    split = {qid: ('test' if i % 5 == 0 else 'dev' if i % 5 == 1 else 'train') for i, qid in enumerate(qids)}
    pd.DataFrame({'question_id': qids, 'split': [split[x] for x in qids]}) \
        .to_csv(os.path.join(TABLES, 'splits.csv'), index=False)

    counts = pd.Series(list(split.values())).value_counts().to_dict()
    print("wrote dataset/tables/: questions, answers, llm_rubric, llm_pairwise, human_pairwise, items, splits")
    print(f"  questions={len(qids)}  items={len(items)}  split(question-level)={counts}")


if __name__ == '__main__':
    main()
