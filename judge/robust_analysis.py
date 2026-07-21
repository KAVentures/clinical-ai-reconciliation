"""Robust decomposition: aggregation-matched, native-scale, EXACT common-support (peer-review rev 2).

Motivation. The panel-mean-then-threshold win-difference used in bootstrap_panel.py amplifies small
native score gaps: on accuracy the four judges' INDIVIDUAL rubric win-differences are
-30.2/-8.1/-6.0/-7.5 (mean -13.0) but panel-mean-then-threshold gives -29.1. So the headline -29.1
(and the -32.7 instrument component) partly reflects the aggregation rule, not the format. This module
reports the format effect in aggregation-matched and native-scale forms, on EXACT common support, with
tie-margin and multiplicity sensitivity.

PRIMARY estimand (format effect with the rater held FIXED):
  For each judge j, on the (question, opponent) pairs where j provides BOTH a rubric grade pair
  (OE, opponent) AND a pairwise vote, threshold that judge's own rubric gap into win/tie/loss and pool
  exactly as the pairwise votes are pooled. C_j and B_j are that judge's rubric and pairwise
  OE-vs-frontier win-differences; Delta_j = C_j - B_j is a within-judge, aggregation-matched format
  effect. instrument = mean_j Delta_j. Holds the RATER fixed (same model does both formats), isolating
  evaluation FORMAT -- the paper's defensible strong claim.

Bootstrap universe (rev 2 fix): every analysis resamples ONLY the question clusters that actually carry
its matched observations (was: the union of rubric/pairwise/human question ids, which pulled in ~391
human-only questions outside the 150 LLM sample and mis-sized every CI). Question-cluster bootstrap;
fixed-judge PRIMARY (four purposive judges are a fixed panel), crossed q x judge as SENSITIVITY.

EXACT common-support A/B/C (rev 2 fix): the previous version's `support = [k for k in hum if k[0] in qi]`
was vacuous (qi already contained every human question), so cell A collapsed to full-bank human values.
Now the support is the true intersection at (question, opponent): a human vote AND all four pairwise
votes AND all four OE-rubric AND all four opponent-rubric scores. A, B, C are computed on identical keys.

No API calls. Core estimand helpers are pure and unit-tested (test_robust_analysis.py).
"""
import os, json
from collections import Counter
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


def windiff_units(units, key, weight):
    """Weighted win-difference over a list of unit dicts, each with a 'qid' and a signed vote at `key`.
    weight maps qid -> multiplicity (default 1). Units whose qid has zero weight drop out."""
    W = L = N = 0.0
    for u in units:
        wt = weight.get(u['qid'], 1.0) if weight is not None else 1.0
        if wt == 0:
            continue
        v = u[key]; N += wt
        if v > 0:
            W += wt
        elif v < 0:
            L += wt
    return 100 * (W - L) / N if N > 0 else np.nan


def matched_units(rub_ax, pw_ax, judge, opponents=FRONTIER):
    """Per-judge matched (question, opponent) units where the judge has BOTH a rubric OE/opponent
    score pair and a pairwise vote (pure; testable with fixtures).

    rub_ax : {(qid, provider, judge): score};  pw_ax : {(qid, opponent, judge): vote in {-1,0,1}}
    """
    out = []
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
            out.append({'qid': q, 'opponent': opp, 'oe_score': oe, 'opp_score': op,
                        'c_vote': threshold(oe - op), 'b_vote': int(b), 'native_gap': oe - op})
    return out


