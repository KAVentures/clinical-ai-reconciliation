"""Robust decomposition: aggregation-matched, native-scale, common-support (peer-review revision).

Motivation. The panel-mean-then-threshold win-difference used in bootstrap_panel.py amplifies
small native score gaps: on accuracy the four judges' INDIVIDUAL rubric win-differences are
-30.2/-8.1/-6.0/-7.5 (mean -13.0) but panel-mean-then-threshold gives -29.1. So the headline
-29.1 (and the -32.7 instrument component) partly reflects the aggregation rule, not the
instrument. This module reports the instrument effect in aggregation-matched and native-scale
forms, on exact common support, with tie-margin and multiplicity sensitivity.

PRIMARY estimand (format effect with the rater held FIXED):
  For each judge j, on the (question, opponent) pairs where j provides BOTH a rubric grade pair
  (OE, opponent) AND a pairwise vote, threshold that judge's own rubric gap into win/tie/loss and
  pool exactly as the pairwise votes are pooled. C_j and B_j are that judge's rubric and pairwise
  OE-vs-frontier win-differences; Delta_j = C_j - B_j is a within-judge, aggregation-matched format
  effect. instrument = mean_j Delta_j. This holds the RATER fixed (same model does both instruments),
  so it isolates evaluation FORMAT, which is the paper's defensible strong claim.

Inference: question-cluster bootstrap (resample question_ids with replacement). Fixed-judge is
PRIMARY (four purposive judges are a fixed panel, not a random sample); crossed q x judge is
reported as panel-composition SENSITIVITY only. RNG seed and NBOOT match bootstrap_panel.py.

No API calls: reads out/grades.jsonl, out/pairwise.jsonl, data/ratings.parquet, data/answers.parquet.
Writes out/robust_analysis.json. Core estimand helpers are pure and unit-tested
(test_robust_analysis.py).
"""
import os, json, re
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
DATA = os.path.join(HERE, '..', 'data')
AXES = ['accuracy', 'clinical_utility', 'source_quality', 'completeness', 'verifiability']
OE = 'openevidence'
FRONTIER = ['gpt-5.5', 'claude-opus-4-8', 'gemini-3.1-pro']
JUDGES = ['gpt-5.5', 'opus-4.8', 'grok-4.3', 'gemini-3.5-flash']
NBOOT = 2000
SEED = 62


# ----------------------------- pure estimand helpers -----------------------------
def threshold(gap, delta=0.0):
    """Signed win/tie/loss for a score gap with a symmetric dead-zone of half-width delta."""
    if gap > delta:
        return 1
    if gap < -delta:
        return -1
    return 0


def windiff(votes, w=None):
    """100*(wins-losses)/n over signed votes; optional per-vote weights w."""
    v = np.asarray(votes, dtype=float)
    if v.size == 0:
        return np.nan
    w = np.ones_like(v) if w is None else np.asarray(w, dtype=float)
    W = np.sum(w * (v > 0)); L = np.sum(w * (v < 0)); N = np.sum(w)
    return 100 * (W - L) / N if N > 0 else np.nan


def matched_units(rub_ax, pw_ax, judge, opponents=FRONTIER):
    """Per-judge matched (question, opponent) units where the judge has BOTH a rubric OE/opponent
    score pair and a pairwise vote. Returns dict of aligned lists (pure; testable with fixtures).

    rub_ax : {(qid, provider, judge): score}
    pw_ax  : {(qid, opponent, judge): vote in {-1,0,1}}
    """
    qids, opps, oe_s, opp_s, c_vote, b_vote = [], [], [], [], [], []
    seen = {q for (q, p, j) in rub_ax if j == judge}
    for q in sorted(seen):
        oe = rub_ax.get((q, OE, judge))
        if oe is None:
            continue
        for opp in opponents:
            op = rub_ax.get((q, opp, judge))
            b = pw_ax.get((q, opp, judge))
            if op is None or b is None:
                continue
            qids.append(q); opps.append(opp); oe_s.append(oe); opp_s.append(op)
            c_vote.append(threshold(oe - op)); b_vote.append(int(b))
    return {'qid': qids, 'opponent': opps, 'oe_score': oe_s, 'opp_score': opp_s,
            'c_vote': c_vote, 'b_vote': b_vote}


