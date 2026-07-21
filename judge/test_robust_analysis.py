"""Deterministic tests for the robust decomposition core (peer-review revision).

Pins the estimand definitions that the manuscript's primary claims depend on — matched-unit
construction, individual-vs-panel aggregation, tie thresholding, and missing-grade handling — with
fixed synthetic rows and no file/network access. Run: python3 test_robust_analysis.py
"""
from robust_analysis import (threshold, windiff, windiff_units, matched_units,
                             common_support_keys, holm, two_sided_p, boot_weights, OE)
import numpy as np

G = 'gpt-5.5'
JS = ['gpt-5.5', 'opus-4.8', 'grok-4.3', 'gemini-3.5-flash']


def test_threshold_deadzone():
    assert threshold(0.4, 0.0) == 1 and threshold(-0.4, 0.0) == -1 and threshold(0.0, 0.0) == 0
    # a 0.2 gap is a WIN at delta=0 but a TIE inside a 0.25 dead-zone
    assert threshold(0.2, 0.0) == 1
    assert threshold(0.2, 0.25) == 0
    assert threshold(0.3, 0.25) == 1


def test_windiff_basic_and_weighted():
    assert windiff([1, 1, -1, 0]) == 100 * (2 - 1) / 4
    # weighting a loss to zero removes it from both numerator and denominator
    assert windiff([1, -1], w=[1, 0]) == 100.0


def test_matched_units_requires_both_instruments():
    # judge G has a rubric pair for q1 AND a pairwise vote -> matched; q2 lacks a pairwise vote -> dropped
    rub = {('q1', OE, G): 2.0, ('q1', G, G): 4.0,
           ('q2', OE, G): 3.0, ('q2', G, G): 1.0}
    pw = {('q1', G, G): 1}  # only q1 has a pairwise vote
    mu = matched_units(rub, pw, G, opponents=[G])
    assert [u['qid'] for u in mu] == ['q1']
    assert mu[0]['c_vote'] == threshold(2.0 - 4.0) == -1   # rubric: OE loses
    assert mu[0]['b_vote'] == 1                            # pairwise: OE wins  -> a per-item flip


def test_common_support_is_exact_intersection():
    # The rev-2 bug fix: only a (q,opp) with a human vote AND full-panel pairwise AND full-panel
    # OE-rubric AND full-panel opponent-rubric survives. Four questions, only q1 is complete.
    R, P, H = {}, {}, {}
    # q1: complete (A + 4 pw + 4 OE-rubric + 4 opp-rubric)
    for j in JS:
        P[('q1', G, j)] = 1
        R[('q1', OE, j)] = 4.0
        R[('q1', G, j)] = 2.0
    H[('q1', G)] = [1]
    # q2: human only
    H[('q2', G)] = [1]
    # q3: human + full pairwise, but NO rubric (missing C)
    for j in JS:
        P[('q3', G, j)] = 1
    H[('q3', G)] = [1]
    # q4: human + full rubric, but NO pairwise (missing B)
    for j in JS:
        R[('q4', OE, j)] = 4.0
        R[('q4', G, j)] = 2.0
    H[('q4', G)] = [1]
    keys = common_support_keys(R, P, H, judges=JS, opponents=[G])
    assert keys == [('q1', G)]   # only q1 survives; q2/q3/q4 dropped


def test_common_support_drops_partial_panel():
    # a (q,opp) missing even ONE judge's pairwise vote is excluded under full-panel requirement
    R, P, H = {}, {}, {}
    for j in JS:
        R[('q1', OE, j)] = 4.0; R[('q1', G, j)] = 2.0
    for j in JS[:3]:            # only 3 of 4 pairwise votes
        P[('q1', G, j)] = 1
    H[('q1', G)] = [1]
    assert common_support_keys(R, P, H, judges=JS, opponents=[G]) == []


def test_boot_weights_universe_is_only_matched_clusters():
    # resampling draws multiplicities ONLY over the supplied cluster list (never phantom questions)
    rng = np.random.default_rng(0)
    w = boot_weights(['q1', 'q2', 'q3'], rng)
    assert set(w) == {'q1', 'q2', 'q3'}
    assert sum(w.values()) == 3   # n draws over n clusters conserves total count


def test_individual_vs_panel_aggregation_differ():
    # THE central artifact, demonstrated with a case where the two aggregations DISAGREE.
    # One judge gives a large positive gap, another a small negative gap:
    #   judge A: OE 4 vs opp 1 -> gap +3 -> vote +1
    #   judge B: OE 3 vs opp 4 -> gap -1 -> vote -1
    # INDIVIDUAL: signed votes [+1, -1] cancel -> win-difference 0.
    individual_votes = [threshold(4 - 1), threshold(3 - 4)]
    assert windiff(individual_votes) == 0.0
    # PANEL-MEAN-THEN-THRESHOLD: mean gap = ((4-1)+(3-4))/2 = +1.0 -> vote +1 -> win-difference +100.
    panel_gap = ((4 - 1) + (3 - 4)) / 2
    assert windiff([threshold(panel_gap)]) == 100.0
    # Same inputs, opposite conclusions: this is why the paper reports the aggregation-matched
    # (individual) statistic as primary rather than panel-mean-then-threshold.


def test_holm_monotone_and_capped():
    adj = holm([0.001, 0.02, 0.5])
    assert adj[0] <= adj[1] <= adj[2] and all(a <= 1.0 for a in adj)
    assert adj[0] == round(min(1.0, 3 * 0.001), 4)


def test_two_sided_p_floor():
    boot = [-5.0] * 100  # entirely below 0
    assert two_sided_p(boot) == 1.0 / 100  # floored, never 0


if __name__ == '__main__':
    fns = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for fn in fns:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\nall {len(fns)} tests passed")
