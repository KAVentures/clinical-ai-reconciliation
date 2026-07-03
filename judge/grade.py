"""LLM-judge absolute-rubric grading of Real-POCQi answers (blinded).
Instrument = absolute 1-4 per axis (Nature-style), vs the human PAIRWISE preference
already in the dataset. Isolates the evaluation INSTRUMENT (queries+answers held fixed).
Resumable: appends one JSON row per (question, provider, judge) to out/grades.jsonl.
Usage: python3 grade.py --n 20 --workers 5   (pilot)
       python3 grade.py --n 620 --workers 8  (full)
"""
import os, re, json, argparse, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import providers as P

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
OUT  = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
GRADES = os.path.join(OUT, 'grades.jsonl')
AXES = ['accuracy','clinical_utility','source_quality','completeness','verifiability']
JUDGES = ['gpt-5.5','opus-4.8','grok-4.3','gemini-3.5-flash']
# map judge -> provider family it belongs to (for self-preference), None if no contestant match
JUDGE_FAMILY = {'gpt-5.5':'gpt-5.5','opus-4.8':'claude-opus-4-8',
                'grok-4.3':None,'gemini-3.5-flash':'gemini-3.1-pro'}

SYSTEM = (
"You are an expert U.S. physician evaluating a single AI-generated answer to a real "
"point-of-care clinical question from a practicing clinician. You are blinded to which "
"system produced the answer. Score the answer on five axes, each on an integer 1-4 scale:\n"
"  1 = unacceptable, 2 = marginal, 3 = good, 4 = excellent.\n"
"Axes:\n"
"  accuracy: factual and clinical correctness of the claims.\n"
"  clinical_utility: usefulness for delivering high-quality clinical care.\n"
"  source_quality: quality/authority of the evidence and reasoning offered.\n"
"  completeness: comprehensiveness given what the question asks.\n"
"  verifiability: how easily a clinician could verify the answer's claims.\n"
"Judge only the answer's content. Respond with ONLY a JSON object, no prose, e.g. "
'{"accuracy":3,"clinical_utility":4,"source_quality":2,"completeness":3,"verifiability":2}')

def make_user(q, ans):
    return f"CLINICAL QUESTION:\n{q}\n\nAI ANSWER TO EVALUATE:\n{ans}\n\nReturn the JSON scores now."

def parse_scores(txt):
    if not txt: return None
    m = re.search(r'\{[^{}]*\}', txt, re.S)
    if not m: return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    alias = {'verifiable':'verifiability','verifiability':'verifiability','utility':'clinical_utility',
             'clinical_utility':'clinical_utility','accuracy':'accuracy','source_quality':'source_quality',
             'completeness':'completeness'}
    dn = {alias.get(k,k):v for k,v in d.items()}
    out = {}
    for ax in AXES:
        v = dn.get(ax)
        if not isinstance(v,(int,float)) or not (1 <= v <= 4): return None
        out[ax] = int(round(v))
    return out

_lock = threading.Lock()
def append_row(row):
    with _lock:
        with open(GRADES,'a') as f: f.write(json.dumps(row)+"\n")

def done_set():
    s=set()
    if os.path.exists(GRADES):
        for line in open(GRADES):
            try:
                r=json.loads(line)
                if r.get('scores'): s.add((r['question_id'],r['provider_key'],r['judge']))
            except Exception: pass
    return s

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--n',type=int,default=20)
    ap.add_argument('--workers',type=int,default=5); ap.add_argument('--seed',type=int,default=62)
    a=ap.parse_args()
    keys=P.load_keys()
    q=pd.read_parquet(os.path.join(DATA,'questions.parquet'))
    ans=pd.read_parquet(os.path.join(DATA,'answers.parquet'))
    qs=q.sample(n=min(a.n,len(q)),random_state=a.seed).question_id.tolist()
    ans=ans[ans.question_id.isin(qs)].merge(q[['question_id','question_text']],on='question_id')
    already=done_set()
    tasks=[]
    for _,row in ans.iterrows():
        for j in JUDGES:
            key=(row.question_id,row.provider_key,j)
            if key in already: continue
            tasks.append((row.question_id,row.provider_key,j,row.question_text,row.answer_markdown))
    print(f"questions={len(qs)} answers={len(ans)} judges={len(JUDGES)} -> {len(tasks)} calls to make "
          f"({len(already)} already done)")
    if not tasks: print("nothing to do"); return
    t0=time.time(); n_ok=0; n_fail=0
    def work(t):
        qid,prov,j,qt,at=t
        txt,meta=P.call(j,SYSTEM,make_user(qt,at),keys,high=True,max_tokens=400)
        sc=parse_scores(txt)
        append_row(dict(question_id=qid,provider_key=prov,judge=j,scores=sc,
                        err=None if sc else (meta.get('__error__') if isinstance(meta,dict) else str(meta)),
                        raw=None if sc else (txt[:200] if txt else None)))
        return sc is not None
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs=[ex.submit(work,t) for t in tasks]
        for i,f in enumerate(as_completed(futs),1):
            ok=f.result(); n_ok+=ok; n_fail+=(not ok)
            if i%20==0 or i==len(tasks):
                el=time.time()-t0
                print(f"  {i}/{len(tasks)}  ok={n_ok} fail={n_fail}  {el:.0f}s  ({el/i:.1f}s/call)")
    print(f"DONE ok={n_ok} fail={n_fail} in {time.time()-t0:.0f}s")

if __name__=="__main__": main()
