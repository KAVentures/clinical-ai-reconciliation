"""Common-estimand analysis for the physician 2x2 (correct for these instruments).

Rubric physicians rate ONE answer; no single rubric physician yields an OE-minus-opponent contrast. So the
two arms cannot share a rater-level signed-difference mixed model. Instead every cell is mapped to the SAME
OE-superiority scale in [0,1], per (pair, axis):

  * PAIRWISE cell (A' human, B LLM): OE win-score = mean over raters of {OE preferred:1, tie:0.5, opp:1->0}.
  * RUBRIC cell (D human, C LLM): probability of superiority
        PoS = P(S_OE > S_opp) + 0.5 * P(S_OE = S_opp)
    computed from the INDEPENDENT OE-answer and opponent-answer score sets for that (pair, axis) -- the
    common-language effect size (equiv. normalised Mann-Whitney U). For humans these are different reviewers
    (independent by design); for the LLM the OE and opponent score sets across judges are used the same way.

Then:  format effect (human) = D - A' ;  format effect (LLM) = C - B ;
       rater effect (pairwise) = A' - B ;  rater effect (rubric) = D - C ;
       rater x format interaction (difference-in-differences) = (D - A') - (C - B).
Uncertainty: resample CLINICAL QUESTIONS with replacement (cluster bootstrap), recompute everything.

The 1-4 ordinal rubric scores may additionally be analysed with a rubric-only ordinal mixed model as a
SECONDARY analysis; that is not the common factorial outcome.

This module ships the pure estimand + the LLM cells (B, C) computed on the physician-sample pairs from repo
data. Human cells A' and D plug in via load_human_returns() once packets come back. No API calls.
"""
import os, json
from collections import defaultdict
import numpy as np
import pandas as pd
import build_physician_study as B

OUTJ = B.OUTJ
AXES = B.AXES
OE = B.OE


# ---------------------------------------------------------------- pure estimands
def win_score(votes):
    """Mean OE-superiority for pairwise votes. votes: iterable of {'oe','tie','opp'} or {1,0,-1}."""
    m = {'oe': 1.0, 'tie': 0.5, 'opp': 0.0, 1: 1.0, 0: 0.5, -1: 0.0}
    v = [m[x] for x in votes if x in m]
    return float(np.mean(v)) if v else np.nan


def prob_superiority(oe_scores, opp_scores):
    """P(S_OE > S_opp) + 0.5 P(S_OE = S_opp) over the independent score sets (common-language effect)."""
    oe = np.asarray(oe_scores, float); op = np.asarray(opp_scores, float)
    if oe.size == 0 or op.size == 0:
        return np.nan
    gt = np.sum(oe[:, None] > op[None, :]); eq = np.sum(oe[:, None] == op[None, :])
    return float((gt + 0.5 * eq) / (oe.size * op.size))


# ---------------------------------------------------------------- LLM cells from repo data
def _sample_pairs():
    return {(r.question_id, r.opponent) for r in B.select_pairs().itertuples()}


def llm_pairwise_cell(pairs):
    """cell B: {(qid,opp,axis): win_score} from out/pairwise.jsonl (LLM votes)."""
    votes = defaultdict(list)
    for line in open(os.path.join(OUTJ, 'pairwise.jsonl')):
        r = json.loads(line); res = r.get('oe_result')
        if not res or (r['question_id'], r['opponent']) not in pairs:
            continue
        for ax in AXES:
            if ax in res:
                votes[(r['question_id'], r['opponent'], ax)].append(res[ax])
    return {k: win_score(v) for k, v in votes.items()}


def llm_rubric_cell(pairs, grades_file='grades.jsonl'):
    """cell C: {(qid,opp,axis): PoS} from OE vs opponent LLM rubric score sets (out/<grades_file>).
    Use grades_expanded.jsonl once the identical-anchor regrade is run."""
    sc = defaultdict(lambda: defaultdict(list))   # (qid, axis) -> provider -> [scores]
    path = os.path.join(OUTJ, grades_file)
    if not os.path.exists(path):
        return {}
    for line in open(path):
        r = json.loads(line); s = r.get('scores')
        if not s:
            continue
        for ax in AXES:
            if ax in s:
                sc[(r['question_id'], ax)][r['provider_key']].append(s[ax])
    out = {}
    for (qid, opp) in pairs:
        for ax in AXES:
            d = sc.get((qid, ax), {})
            out[(qid, opp, ax)] = prob_superiority(d.get(OE, []), d.get(opp, []))
    return out


