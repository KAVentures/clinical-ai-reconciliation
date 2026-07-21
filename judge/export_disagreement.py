"""Per-item instrument-disagreement export (GitHub issue #1).

Emits one machine-readable row per (question_id, axis, opponent) — OpenEvidence vs each
frontier system — recording how the RUBRIC instrument (cell C, LLM 1-4 panel) and the
PAIRWISE instrument scored the same fixed answers, and whether they disagree on the winner.
Two pairwise references are reported side by side:

  * pw_llm   = LLM pairwise (cell B): SAME four judges as the rubric, so a rubric-vs-pw_llm
               disagreement is a PURE instrument flip (rater held fixed).
  * pw_human = human pairwise (cell A): Real-POCQi's actual blinded-physician result; a
               rubric-vs-pw_human disagreement is the headline reconciliation flip (which
               also mixes in the human->LLM rater change; see the paper's A->B->C decomposition).

Winner / margin definitions match judge/bootstrap_panel.py exactly:
  rubric  : per-provider panel MEAN 1-4 score (over judges that scored that provider);
            margin = oe_mean - opponent_mean; winner = sign(margin).
  pairwise: per-vote {oe:+1, opp:-1, tie:0}; net = sum over judges/raters; margin = net / n;
            winner = sign(net).
A flip requires BOTH instruments to be decisive (non-tie) and of opposite sign — never
adjudicated against clinical truth (the repo has none), only instrument-vs-instrument.

NOTE: the per-item rows discretize each (question, opponent) to a single winner and drop ties
from win counts, so re-aggregating this CSV reproduces the *sign* of every published win-difference
(judge/out/panel_bootstrap.json) but not its exact magnitude. The continuous win-difference and its
crossed-bootstrap CIs in bootstrap_panel.py remain the inferential quantities; this export is a
descriptive audit layer for inspecting *where* disagreement concentrates, not a significance test.

No API calls: reads only out/grades.jsonl, out/pairwise.jsonl, data/ratings.parquet.
Writes out/instrument_disagreement.csv and out/instrument_disagreement_by_axis.json.

The core (`build_rows`) is a pure function over record lists so it can be unit-tested with
fixed synthetic rows and no file/network access (see test_export_disagreement.py).
"""
import os, json, csv, argparse, math
from collections import defaultdict

AXES = ['accuracy', 'clinical_utility', 'source_quality', 'completeness', 'verifiability']
OE = 'openevidence'
FRONTIER = ['gpt-5.5', 'claude-opus-4-8', 'gemini-3.1-pro']


def _sign(x, eps=1e-9):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return 0 if abs(x) < eps else (1 if x > 0 else -1)


def _winner_label(sign, opponent):
    """Map a signed winner to a human-readable provider label ('' when undefined)."""
    if sign is None:
        return ''
    return {1: OE, -1: opponent, 0: 'tie'}[sign]


