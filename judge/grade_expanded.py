"""Re-grade LLM rubric cell C with the EXPANDED per-score anchors (identical to the physician rubric).

Makes cell C (LLM rubric) and cell D (physician rubric) use the SAME instructions, so D vs C is a clean
rater contrast rather than a rater+anchor-detail contrast. Same answers, same five axes, same 1-4 scale as
grade.py, but the system prompt embeds the per-score anchors from judge/rubric_anchors.py (which the
physician workbook also renders).

** NOT RUN here (needs the four judge API keys; costs spend). ** Cost is ~the original cell C: 150 questions
x 4 systems x 4 judges = ~2,400 calls (~6-7M tokens); ~$40-90 under current per-token pricing (verify + rotate
keys first). Resumable: appends to out/grades_expanded.jsonl. After running, re-point the cell-C loaders at
grades_expanded.jsonl to recompute C / the C-vs-D comparison.

Usage: python3 grade_expanded.py --n 150 --workers 8
"""
import os, re, json, argparse, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import providers as P
from rubric_anchors import AXES, system_prompt
from blinding import render_blinded_answer   # SAME rendering the physician cells (A'/D) see

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
GRADES = os.path.join(OUT, 'grades_expanded.jsonl')
JUDGES = ['gpt-5.5', 'opus-4.8', 'grok-4.3', 'gemini-3.5-flash']
SYSTEM = system_prompt()
PROVS = ['openevidence', 'gpt-5.5', 'claude-opus-4-8', 'gemini-3.1-pro']


def make_user(q, ans):
    return f"CLINICAL QUESTION:\n{q}\n\nAI ANSWER TO EVALUATE:\n{ans}\n\nReturn the JSON scores now."


def parse_scores(txt):
    if not txt:
        return None
    m = re.search(r'\{[^{}]*\}', txt, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    out = {}
    for ax in AXES:
        v = d.get(ax)
        if not isinstance(v, (int, float)) or not (1 <= v <= 4):
            return None
        out[ax] = int(round(v))
    return out


_lock = threading.Lock()
def append_row(row):
    with _lock:
        with open(GRADES, 'a') as f:
            f.write(json.dumps(row) + "\n")


def done_set():
    s = set()
    if os.path.exists(GRADES):
        for line in open(GRADES):
            try:
                r = json.loads(line)
                if r.get('scores'):
                    s.add((r['question_id'], r['provider_key'], r['judge']))
            except Exception:
                pass
    return s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=150)
    ap.add_argument('--workers', type=int, default=8); ap.add_argument('--seed', type=int, default=62)
    a = ap.parse_args()
    keys = P.load_keys()
    q = pd.read_parquet(os.path.join(DATA, 'questions.parquet'))
    ans = pd.read_parquet(os.path.join(DATA, 'answers.parquet'))
    qs = q.sample(n=min(a.n, len(q)), random_state=a.seed).question_id.tolist()
    ans = ans[ans.question_id.isin(qs)].merge(q[['question_id', 'question_text']], on='question_id')
    already = done_set()
    tasks = [(r.question_id, r.provider_key, j, r.question_text, r.answer_markdown)
             for _, r in ans.iterrows() for j in JUDGES
             if (r.question_id, r.provider_key, j) not in already]
    print(f"{len(tasks)} calls to make ({len(already)} done); prompt uses EXPANDED anchors")
    if not tasks:
        print("nothing to do"); return
    t0 = time.time(); ok = fail = 0

    def work(t):
        qid, prov, j, qt, at = t
        at = render_blinded_answer(at)   # identical rendering to physician cells (A'/D)
        txt, meta = P.call(j, SYSTEM, make_user(qt, at), keys, high=True, max_tokens=500)
        sc = parse_scores(txt)
        append_row(dict(question_id=qid, provider_key=prov, judge=j, scores=sc,
                        err=None if sc else str(meta)[:200]))
        return sc is not None

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, f in enumerate(as_completed([ex.submit(work, t) for t in tasks]), 1):
            r = f.result(); ok += r; fail += (not r)
            if i % 20 == 0 or i == len(tasks):
                print(f"  {i}/{len(tasks)} ok={ok} fail={fail} {time.time()-t0:.0f}s")
    print(f"DONE ok={ok} fail={fail}")


if __name__ == '__main__':
    main()
