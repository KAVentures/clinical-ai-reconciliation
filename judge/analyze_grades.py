"""Analyze LLM-judge grades vs human pairwise preference (the instrument existence proof).
Outputs to out/grade_results.json + console."""
import os, json, itertools
import numpy as np, pandas as pd

HERE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(HERE,'..','data'); OUT=os.path.join(HERE,'out')
AXES=['accuracy','clinical_utility','source_quality','completeness','verifiability']
FRONTIER=['gpt-5.5','claude-opus-4-8','gemini-3.1-pro']
JUDGE_FAMILY={'gpt-5.5':'gpt-5.5','opus-4.8':'claude-opus-4-8','grok-4.3':None,'gemini-3.5-flash':'gemini-3.1-pro'}

def load_grades():
    rows=[]
    for line in open(os.path.join(OUT,'grades.jsonl')):
        r=json.loads(line)
        if r.get('scores'):
            for ax in AXES: rows.append(dict(question_id=r['question_id'],provider_key=r['provider_key'],
                                             judge=r['judge'],axis=ax,score=r['scores'][ax]))
    return pd.DataFrame(rows)

def human_text_only_windiff(qids=None):
    """OE-vs-rest human pairwise win-diff on text-only ratings. Pass qids to restrict to the
    SAME graded questions as the LLM cell (otherwise the comparison mixes question samples)."""
    r=pd.read_parquet(os.path.join(DATA,'ratings.parquet'))
    r=r[r.render_mode=='qa_text_only']
    if qids is not None:
        r=r[r.question_id.isin(set(qids))]
    pref={'strongly_a':'a','slightly_a':'a','strongly_b':'b','slightly_b':'b','tie':None}
    r['pref']=r.choice.map(pref)
    def pp(x): return x.slot_a_provider if x.pref=='a' else (x.slot_b_provider if x.pref=='b' else None)
    r['pp']=r.apply(pp,axis=1)
    out={}
    for ax in AXES:
        d=r[r.axis==ax]; sub=d[(d.slot_a_provider=='openevidence')|(d.slot_b_provider=='openevidence')]
        o=np.where(sub.pp=='openevidence',1.0,np.where(sub.pp.isna(),0.0,-1.0))
        out[ax]=round(100*o.mean(),1)
    return out

def judge_windiff(g):
    """Derive OE-vs-rest pairwise win-diff from absolute scores: per question, per axis,
    compare OE mean-panel score vs each frontier mean-panel score."""
    # panel mean score per (question, provider, axis)
    pm=g.groupby(['question_id','provider_key','axis']).score.mean().reset_index()
    res={}
    for ax in AXES:
        d=pm[pm.axis==ax].pivot(index='question_id',columns='provider_key',values='score')
        if 'openevidence' not in d: continue
        wins=losses=ties=0
        for fr in FRONTIER:
            if fr not in d: continue
            sub=d[['openevidence',fr]].dropna()
            wins+=(sub['openevidence']>sub[fr]).sum()
            losses+=(sub['openevidence']<sub[fr]).sum()
            ties+=(sub['openevidence']==sub[fr]).sum()
        n=wins+losses+ties
        res[ax]=round(100*(wins-losses)/n,1) if n else None
    return res

def judge_windiff_by_judge(g):
    out={}
    for j in g.judge.unique():
        out[j]=judge_windiff(g[g.judge==j])
    return out

def mean_scores(g):
    return g.groupby(['provider_key','axis']).score.mean().round(2).unstack()

def self_preference(g):
    """For each judge with a contestant family, mean score to own family vs to others,
    paired within question+axis (delta)."""
    out={}
    for j,fam in JUDGE_FAMILY.items():
        if fam is None: continue
        gj=g[g.judge==j]
        own=gj[gj.provider_key==fam].groupby(['question_id','axis']).score.mean()
        oth=gj[gj.provider_key!=fam].groupby(['question_id','axis']).score.mean()
        m=pd.concat([own.rename('own'),oth.rename('oth')],axis=1).dropna()
        out[j]=dict(family=fam,delta_own_minus_others=round(float((m.own-m.oth).mean()),3),
                    n=int(len(m)))
    return out

def interjudge_agreement(g):
    # correlation of per-(question,provider) mean-across-axes score between judge pairs
    piv=g.groupby(['question_id','provider_key','judge']).score.mean().reset_index()
    w=piv.pivot_table(index=['question_id','provider_key'],columns='judge',values='score')
    corr=w.corr(method='spearman').round(2)
    return corr

def main():
    g=load_grades()
    if g.empty: print("no grades yet"); return
    nq=g.question_id.nunique()
    print(f"grades: {len(g)} axis-rows | questions={nq} | judges={sorted(g.judge.unique())} | providers={sorted(g.provider_key.unique())}")
    hum=human_text_only_windiff(qids=g.question_id.unique())     # same graded questions
    hum_full=human_text_only_windiff()                            # full text-only bank (reference)
    jw=judge_windiff(g)
    jw_byj=judge_windiff_by_judge(g)
    ms=mean_scores(g)
    sp=self_preference(g)
    print("\n=== OE-vs-rest WIN-DIFFERENCE: human pairwise vs LLM-judge panel (same queries+answers) ===")
    print(f"(human on the SAME graded questions; full text-only bank shown for reference)")
    print(f"{'axis':16s}{'HUMAN(same)':>13s}{'HUMAN(full)':>13s}{'LLM-judge panel':>18s}{'flip?':>8s}")
    for ax in AXES:
        h=hum[ax]; hf=hum_full[ax]; j=jw.get(ax)
        flip = '' if j is None else ('YES' if (h>0)!=(j>0) else '')
        print(f"{ax:16s}{h:>+13.1f}{hf:>+13.1f}{(j if j is not None else float('nan')):>+18.1f}{flip:>8s}")
    print("\n=== LLM-judge win-diff by individual judge (accuracy axis) ===")
    for j,dd in jw_byj.items():
        print(f"  {j:16s} " + "  ".join(f"{ax[:4]}={dd.get(ax)}" for ax in AXES))
    print("\n=== mean absolute 1-4 score by provider x axis (panel) ===")
    print(ms.to_string())
    print("\n=== self-preference (own-family minus others, paired within question+axis) ===")
    for j,d in sp.items(): print(f"  {j:16s} family={d['family']:16s} delta={d['delta_own_minus_others']:+.3f} (n={d['n']})")
    print("\n=== inter-judge Spearman agreement (per question-provider mean score) ===")
    print(interjudge_agreement(g).to_string())
    json.dump(dict(n_questions=nq,human_pairwise=hum,human_pairwise_fullbank=hum_full,judge_panel_windiff=jw,
                   judge_windiff_by_judge=jw_byj,mean_scores=ms.reset_index().to_dict('records'),
                   self_preference=sp), open(os.path.join(OUT,'grade_results.json'),'w'), indent=2)
    print("\nwrote out/grade_results.json")

if __name__=="__main__": main()
