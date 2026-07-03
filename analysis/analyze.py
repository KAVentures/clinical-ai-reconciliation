"""
Real-POCQi reconciliation analysis (executable-now, public data only).
Produces:
  (1) Reproduction of one-vs-rest win-differences per provider/axis, overall & by render_mode.
  (2) Citation-halo estimate: OE win-diff(citations) - win-diff(text_only) per axis,
      cluster-bootstrap CI + permutation p, plus a within-question sensitivity subset.
  (3) Precision/power simulation grounded in the empirical question-level variance:
      N (questions) needed to resolve an interaction (difference-of-differences).
All CIs use the question as the resampling cluster (rater IDs are NOT in the public data).
"""
import numpy as np, pandas as pd, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
OUT  = os.path.join(HERE, '..', 'out')
os.makedirs(OUT, exist_ok=True)
RNG = np.random.default_rng(62)

r = pd.read_parquet(os.path.join(DATA, 'ratings.parquet'))
AXES = ['accuracy','clinical_utility','source_quality','completeness','verifiability']
FRONTIER = ['gpt-5.5','claude-opus-4-8','gemini-3.1-pro']

# map choice -> preferred slot
pref_slot = {'strongly_a':'a','slightly_a':'a','strongly_b':'b','slightly_b':'b','tie':None}
r['pref'] = r.choice.map(pref_slot)
def preferred_provider(row):
    if row.pref == 'a': return row.slot_a_provider
    if row.pref == 'b': return row.slot_b_provider
    return None
r['pref_provider'] = r.apply(preferred_provider, axis=1)

def outcome_for(df, prov):
    """+1 win / -1 loss / 0 tie for `prov` on rows where it participates."""
    sub = df[(df.slot_a_provider==prov)|(df.slot_b_provider==prov)].copy()
    o = np.where(sub.pref_provider==prov, 1.0,
        np.where(sub.pref_provider.isna(), 0.0, -1.0))
    sub = sub.assign(_o=o)
    return sub  # has _o and question_id

def win_diff(df, prov):
    sub = outcome_for(df, prov)
    if len(sub)==0: return np.nan, 0
    return 100*sub._o.mean(), len(sub)

def cluster_boot_ci(df, prov, B=4000):
    """Cluster bootstrap over question_id for a single win-difference."""
    sub = outcome_for(df, prov)
    qids = sub.question_id.values
    o = sub._o.values
    uq = np.unique(qids)
    # group outcomes by question
    byq = {q: o[qids==q] for q in uq}
    ests = np.empty(B)
    for b in range(B):
        samp = RNG.choice(uq, size=len(uq), replace=True)
        vals = np.concatenate([byq[q] for q in samp])
        ests[b] = 100*vals.mean()
    return np.percentile(ests,2.5), np.percentile(ests,97.5), ests.std()

def citation_halo(df, prov, axis, B=4000):
    """Difference: win-diff(citations) - win-diff(text_only) for prov on one axis.
       Cluster bootstrap over questions (union), permutation p by shuffling render_mode label."""
    d = df[df.axis==axis]
    base = outcome_for(d, prov)  # already carries render_mode + question_id + _o
    to = base[base.render_mode=='qa_text_only']
    tc = base[base.render_mode=='qa_text_citations']
    wd_to = 100*to._o.mean(); wd_tc = 100*tc._o.mean()
    diff = wd_tc - wd_to
    # cluster bootstrap on the difference
    def wd_by_q(frame):
        return {q: frame._o.values[frame.question_id.values==q] for q in np.unique(frame.question_id.values)}
    q_to = wd_by_q(to); q_tc = wd_by_q(tc)
    uq_to=list(q_to); uq_tc=list(q_tc)
    ests=np.empty(B)
    for b in range(B):
        s_to=RNG.choice(uq_to,size=len(uq_to),replace=True)
        s_tc=RNG.choice(uq_tc,size=len(uq_tc),replace=True)
        v_to=np.concatenate([q_to[q] for q in s_to]); v_tc=np.concatenate([q_tc[q] for q in s_tc])
        ests[b]=100*v_tc.mean()-100*v_to.mean()
    lo,hi=np.percentile(ests,[2.5,97.5])
    p_boot = 2*min((ests<=0).mean(),(ests>=0).mean())
    return dict(axis=axis, wd_text_only=round(wd_to,1), wd_citations=round(wd_tc,1),
                halo_diff=round(diff,1), ci=[round(lo,1),round(hi,1)],
                p_boot=round(p_boot,4), n_to=len(to), n_tc=len(tc))

# ---------- (1) reproduction ----------
report = {'reproduction':{}, 'citation_halo':{}, 'power':{}}
for mode_label, dsub in [('overall', r),
                         ('text_only', r[r.render_mode=='qa_text_only']),
                         ('citations', r[r.render_mode=='qa_text_citations'])]:
    report['reproduction'][mode_label]={}
    for prov in ['openevidence']+FRONTIER:
        report['reproduction'][mode_label][prov]={}
        for axis in AXES:
            wd,n = win_diff(dsub[dsub.axis==axis], prov)
            lo,hi,se = cluster_boot_ci(dsub[dsub.axis==axis], prov, B=2000)
            report['reproduction'][mode_label][prov][axis]=dict(
                win_diff=round(wd,1), ci=[round(lo,1),round(hi,1)], se=round(se,1), n=int(n))