def common_support_keys(R_ax, P_ax, H_ax, judges=JUDGES, opponents=FRONTIER, require_full_panel=True):
    """EXACT common support: (qid, opponent) keys with a human vote AND (all four | any) pairwise votes
    AND all four OE-rubric AND all four opponent-rubric scores. Pure; unit-tested.

    R_ax:{(q,prov,j):score}  P_ax:{(q,opp,j):vote}  H_ax:{(q,opp):[human votes]}
    """
    keys = []
    for (q, opp), hv in H_ax.items():
        if not hv or opp not in opponents:
            continue
        pw = [j for j in judges if (q, opp, j) in P_ax]
        roe = [j for j in judges if (q, OE, j) in R_ax]
        rop = [j for j in judges if (q, opp, j) in R_ax]
        ok = (len(pw) == len(judges) and len(roe) == len(judges) and len(rop) == len(judges)) \
            if require_full_panel else (pw and roe and rop)
        if ok:
            keys.append((q, opp))
    return keys


# ----------------------------- loaders -----------------------------
def load_rubric():
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
    """{axis: {(qid, opponent): [votes]}} from qa_text_only human pairwise."""
    r = pd.read_parquet(os.path.join(DATA, 'ratings.parquet'))
    r = r[r.render_mode == 'qa_text_only']
    pref = {'strongly_a': 1, 'slightly_a': 1, 'strongly_b': -1, 'slightly_b': -1, 'tie': 0}
    H = {ax: {} for ax in AXES}
    for _, x in r.iterrows():
        if x.axis not in AXES or (x.slot_a_provider != OE and x.slot_b_provider != OE):
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
        H[x.axis].setdefault((x.question_id, opp), []).append(o)
    return H


def oe_citation_qids():
    import re
    a = pd.read_parquet(os.path.join(DATA, 'answers.parquet'))
    a = a[a.provider_key == OE]
    pat = re.compile(r'\[[0-9]+\]|\]\(https?://|\bdoi\b|PMID|https?://', re.I)
    return {row.question_id for _, row in a.iterrows() if pat.search(str(row.answer_markdown))}


# ----------------------------- bootstrap scaffolding -----------------------------
def boot_weights(cluster_qids, rng):
    """Resample the given question clusters WITH REPLACEMENT; return qid -> multiplicity."""
    n = len(cluster_qids)
    idx = rng.integers(0, n, n)
    cnt = np.bincount(idx, minlength=n)
    return {cluster_qids[k]: float(cnt[k]) for k in range(n)}


def ci(a):
    a = np.asarray(a, dtype=float); a = a[~np.isnan(a)]
    if a.size == 0:
        return [np.nan, np.nan]
    return [round(float(np.percentile(a, 2.5)), 1), round(float(np.percentile(a, 97.5)), 1)]


def two_sided_p(boot, null=0.0):
    b = np.asarray(boot, dtype=float); b = b[~np.isnan(b)]
    if b.size == 0:
        return np.nan
    return float(max(min(2 * min(np.mean(b <= null), np.mean(b >= null)), 1.0), 1.0 / len(b)))


def holm(pvals):
    items = sorted(enumerate(pvals), key=lambda t: (np.inf if np.isnan(t[1]) else t[1]))
    m = len(items); adj = [None] * m; running = 0.0
    for rank, (idx, p) in enumerate(items):
        val = min(1.0, (m - rank) * p) if not np.isnan(p) else np.nan
        running = max(running, 0 if np.isnan(val) else val)
        adj[idx] = round(running if not np.isnan(val) else np.nan, 4)
    return adj


