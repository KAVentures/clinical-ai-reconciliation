"""LLM-judge FORCED-CHOICE PAIRWISE grading (the {pairwise, LLM} cell).
Breaks the human-vs-LLM rater confound: same 150 questions, same 4 judges at high reasoning,
but now the instrument is blinded pairwise preference (matching Real-POCQi's human instrument)
instead of the absolute rubric. Each judge compares OpenEvidence vs each frontier system on the
SAME five axes and picks A / B / tie per axis. Slot order is randomized per (question,opponent,judge)
deterministically (reproducible) to remove position bias, and de-blinded at scoring time.
Resumable: one JSON row per (question, opponent, judge) -> out/pairwise.jsonl.
Usage: python3 pairwise.py --n 150 --workers 12
"""
import os, re, json, argparse, threading, time, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import providers as P

HERE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(HERE,'..','data')
OUT=os.path.join(HERE,'out'); os.makedirs(OUT,exist_ok=True)
PAIRS=os.path.join(OUT,'pairwise.jsonl')
AXES=['accuracy','clinical_utility','source_quality','completeness','verifiability']
JUDGES=['gpt-5.5','opus-4.8','grok-4.3','gemini-3.5-flash']
FRONTIER=['gpt-5.5','claude-opus-4-8','gemini-3.1-pro']  # opponents OE is compared against

SYSTEM=(
"You are an expert U.S. physician comparing TWO AI-generated answers (labeled A and B) to the same "
"real point-of-care clinical question from a practicing clinician. You are blinded to which system "
"produced each answer. For EACH of five axes, decide which answer is better, or whether they tie:\n"
"  accuracy: factual and clinical correctness of the claims.\n"
"  clinical_utility: usefulness for delivering high-quality clinical care.\n"
"  source_quality: quality/authority of the evidence and reasoning offered.\n"
"  completeness: comprehensiveness given what the question asks.\n"
"  verifiability: how easily a clinician could verify the answer's claims.\n"
"Judge only content, not length or formatting per se. Respond with ONLY a JSON object mapping each "
'axis to "A", "B", or "tie", e.g. '
'{"accuracy":"A","clinical_utility":"tie","source_quality":"B","completeness":"A","verifiability":"tie"}')

def make_user(q, a_text, b_text):
    return (f"CLINICAL QUESTION:\n{q}\n\nANSWER A:\n{a_text}\n\nANSWER B:\n{b_text}\n\n"
            "Return the JSON verdicts now.")

def oe_in_slot_a(qid, opp, judge):
    h=hashlib.sha1(f"{qid}|{opp}|{judge}".encode()).hexdigest()
    return int(h,16)%2==0

def _norm_verdict(v):
    if not isinstance(v,str): return None
    vv=v.strip().upper()
    if vv in ('A','B','TIE'): return vv
    if vv in ('TIE.','TIED','TIE,','NEITHER','EQUAL'): return 'TIE'
    if vv.startswith('A'): return 'A'
    if vv.startswith('B'): return 'B'
    return None

def _canon_axis(k):
    """Map a (possibly aliased) JSON key to one of AXES by substring; robust to
    Gemini variants like 'verifiable_quality', 'utility', 'clinical utility'."""
    kk=k.lower().replace(' ','_')
    if 'accura' in kk: return 'accuracy'
    if 'verifiab' in kk: return 'verifiability'
    if 'complet' in kk: return 'completeness'
    if 'source' in kk: return 'source_quality'
    if 'utilit' in kk or 'clinical' in kk: return 'clinical_utility'
    return None

