"""LENGTH-MATCHED sub-study on the rubric cell (cell C = {rubric, LLM}).
The unbroken confound flagged by the reviewer: OE and frontier answers differ in length, and an
absolute rubric may reward (or penalize) length. We test whether the rubric reversal is a length
artifact — WITHOUT regenerating answers — three ways, all on the existing 150-question grades:

  (1) Length distribution per system. NB OE is the LONGEST provider, yet it LOSES under the rubric,
      so a naive 'longer answers win' story runs *backwards* against the finding.
  (2) Length-STRATIFIED win-diff: split every OE-vs-opponent comparison by sign(len_OE - len_opp).
      If OE loses in BOTH the 'OE longer' and 'OE shorter' strata, length is not the driver.
  (3) Length-ADJUSTED regression: per axis, regress the paired score gap dScore=(OE-opp) on the paired
      length gap dLen. The INTERCEPT is the length-adjusted OE advantage (expected dScore at equal
      length); the SLOPE is score-points bought per +1000 chars. Cluster-bootstrap CIs on question_id.

Reads data/answers.parquet + judge/out/grades.jsonl -> judge/out/length_results.json (+ figure).
"""
import os, json
import numpy as np, pandas as pd

HERE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(HERE,'..','data'); OUT=os.path.join(HERE,'out')
AXES=['accuracy','clinical_utility','source_quality','completeness','verifiability']
FRONTIER=['gpt-5.5','claude-opus-4-8','gemini-3.1-pro']
OE='openevidence'
RNG=np.random.default_rng(62); NBOOT=2000

def load():
    ans=pd.read_parquet(os.path.join(DATA,'answers.parquet'))
    ans['clen']=ans.answer_markdown.str.len()
    length={(r.question_id,r.provider_key):r.clen for _,r in ans.iterrows()}
    # panel-mean rubric score per (question, provider, axis)
    rows=[]
    for line in open(os.path.join(OUT,'grades.jsonl')):
        r=json.loads(line)
        if not r.get('scores'): continue
        for ax,v in r['scores'].items():
            if ax in AXES: rows.append((r['question_id'],r['provider_key'],ax,v))
    g=pd.DataFrame(rows,columns=['question_id','provider_key','axis','score'])
    g=g.groupby(['question_id','provider_key','axis'],as_index=False).score.mean()
    return length,g

def build_pairs(length,g):
    """One row per (question, opponent, axis): OE score/len minus opponent score/len."""
    piv=g.pivot_table(index=['question_id','axis'],columns='provider_key',values='score')
    recs=[]
    for (qid,ax),row in piv.iterrows():
        if OE not in row or pd.isna(row[OE]): continue
        for opp in FRONTIER:
            if opp not in row or pd.isna(row[opp]): continue
            lo=length.get((qid,OE)); lp=length.get((qid,opp))
            if lo is None or lp is None: continue
            recs.append(dict(question_id=qid,opponent=opp,axis=ax,
                             dscore=row[OE]-row[opp], dlen=(lo-lp)/1000.0))  # dlen in thousands of chars
    return pd.DataFrame(recs)

def windiff(sub):
    w=(sub.dscore>0).sum(); l=(sub.dscore<0).sum(); n=len(sub)
    return 100*(w-l)/n if n else np.nan

def ols_intercept_slope(x,y):
    """simple least squares y=a+b x; returns (a,b)."""
    x=np.asarray(x,float); y=np.asarray(y,float)
    if len(x)<3 or np.ptp(x)==0: return (np.nanmean(y), 0.0)
    b=np.cov(x,y,bias=True)[0,1]/np.var(x); a=y.mean()-b*x.mean()
    return (a,b)

