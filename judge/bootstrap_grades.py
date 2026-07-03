"""Cluster-bootstrap CIs + leave-one-judge-out robustness for the instrument existence proof.
Resamples QUESTIONS with replacement (cluster on question_id) to get 95% CIs on the
OE-vs-rest LLM-judge win-difference per axis, and recomputes the panel dropping each judge
(critically GPT-5.5, the self-preferring outlier). Writes out/bootstrap_results.json."""
import os, json
import numpy as np, pandas as pd

HERE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(HERE,'..','data'); OUT=os.path.join(HERE,'out')
AXES=['accuracy','clinical_utility','source_quality','completeness','verifiability']
FRONTIER=['gpt-5.5','claude-opus-4-8','gemini-3.1-pro']
RNG=np.random.default_rng(62)
NBOOT=2000

def load_grades():
    rows=[]
    for line in open(os.path.join(OUT,'grades.jsonl')):
        r=json.loads(line)
        if r.get('scores'):
            for ax in AXES: rows.append(dict(question_id=r['question_id'],provider_key=r['provider_key'],
                                             judge=r['judge'],axis=ax,score=r['scores'][ax]))
    return pd.DataFrame(rows)

def human_perq(qids=None):
    """Per-question OE win/loss/tie counts from human text-only pairwise ratings.
    Restrict to `qids` (the graded question set) so the human baseline is on the SAME
    questions as the LLM rubric cell — otherwise the reversal magnitude mixes samples."""
    r=pd.read_parquet(os.path.join(DATA,'ratings.parquet'))
    r=r[r.render_mode=='qa_text_only']
    if qids is not None:
        r=r[r.question_id.isin(set(qids))]
    pref={'strongly_a':'a','slightly_a':'a','strongly_b':'b','slightly_b':'b','tie':None}
    r['pref']=r.choice.map(pref)
    def pp(x): return x.slot_a_provider if x.pref=='a' else (x.slot_b_provider if x.pref=='b' else None)
    r['pp']=r.apply(pp,axis=1)
    per_q={ax:{} for ax in AXES}
    for ax in AXES:
        d=r[r.axis==ax]; sub=d[(d.slot_a_provider=='openevidence')|(d.slot_b_provider=='openevidence')]
        for qid,grp in sub.groupby('question_id'):
            w=int((grp.pp=='openevidence').sum())
            t=int(grp.pp.isna().sum())
            l=int(len(grp)-w-t)
            per_q[ax][qid]=(w,l,t)
    return per_q

def human_text_only_windiff(qids=None):
    pq=human_perq(qids)
    out={}
    for ax in AXES:
        qs=list(pq[ax].keys())
        out[ax]=round(windiff_from_perq(pq[ax],qs),1) if qs else None
    return out

def panel_windiff_per_axis(g):
    """Return dict axis -> {qid -> signed win-diff contribution}, plus overall win-diff.
    We build per-question OE-vs-frontier win/loss/tie counts so bootstrap can resample questions."""
    pm=g.groupby(['question_id','provider_key','axis']).score.mean().reset_index()
    per_q={ax:{} for ax in AXES}
    for ax in AXES:
        d=pm[pm.axis==ax].pivot(index='question_id',columns='provider_key',values='score')
        if 'openevidence' not in d: continue
        for qid,rowv in d.iterrows():
            w=l=t=0
            for fr in FRONTIER:
                if fr not in d.columns: continue
                a=rowv.get('openevidence'); b=rowv.get(fr)
                if pd.isna(a) or pd.isna(b): continue
                if a>b: w+=1
                elif a<b: l+=1
                else: t+=1
            per_q[ax][qid]=(w,l,t)
    return per_q

def windiff_from_perq(per_q_axis, qids):
    W=L=N=0
    for qid in qids:
        v=per_q_axis.get(qid)
        if v is None: continue
        w,l,t=v; W+=w; L+=l; N+=w+l+t
    return 100*(W-L)/N if N else np.nan

