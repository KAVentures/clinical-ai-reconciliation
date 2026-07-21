"""Deterministic tests for the per-item disagreement export (GitHub issue #1).

Uses a few fixed synthetic rows and no file/network access, so the flip definition is
pinned and future analysis changes cannot silently alter it. Run:  python3 test_export_disagreement.py
(also collectable by pytest).
"""
from export_disagreement import build_rows, summarize_by_axis, OE

G = 'gpt-5.5'  # a frontier opponent


def _grade(qid, prov, judge, acc):
    return {'question_id': qid, 'provider_key': prov, 'judge': judge,
            'scores': {'accuracy': acc, 'clinical_utility': acc, 'source_quality': acc,
                       'completeness': acc, 'verifiability': acc}}


def _pw(qid, opp, judge, res):
    return {'question_id': qid, 'opponent': opp, 'judge': judge,
            'oe_result': {'accuracy': res, 'clinical_utility': res, 'source_quality': res,
                          'completeness': res, 'verifiability': res}}


def _row(rows, qid, ax, opp):
    return next(r for r in rows if r['question_id'] == qid and r['axis'] == ax and r['opponent'] == opp)


def test_flip_when_rubric_and_pairwise_disagree():
    # Rubric: OE scores 2, opponent 4 -> rubric favours OPPONENT (margin -2).
    # LLM pairwise: two judges pick OE -> pairwise favours OE. => instrument flip.
    grades = [_grade('q1', OE, 'gpt-5.5', 2), _grade('q1', OE, 'opus-4.8', 2),
              _grade('q1', G, 'gpt-5.5', 4), _grade('q1', G, 'opus-4.8', 4)]
    pairwise = [_pw('q1', G, 'gpt-5.5', 'oe'), _pw('q1', G, 'opus-4.8', 'oe')]
    human = [{'question_id': 'q1', 'opponent': G, 'axis': 'accuracy', 'o': 1}]
    r = _row(build_rows(grades, pairwise, human), 'q1', 'accuracy', G)
    assert r['rubric_winner'] == G and r['rubric_margin'] == -2.0
    assert r['pw_llm_winner'] == OE and r['pw_llm_net'] == 2
    assert r['instrument_flip_llm'] is True
    assert r['instrument_flip_vs_human'] is True  # rubric(opp) vs human(oe)
    assert r['excluded_reason'] == ''


def test_no_flip_when_they_agree():
    grades = [_grade('q2', OE, 'gpt-5.5', 4), _grade('q2', G, 'gpt-5.5', 2)]  # rubric -> OE
    pairwise = [_pw('q2', G, 'gpt-5.5', 'oe')]                                 # pairwise -> OE
    r = _row(build_rows(grades, pairwise), 'q2', 'accuracy', G)
    assert r['rubric_winner'] == OE and r['pw_llm_winner'] == OE
    assert r['instrument_flip_llm'] is False


def test_tie_is_never_a_flip():
    # rubric tie (equal means) -> no flip regardless of pairwise
    grades = [_grade('q3', OE, 'gpt-5.5', 3), _grade('q3', G, 'gpt-5.5', 3)]
    pairwise = [_pw('q3', G, 'gpt-5.5', 'oe')]
    r = _row(build_rows(grades, pairwise), 'q3', 'accuracy', G)
    assert r['rubric_winner'] == 'tie'
    assert r['instrument_flip_llm'] is False


def test_missing_cells_are_flagged_and_not_flips():
    # rubric present, no pairwise at all
    grades = [_grade('q4', OE, 'gpt-5.5', 4), _grade('q4', G, 'gpt-5.5', 2)]
    r = _row(build_rows(grades, [], []), 'q4', 'accuracy', G)
    assert 'no_llm_pairwise' in r['excluded_reason']
    assert 'no_human_pairwise' in r['excluded_reason']
    assert r['instrument_flip_llm'] is False and r['instrument_flip_vs_human'] is False

    # pairwise present, rubric only scored one side -> incomplete, no rubric winner
    r2 = _row(build_rows([_grade('q5', OE, 'gpt-5.5', 4)], [_pw('q5', G, 'gpt-5.5', 'opp')], []),
              'q5', 'accuracy', G)
    assert r2['rubric_winner'] == '' and 'rubric_incomplete' in r2['excluded_reason']
    assert r2['pw_llm_winner'] == G
    assert r2['instrument_flip_llm'] is False


def test_counts_and_dispersion():
    # two judges disagree on the diff: judge1 oe-opp = 4-2=+2, judge2 = 2-4=-2 -> mean 0 (tie), SD 2
    grades = [_grade('q6', OE, 'gpt-5.5', 4), _grade('q6', OE, 'opus-4.8', 2),
              _grade('q6', G, 'gpt-5.5', 2), _grade('q6', G, 'opus-4.8', 4)]
    r = _row(build_rows(grades, [], []), 'q6', 'accuracy', G)
    assert r['rubric_n_judges_oe'] == 2 and r['rubric_n_judges_common'] == 2
    assert r['rubric_winner'] == 'tie' and r['rubric_judge_diff_sd'] == 2.0


def test_summary_flip_rate():
    # one clean flip (q1) + one agreement (q2) on accuracy => flip rate 0.5 vs LLM pairwise
    grades = [_grade('q1', OE, 'gpt-5.5', 2), _grade('q1', G, 'gpt-5.5', 4),
              _grade('q2', OE, 'gpt-5.5', 4), _grade('q2', G, 'gpt-5.5', 2)]
    pairwise = [_pw('q1', G, 'gpt-5.5', 'oe'), _pw('q2', G, 'gpt-5.5', 'oe')]
    s = summarize_by_axis(build_rows(grades, pairwise, []))
    assert s['accuracy']['n_comparable_vs_llm_pairwise'] == 2
    assert s['accuracy']['n_flip_vs_llm_pairwise'] == 1
    assert s['accuracy']['flip_rate_vs_llm_pairwise'] == 0.5


if __name__ == '__main__':
    fns = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\nall {len(fns)} tests passed")