# ----------------------------- loaders -----------------------------
def load_rubric():
    """{axis: {(qid, provider, judge): score}}."""
    R = {ax: {} for ax in AXES}
    for line in open(os.path.join(OUT, 'grades.jsonl')):
        r = json.loads(line)
        sc = r.get('scores')
        if not sc:
            continue
        for ax in AXES:
            if ax in sc and sc[ax] is not None:
                R[ax][(r['question_id'], r['provider_key'], r['judge'])] = float(sc[ax])
    return R


def load_pairwise():
    """{axis: {(qid, opponent, judge): vote}}."""
    P = {ax: {} for ax in AXES}
    for line in open(os.path.join(OUT, 'pairwise.jsonl')):
        r = json.loads(line)
        res = r.get('oe_result')
        if not res:
            continue
        for ax in AXES:
            if ax in res:
                P[ax][(r['question_id'], r['opponent'], r['judge'])] = \
                    1 if res[ax] == 'oe' else (-1 if res[ax] == 'opp' else 0)
    return P


def load_human():
    """{axis: list of (qid, opponent, vote)} from qa_text_only human pairwise."""
    r = pd.read_parquet(os.path.join(DATA, 'ratings.parquet'))
    r = r[r.render_mode == 'qa_text_only']
    pref = {'strongly_a': 1, 'slightly_a': 1, 'strongly_b': -1, 'slightly_b': -1, 'tie': 0}
    H = {ax: [] for ax in AXES}
    for _, x in r.iterrows():
        if x.axis not in AXES:
            continue
        if x.slot_a_provider != OE and x.slot_b_provider != OE:
            continue
        pr = pref.get(x.choice)
        if pr is None:
            continue
        opp = x.slot_b_provider if x.slot_a_provider == OE else x.slot_a_provider
        if opp not in FRONTIER:
            continue
        if pr == 0:
            o = 0
        else:
            winner = x.slot_a_provider if pr == 1 else x.slot_b_provider
            o = 1 if winner == OE else -1
        H[x.axis].append((x.question_id, opp, o))
    return H


def oe_citation_qids():
    """Question ids whose OE answer_markdown carries citation/link markers."""
    a = pd.read_parquet(os.path.join(DATA, 'answers.parquet'))
    a = a[a.provider_key == OE]
    pat = re.compile(r'\[[0-9]+\]|\]\(https?://|\bdoi\b|PMID|https?://', re.I)
    return {row.question_id for _, row in a.iterrows() if pat.search(str(row.answer_markdown))}


# ----------------------------- bootstrap scaffolding -----------------------------
def qindex(*dicts_lists):
    qids = set()
    for d in dicts_lists:
        if isinstance(d, dict):
            for k in d:
                qids.add(k[0])
        else:
            for t in d:
                qids.add(t[0])
    return {q: i for i, q in enumerate(sorted(qids))}


def ci(a):
    a = np.asarray(a, dtype=float); a = a[~np.isnan(a)]
    if a.size == 0:
        return [np.nan, np.nan]
    return [round(float(np.percentile(a, 2.5)), 1), round(float(np.percentile(a, 97.5)), 1)]


def two_sided_p(boot, null=0.0):
    """Bootstrap two-sided p: 2*min(P(stat<=null), P(stat>=null)), floored at 1/NBOOT."""
    b = np.asarray(boot, dtype=float); b = b[~np.isnan(b)]
    if b.size == 0:
        return np.nan
    p_lo = np.mean(b <= null); p_hi = np.mean(b >= null)
    return float(max(min(2 * min(p_lo, p_hi), 1.0), 1.0 / len(b)))


def holm(pvals):
    """Holm-Bonferroni adjusted p-values, returned in original order."""
    items = sorted(enumerate(pvals), key=lambda t: (np.inf if np.isnan(t[1]) else t[1]))
    m = len(items); adj = [None] * m; running = 0.0
    for rank, (idx, p) in enumerate(items):
        val = min(1.0, (m - rank) * p) if not np.isnan(p) else np.nan
        running = max(running, 0 if np.isnan(val) else val)
        adj[idx] = round(running if not np.isnan(val) else np.nan, 4)
    return adj


