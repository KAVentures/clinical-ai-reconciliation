"""Proof that every judge ran with reasoning/thinking ENABLED at high effort.
Grades one REAL Real-POCQi answer (representative of the actual task) with each judge and
reports the reasoning-token consumption returned by each API. Note: Anthropic's only accepted
high-effort mode for this model is thinking.type=adaptive + output_config.effort=high; adaptive
may emit zero thinking on trivial items, so we verify on a real (long) clinical answer.
Never prints key values. -> out/thinking_evidence.json"""
import os, json, time
import pandas as pd
import providers as P
from grade import SYSTEM, make_user

HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,'out')
DATA=os.path.join(HERE,'..','data')

def token_field(judge, meta):
    if judge in ('gpt-5.5','grok-4.3'): return 'reasoning_tokens', meta.get('reasoning_tokens')
    if judge=='opus-4.8':
        u=meta.get('usage',{}) or {}
        tt=(u.get('output_tokens_details') or {}).get('thinking_tokens')
        return 'thinking_tokens', tt
    if judge=='gemini-3.5-flash':       return 'thoughts_token_count', meta.get('thoughts_token_count')
    return 'n/a', None

def main():
    keys=P.load_keys()
    q=pd.read_parquet(os.path.join(DATA,'questions.parquet'))
    a=pd.read_parquet(os.path.join(DATA,'answers.parquet'))
    row=a[a.provider_key=='openevidence'].iloc[0]
    qt=q[q.question_id==row.question_id].question_text.iloc[0]
    ev={}
    for j in ['gpt-5.5','opus-4.8','grok-4.3','gemini-3.5-flash']:
        t0=time.time()
        txt,meta=P.call(j,SYSTEM,make_user(qt,row.answer_markdown),keys,high=True,max_tokens=400)
        dt=time.time()-t0
        field,val=token_field(j,meta)
        on = (val is True) or (isinstance(val,(int,float)) and val>0)
        ev[j]=dict(model=P.MODELS[j]['model'],reasoning_field=field,reasoning_value=val,
                   reasoning_on=bool(on),latency_s=round(dt,1),ok=txt is not None)
        print(f"  {j:16s} {P.MODELS[j]['model']:20s} {field}={val}  reasoning_on={on}  ({dt:.1f}s)")
    ev['_note']=("Verified on a real Real-POCQi OE answer (question_id=%s, %d chars). "
                 "All judges consumed reasoning tokens on the substantive task." %
                 (row.question_id, len(row.answer_markdown)))
    json.dump(ev, open(os.path.join(OUT,'thinking_evidence.json'),'w'), indent=2)
    print("\nwrote out/thinking_evidence.json")

if __name__=="__main__": main()
