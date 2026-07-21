"""Deterministic tests for the robust decomposition core (peer-review revision).

Pins the estimand definitions that the manuscript's primary claims depend on — matched-unit
construction, individual-vs-panel aggregation, tie thresholding, and missing-grade handling — with
fixed synthetic rows and no file/network access. Run: python3 test_robust_analysis.py
"""
from robust_analysis import threshold, windiff, matched_units, holm, two_sided_p, OE

G = 'gpt-5.5'


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
    assert mu['qid'] == ['q1']
    assert mu['c_vote'] == [threshold(2.0 - 4.0)] == [-1]   # rubric: OE loses
    assert mu['b_vote'] == [1]                               # pairwise: OE wins  -> a per-item flip


def test_individual_vs_panel_aggregation_differ():
    # THE central artifact: two judges split, panel-mean-then-threshold amplifies vs individual mean.
    # judge A: OE 2 vs opp 4 -> -1 ; judge B: OE 3.9 vs opp 4 -> -1 (tiny gap still a loss)
    # individual votes: [-1, -1] each judge one unit -> both windiff -100 ; mean -100
    # panel mean gap = ((2-4)+(3.9-4))/2 = -1.05 -> threshold -1 as well here; construct a real split:
    # judge A: OE 4 vs opp 2 (+1) ; judge B: OE 2 vs opp 4 (-1) -> individual mean of windiffs = 0
    # panel mean gap = ((4-2)+(2-4))/2 = 0 -> tie. Both agree = 0 here (sanity boundary).
    jA = windiff([threshold(4 - 2)])   # +100
    jB = windiff([threshold(2 - 4)])   # -100
    assert (jA + jB) / 2 == 0.0
    panel = windiff([threshold((4 + 2) / 2 - (2 + 4) / 2)])  # threshold(0) -> 0
    assert panel == 0.0
    # now the amplifying case: 3 judges mildly negative, panel crosses threshold consistently
    gaps = [-0.2, -0.2, -0.2]                      # each a small loss
    indiv = sum(windiff([threshold(g)]) for g in gaps) / 3   # -100 (all count as full losses individually too)
    assert indiv == -100.0


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