# ----------------------------- primary analyses -----------------------------
def analyze():
    R, P, H = load_rubric(), load_pairwise(), load_human()
    qi = qindex(R['accuracy'], P['accuracy'], H['accuracy'])
    nQ = len(qi)
    rng = np.random.default_rng(SEED)

    # ---- build per-judge matched arrays (aggregation-matched same-judge B-C) ----
    # arrays[ax][judge] = dict of np arrays: qidx, oppidx, c_vote, b_vote, native_gap
    oppidx = {o: k for k, o in enumerate(FRONTIER)}
    arrays = {ax: {} for ax in AXES}
    for ax in AXES:
        for j in JUDGES:
            mu = matched_units(R[ax], P[ax], j)
            arrays[ax][j] = {
                'qidx': np.array([qi[q] for q in mu['qid']], dtype=int),
                'oppidx': np.array([oppidx[o] for o in mu['opponent']], dtype=int),
                'c_vote': np.array(mu['c_vote'], dtype=float),
                'b_vote': np.array(mu['b_vote'], dtype=float),
                'native_gap': np.array([a - b for a, b in zip(mu['oe_score'], mu['opp_score'])], dtype=float),
            }

    def wd_from(arr, key, qw, mask=None):
        idx = arr['qidx']; v = arr[key]; w = qw[idx]
        if mask is not None:
            w = w * mask
        return windiff(v, w)

    def native_from(arr, qw, mask=None):
        idx = arr['qidx']; g = arr['native_gap']; w = qw[idx]
        if mask is not None:
            w = w * mask
        return float(np.sum(w * g) / np.sum(w)) if np.sum(w) > 0 else np.nan

    ones = np.ones(nQ)

    # point estimates
    def instrument_point(ax, qw):
        deltas = []
        for j in JUDGES:
            c = wd_from(arrays[ax][j], 'c_vote', qw); b = wd_from(arrays[ax][j], 'b_vote', qw)
            deltas.append(c - b)
        return deltas  # per-judge Delta_j

    primary = {}
    for ax in AXES:
        d = instrument_point(ax, ones)
        primary[ax] = {'per_judge_delta': {j: round(v, 1) for j, v in zip(JUDGES, d)},
                       'instrument_mean': round(float(np.mean(d)), 1)}

    # native score gaps (1-4 scale), pooled over judges+units
    native = {}
    for ax in AXES:
        gaps = np.concatenate([arrays[ax][j]['native_gap'] for j in JUDGES])
        qidxs = np.concatenate([arrays[ax][j]['qidx'] for j in JUDGES])
        native[ax] = {'mean_gap_1to4': round(float(np.mean(gaps)), 3), '_qidxs': qidxs, '_gaps': gaps}

    # ---- bootstrap (fixed-judge primary + crossed sensitivity) ----
    boot_instr_fixed = {ax: [] for ax in AXES}
    boot_instr_crossed = {ax: [] for ax in AXES}
    boot_delta_j = {ax: {j: [] for j in JUDGES} for ax in AXES}
    boot_native = {ax: [] for ax in AXES}
    for _ in range(NBOOT):
        qcnt = np.bincount(rng.integers(0, nQ, nQ), minlength=nQ).astype(float)
        jcnt = np.bincount(rng.integers(0, len(JUDGES), len(JUDGES)), minlength=len(JUDGES)).astype(float)
        for ax in AXES:
            deltas = []
            for j in JUDGES:
                c = wd_from(arrays[ax][j], 'c_vote', qcnt); b = wd_from(arrays[ax][j], 'b_vote', qcnt)
                deltas.append(c - b)
                boot_delta_j[ax][j].append(c - b)
            deltas = np.array(deltas)
            boot_instr_fixed[ax].append(float(np.mean(deltas)))
            wj = jcnt / jcnt.sum()
            boot_instr_crossed[ax].append(float(np.nansum(deltas * wj)))
            # native gap bootstrap (question-weighted)
            g = native[ax]['_gaps']; idx = native[ax]['_qidxs']; w = qcnt[idx]
            boot_native[ax].append(float(np.sum(w * g) / np.sum(w)) if np.sum(w) > 0 else np.nan)

    # assemble primary + multiplicity
    p_raw = []
    for ax in AXES:
        primary[ax]['instrument_ci_fixed'] = ci(boot_instr_fixed[ax])
        primary[ax]['instrument_ci_crossed'] = ci(boot_instr_crossed[ax])
        primary[ax]['per_judge_delta_ci'] = {j: ci(boot_delta_j[ax][j]) for j in JUDGES}
        primary[ax]['sign_consistent_all_judges'] = bool(
            all(v < 0 for v in primary[ax]['per_judge_delta'].values()) or
            all(v > 0 for v in primary[ax]['per_judge_delta'].values()))
        p = two_sided_p(boot_instr_fixed[ax]); primary[ax]['instrument_p_raw'] = round(p, 4)
        p_raw.append(p)
        native[ax]['gap_ci'] = ci(boot_native[ax])
        native[ax]['gap_p_raw'] = round(two_sided_p(boot_native[ax]), 4)
        del native[ax]['_qidxs'], native[ax]['_gaps']

    p_holm = holm(p_raw)
    # max-|T| simultaneous intervals for the instrument component
    T = {ax: np.array(boot_instr_fixed[ax]) for ax in AXES}
    centers = {ax: primary[ax]['instrument_mean'] for ax in AXES}
    sds = {ax: (np.nanstd(T[ax]) or np.nan) for ax in AXES}
    maxabs = []
    for k in range(NBOOT):
        vals = [abs((T[ax][k] - centers[ax]) / sds[ax]) for ax in AXES if sds[ax] and not np.isnan(sds[ax])]
        if vals:
            maxabs.append(max(vals))
    crit = float(np.percentile(maxabs, 95)) if maxabs else np.nan
    for i, ax in enumerate(AXES):
        primary[ax]['instrument_p_holm'] = p_holm[i]
        primary[ax]['instrument_simultaneous_ci'] = [
            round(centers[ax] - crit * sds[ax], 1), round(centers[ax] + crit * sds[ax], 1)] \
            if sds[ax] and not np.isnan(sds[ax]) else [np.nan, np.nan]

    # ---- tie-margin sensitivity (panel-mean-then-threshold with dead-zone) ----
    tie = {ax: {} for ax in AXES}
    for ax in AXES:
        # panel mean gap per (q, opp)
        gaps = {}
        for j in JUDGES:
            a = arrays[ax][j]
            for k in range(len(a['qidx'])):
                key = (a['qidx'][k], a['oppidx'][k])
                gaps.setdefault(key, []).append(a['native_gap'][k])
        panel_gap = {k: float(np.mean(v)) for k, v in gaps.items()}
        for delta in [0.0, 0.125, 0.25, 0.5]:
            votes = [threshold(g, delta) for g in panel_gap.values()]
            tie[ax][f'panel_thresh_delta_{delta}'] = round(windiff(votes), 1)
        med_gap = {k: float(np.median(v)) for k, v in gaps.items()}
        tie[ax]['panel_MEDIAN_thresh'] = round(windiff([threshold(g) for g in med_gap.values()]), 1)
        tie[ax]['individual_mean_delta_note'] = primary[ax]['instrument_mean']  # for cross-reference

    # ---- opponent-specific (OE vs each frontier separately) ----
    opp_spec = {ax: {} for ax in AXES}
    for ax in AXES:
        for oi, opp in enumerate(FRONTIER):
            deltas = []
            for j in JUDGES:
                a = arrays[ax][j]; m = (a['oppidx'] == oi)
                c = windiff(a['c_vote'][m]); b = windiff(a['b_vote'][m])
                deltas.append(c - b)
            opp_spec[ax][opp] = {'instrument_mean': round(float(np.nanmean(deltas)), 1),
                                 'C_indiv': round(float(np.nanmean(
                                     [windiff(arrays[ax][j]['c_vote'][arrays[ax][j]['oppidx'] == oi]) for j in JUDGES])), 1),
                                 'B': round(float(np.nanmean(
                                     [windiff(arrays[ax][j]['b_vote'][arrays[ax][j]['oppidx'] == oi]) for j in JUDGES])), 1)}

    # ---- exact common-support A-B-C (only where a human vote exists) ----
    common = common_support_abc(R, P, H, qi, rng)

    # ---- rendering verification + citation-free mitigation ----
    cited = oe_citation_qids()
    cited_idx = {qi[q] for q in cited if q in qi}
    render = {'oe_answers_with_citations_frac': round(len(cited) / len(load_answers_oe()), 3),
              'human_render_mode': 'qa_text_only', 'llm_render': 'answer_markdown (raw, may include citations)',
              'note': 'A used qa_text_only; B/C judged answer_markdown -> A vs B/C not presentation-matched.'}
    # recompute same-judge instrument on OE citation-FREE questions only
    render['instrument_citationfree_subset'] = {}
    for ax in AXES:
        deltas = []
        for j in JUDGES:
            a = arrays[ax][j]; keep = np.array([qx not in cited_idx for qx in a['qidx']])
            c = windiff(a['c_vote'][keep]); b = windiff(a['b_vote'][keep])
            deltas.append(c - b)
        render['instrument_citationfree_subset'][ax] = round(float(np.nanmean(deltas)), 1)

    out = {'nboot': NBOOT, 'seed': SEED, 'n_questions': nQ, 'judges': JUDGES,
           'estimand': 'instrument = mean_j (C_j - B_j), aggregation-matched same-judge, rater fixed',
           'primary_instrument': primary, 'native_score_gaps': native,
           'tie_margin_sensitivity': tie, 'opponent_specific': opp_spec,
           'common_support_abc': common, 'rendering': render,
           'panel_threshold_reference': {ax: -0.0 for ax in AXES}}
    # attach the old panel-level instrument for contrast if available
    pb = os.path.join(OUT, 'panel_bootstrap.json')
    if os.path.exists(pb):
        d = json.load(open(pb))
        out['panel_threshold_reference'] = {ax: d['point'][ax]['instrument'] for ax in AXES}
    json.dump(out, open(os.path.join(OUT, 'robust_analysis.json'), 'w'), indent=2)
    return out