def _pop_sd(values):
    """Population SD; None for <2 values."""
    if len(values) < 2:
        return None
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def build_rows(grades, pairwise, human=None):
    """Pure core. Inputs are lists of dicts:

      grades[i]   = {question_id, provider_key, judge, scores:{axis:int1-4}}   (scores may be None)
      pairwise[i] = {question_id, opponent, judge, oe_result:{axis:'oe'|'opp'|'tie'}}
      human[i]    = {question_id, opponent, axis, o:+1|-1|0}                    (optional)

    Returns a list of per-(question_id, axis, opponent) dict rows, deterministically sorted.
    """
    human = human or []

    # --- rubric (cell C): (qid, provider, axis) -> {judge: score} ---
    rub = defaultdict(dict)
    for r in grades:
        sc = r.get('scores')
        if not sc:
            continue
        for ax in AXES:
            if ax in sc and sc[ax] is not None:
                rub[(r['question_id'], r['provider_key'], ax)][r['judge']] = float(sc[ax])

    # --- LLM pairwise (cell B): (qid, opponent, axis) -> [votes in {+1,-1,0}] ---
    pwl = defaultdict(list)
    for r in pairwise:
        res = r.get('oe_result')
        if not res:
            continue
        for ax, v in res.items():
            if ax not in AXES:
                continue
            pwl[(r['question_id'], r['opponent'], ax)].append(1 if v == 'oe' else (-1 if v == 'opp' else 0))

    # --- human pairwise (cell A): (qid, opponent, axis) -> [votes] ---
    pwh = defaultdict(list)
    for r in human:
        if r['axis'] in AXES:
            pwh[(r['question_id'], r['opponent'], r['axis'])].append(int(r['o']))

    # grid of (qid, opponent, axis) actually observed by any instrument
    qids = {k[0] for k in rub} | {k[0] for k in pwl} | {k[0] for k in pwh}
    keys = set()
    for qid in qids:
        for opp in FRONTIER:
            for ax in AXES:
                if ((qid, OE, ax) in rub and (qid, opp, ax) in rub) \
                        or (qid, opp, ax) in pwl or (qid, opp, ax) in pwh:
                    keys.add((qid, opp, ax))

    rows = []
    for qid, opp, ax in sorted(keys):
        excluded = []

        # ---- rubric ----
        oe_scores = rub.get((qid, OE, ax), {})
        opp_scores = rub.get((qid, opp, ax), {})
        rub_oe_mean = sum(oe_scores.values()) / len(oe_scores) if oe_scores else None
        rub_opp_mean = sum(opp_scores.values()) / len(opp_scores) if opp_scores else None
        if rub_oe_mean is not None and rub_opp_mean is not None:
            rub_margin = rub_oe_mean - rub_opp_mean
            rub_sign = _sign(rub_margin)
        else:
            rub_margin = None
            rub_sign = None
            excluded.append('rubric_incomplete' if (oe_scores or opp_scores) else 'no_rubric')
        common = sorted(set(oe_scores) & set(opp_scores))
        rub_diffs = [oe_scores[j] - opp_scores[j] for j in common]
        rub_dispersion = _pop_sd(rub_diffs)  # SD of per-judge (oe-opp) diffs = judge (dis)agreement

        # ---- LLM pairwise ----
        vl = pwl.get((qid, opp, ax), [])
        pwl_net = sum(vl) if vl else None
        pwl_margin = (pwl_net / len(vl)) if vl else None
        pwl_sign = _sign(pwl_net) if vl else None
        if not vl:
            excluded.append('no_llm_pairwise')
        pwl_agree = (max(vl.count(1), vl.count(-1), vl.count(0)) / len(vl)) if vl else None

        # ---- human pairwise ----
        vh = pwh.get((qid, opp, ax), [])
        pwh_net = sum(vh) if vh else None
        pwh_margin = (pwh_net / len(vh)) if vh else None
        pwh_sign = _sign(pwh_net) if vh else None
        if not vh:
            excluded.append('no_human_pairwise')

        # ---- flips (both instruments must be decisive & opposite) ----
        def flip(a, b):
            return bool(a is not None and b is not None and a != 0 and b != 0 and a != b)
        flip_llm = flip(rub_sign, pwl_sign)      # pure instrument (rater fixed) <- headline of issue
        flip_human = flip(rub_sign, pwh_sign)    # rubric vs Real-POCQi human pairwise

        rows.append({
            'question_id': qid,
            'axis': ax,
            'opponent': opp,
            # rubric (cell C)
            'rubric_oe_mean': round(rub_oe_mean, 4) if rub_oe_mean is not None else '',
            'rubric_opp_mean': round(rub_opp_mean, 4) if rub_opp_mean is not None else '',
            'rubric_margin': round(rub_margin, 4) if rub_margin is not None else '',
            'rubric_winner': _winner_label(rub_sign, opp),
            'rubric_n_judges_oe': len(oe_scores),
            'rubric_n_judges_opp': len(opp_scores),
            'rubric_n_judges_common': len(common),
            'rubric_judge_diff_sd': round(rub_dispersion, 4) if rub_dispersion is not None else '',
            # LLM pairwise (cell B)
            'pw_llm_margin': round(pwl_margin, 4) if pwl_margin is not None else '',
            'pw_llm_winner': _winner_label(pwl_sign, opp),
            'pw_llm_net': pwl_net if pwl_net is not None else '',
            'pw_llm_n_judges': len(vl),
            'pw_llm_agreement': round(pwl_agree, 4) if pwl_agree is not None else '',
            # human pairwise (cell A)
            'pw_human_margin': round(pwh_margin, 4) if pwh_margin is not None else '',
            'pw_human_winner': _winner_label(pwh_sign, opp),
            'pw_human_net': pwh_net if pwh_net is not None else '',
            'pw_human_n_ratings': len(vh),
            # disagreement
            'instrument_flip_llm': flip_llm,
            'instrument_flip_vs_human': flip_human,
            'excluded_reason': ';'.join(excluded),
        })
    return rows


