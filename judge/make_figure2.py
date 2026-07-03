"""Figure 2: the 2x2 rater-vs-instrument decomposition.
Left panel  — three cells of the {pairwise,rubric} x {human,LLM} design per axis:
  A = pairwise/human, B = pairwise/LLM (95% CI), C = rubric/LLM.
  The story: A and B are both positive (OE wins under BOTH human and LLM pairwise);
  only C (the rubric) drops OE. => it is the instrument, not the rater.
Right panel — the A->C swing split into rater (B-A) and instrument (C-B) components,
  showing the instrument component dominates on every axis.
Reads out/pairwise_results.json (+ its embedded cell C) -> out/decomposition.png"""
import os, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,'out')
AXES=['accuracy','clinical_utility','source_quality','completeness','verifiability']
LBL={'accuracy':'Accuracy','clinical_utility':'Clinical\nutility','source_quality':'Source\nquality',
     'completeness':'Complete-\nness','verifiability':'Verifi-\nability'}

R=json.load(open(os.path.join(OUT,'pairwise_results.json')))
A=R['cellA_pairwise_human']; B=R['cellB_pairwise_llm']; C=R['cellC_rubric_llm']; dec=R['decomposition']
x=np.arange(len(AXES))

fig,(axL,axR)=plt.subplots(1,2,figsize=(14,5.4))

# ---- Left: three cells ----
w=0.27
axL.axhline(0,color='#444',lw=1)
axL.bar(x-w,[A[a] for a in AXES],w,label='A: pairwise / HUMAN (Real-POCQi)',color='#2c7fb8')
bpts=[B[a]['point'] for a in AXES]
berr=[[B[a]['point']-B[a]['lo'] for a in AXES],[B[a]['hi']-B[a]['point'] for a in AXES]]
axL.bar(x,bpts,w,yerr=berr,capsize=3,label='B: pairwise / LLM panel (95% CI)',color='#41ab5d',ecolor='#333')
axL.bar(x+w,[C[a]['point'] for a in AXES],w,label='C: rubric / LLM panel',color='#d95f0e')
axL.set_xticks(x); axL.set_xticklabels([LBL[a] for a in AXES])
axL.set_ylabel('OpenEvidence-vs-rest win-difference (pp)')
axL.set_title('Both pairwise cells favor OpenEvidence (A,B > 0);\nonly the rubric (C) reverses it')
axL.legend(loc='lower left',fontsize=8.5,framealpha=0.95)
axL.grid(axis='y',alpha=0.25)

# ---- Right: decomposition of the A->C swing ----
rater=[dec[a]['rater'] for a in AXES]
instr=[dec[a]['instrument'] for a in AXES]
w2=0.38
axR.axhline(0,color='#444',lw=1)
axR.bar(x-w2/2,rater,w2,label='Rater-modality effect (B - A): human -> LLM',color='#9e9ac8')
axR.bar(x+w2/2,instr,w2,label='Instrument-format effect (C - B): pairwise -> rubric',color='#e34a33')
for i,a in enumerate(AXES):
    axR.text(x[i]-w2/2,rater[i]+(0.8 if rater[i]>=0 else -0.8),f"{rater[i]:+.0f}",
             ha='center',va='bottom' if rater[i]>=0 else 'top',fontsize=8,color='#54278f')
    axR.text(x[i]+w2/2,instr[i]-0.8,f"{instr[i]:+.0f}",ha='center',va='top',fontsize=8,color='#b30000')
axR.set_xticks(x); axR.set_xticklabels([LBL[a] for a in AXES])
axR.set_ylabel('Contribution to the human-pairwise -> LLM-rubric swing (pp)')
axR.set_title('The instrument-format effect dominates the rater effect\non every axis')
axR.legend(loc='lower left',fontsize=8.5,framealpha=0.95)
axR.grid(axis='y',alpha=0.25)

fig.suptitle('Decomposing why the winner flips: instrument, not rater  (n=%d questions)'%R['n_questions'],
             fontsize=13,y=1.00)
fig.tight_layout()
fig.savefig(os.path.join(OUT,'decomposition.png'),dpi=150,bbox_inches='tight')
print("wrote out/decomposition.png")