# ---------------------------------------------------------------- human cells (plug in on return)
def load_human_returns(rubric_long, pairwise_long):
    """Build human cells A' and D from returned, un-blinded long-format ratings.
      rubric_long : DataFrame [question_id, opponent, axis, provider ('oe'/opponent), score_1to4]
      pairwise_long: DataFrame [question_id, opponent, axis, oe_vote ('oe'/'tie'/'opp')]
    Returns (A_prime, D) dicts keyed (qid, opp, axis)."""
    A = defaultdict(list)
    for r in pairwise_long.itertuples():
        A[(r.question_id, r.opponent, r.axis)].append(r.oe_vote)
    A = {k: win_score(v) for k, v in A.items()}
    oe_s = defaultdict(list); op_s = defaultdict(list)
    for r in rubric_long.itertuples():
        (oe_s if r.provider == 'oe' else op_s)[(r.question_id, r.opponent, r.axis)].append(r.score_1to4)
    D = {k: prob_superiority(oe_s.get(k, []), op_s.get(k, [])) for k in set(oe_s) | set(op_s)}
    return A, D


# ---------------------------------------------------------------- decomposition + question-cluster bootstrap
def decompose(cells, nboot=2000, seed=62):
    """cells: dict arm-> {(qid,opp,axis): value in [0,1]}. Returns per-axis format/rater/DiD effects with
    clinical-question cluster-bootstrap CIs. Arms present drive which effects are computable."""
    keys = set().union(*[set(c) for c in cells.values() if c]) if cells else set()
    qids = sorted({k[0] for k in keys})
    rng = np.random.default_rng(seed)

    def mean_over(arm, axis, wq):
        vals, wts = [], []
        for (qid, opp, ax), v in cells.get(arm, {}).items():
            if ax == axis and not np.isnan(v):
                vals.append(v); wts.append(wq.get(qid, 1.0))
        return np.average(vals, weights=wts) if vals else np.nan

    def effects(wq):
        out = {}
        for ax in AXES:
            A, D, Bc, C = (mean_over(a, ax, wq) for a in ('A_prime', 'D', 'B', 'C'))
            out[ax] = {'A_prime': A, 'D': D, 'B': Bc, 'C': C,
                       'format_human': (D - A) if not (np.isnan(D) or np.isnan(A)) else np.nan,
                       'format_llm': (C - Bc) if not (np.isnan(C) or np.isnan(Bc)) else np.nan,
                       'rater_pairwise': (A - Bc) if not (np.isnan(A) or np.isnan(Bc)) else np.nan,
                       'rater_rubric': (D - C) if not (np.isnan(D) or np.isnan(C)) else np.nan}
            fh, fl = out[ax]['format_human'], out[ax]['format_llm']
            out[ax]['interaction_DiD'] = (fh - fl) if not (np.isnan(fh) or np.isnan(fl)) else np.nan
        return out

    point = effects({q: 1.0 for q in qids})
    boot = {ax: defaultdict(list) for ax in AXES}
    for _ in range(nboot):
        idx = rng.integers(0, len(qids), len(qids))
        wq = defaultdict(float)
        for i in idx:
            wq[qids[i]] += 1.0
        e = effects(wq)
        for ax in AXES:
            for k, v in e[ax].items():
                boot[ax][k].append(v)

    def ci(a):
        a = np.asarray(a, float); a = a[~np.isnan(a)]
        return [round(float(np.percentile(a, 2.5)), 3), round(float(np.percentile(a, 97.5)), 3)] if a.size else [np.nan, np.nan]
    return {ax: {k: {'point': round(point[ax][k], 3) if not np.isnan(point[ax][k]) else None,
                     'ci': ci(boot[ax][k])} for k in point[ax]} for ax in AXES}


def main():
    pairs = _sample_pairs()
    cells = {'B': llm_pairwise_cell(pairs), 'C': llm_rubric_cell(pairs)}
    res = decompose(cells)
    print("LLM-only demonstration on the physician-sample pairs (human A'/D plug in on return):")
    print(f"{'axis':16s}{'B(pw)':>8s}{'C(rub)':>8s}{'format_llm C-B':>16s}")
    for ax in AXES:
        r = res[ax]
        print(f"{ax:16s}{str(r['B']['point']):>8s}{str(r['C']['point']):>8s}"
              f"{str(r['format_llm']['point']):>10s} {r['format_llm']['ci']}")
    print("\nFull 2x2 (format_human D-A', rater terms, interaction DiD) computes once A'/D are loaded via "
          "load_human_returns().")


if __name__ == '__main__':
    main()