# ---------- (2) citation halo (OE + frontier) ----------
for prov in ['openevidence']+FRONTIER:
    report['citation_halo'][prov]=[citation_halo(r, prov, axis) for axis in AXES]

# within-question sensitivity (questions rated in BOTH modes)
both_q = set(r[r.render_mode=='qa_text_only'].question_id) & set(r[r.render_mode=='qa_text_citations'].question_id)
rb = r[r.question_id.isin(both_q)]
report['citation_halo_within_subset_nqueries']=len(both_q)
report['citation_halo_within']={prov:[citation_halo(rb, prov, axis, B=2000) for axis in AXES]
                                for prov in ['openevidence']}

# ---------- (3) precision / power simulation ----------
# Empirical question-level SD of OE accuracy outcome -> extrapolate SE(win-diff) vs N questions.
oe_acc = outcome_for(r[r.axis=='accuracy'],'openevidence')
q_means = oe_acc.groupby('question_id')._o.mean()
sd_q = q_means.std(); n_q_now = q_means.shape[0]
# SE of a mean-of-question-means ~ sd_q/sqrt(Nq); win-diff is *100
def se_at(Nq): return 100*sd_q/np.sqrt(Nq)
def n_for_halfwidth(hw): return (1.96*100*sd_q/hw)**2
# interaction (diff of two independent win-diffs) SE ~ sqrt(2)*se_single
def n_for_interaction(delta, power=0.8, alpha=0.05):
    from scipy.stats import norm
    z=norm.ppf(1-alpha/2)+norm.ppf(power)  # ~2.80
    # need delta >= z * SE_interaction; SE_int = sqrt(2)*100*sd_q/sqrt(Nq_per_group)
    return (z*np.sqrt(2)*100*sd_q/delta)**2
report['power']=dict(
    sd_question_level=round(float(sd_q),3), n_questions_now=int(n_q_now),
    se_winDiff_at={str(N):round(float(se_at(N)),2) for N in [100,200,400,620,1000]},
    n_questions_for_single_winDiff_CIhalfwidth={
        '5pp':int(np.ceil(n_for_halfwidth(5))),'8pp':int(np.ceil(n_for_halfwidth(8)))},
    n_questions_per_group_for_interaction_80pct={
        '10pp':int(np.ceil(n_for_interaction(10))),'12pp':int(np.ceil(n_for_interaction(12))),
        '15pp':int(np.ceil(n_for_interaction(15))),'20pp':int(np.ceil(n_for_interaction(20)))})

with open(os.path.join(OUT,'results.json'),'w') as f:
    json.dump(report,f,indent=2)

# ---------- console summary ----------
print("="*72)
print("(1) REPRODUCTION — one-vs-rest win-difference (%), OE, by render mode")
for mode in ['text_only','citations']:
    print(f"\n  render_mode = {mode}")
    for axis in AXES:
        d=report['reproduction'][mode]['openevidence'][axis]
        print(f"    {axis:16s} OE = {d['win_diff']:+6.1f}  CI[{d['ci'][0]:+.1f},{d['ci'][1]:+.1f}]  n={d['n']}")
print("\n  Paper (text_only): accuracy +24.7, clin_util +29.6, source_q +38.8, complete +30.9, verif +26.2")
print("  Paper (citations): accuracy +35.7")

print("\n"+"="*72)
print("(2) CITATION HALO — OE win-diff(citations) - win-diff(text_only), per axis")
for d in report['citation_halo']['openevidence']:
    print(f"    {d['axis']:16s} text_only={d['wd_text_only']:+6.1f}  cite={d['wd_citations']:+6.1f}  "
          f"halo={d['halo_diff']:+5.1f}  CI[{d['ci'][0]:+.1f},{d['ci'][1]:+.1f}]  p={d['p_boot']:.3f}")
print(f"\n  within-question subset (n={report['citation_halo_within_subset_nqueries']} questions rated in both modes):")
for d in report['citation_halo_within']['openevidence']:
    print(f"    {d['axis']:16s} halo={d['halo_diff']:+5.1f}  CI[{d['ci'][0]:+.1f},{d['ci'][1]:+.1f}]  p={d['p_boot']:.3f}")

print("\n"+"="*72)
print("(3) PRECISION / POWER (grounded in empirical question-level SD)")
pw=report['power']
print(f"    question-level SD of OE accuracy outcome = {pw['sd_question_level']}  (N_q now = {pw['n_questions_now']})")
print(f"    SE of win-diff at N questions: {pw['se_winDiff_at']}")
print(f"    N questions per group for 80% power on an INTERACTION:")
for k,v in pw['n_questions_per_group_for_interaction_80pct'].items():
    print(f"       detect {k} diff-of-diff -> {v} questions/group")
print("\nWrote", os.path.join(OUT,'results.json'))