def parse_choices(txt):
    if not txt: return None
    out={}
    # primary path: parse the first balanced JSON object
    m=re.search(r'\{[^{}]*\}',txt,re.S)
    if m:
        try:
            d=json.loads(m.group(0))
            for k,v in d.items():
                ax=_canon_axis(k); vv=_norm_verdict(v)
                if ax and vv and ax not in out: out[ax]=vv
        except Exception:
            pass
    # fallback: per-axis "key": "verdict" regex — recovers truncated / brace-less output
    if len(out)<len(AXES):
        for k,v in re.findall(r'"([a-zA-Z_ ]+?)"\s*:\s*"([^"]+)"',txt):
            ax=_canon_axis(k); vv=_norm_verdict(v)
            if ax and vv and ax not in out: out[ax]=vv
    return out if len(out)==len(AXES) else None

_lock=threading.Lock()
def append_row(row):
    with _lock:
        with open(PAIRS,'a') as f: f.write(json.dumps(row)+"\n")

def done_set():
    s=set()
    if os.path.exists(PAIRS):
        for line in open(PAIRS):
            try:
                r=json.loads(line)
                if r.get('choices'): s.add((r['question_id'],r['opponent'],r['judge']))
            except Exception: pass
    return s

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--n',type=int,default=150)
    ap.add_argument('--workers',type=int,default=12); ap.add_argument('--seed',type=int,default=62)
    a=ap.parse_args()
    keys=P.load_keys()
    q=pd.read_parquet(os.path.join(DATA,'questions.parquet'))
    ans=pd.read_parquet(os.path.join(DATA,'answers.parquet'))
    qs=q.sample(n=min(a.n,len(q)),random_state=a.seed).question_id.tolist()  # SAME sample as grade.py
    amap={(r.question_id,r.provider_key):r.answer_markdown for _,r in ans.iterrows()}
    qtext={r.question_id:r.question_text for _,r in q.iterrows()}
    already=done_set()
    tasks=[]
    for qid in qs:
        if ('openevidence' not in [k[1] for k in amap if k[0]==qid]): continue
        for opp in FRONTIER:
            if (qid,opp) not in amap or (qid,'openevidence') not in amap: continue
            for j in JUDGES:
                if (qid,opp,j) in already: continue
                tasks.append((qid,opp,j))
    print(f"questions={len(qs)} opponents={len(FRONTIER)} judges={len(JUDGES)} -> {len(tasks)} calls "
          f"({len(already)} already done)")
    if not tasks: print("nothing to do"); return
    t0=time.time(); n_ok=0; n_fail=0
    def work(t):
        qid,opp,j=t
        oe=amap[(qid,'openevidence')]; fr=amap[(qid,opp)]
        oeA=oe_in_slot_a(qid,opp,j)
        a_text,b_text=(oe,fr) if oeA else (fr,oe)
        txt,meta=P.call(j,SYSTEM,make_user(qtext[qid],a_text,b_text),keys,high=True,max_tokens=900)
        ch=parse_choices(txt)
        # de-blind: map A/B verdict to OE win/loss/tie
        oe_res=None
        if ch:
            oe_res={}
            for ax,v in ch.items():
                if v=='TIE': oe_res[ax]='tie'
                elif (v=='A')==oeA: oe_res[ax]='oe'      # winner slot holds OE
                else: oe_res[ax]='opp'
        append_row(dict(question_id=qid,opponent=opp,judge=j,oe_slot='A' if oeA else 'B',
                        choices=ch,oe_result=oe_res,
                        err=None if ch else (meta.get('__error__') if isinstance(meta,dict) else str(meta)),
                        raw=None if ch else (txt[:200] if txt else None)))
        return ch is not None
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs=[ex.submit(work,t) for t in tasks]
        for i,f in enumerate(as_completed(futs),1):
            ok=f.result(); n_ok+=ok; n_fail+=(not ok)
            if i%50==0 or i==len(tasks):
                el=time.time()-t0
                print(f"  {i}/{len(tasks)}  ok={n_ok} fail={n_fail}  {el:.0f}s  ({el/i:.1f}s/call)")
    print(f"DONE ok={n_ok} fail={n_fail} in {time.time()-t0:.0f}s")

if __name__=="__main__": main()