# ----------------------------- primary + native + tie + opponent -----------------------------
def analyze():
    R, P, H = load_rubric(), load_pairwise(), load_human()
    rng = np.random.default_rng(SEED)

    # matched same-judge units per (axis, judge)
    units = {ax: {j: matched_units(R[ax], P[ax], j) for j in JUDGES} for ax in AXES}
    # PRIMARY cluster universe = questions that actually appear in matched same-judge units
    primary_qids = sorted({u['qid'] for ax in AXES for j in JUDGES for u in units[ax][j]})
    cited = oe_citation_qids()

    def instrument_deltas(ax, w):
        return np.array([windiff_units(units[ax][j], 'c_vote', w) - windiff_units(units[ax][j], 'b_vote', w)
                         for j in JUDGES])

    ones = {q: 1.0 for q in primary_qids}
    primary = {}
    for ax in AXES:
        d = instrument_deltas(ax, ones)
        primary[ax] = {'per_judge_delta': {j: round(float(v), 1) for j, v in zip(JUDGES, d)},
                       'instrument_mean': round(float(np.mean(d)), 1)}

    # native rubric gaps (1-4), pooled over judges+units
    native = {}
    for ax in AXES:
        allu = [u for j in JUDGES for u in units[ax][j]]
        native[ax] = {'_units': allu, 'mean_gap_1to4': round(float(np.mean([u['native_gap'] for u in allu])), 3)}

    # bootstrap (fixed-judge primary + crossed sensitivity + native)
    bfix = {ax: [] for ax in AXES}; bcross = {ax: [] for ax in AXES}
    bdelta = {ax: {j: [] for j in JUDGES} for ax in AXES}; bnative = {ax: [] for ax in AXES}
    for _ in range(NBOOT):
        w = boot_weights(primary_qids, rng)
        jcnt = np.bincount(rng.integers(0, len(JUDGES), len(JUDGES)), minlength=len(JUDGES)).astype(float)
        for ax in AXES:
            d = instrument_deltas(ax, w)
            for k, j in enumerate(JUDGES):
                bdelta[ax][j].append(d[k])
            bfix[ax].append(float(np.mean(d)))
            bcross[ax].append(float(np.nansum(d * (jcnt / jcnt.sum()))))
            g = native[ax]['_units']
            num = sum(w.get(u['qid'], 0.0) * u['native_gap'] for u in g)
            den = sum(w.get(u['qid'], 0.0) for u in g)
            bnative[ax].append(num / den if den > 0 else np.nan)

    p_raw = []
    for ax in AXES:
        primary[ax]['instrument_ci_fixed'] = ci(bfix[ax])
        primary[ax]['instrument_ci_crossed'] = ci(bcross[ax])
        primary[ax]['per_judge_delta_ci'] = {j: ci(bdelta[ax][j]) for j in JUDGES}
        primary[ax]['sign_consistent_all_judges'] = bool(
            all(v < 0 for v in primary[ax]['per_judge_delta'].values()) or
            all(v > 0 for v in primary[ax]['per_judge_delta'].values()))
        p = two_sided_p(bfix[ax]); primary[ax]['instrument_p_raw'] = round(p, 4); p_raw.append(p)
        native[ax]['gap_ci'] = ci(bnative[ax]); native[ax]['gap_p_raw'] = round(two_sided_p(bnative[ax]), 4)
        del native[ax]['_units']

    p_holm = holm(p_raw)
    T = {ax: np.array(bfix[ax]) for ax in AXES}
    centers = {ax: primary[ax]['instrument_mean'] for ax in AXES}
    sds = {ax: float(np.nanstd(T[ax])) for ax in AXES}
    maxabs = [max(abs((T[ax][k] - centers[ax]) / sds[ax]) for ax in AXES if sds[ax])
              for k in range(NBOOT)]
    crit = float(np.percentile(maxabs, 95)) if maxabs else np.nan
    for i, ax in enumerate(AXES):
        primary[ax]['instrument_p_holm'] = p_holm[i]
        primary[ax]['instrument_simultaneous_ci'] = (
            [round(centers[ax] - crit * sds[ax], 1), round(centers[ax] + crit * sds[ax], 1)] if sds[ax] else [np.nan, np.nan])

    # citation-free subset (RESTRICTION, not stripping)
    citefree = {}
    for ax in AXES:
        d = [windiff_units([u for u in units[ax][j] if u['qid'] not in cited], 'c_vote', None)
             - windiff_units([u for u in units[ax][j] if u['qid'] not in cited], 'b_vote', None) for j in JUDGES]
        citefree[ax] = round(float(np.nanmean(d)), 1)

    # tie-margin: report BOTH cell C (rubric win-diff) AND the format effect C-B, per dead-zone,
    # on the (q,opp) support where BOTH a panel rubric gap and >=1 pairwise vote exist.
    tie = {}
    for ax in AXES:
        gaps = {}
        bvotes = {}
        for j in JUDGES:
            for u in units[ax][j]:
                gaps.setdefault((u['qid'], u['opponent']), []).append(u['native_gap'])
                bvotes.setdefault((u['qid'], u['opponent']), []).append(u['b_vote'])
        panel_gap = {k: float(np.mean(v)) for k, v in gaps.items()}
        # B win-diff at panel/(q,opp) resolution: sign of mean pairwise vote per (q,opp)
        B_units = [{'qid': k[0], 'v': threshold(float(np.mean(v)))} for k, v in bvotes.items()]
        B_wd = windiff([u['v'] for u in B_units])
        tie[ax] = {}
        for delta in [0.0, 0.125, 0.25, 0.5]:
            C_units = [{'qid': k[0], 'v': threshold(g, delta)} for k, g in panel_gap.items()]
            C_wd = windiff([u['v'] for u in C_units])
            tie[ax][f'delta_{delta}'] = {'C': round(C_wd, 1), 'C_minus_B': round(C_wd - B_wd, 1)}
        med_gap = {k: float(np.median(v)) for k, v in gaps.items()}
        Cmed = windiff([threshold(g) for g in med_gap.values()])
        tie[ax]['panel_median'] = {'C': round(Cmed, 1), 'C_minus_B': round(Cmed - B_wd, 1)}
        tie[ax]['individual_matched_instrument'] = primary[ax]['instrument_mean']

    # opponent-specific
    opp_spec = {ax: {} for ax in AXES}
    for ax in AXES:
        for opp in FRONTIER:
            d = []
            for j in JUDGES:
                uu = [u for u in units[ax][j] if u['opponent'] == opp]
                d.append(windiff_units(uu, 'c_vote', None) - windiff_units(uu, 'b_vote', None))
            opp_spec[ax][opp] = round(float(np.nanmean(d)), 1)

    common = common_support_abc(R, P, H, rng)

    out = {'nboot': NBOOT, 'seed': SEED, 'n_primary_cluster_questions': len(primary_qids),
           'judges': JUDGES,
           'estimand': 'instrument = mean_j (C_j - B_j), aggregation-matched same-judge, rater fixed; '
                       'bootstrap over matched question clusters only',
           'primary_instrument': primary, 'native_score_gaps': native,
           'tie_margin_sensitivity': tie, 'opponent_specific': opp_spec,
           'instrument_citationfree_subset': citefree,
           'common_support_abc': common,
           'rendering_note': 'A used qa_text_only; B/C judged answer_markdown (OE carries citations in '
                             '~29% of answers). A-vs-B/C is NOT presentation-matched; the citation-free '
                             'subset RESTRICTS to OE answers with no detected citation markers (it does '
                             'not strip citations and does not equate the human/LLM renderings).'}
    pb = os.path.join(OUT, 'panel_bootstrap.json')
    if os.path.exists(pb):
        d = json.load(open(pb))
        out['panel_threshold_reference'] = {ax: d['point'][ax]['instrument'] for ax in AXES}
    json.dump(out, open(os.path.join(OUT, 'robust_analysis.json'), 'w'), indent=2)
    return out


