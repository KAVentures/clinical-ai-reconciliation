"""Exploratory supplementary analyses (peer-review revision) — EXPLANATORY, not confirmatory.

These do not carry the paper's primary claims (see robust_analysis.py). They probe WHY the
evaluation format shifts the OE-vs-frontier ranking and address specific reviewer requests:

  1. reliability_resolution : rubric measurement resolution (tie/ceiling rate, entropy, inter-judge
     agreement, question/judge/residual variance shares). The mechanism candidate: an absolute 1-4
     rubric is compressed and ceiling-heavy, so it resolves OE's citation/framing advantages less
     than a forced pairwise choice does.
  2. self_preference_did : self-preference as a difference-in-differences (how much MORE favorable a
     judge is to its own family than OTHER judges are to that family), under each format separately —
     removes the "the family's answers are simply better" confound in the naive own-vs-others gap.
  3. axis_factor_structure : correlation/'factor' structure of the five axes to justify collapsing
     them into content vs evidence-presentation composites (reduces multiplicity).
  4. length_opponent_fe : rubric score gap vs answer-length gap WITH opponent fixed effects and a
     within-opponent breakdown (observational adjustment, not a causal length claim).
  5. citation_halo_paired : within-question paired human OE win-diff, text-only vs with-citations,
     on questions rated in BOTH render modes (a true paired contrast, not two independent groups).

No API calls. Reads out/grades.jsonl, out/pairwise.jsonl, data/ratings.parquet, data/answers.parquet.
Writes out/robust_supplementary.json.
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
PROVS = [OE] + FRONTIER
JUDGES = ['gpt-5.5', 'opus-4.8', 'grok-4.3', 'gemini-3.5-flash']
JUDGE_FAMILY = {'gpt-5.5': 'gpt-5.5', 'opus-4.8': 'claude-opus-4-8',
                'grok-4.3': None, 'gemini-3.5-flash': 'gemini-3.1-pro'}


def load_grades_df():
    rows = []
    for line in open(os.path.join(OUT, 'grades.jsonl')):
        r = json.loads(line)
        if r.get('scores'):
            for ax in AXES:
                if ax in r['scores']:
                    rows.append((r['question_id'], r['provider_key'], r['judge'], ax, float(r['scores'][ax])))
    return pd.DataFrame(rows, columns=['qid', 'prov', 'judge', 'axis', 'score'])


def load_pairwise_df():
    rows = []
    for line in open(os.path.join(OUT, 'pairwise.jsonl')):
        r = json.loads(line)
        res = r.get('oe_result')
        if res:
            for ax in AXES:
                if ax in res:
                    rows.append((r['question_id'], r['opponent'], r['judge'], ax,
                                 1 if res[ax] == 'oe' else (-1 if res[ax] == 'opp' else 0)))
    return pd.DataFrame(rows, columns=['qid', 'opponent', 'judge', 'axis', 'vote'])


# ---------- 1. reliability / resolution ----------
def reliability_resolution(g, pw):
    out = {}
    for ax in AXES:
        d = g[g.axis == ax]
        sc = d.score.values
        # rubric resolution
        p = np.array([np.mean(sc == k) for k in (1, 2, 3, 4)])
        entropy = float(-np.sum([x * np.log2(x) for x in p if x > 0]))
        # inter-judge agreement: mean pairwise Spearman of per-(q,prov) scores across judges
        piv = d.pivot_table(index=['qid', 'prov'], columns='judge', values='score')
        cors = []
        js = [j for j in JUDGES if j in piv.columns]
        for a in range(len(js)):
            for b in range(a + 1, len(js)):
                sub = piv[[js[a], js[b]]].dropna()
                if len(sub) > 10:
                    cors.append(float(sub.corr(method='spearman').iloc[0, 1]))
        # variance components (simple): between-question, between-judge, residual on the (q,prov,judge) grid
        gm = sc.mean()
        vq = d.groupby('qid').score.mean().var(ddof=0)
        vj = d.groupby('judge').score.mean().var(ddof=0)
        vtot = sc.var(ddof=0)
        # pairwise tie rate for contrast
        tie_rate_pw = float(np.mean(pw[pw.axis == ax].vote.values == 0)) if len(pw[pw.axis == ax]) else None
        out[ax] = {
            'rubric_score_dist_1to4': [round(float(x), 3) for x in p],
            'rubric_ceiling_frac_score4': round(float(p[3]), 3),
            'rubric_entropy_bits_of_2': round(entropy, 3),
            'rubric_mean_interjudge_spearman': round(float(np.mean(cors)), 3) if cors else None,
            'var_share_question': round(float(vq / vtot), 3) if vtot else None,
            'var_share_judge': round(float(vj / vtot), 3) if vtot else None,
            'pairwise_tie_rate': round(tie_rate_pw, 3) if tie_rate_pw is not None else None,
        }
    return out


# ---------- 2. self-preference difference-in-differences ----------
def self_preference_did(g, pw):
    """Rubric DiD: for family f with judge j_f, DiD = (score_{j_f}(f) - score_{others}(f))
    minus the same own-vs-others gap averaged over the OTHER providers. Positive => j_f favors its
    own family beyond what the panel already gives that family (controls for the family being good).
    Pairwise DiD: analogous using OE-vs-family votes is not identifiable per family here, so we report
    the rubric DiD and, for pairwise, the naive own-family lift for context."""
    out = {'rubric_did': {}, 'note': 'DiD>0 means the judge inflates its OWN family beyond the panel consensus for that family.'}
    for j, fam in JUDGE_FAMILY.items():
        if fam is None:
            continue
        vals = []
        for ax in AXES:
            d = g[g.axis == ax]
            piv = d.pivot_table(index='qid', columns=['prov', 'judge'], values='score')
            # own-family: judge j scoring provider fam, vs other judges scoring fam
            try:
                own_fam_j = d[(d.prov == fam) & (d.judge == j)].groupby('qid').score.mean()
                oth_fam = d[(d.prov == fam) & (d.judge != j)].groupby('qid').score.mean()
                gap_fam = (own_fam_j - oth_fam).dropna()
                # baseline: same judge-vs-others gap on OTHER providers (its general leniency)
                own_oth_j = d[(d.prov != fam) & (d.judge == j)].groupby('qid').score.mean()
                oth_oth = d[(d.prov != fam) & (d.judge != j)].groupby('qid').score.mean()
                gap_oth = (own_oth_j - oth_oth).dropna()
                did = float(gap_fam.mean() - gap_oth.mean())
                vals.append(did)
            except Exception:
                pass
        out['rubric_did'][j] = {'family': fam, 'did_mean_over_axes': round(float(np.mean(vals)), 3) if vals else None}
    return out


# ---------- 3. axis factor structure ----------
def axis_factor_structure(g):
    piv = g.pivot_table(index=['qid', 'prov', 'judge'], columns='axis', values='score')
    corr = piv.corr(method='spearman')
    # 2-cluster hint via correlation to seed composites
    return {'spearman_corr': {a: {b: round(float(corr.loc[a, b]), 2) for b in AXES} for a in AXES},
            'proposed_composites': {'clinical_content': ['accuracy', 'clinical_utility', 'completeness'],
                                    'evidence_presentation': ['source_quality', 'verifiability']}}


# ---------- 4. length with opponent fixed effects ----------
def length_opponent_fe(g):
    a = pd.read_parquet(os.path.join(DATA, 'answers.parquet'))
    length = {(r.question_id, r.provider_key): len(str(r.answer_markdown)) for _, r in a.iterrows()}
    # per (qid, opponent): panel-mean rubric gap (accuracy) and length gap
    d = g[g.axis == 'accuracy']
    panel = d.groupby(['qid', 'prov']).score.mean()
    rows = []
    for (qid, opp) in {(q, o) for (q, o) in [(x[0], x[1]) for x in panel.index] if o in FRONTIER}:
        if (qid, OE) in panel.index and (qid, opp) in panel.index:
            sg = panel[(qid, OE)] - panel[(qid, opp)]
            lg = length.get((qid, OE), np.nan) - length.get((qid, opp), np.nan)
            if not np.isnan(lg):
                rows.append((opp, sg, lg))
    df = pd.DataFrame(rows, columns=['opp', 'score_gap', 'len_gap'])
    out = {'overall_corr_scoregap_lengap': round(float(df.score_gap.corr(df.len_gap)), 3)}
    out['within_opponent_corr'] = {opp: round(float(df[df.opp == opp].score_gap.corr(df[df.opp == opp].len_gap)), 3)
                                   for opp in FRONTIER}
    # OE is longest yet loses on accuracy rubric: report mean length by provider
    out['mean_len_chars'] = {p: int(np.mean([length[k] for k in length if k[1] == p])) for p in PROVS}
    return out


# ---------- 5. citation-halo paired (within-question) ----------
def citation_halo_paired():
    r = pd.read_parquet(os.path.join(DATA, 'ratings.parquet'))
    pref = {'strongly_a': 1, 'slightly_a': 1, 'strongly_b': -1, 'slightly_b': -1, 'tie': 0}

    def oe_vote(row):
        if row.slot_a_provider != OE and row.slot_b_provider != OE:
            return None
        pr = pref.get(row.choice)
        if pr is None:
            return None
        if pr == 0:
            return 0
        winner = row.slot_a_provider if pr == 1 else row.slot_b_provider
        return 1 if winner == OE else -1

    r = r[r.axis.isin(AXES)].copy()
    r['oe'] = r.apply(oe_vote, axis=1)
    r = r.dropna(subset=['oe'])
    # aggregate to (question_id, render_mode): mean OE vote
    agg = r.groupby(['question_id', 'render_mode']).oe.mean().unstack('render_mode')
    if 'qa_text_only' in agg and 'qa_text_citations' in agg:
        paired = agg[['qa_text_only', 'qa_text_citations']].dropna()
        diff = (paired['qa_text_citations'] - paired['qa_text_only'])
        # paired sign test (within-question)
        n = len(diff); pos = int((diff > 0).sum()); neg = int((diff < 0).sum())
        return {'n_paired_questions': n, 'mean_within_q_diff_citations_minus_textonly': round(float(diff.mean()), 4),
                'n_pos': pos, 'n_neg': neg,
                'interpretation': 'positive => citations raise OE preference within the same question (halo)'}
    return {'note': 'render modes not both present'}


def main():
    g = load_grades_df(); pw = load_pairwise_df()
    out = {
        'reliability_resolution': reliability_resolution(g, pw),
        'self_preference_did': self_preference_did(g, pw),
        'axis_factor_structure': axis_factor_structure(g),
        'length_opponent_fe': length_opponent_fe(g),
        'citation_halo_paired': citation_halo_paired(),
        'disclaimer': 'Exploratory/supplementary. Does not carry primary claims (see robust_analysis.py).',
    }
    json.dump(out, open(os.path.join(OUT, 'robust_supplementary.json'), 'w'), indent=2)
    rr = out['reliability_resolution']
    print("=== reliability / resolution (rubric) ===")
    for ax in AXES:
        v = rr[ax]
        print(f"  {ax:16s} ceiling(=4)={v['rubric_ceiling_frac_score4']:.2f}  entropy={v['rubric_entropy_bits_of_2']:.2f}"
              f"  interjudge_rho={v['rubric_mean_interjudge_spearman']}  pw_tie={v['pairwise_tie_rate']}")
    print("\n=== self-preference difference-in-differences (rubric) ===")
    for j, v in out['self_preference_did']['rubric_did'].items():
        print(f"  {j:16s} own-family DiD = {v['did_mean_over_axes']}")
    print("\n=== length vs accuracy score-gap ===")
    lo = out['length_opponent_fe']
    print(f"  overall corr={lo['overall_corr_scoregap_lengap']}  within-opp={lo['within_opponent_corr']}")
    print(f"  mean length chars={lo['mean_len_chars']}")
    print("\n=== citation-halo paired (human, within-question) ===")
    print(f"  {out['citation_halo_paired']}")
    print("\nwrote out/robust_supplementary.json")


if __name__ == '__main__':
    main()
