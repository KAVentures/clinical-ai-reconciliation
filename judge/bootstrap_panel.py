"""Panel-composition uncertainty: crossed question x judge bootstrap.

The published CIs (bootstrap_grades.py, analyze_pairwise.py) resample only QUESTIONS and treat
the four judges as a fixed population. A skeptic's real worry is judge composition: 3 of 4 judges
are contestant families and GPT-5.5 self-prefers by ~+0.48 pts. This script re-does the cell-C
rubric win-diff and the A->C decomposition with a *crossed* bootstrap that resamples BOTH questions
(cluster on question_id) AND judges (with replacement from the 4), so every CI reflects "how stable
across choice of judges" in addition to "how stable across questions". Judges are resampled ONCE per
replicate and applied consistently to cells B and C (they are the same 4 judges in both instruments);
cell A is human (no judge dimension) and takes question resampling only.

No API calls: operates entirely on out/grades.jsonl, out/pairwise.jsonl, and data/ratings.parquet.
Writes out/panel_bootstrap.json."""
import os, json, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore", category=RuntimeWarning)  # empty-slice nanmean on missing cells
HERE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(HERE,'..','data'); OUT=os.path.join(HERE,'out')
AXES=['accuracy','clinical_utility','source_quality','completeness','verifiability']
FRONTIER=['gpt-5.5','claude-opus-4-8','gemini-3.1-pro']
PROVS=['openevidence']+FRONTIER
RNG=np.random.default_rng(62); NBOOT=2000

# ---------- load raw cells ----------
def load_gradesC():
    """cell C rubric: array score[axis][qid_idx, prov_idx, judge_idx] (NaN if missing)."""
    rows=[]
    for line in open(os.path.join(OUT,'grades.jsonl')):
        r=json.loads(line)
        if r.get('scores'):
            for ax in AXES:
                rows.append((r['question_id'],r['provider_key'],r['judge'],ax,r['scores'][ax]))
    df=pd.DataFrame(rows,columns=['qid','prov','judge','axis','score'])
    qids=sorted(df.qid.unique()); judges=sorted(df.judge.unique())
    qi={q:i for i,q in enumerate(qids)}; pi={p:i for i,p in enumerate(PROVS)}; ji={j:i for i,j in enumerate(judges)}
    S={ax:np.full((len(qids),len(PROVS),len(judges)),np.nan) for ax in AXES}
    for q,p,j,ax,sc in rows:
        if p in pi: S[ax][qi[q],pi[p],ji[j]]=sc
    return S,qids,judges,qi

def load_pairwiseB(qids,judges):
    """cell B LLM pairwise: per axis, arrays of (qidx, jidx, o) with o in {+1 oe, -1 opp, 0 tie}."""
    qi={q:i for i,q in enumerate(qids)}; ji={j:i for i,j in enumerate(judges)}
    rows={ax:[] for ax in AXES}
    for line in open(os.path.join(OUT,'pairwise.jsonl')):
        r=json.loads(line)
        if not r.get('oe_result'): continue
        q=r['question_id']; j=r['judge']
        if q not in qi or j not in ji: continue
        for ax,res in r['oe_result'].items():
            o=1 if res=='oe' else (-1 if res=='opp' else 0)
            rows[ax].append((qi[q],ji[j],o))
    return {ax:(np.array([x[0] for x in rows[ax]]),
               np.array([x[1] for x in rows[ax]]),
               np.array([x[2] for x in rows[ax]],dtype=float)) for ax in AXES}

def load_humanA(qids):
    """cell A human pairwise (text-only) on the SAME questions: per axis (qidx, o)."""
    qi={q:i for i,q in enumerate(qids)}
    r=pd.read_parquet(os.path.join(DATA,'ratings.parquet'))
    r=r[(r.render_mode=='qa_text_only')&(r.question_id.isin(set(qids)))]
    pref={'strongly_a':1,'slightly_a':1,'strongly_b':-1,'slightly_b':-1,'tie':0}
    out={}
    for ax in AXES:
        d=r[r.axis==ax]; sub=d[(d.slot_a_provider=='openevidence')|(d.slot_b_provider=='openevidence')]
        qidx=[]; ov=[]
        for _,x in sub.iterrows():
            pr=pref.get(x.choice)
            if pr is None: continue  # unknown choice label -> skip
            if pr==0: o=0
            else:
                winner=x.slot_a_provider if pr==1 else x.slot_b_provider
                o=1 if winner=='openevidence' else -1
            qidx.append(qi[x.question_id]); ov.append(o)
        out[ax]=(np.array(qidx),np.array(ov,dtype=float))
    return out

# ---------- win-diff under multiplicity weights ----------
def wd_C(S_ax, cj, cq):
    """cell C win-diff for one axis given judge weights cj (len nJ) and question weights cq (len nQ)."""
    m=~np.isnan(S_ax)                       # (nQ,nP,nJ)
    w=cj[None,None,:]
    den=np.sum(m*w,axis=2)                  # (nQ,nP)
    num=np.nansum(np.where(m,S_ax,0.0)*w,axis=2)
    with np.errstate(invalid='ignore'): M=np.where(den>0,num/den,np.nan)  # weighted panel mean
    oe=M[:,0]; W=L=N=0.0
    for fp in range(1,len(PROVS)):
        fr=M[:,fp]; valid=~np.isnan(oe)&~np.isnan(fr)
        d=oe-fr
        W+=np.sum(cq[valid]*(d[valid]>0)); L+=np.sum(cq[valid]*(d[valid]<0)); N+=np.sum(cq[valid])
    return 100*(W-L)/N if N else np.nan

