#!/usr/bin/env bash
# Reproduce the full reconciliation analysis end to end.
# Steps 1-2 need no API keys (public data). Steps 3-6 call the four judge APIs and COST money.
set -euo pipefail
cd "$(dirname "$0")"

echo "== 0. deps =="
python3 -m pip install -q -r requirements.txt

echo "== 1. fetch public data (Real-POCQi, CC BY 4.0) =="
python3 fetch_data.py

echo "== 2. public-data analyses (metric reproduction, citation halo, power) -- no API keys =="
python3 analysis/analyze.py

echo "== 2b. deterministic unit tests (no API) =="
( cd judge && python3 test_export_disagreement.py && python3 test_robust_analysis.py )

echo "== 2c. no-API robust analyses on committed judge outputs (crossed bootstrap = PRIMARY-panel;"
echo "        aggregation-matched same-judge = PRIMARY; supplementary; per-item export) =="
if [ -f judge/out/grades.jsonl ] && [ -f judge/out/pairwise.jsonl ]; then
  ( cd judge && python3 bootstrap_panel.py && python3 robust_analysis.py \
        && python3 robust_supplementary.py && python3 export_disagreement.py \
        && python3 judge_subsets.py && python3 flip_predictors.py && python3 sample_human_study.py )
  ( cd dataset && python3 build_dataset.py )
else
  echo "   (judge/out/grades.jsonl or pairwise.jsonl absent — will be produced by judge steps below)"
fi

# ---- The steps below require judge/providers.py KEYS_PATH to point at a file with
# ---- OPENAI_API_KEY / ANTHROPIC_API_KEY / XAI_API_KEY / GOOGLE_API_KEY. Skip with SKIP_JUDGES=1.
if [ "${SKIP_JUDGES:-0}" = "1" ]; then
  echo "== SKIP_JUDGES=1 set: skipping LLM-judge steps (3-9); robust analyses above used committed outputs. =="
  exit 0
fi

echo "== 3. verify all judges run with reasoning/thinking ON (real task) =="
( cd judge && python3 verify_thinking.py )

echo "== 4. LLM-judge grading (n=150 x 4 systems x 4 judges; resumable; ~30 min, spends credits) =="
( cd judge && python3 grade.py --n 150 --workers 12 )

echo "== 5. existence-proof analysis (human pairwise vs LLM-judge win-diff, self-pref, agreement) =="
( cd judge && python3 analyze_grades.py )

echo "== 6. cluster-bootstrap CIs + leave-one-judge-out + figure =="
( cd judge && python3 bootstrap_grades.py && python3 make_figure.py )

echo "== 7. LLM-PAIRWISE cell (breaks human-vs-LLM rater confound; same 150 q x 3 opp x 4 judges) =="
( cd judge && python3 pairwise.py --n 150 --workers 12 )

echo "== 8. 2x2 decomposition (rater-modality vs instrument-format effects) + Figure 2 =="
( cd judge && python3 analyze_pairwise.py && python3 make_figure2.py )

echo "== 9. length-matched sub-study on the rubric cell (no new API calls; uses existing grades) =="
( cd judge && python3 length_analysis.py )

echo "== 10. regenerate robust analyses on freshly graded outputs (crossed bootstrap, aggregation-matched"
echo "         same-judge PRIMARY, supplementary, per-item export) =="
( cd judge && python3 bootstrap_panel.py && python3 robust_analysis.py \
      && python3 robust_supplementary.py && python3 export_disagreement.py \
      && python3 judge_subsets.py && python3 flip_predictors.py )

echo "== DONE. Outputs in out/ and judge/out/. =="