def common_support_abc(R, P, H, rng):
    """EXACT common support (human ∩ 4 pairwise ∩ 4 OE-rubric ∩ 4 opponent-rubric), identical keys
    for A, B, C. Bootstrap over the matched question clusters only."""
    res = {}
    for ax in AXES:
        keys = common_support_keys(R[ax], P[ax], H[ax])
        if not keys:
            res[ax] = {'n_qopp': 0}
            continue
        A, B, Ci, Cp = [], [], [], []
        for (q, opp) in keys:
            for o in H[ax][(q, opp)]:
                A.append({'qid': q, 'v': o})
            oe_m, op_m = [], []
            for j in JUDGES:
                B.append({'qid': q, 'v': P[ax][(q, opp, j)]})
                Ci.append({'qid': q, 'v': threshold(R[ax][(q, OE, j)] - R[ax][(q, opp, j)])})
                oe_m.append(R[ax][(q, OE, j)]); op_m.append(R[ax][(q, opp, j)])
            Cp.append({'qid': q, 'v': threshold(float(np.mean(oe_m)) - float(np.mean(op_m)))})
        cluster_qids = sorted({k[0] for k in keys})

        def wds(w):
            a = windiff_units(A, 'v', w); b = windiff_units(B, 'v', w)
            ci_ = windiff_units(Ci, 'v', w); cp = windiff_units(Cp, 'v', w)
            return a, b, ci_, cp
        a0, b0, ci0, cp0 = wds({q: 1.0 for q in cluster_qids})
        bA = bB = None
        bootR, bootI = [], []
        bootA, bootB, bootCi = [], [], []
        for _ in range(NBOOT):
            w = boot_weights(cluster_qids, rng)
            a, b, ci_, cp = wds(w)
            bootA.append(a); bootB.append(b); bootCi.append(ci_)
            bootR.append(b - a); bootI.append(ci_ - b)
        res[ax] = {
            'n_qopp': len(keys), 'n_cluster_questions': len(cluster_qids),
            'n_human_votes': len(A), 'n_llm_pairwise_votes': len(B),
            'A_human': round(a0, 1), 'A_ci': ci(bootA),
            'B_llm_pairwise': round(b0, 1), 'B_ci': ci(bootB),
            'C_individual': round(ci0, 1), 'C_individual_ci': ci(bootCi),
            'C_panel_threshold': round(cp0, 1),
            'rater_B_minus_A': round(b0 - a0, 1), 'rater_ci': ci(bootR),
            'rater_p': round(two_sided_p(bootR), 4),
            'instrument_Cind_minus_B': round(ci0 - b0, 1), 'instrument_ci': ci(bootI),
            'instrument_p': round(two_sided_p(bootI), 4),
        }
    return res


