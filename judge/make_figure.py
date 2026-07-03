"""Figure 1: instrument existence proof. OE-vs-rest win-difference under the human pairwise
instrument vs the LLM-judge absolute-rubric panel, per axis, with 95% cluster-bootstrap CIs.
Reads out/bootstrap_results.json -> out/existence_proof.png"""
import os, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,'out')
AXES=['accuracy','clinical_utility','source_quality','completeness','verifiability']
LBL={'accuracy':'Accuracy','clinical_utility':'Clinical\nutility','source_quality':'Source\nquality',
     'completeness':'Complete-\nness','verifiability':'Verifi-\nability'}

R=json.load(open(os.path.join(OUT,'bootstrap_results.json')))
hum=R['human_pairwise']; llm=R['llm_panel_ci']
humci=R.get('human_pairwise_ci',{})
x=np.arange(len(AXES)); w=0.38

fig,ax=plt.subplots(figsize=(9,5.2))
ax.axhline(0,color='#444',lw=1)
hpts=[hum[a] for a in AXES]
if humci:
    herr=[[hum[a]-humci[a]['lo'] for a in AXES],[humci[a]['hi']-hum[a] for a in AXES]]
    ax.bar(x-w/2,hpts,w,yerr=herr,capsize=4,
           label='Human blinded pairwise (same questions, 95%% CI)',color='#2c7fb8',ecolor='#333')
else:
    ax.bar(x-w/2,hpts,w,label='Human blinded pairwise (dataset instrument)',color='#2c7fb8')
pts=[llm[a]['point'] for a in AXES]
err=[[llm[a]['point']-llm[a]['lo'] for a in AXES],[llm[a]['hi']-llm[a]['point'] for a in AXES]]
ax.bar(x+w/2,pts,w,yerr=err,capsize=4,label='LLM-judge absolute rubric (n=%d, 95%% CI)'%R['n_questions'],
       color='#d95f0e',ecolor='#333')
for i,a in enumerate(AXES):
    ax.text(x[i]-w/2,(humci[a]['hi'] if humci else hum[a])+1.2,f"{hum[a]:+.0f}",ha='center',va='bottom',fontsize=9,color='#2c7fb8')
    yv=llm[a]['point']
    ax.text(x[i]+w/2,llm[a]['lo']-1.5,f"{yv:+.0f}",ha='center',va='top',fontsize=9,color='#d95f0e')
ax.set_xticks(x); ax.set_xticklabels([LBL[a] for a in AXES])
ax.set_ylabel('OpenEvidence-vs-rest win-difference (pp)')
ax.set_title('Same queries + same answers, different instrument:\nOpenEvidence advantage eliminated on every axis (reversed on 2, null on 2, 3x smaller on 1)')
ax.legend(loc='upper right',fontsize=9,framealpha=0.95)
ax.grid(axis='y',alpha=0.25)
fig.tight_layout()
fig.savefig(os.path.join(OUT,'existence_proof.png'),dpi=150)
print("wrote out/existence_proof.png")