def summarize_by_axis(rows):
    """Aggregate flip rates per axis over rows where the relevant comparison is decidable."""
    out = {}
    for ax in AXES:
        rax = [r for r in rows if r['axis'] == ax]
        llm_dec = [r for r in rax if r['rubric_winner'] in (OE,) or r['rubric_winner'] in FRONTIER]
        llm_comparable = [r for r in rax if r['rubric_winner'] in ([OE] + FRONTIER)
                          and r['pw_llm_winner'] in ([OE] + FRONTIER)]
        human_comparable = [r for r in rax if r['rubric_winner'] in ([OE] + FRONTIER)
                            and r['pw_human_winner'] in ([OE] + FRONTIER)]
        n_flip_llm = sum(1 for r in llm_comparable if r['instrument_flip_llm'])
        n_flip_human = sum(1 for r in human_comparable if r['instrument_flip_vs_human'])
        out[ax] = {
            'n_rows': len(rax),
            'n_rubric_decisive': len(llm_dec),
            'n_comparable_vs_llm_pairwise': len(llm_comparable),
            'n_flip_vs_llm_pairwise': n_flip_llm,
            'flip_rate_vs_llm_pairwise': round(n_flip_llm / len(llm_comparable), 4) if llm_comparable else None,
            'n_comparable_vs_human_pairwise': len(human_comparable),
            'n_flip_vs_human_pairwise': n_flip_human,
            'flip_rate_vs_human_pairwise': round(n_flip_human / len(human_comparable), 4) if human_comparable else None,
        }
    return out


# --------------------------- file I/O (main only) ---------------------------
def _load_jsonl(path):
    out = []
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _load_human(data_dir):
    """Replicate bootstrap_panel.load_humanA row selection -> [{question_id,opponent,axis,o}]."""
    path = os.path.join(data_dir, 'ratings.parquet')
    if not os.path.exists(path):
        return []
    import pandas as pd
    r = pd.read_parquet(path)
    r = r[(r.render_mode == 'qa_text_only')]
    pref = {'strongly_a': 1, 'slightly_a': 1, 'strongly_b': -1, 'slightly_b': -1, 'tie': 0}
    rec = []
    for _, x in r.iterrows():
        if x.axis not in AXES:
            continue
        if x.slot_a_provider != OE and x.slot_b_provider != OE:
            continue
        pr = pref.get(x.choice)
        if pr is None:
            continue
        opponent = x.slot_b_provider if x.slot_a_provider == OE else x.slot_a_provider
        if opponent not in FRONTIER:
            continue
        if pr == 0:
            o = 0
        else:
            winner = x.slot_a_provider if pr == 1 else x.slot_b_provider
            o = 1 if winner == OE else -1
        rec.append({'question_id': x.question_id, 'opponent': opponent, 'axis': x.axis, 'o': o})
    return rec


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(here, 'out')
    data_dir = os.path.join(here, '..', 'data')
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-human', action='store_true', help='skip data/ratings.parquet (cell A)')
    a = ap.parse_args()

    grades = _load_jsonl(os.path.join(out_dir, 'grades.jsonl'))
    pairwise = _load_jsonl(os.path.join(out_dir, 'pairwise.jsonl'))
    human = [] if a.no_human else _load_human(data_dir)

    rows = build_rows(grades, pairwise, human)
    by_axis = summarize_by_axis(rows)

    csv_path = os.path.join(out_dir, 'instrument_disagreement.csv')
    with open(csv_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ['question_id'])
        w.writeheader()
        w.writerows(rows)

    json_path = os.path.join(out_dir, 'instrument_disagreement_by_axis.json')
    total_llm = sum(v['n_flip_vs_llm_pairwise'] for v in by_axis.values())
    total_llm_cmp = sum(v['n_comparable_vs_llm_pairwise'] for v in by_axis.values())
    json.dump({'n_rows': len(rows), 'by_axis': by_axis,
               'overall_flip_rate_vs_llm_pairwise': round(total_llm / total_llm_cmp, 4) if total_llm_cmp else None},
              open(json_path, 'w'), indent=2)

    print(f"wrote {csv_path}  ({len(rows)} rows)")
    print(f"wrote {json_path}")
    print(f"\naxis                 rows  rubric-decisive  flips-vs-LLM-pw  flip-rate-vs-LLM  flip-rate-vs-human")
    for ax in AXES:
        v = by_axis[ax]
        print(f"{ax:20s}{v['n_rows']:>6d}{v['n_rubric_decisive']:>17d}{v['n_flip_vs_llm_pairwise']:>17d}"
              f"{str(v['flip_rate_vs_llm_pairwise']):>18s}{str(v['flip_rate_vs_human_pairwise']):>20s}")


if __name__ == '__main__':
    main()
