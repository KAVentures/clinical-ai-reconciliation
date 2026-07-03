"""2x2 decomposition: separate the RATER MODALITY effect from the INSTRUMENT FORMAT effect.
Three of the four {pairwise,rubric} x {human,LLM} cells are available:
  A = {pairwise, human}  -> from Real-POCQi ratings (dataset)          e.g. accuracy +24.4
  B = {pairwise, LLM}    -> from out/pairwise.jsonl (this run)          <- NEW, breaks the confound
  C = {rubric,  LLM}     -> from out/grades.jsonl (bootstrap_results)   e.g. accuracy -29.1
Decomposition of the A->C swing:
  rater-modality effect  (holding instrument=pairwise) = B - A
  instrument-format effect (holding rater=LLM)          = C - B
Writes out/pairwise_results.json and prints a table with 95% cluster-bootstrap CIs."""
import os, json
import numpy as np, pandas as pd

HERE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(HERE,'..','data'); OUT=os.path.join(HERE,'out')
AXES=['accuracy','clinical_utility','source_quality','completeness','verifiability']
FRONTIER=['gpt-5.5','claude-opus-4-8','gemini-3.1-pro']
RNG=np.random.default_rng(62); NBOOT=2000

# ---- cell A: human pairwise (text-only), OE-vs-rest win-diff (matches analyze_grades) ----
# IMPORTANT: cell A MUST be computed on the SAME question set as cells B and C, otherwise B-A
# ("rater modality") silently absorbs a sample-composition difference (150 sampled q vs the full
# text-only bank). Pass qids = the questions actually graded in cells B/C.
def cellA_human(qids=None):
    r=pd.read_parquet(os.path.join(DATA,'ratings.parquet'))
    r=r[r.render_mode=='qa_text_only']
    if qids is not None:
        r=r[r.question_id.isin(set(qids))]
    pref={'strongly_a':'a','slightly_a':'a','strongly_b':'b','slightly_b':'b','tie':None}
    r['pref']=r.choice.map(pref)
    r['pp']=r.apply(lambda x:x.slot_a_provider if x.pref=='a' else (x.slot_b_provider if x.pref=='b' else None),axis=1)
    out={}
    for ax in AXES:
        d=r[r.axis==ax]; sub=d[(d.slot_a_provider=='openevidence')|(d.slot_b_provider=='openevidence')]
        o=np.where(sub.pp=='openevidence',1.0,np.where(sub.pp.isna(),0.0,-1.0))
        out[ax]=round(100*o.mean(),1)
    return out

# ---- cell B: LLM pairwise, per-(question,opponent,judge,axis) OE result ----
def load_pairwise():
    rows=[]
    for line in open(os.path.join(OUT,'pairwise.jsonl')):
        r=json.loads(line)
        if r.get('oe_result'):
            for ax,res in r['oe_result'].items():
                rows.append(dict(question_id=r['question_id'],opponent=r['opponent'],
                                 judge=r['judge'],axis=ax,res=res))
    return pd.DataFrame(rows)

def windiff_pairwise(df, qids=None):
    """OE-vs-rest win-diff per axis: 100*(wins-losses)/N over all comparisons; optional question subset."""
    if qids is not None: df=df[df.question_id.isin(qids)]
    out={}
    for ax in AXES:
        d=df[df.axis==ax]
        w=(d.res=='oe').sum(); l=(d.res=='opp').sum(); n=len(d)
        out[ax]=100*(w-l)/n if n else np.nan
    return out

def boot_pairwise(df):
    qids=df.question_id.unique()
    point=windiff_pairwise(df)
    # pre-group by question for speed
    byq={q:df[df.question_id==q] for q in qids}
    res={ax:[] for ax in AXES}
    for _ in range(NBOOT):
        samp=RNG.choice(qids,size=len(qids),replace=True)
        sub=pd.concat([byq[q] for q in samp],ignore_index=True)
        wd=windiff_pairwise(sub)
        for ax in AXES: res[ax].append(wd[ax])
    out={}
    for ax in AXES:
        lo,hi=np.nanpercentile(res[ax],[2.5,97.5])
        out[ax]=dict(point=round(point[ax],1),lo=round(lo,1),hi=round(hi,1))
    return out

def main():
    dfB=load_pairwise()
    nB_q=dfB.question_id.nunique()
    qidsB=dfB.question_id.unique()
    # cell A on the SAME questions as B/C (not the full text-only bank)
    A=cellA_human(qids=qidsB)
    A_full=cellA_human()  # kept for reference: published-style full text-only win-diff
    r_all=pd.read_parquet(os.path.join(DATA,'ratings.parquet'))
    nA_q=r_all[(r_all.render_mode=='qa_text_only')&(r_all.question_id.isin(set(qidsB)))].question_id.nunique()
    B=boot_pairwise(dfB)
    # cell C from existing bootstrap_results
    C=json.load(open(os.path.join(OUT,'bootstrap_results.json')))['llm_panel_ci']

    print(f"cell A restricted to the {nA_q} of {nB_q} graded questions that have human text-only ratings.")
    print(f"  cell A (same-150 subset): {A}")
    print(f"  cell A (full text-only bank, reference only): {A_full}\n")
    print(f"cell B (LLM pairwise): {len(dfB)} axis-verdicts over {nB_q} questions, {NBOOT} bootstrap\n")
    print(f"{'axis':16s}{'A pairwise/human':>18s}{'B pairwise/LLM [CI]':>26s}{'C rubric/LLM':>16s}")
    for ax in AXES:
        b=B[ax]; c=C[ax]
        bstr="%+.1f [%+.1f,%+.1f]"%(b['point'],b['lo'],b['hi'])
        print(f"{ax:16s}{A[ax]:>+18.1f}{bstr:>26s}{c['point']:>+16.1f}")

    print("\n=== DECOMPOSITION of the human-pairwise -> LLM-rubric swing (A -> C) ===")
    print(f"{'axis':16s}{'total A->C':>12s}{'rater (B-A)':>14s}{'instrument (C-B)':>18s}")
    dec={}
    for ax in AXES:
        tot=C[ax]['point']-A[ax]
        rater=B[ax]['point']-A[ax]
        instr=C[ax]['point']-B[ax]['point']
        dec[ax]=dict(total=round(tot,1),rater=round(rater,1),instrument=round(instr,1))
        print(f"{ax:16s}{tot:>+12.1f}{rater:>+14.1f}{instr:>+18.1f}")

    # per-judge cell B (accuracy) to see if pairwise LLM already disagrees with humans
    print("\n=== cell B per judge (win-diff, all axes) ===")
    for j in sorted(dfB.judge.unique()):
        wd=windiff_pairwise(dfB[dfB.judge==j])
        print(f"  {j:16s} " + "  ".join(f"{ax[:4]}={wd[ax]:+.0f}" for ax in AXES))

    json.dump(dict(n_questions=nB_q,n_questions_cellA=nA_q,nboot=NBOOT,
                   cellA_pairwise_human=A,cellA_pairwise_human_fullbank=A_full,
                   cellB_pairwise_llm=B,cellC_rubric_llm=C,
                   decomposition=dec),
              open(os.path.join(OUT,'pairwise_results.json'),'w'),indent=2)
    print("\nwrote out/pairwise_results.json")

if __name__=="__main__": main()