def bootstrap_ci(per_q_axis, qids):
    point=windiff_from_perq(per_q_axis,qids)
    qids=np.array(qids)
    boots=np.empty(NBOOT)
    for b in range(NBOOT):
        samp=RNG.choice(qids,size=len(qids),replace=True)
        boots[b]=windiff_from_perq(per_q_axis,samp)
    lo,hi=np.nanpercentile(boots,[2.5,97.5])
    return round(point,1),round(lo,1),round(hi,1)

def main():
    g=load_grades()
    qids=sorted(g.question_id.unique())

    # full LLM panel with CIs (computed FIRST so its bootstrap RNG stream is unaffected by the
    # human bootstrap added below — keeps cell C CIs identical to prior published runs)
    per_q=panel_windiff_per_axis(g)
    full={}
    for ax in AXES:
        pt,lo,hi=bootstrap_ci(per_q[ax],qids)
        full[ax]=dict(point=pt,lo=lo,hi=hi)

    # Human baseline on the SAME graded questions (not the full text-only bank), with a CI.
    hum_pq=human_perq(qids)
    hum={}; hum_ci={}
    for ax in AXES:
        qs=sorted(hum_pq[ax].keys())
        pt,lo,hi=bootstrap_ci(hum_pq[ax],qs)
        hum[ax]=pt; hum_ci[ax]=dict(point=pt,lo=lo,hi=hi,n_q=len(qs))
    hum_full=human_text_only_windiff()  # reference: full text-only bank (matches published +24.x)

    # leave-one-judge-out
    judges=sorted(g.judge.unique())
    lojo={}
    for drop in judges:
        gg=g[g.judge!=drop]
        pq=panel_windiff_per_axis(gg)
        lojo[drop]={ax:round(windiff_from_perq(pq[ax],qids),1) for ax in AXES}

    n_hq=hum_ci[AXES[0]]['n_q']
    print(f"n_questions(LLM)={len(qids)}  n_questions(human text-only subset)={n_hq}  bootstrap={NBOOT} (cluster on question_id)")
    print(f"human baseline computed on the SAME graded questions; full-bank reference (published-style): {hum_full}\n")
    print(f"{'axis':16s}{'HUMAN same-set [95% CI]':>26s}{'LLM-panel [95% CI]':>26s}{'flip?':>7s}{'CI excl 0?':>12s}")
    for ax in AXES:
        h=hum_ci[ax]; f=full[ax]
        flip='YES' if (h['point']>0)!=(f['point']>0) else ''
        excl='yes' if (f['lo']>0 or f['hi']<0) else 'no'
        hci=f"{h['point']:+.1f} [{h['lo']:+.1f},{h['hi']:+.1f}]"
        ci=f"{f['point']:+.1f} [{f['lo']:+.1f},{f['hi']:+.1f}]"
        print(f"{ax:16s}{hci:>26s}{ci:>26s}{flip:>7s}{excl:>12s}")

    print("\n=== leave-one-judge-out panel win-diff (drop the named judge) ===")
    print(f"{'dropped':18s}"+"".join(f"{ax[:5]:>9s}" for ax in AXES))
    print(f"{'(none/full)':18s}"+"".join(f"{full[ax]['point']:>+9.1f}" for ax in AXES))
    for drop in judges:
        print(f"{'-'+drop:18s}"+"".join(f"{lojo[drop][ax]:>+9.1f}" for ax in AXES))

    json.dump(dict(n_questions=len(qids),n_questions_human=n_hq,nboot=NBOOT,
                   human_pairwise=hum,human_pairwise_ci=hum_ci,human_pairwise_fullbank=hum_full,
                   llm_panel_ci=full,leave_one_judge_out=lojo),
              open(os.path.join(OUT,'bootstrap_results.json'),'w'),indent=2)
    print("\nwrote out/bootstrap_results.json")

if __name__=="__main__": main()