def main():
    out = analyze()
    P = out['primary_instrument']
    print(f"primary cluster questions = {out['n_primary_cluster_questions']}  nboot={out['nboot']}\n")
    print("=== PRIMARY: aggregation-matched same-judge instrument = mean_j(C_j - B_j) ===")
    print(f"{'axis':16s}{'instr':>7s}{'fixed CI':>16s}{'p_holm':>8s}{'sign':>6s}{'[panel ref]':>13s}")
    for ax in AXES:
        p = P[ax]; ref = out.get('panel_threshold_reference', {}).get(ax, float('nan'))
        print(f"{ax:16s}{p['instrument_mean']:>+7.1f}{str(p['instrument_ci_fixed']):>16s}"
              f"{str(p['instrument_p_holm']):>8s}{str(p['sign_consistent_all_judges']):>6s}{ref:>+13.1f}")
    print("\n=== EXACT common-support A -> B -> C (human ∩ 4pw ∩ 4rubric) ===")
    for ax in AXES:
        c = out['common_support_abc'][ax]
        if c.get('n_qopp'):
            print(f"{ax:16s} n(q×opp)={c['n_qopp']:3d}  A={c['A_human']:+6.1f}{str(c['A_ci']):>15s}"
                  f"  B={c['B_llm_pairwise']:+6.1f}  Cind={c['C_individual']:+6.1f}"
                  f"  rater={c['rater_B_minus_A']:+6.1f}{str(c['rater_ci']):>15s} p={c['rater_p']}"
                  f"  instr={c['instrument_Cind_minus_B']:+6.1f}{str(c['instrument_ci']):>15s}")
    print("\n=== tie-margin (accuracy): cell C and format effect C-B per dead-zone ===")
    for k, v in out['tie_margin_sensitivity']['accuracy'].items():
        print(f"  {k:24s} {v}")
    print("\nwrote out/robust_analysis.json")


if __name__ == '__main__':
    main()