def wd_B(B_ax, cj, cq):
    qidx,jidx,o=B_ax
    w=cq[qidx]*cj[jidx]
    W=np.sum(w*(o>0)); L=np.sum(w*(o<0)); N=np.sum(w)
    return 100*(W-L)/N if N else np.nan

def wd_A(A_ax, cq):
    qidx,o=A_ax
    if len(qidx)==0: return np.nan
    w=cq[qidx]; return 100*np.sum(w*o)/np.sum(w)

def counts(n): return np.bincount(RNG.integers(0,n,n),minlength=n).astype(float)

def ci(a):
    a=np.asarray(a); a=a[~np.isnan(a)]
    return round(float(np.percentile(a,2.5)),1),round(float(np.percentile(a,97.5)),1)

def main():
    S,qids,judges,qi=load_gradesC(); nQ=len(qids); nJ=len(judges)
    B=load_pairwiseB(qids,judges); A=load_humanA(qids)
    ones_q=np.ones(nQ); ones_j=np.ones(nJ)

    # ----- point estimates (all weights = 1) -----
    ptC={ax:wd_C(S[ax],ones_j,ones_q) for ax in AXES}
    ptB={ax:wd_B(B[ax],ones_j,ones_q) for ax in AXES}
    ptA={ax:wd_A(A[ax],ones_q) for ax in AXES}

    # ----- bootstraps -----
    qonly={ax:[] for ax in AXES}      # cell C, questions only (reproduces published CI)
    jonly={ax:[] for ax in AXES}      # cell C, judges only
    crossC={ax:[] for ax in AXES}     # cell C, crossed q x judge  <-- item 1
    raterD={ax:[] for ax in AXES}     # B-A, crossed
    instrD={ax:[] for ax in AXES}     # C-B, crossed
    accfrac=[]                        # instrument share of accuracy swing (C-B)/(C-A)
    for _ in range(NBOOT):
        cq=counts(nQ); cj=counts(nJ)
        for ax in AXES:
            qonly[ax].append(wd_C(S[ax],ones_j,cq))
            jonly[ax].append(wd_C(S[ax],cj,ones_q))
            c=wd_C(S[ax],cj,cq); b=wd_B(B[ax],cj,cq); a=wd_A(A[ax],cq)
            crossC[ax].append(c)
            raterD[ax].append(b-a); instrD[ax].append(c-b)
            if ax=='accuracy':
                tot=c-a
                accfrac.append(100*(c-b)/tot if abs(tot)>1e-9 else np.nan)

    out={'nboot':NBOOT,'n_questions':nQ,'judges':judges,'point':{
            ax:dict(A=round(ptA[ax],1),B=round(ptB[ax],1),C=round(ptC[ax],1),
                    rater=round(ptB[ax]-ptA[ax],1),instrument=round(ptC[ax]-ptB[ax],1)) for ax in AXES}}
    print(f"n_questions={nQ}  judges={judges}  nboot={NBOOT}\n")
    print("=== cell C (rubric) win-diff: question-only vs judge-only vs CROSSED question x judge ===")
    print(f"{'axis':16s}{'point':>8s}{'Q-only CI':>20s}{'J-only CI':>20s}{'CROSSED CI':>20s}{'excl 0?':>9s}")
    out['cellC']={}
    for ax in AXES:
        qc=ci(qonly[ax]); jc=ci(jonly[ax]); cc=ci(crossC[ax])
        excl='yes' if (cc[0]>0 or cc[1]<0) else 'NO'
        out['cellC'][ax]=dict(point=round(ptC[ax],1),q_only_ci=qc,j_only_ci=jc,crossed_ci=cc,crossed_excl0=(excl=='yes'))
        print(f"{ax:16s}{ptC[ax]:>+8.1f}{str(qc):>20s}{str(jc):>20s}{str(cc):>20s}{excl:>9s}")

    print("\n=== A->C decomposition with CROSSED (q x judge) 95% CIs ===")
    print(f"{'axis':16s}{'rater(B-A)':>14s}{'rater CI':>18s}{'instr(C-B)':>14s}{'instr CI':>18s}")
    out['decomposition']={}
    for ax in AXES:
        rc=ci(raterD[ax]); ic=ci(instrD[ax])
        out['decomposition'][ax]=dict(rater=round(ptB[ax]-ptA[ax],1),rater_ci=rc,
                                       instrument=round(ptC[ax]-ptB[ax],1),instrument_ci=ic)
        print(f"{ax:16s}{ptB[ax]-ptA[ax]:>+14.1f}{str(rc):>18s}{ptC[ax]-ptB[ax]:>+14.1f}{str(ic):>18s}")

    af=np.asarray(accfrac); af=af[~np.isnan(af)]
    frac_pt=100*(ptC['accuracy']-ptB['accuracy'])/(ptC['accuracy']-ptA['accuracy'])
    out['accuracy_instrument_fraction']=dict(point=round(frac_pt,1),
        ci=[round(float(np.percentile(af,2.5)),1),round(float(np.percentile(af,97.5)),1)],
        median=round(float(np.median(af)),1))
    print(f"\naccuracy instrument fraction (C-B)/(C-A): point {frac_pt:.0f}%  "
          f"median {np.median(af):.0f}%  95% CI [{np.percentile(af,2.5):.0f}%, {np.percentile(af,97.5):.0f}%]")

    json.dump(out,open(os.path.join(OUT,'panel_bootstrap.json'),'w'),indent=2)
    print("\nwrote out/panel_bootstrap.json")

if __name__=="__main__": main()