def load_answers_oe():
    a = pd.read_parquet(os.path.join(DATA, 'answers.parquet'))
    return a[a.provider_key == OE]


def common_support_abc(R, P, H, qi, rng):
    """A, B, C, rater, instrument on the EXACT (question, opponent, axis) support where a human
    text-only vote exists. A/B pooled at vote level; C both individual and panel-threshold."""
    res = {}
    for ax in AXES:
        # human support keyed by (qid, opp); keep triples with >=1 human vote
        hum = {}
        for q, opp, o in H[ax]:
            hum.setdefault((q, opp), []).append(o)
        support = [k for k in hum if k[0] in qi]
        if not support:
            res[ax] = {'n_support': 0}
            continue
        # gather aligned observations on support
        A_votes, A_q = [], []
        B_votes, B_q = [], []
        Cind_votes, Cind_q = [], []
        Cpanel_votes, Cpanel_q = [], []
        for (q, opp) in support:
            for o in hum[(q, opp)]:
                A_votes.append(o); A_q.append(qi[q])
            for j in JUDGES:
                b = P[ax].get((q, opp, j))
                if b is not None:
                    B_votes.append(b); B_q.append(qi[q])
                oe = R[ax].get((q, OE, j)); op = R[ax].get((q, opp, j))
                if oe is not None and op is not None:
                    Cind_votes.append(threshold(oe - op)); Cind_q.append(qi[q])
            # panel mean gap on support
            oe_m = [R[ax].get((q, OE, j)) for j in JUDGES if R[ax].get((q, OE, j)) is not None]
            op_m = [R[ax].get((q, opp, j)) for j in JUDGES if R[ax].get((q, opp, j)) is not None]
            if oe_m and op_m:
                Cpanel_votes.append(threshold(np.mean(oe_m) - np.mean(op_m))); Cpanel_q.append(qi[q])
        A_q, B_q, Cind_q, Cpanel_q = map(lambda x: np.array(x, int), (A_q, B_q, Cind_q, Cpanel_q))
        A_v, B_v, Ci_v, Cp_v = map(lambda x: np.array(x, float), (A_votes, B_votes, Cind_votes, Cpanel_votes))
        nQ = len(qi)
        A = windiff(A_v); B = windiff(B_v); Ci = windiff(Ci_v); Cp = windiff(Cp_v)
        # crossed-ish bootstrap: resample questions; (judges fixed here for simplicity/primary)
        bootA, bootB, bootCi, bootCp, bootRater, bootInstr = [], [], [], [], [], []
        for _ in range(NBOOT):
            qcnt = np.bincount(rng.integers(0, nQ, nQ), minlength=nQ).astype(float)
            a = windiff(A_v, qcnt[A_q]); b = windiff(B_v, qcnt[B_q])
            ci_ = windiff(Ci_v, qcnt[Cind_q]); cp = windiff(Cp_v, qcnt[Cpanel_q])
            bootA.append(a); bootB.append(b); bootCi.append(ci_); bootCp.append(cp)
            bootRater.append(b - a); bootInstr.append(ci_ - b)
        res[ax] = {
            'n_support_qopp': len(support), 'n_human_votes': len(A_votes),
            'A_human': round(A, 1), 'A_ci': ci(bootA),
            'B_llm_pairwise': round(B, 1), 'B_ci': ci(bootB),
            'C_individual': round(Ci, 1), 'C_individual_ci': ci(bootCi),
            'C_panel_threshold': round(Cp, 1), 'C_panel_ci': ci(bootCp),
            'rater_B_minus_A': round(B - A, 1), 'rater_ci': ci(bootRater),
            'instrument_Cind_minus_B': round(Ci - B, 1), 'instrument_ci': ci(bootInstr),
        }
    return res