def boot_axis(df_ax):
    qids=df_ax.question_id.unique()
    byq={q:df_ax[df_ax.question_id==q] for q in qids}
    raw=df_ax.dscore.mean()
    a0,b0=ols_intercept_slope(df_ax.dlen,df_ax.dscore)
    wd0=windiff(df_ax)
    longer=df_ax[df_ax.dlen>0]; shorter=df_ax[df_ax.dlen<0]
    wl0=windiff(longer); ws0=windiff(shorter)
    A=[];B=[];WD=[];WL=[];WS=[];RAW=[]
    for _ in range(NBOOT):
        samp=RNG.choice(qids,size=len(qids),replace=True)
        sub=pd.concat([byq[q] for q in samp],ignore_index=True)
        a,b=ols_intercept_slope(sub.dlen,sub.dscore)
        A.append(a);B.append(b);WD.append(windiff(sub));RAW.append(sub.dscore.mean())
        WL.append(windiff(sub[sub.dlen>0])); WS.append(windiff(sub[sub.dlen<0]))
    def ci(v):
        lo,hi=np.nanpercentile(v,[2.5,97.5]); return [round(float(lo),3),round(float(hi),3)]
    return dict(
        n=int(len(df_ax)), n_longer=int((df_ax.dlen>0).sum()), n_shorter=int((df_ax.dlen<0).sum()),
        raw_mean_dscore=round(float(raw),3), raw_ci=ci(RAW),
        adj_intercept=round(float(a0),3), adj_intercept_ci=ci(A),
        slope_per_1k=round(float(b0),3), slope_ci=ci(B),
        windiff_all=round(float(wd0),1), windiff_ci=ci(WD),
        windiff_OElonger=round(float(wl0),1), windiff_OElonger_ci=ci(WL),
        windiff_OEshorter=round(float(ws0),1), windiff_OEshorter_ci=ci(WS),
    )

def main():
    length,g=load()
    df=build_pairs(length,g)
    ans=pd.read_parquet(os.path.join(DATA,'answers.parquet')); ans['clen']=ans.answer_markdown.str.len()
    qs=set(df.question_id.unique())
    lenstats=ans[ans.question_id.isin(qs)].groupby('provider_key').clen.agg(['mean','median']).round(0)
    print("=== (1) answer length by system (chars), on the graded question set ===")
    print(lenstats.to_string()); print()
    print(f"OE is the {'LONGEST' if lenstats.loc[OE,'median']>=lenstats['median'].max() else 'NOT longest'} provider by median.\n")

    res={}
    print(f"{'axis':16s}{'rawΔ(OE-opp)':>14s}{'len-adj intcpt [95CI]':>26s}{'slope/1k':>10s}"
          f"{'  wd_all':>8s}{'  wd_long':>9s}{'  wd_short':>10s}")
    for ax in AXES:
        r=boot_axis(df[df.axis==ax]); res[ax]=r
        ic="%+.2f [%+.2f,%+.2f]"%(r['adj_intercept'],*r['adj_intercept_ci'])
        print(f"{ax:16s}{r['raw_mean_dscore']:>+14.3f}{ic:>26s}{r['slope_per_1k']:>+10.3f}"
              f"{r['windiff_all']:>+8.1f}{r['windiff_OElonger']:>+9.1f}{r['windiff_OEshorter']:>+10.1f}")

    out=dict(nboot=NBOOT, length_median={k:float(v) for k,v in lenstats['median'].items()},
             length_mean={k:float(v) for k,v in lenstats['mean'].items()},
             oe_is_longest=bool(lenstats.loc[OE,'median']>=lenstats['median'].max()),
             per_axis=res)
    json.dump(out,open(os.path.join(OUT,'length_results.json'),'w'),indent=2)
    print("\nwrote out/length_results.json")

    print("\n=== READING ===")
    acc=res['accuracy']
    print(f"accuracy: raw OE-opp gap {acc['raw_mean_dscore']:+.3f} pts; length-ADJUSTED intercept "
          f"{acc['adj_intercept']:+.3f} [{acc['adj_intercept_ci'][0]:+.3f},{acc['adj_intercept_ci'][1]:+.3f}]. "
          f"win-diff: all {acc['windiff_all']:+.0f}, OE-longer {acc['windiff_OElonger']:+.0f}, "
          f"OE-shorter {acc['windiff_OEshorter']:+.0f}.")

if __name__=='__main__': main()
