"""What predicts an instrument flip? A prespecified, question-clustered logistic model (mechanism).

Outcome: instrument_flip_llm (rubric winner vs LLM-pairwise winner disagree; both decisive) per
(question, axis, opponent). Fit a GEE logistic (Binomial, exchangeable working correlation, clustered
by question_id -> cluster-robust SEs) on prespecified predictors available from EXISTING data:
  axis, opponent, |rubric margin|, LLM-pairwise agreement, rubric judge dispersion, rubric ceiling
  status, OE citation marker, |answer-length difference|.
(Query provenance is NOT included: the vendored corpus is entirely OE-originated with no HealthBench
items or source flag, so a format x provenance test needs new data — see manuscript Limitations/future.)

Interpretation the model is built to separate (observational, NOT causal):
  * flips concentrated at small |margin| and low agreement  -> measurement resolution / instability;
  * flips persisting at large |margin| and unanimous judges  -> genuinely different evaluation constructs.

No API calls. Reads out/instrument_disagreement.csv (+ data/answers,questions). Writes out/flip_predictors.json.
"""
import os, re, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
DATA = os.path.join(HERE, '..', 'data')
OE = 'openevidence'
FRONTIER = ['gpt-5.5', 'claude-opus-4-8', 'gemini-3.1-pro']
CEILING = 3.75  # panel-mean at/above this counts as "at ceiling" on the 1-4 scale
_CIT = re.compile(r'\[[0-9]+\]|\]\(https?://|\bdoi\b|PMID|https?://', re.I)


def build_frame():
    df = pd.read_csv(os.path.join(OUT, 'instrument_disagreement.csv'))
    # decisive on BOTH instruments -> flip is defined
    dec = df[df.rubric_winner.isin([OE] + FRONTIER) & df.pw_llm_winner.isin([OE] + FRONTIER)].copy()
    dec['flip'] = dec['instrument_flip_llm'].astype(int)
    dec['abs_margin'] = dec['rubric_margin'].abs()
    dec['agreement'] = pd.to_numeric(dec['pw_llm_agreement'], errors='coerce')
    dec['dispersion'] = pd.to_numeric(dec['rubric_judge_diff_sd'], errors='coerce')
    dec['ceiling'] = ((pd.to_numeric(dec['rubric_oe_mean'], errors='coerce') >= CEILING) |
                      (pd.to_numeric(dec['rubric_opp_mean'], errors='coerce') >= CEILING)).astype(int)
    # joins: OE citation marker + |length diff| + specialty
    a = pd.read_parquet(os.path.join(DATA, 'answers.parquet'))
    length = {(r.question_id, r.provider_key): len(str(r.answer_markdown)) for _, r in a.iterrows()}
    oe_cited = {r.question_id: int(bool(_CIT.search(str(r.answer_markdown))))
                for _, r in a[a.provider_key == OE].iterrows()}
    q = pd.read_parquet(os.path.join(DATA, 'questions.parquet')).set_index('question_id')['specialty']
    dec['oe_cited'] = dec['question_id'].map(oe_cited).fillna(0).astype(int)
    dec['abs_len_diff_k'] = dec.apply(
        lambda r: abs(length.get((r.question_id, OE), np.nan) - length.get((r.question_id, r.opponent), np.nan)) / 1000.0,
        axis=1)
    dec['specialty'] = dec['question_id'].map(q)
    return dec.dropna(subset=['agreement', 'dispersion', 'abs_len_diff_k'])


def descriptive(dec):
    """Flip rate by |margin| tertile x agreement (the reviewer's resolution-vs-construct cut)."""
    d = dec.copy()
    d['margin_bin'] = pd.qcut(d['abs_margin'], 3, labels=['small', 'mid', 'large'], duplicates='drop')
    d['agree_bin'] = np.where(d['agreement'] >= d['agreement'].median(), 'high_agree', 'low_agree')
    tab = d.groupby(['margin_bin', 'agree_bin'], observed=True)['flip'].agg(['mean', 'size'])
    return {f"{m}|{a}": {'flip_rate': round(float(r['mean']), 3), 'n': int(r['size'])}
            for (m, a), r in tab.iterrows()}


def main():
    dec = build_frame()
    out = {'n_decisive_items': int(len(dec)), 'n_questions': int(dec.question_id.nunique()),
           'overall_flip_rate': round(float(dec.flip.mean()), 3),
           'note': 'observational associations, NOT causal; query provenance unavailable in vendored data'}

    try:
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
        formula = ("flip ~ C(axis) + C(opponent) + abs_margin + agreement + dispersion "
                   "+ ceiling + oe_cited + abs_len_diff_k")
        m = smf.gee(formula, groups='question_id', data=dec,
                    family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable())
        r = m.fit()
        out['gee_logistic'] = {
            'terms': {name: {'log_odds': round(float(b), 3), 'p': round(float(p), 4)}
                      for name, b, p in zip(r.params.index, r.params.values, r.pvalues.values)},
            'family': 'Binomial', 'cov': 'exchangeable, clustered by question_id',
        }
    except Exception as e:  # pragma: no cover
        out['gee_logistic'] = {'error': str(e)}

    out['flip_rate_by_margin_x_agreement'] = descriptive(dec)
    json.dump(out, open(os.path.join(OUT, 'flip_predictors.json'), 'w'), indent=2)

    print(f"decisive items={out['n_decisive_items']}  questions={out['n_questions']}  "
          f"overall flip rate={out['overall_flip_rate']}\n")
    print("=== GEE logistic (log-odds of a flip; cluster-robust by question) ===")
    for name, v in out.get('gee_logistic', {}).get('terms', {}).items():
        star = '*' if v['p'] < 0.05 else ' '
        print(f"  {name:28s} {v['log_odds']:+7.3f}  p={v['p']:.4f} {star}")
    print("\n=== flip rate by |rubric margin| tertile x pairwise agreement ===")
    for k, v in out['flip_rate_by_margin_x_agreement'].items():
        print(f"  {k:18s} flip_rate={v['flip_rate']:.3f}  (n={v['n']})")
    print("\nwrote out/flip_predictors.json")


if __name__ == '__main__':
    main()