def main():
    out = analyze()
    P = out['primary_instrument']
    print(f"n_questions={out['n_questions']}  nboot={out['nboot']}  (fixed-judge PRIMARY)\n")
    print("=== PRIMARY: aggregation-matched same-judge instrument = mean_j(C_j - B_j) ===")
    print(f"{'axis':16s}{'instr':>7s}{'fixed CI':>16s}{'p_holm':>8s}{'sign-cons':>10s}{'[panel ref]':>13s}")
    for ax in AXES:
        p = P[ax]; ref = out['panel_threshold_reference'][ax]
        print(f"{ax:16s}{p['instrument_mean']:>+7.1f}{str(p['instrument_ci_fixed']):>16s}"
              f"{str(p['instrument_p_holm']):>8s}{str(p['sign_consistent_all_judges']):>10s}{ref:>+13.1f}")
    print("\n=== native rubric score gap (OE - opponent, 1-4 scale) ===")
    for ax in AXES:
        n = out['native_score_gaps'][ax]
        print(f"{ax:16s}{n['mean_gap_1to4']:>+7.3f}  CI {n['gap_ci']}")
    print("\n=== exact common-support A -> B -> C (where human vote exists) ===")
    for ax in AXES:
        c = out['common_support_abc'][ax]
        if c.get('n_support_qopp'):
            print(f"{ax:16s} A={c['A_human']:+6.1f}  B={c['B_llm_pairwise']:+6.1f}  "
                  f"Cind={c['C_individual']:+6.1f}  rater={c['rater_B_minus_A']:+6.1f}{str(c['rater_ci']):>16s}"
                  f"  instr={c['instrument_Cind_minus_B']:+6.1f}{str(c['instrument_ci']):>16s}")
    print("\n=== rendering: instrument on OE citation-FREE subset ===")
    print(f"  OE answers with citations: {out['rendering']['oe_answers_with_citations_frac']:.1%}")
    for ax in AXES:
        print(f"  {ax:16s} citation-free instrument = {out['rendering']['instrument_citationfree_subset'][ax]:+.1f}"
              f"  (full = {P[ax]['instrument_mean']:+.1f})")
    print("\nwrote out/robust_analysis.json")


if __name__ == '__main__':
    main()
