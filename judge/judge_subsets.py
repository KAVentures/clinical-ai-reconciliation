"""Finite-panel sensitivity: the aggregation-matched format effect over all 15 non-empty judge subsets.

With only four purposive judges we cannot claim random-judge generalization; this quantifies how the
same-judge format component (mean_j C_j - B_j) behaves as the panel is subsetted — every single judge,
every pair, every triple, and the full panel. Reports, per axis: the distribution of the format effect
across subsets, the fraction of subsets preserving the (negative) sign, and a breakdown by panel size.
Label: FINITE-PANEL sensitivity, not population inference.

No API calls; reuses matched units from robust_analysis.py. Writes out/judge_subsets.json.
"""
import os, json
from itertools import combinations
import numpy as np
from robust_analysis import (load_rubric, load_pairwise, matched_units, windiff_units,
                             AXES, JUDGES, OUT)


def format_effect(units_axis, subset):
    """mean over judges in subset of (C_j - B_j), unit-weighted."""
    d = [windiff_units(units_axis[j], 'c_vote', None) - windiff_units(units_axis[j], 'b_vote', None)
         for j in subset]
    return float(np.nanmean(d))


def main():
    R, P = load_rubric(), load_pairwise()
    units = {ax: {j: matched_units(R[ax], P[ax], j) for j in JUDGES} for ax in AXES}
    subsets = [c for k in range(1, len(JUDGES) + 1) for c in combinations(JUDGES, k)]

    out = {'n_subsets': len(subsets), 'judges': JUDGES, 'by_axis': {}}
    print(f"{'axis':16s}{'full':>7s}{'min':>7s}{'max':>7s}{'median':>8s}{'neg/15':>8s}  by size (1|2|3|4)")
    for ax in AXES:
        vals = {sub: format_effect(units[ax], sub) for sub in subsets}
        full = vals[tuple(JUDGES)]
        arr = np.array(list(vals.values()))
        neg = int(np.sum(arr < 0))
        by_size = {}
        for k in range(1, 5):
            ks = [vals[s] for s in subsets if len(s) == k]
            by_size[k] = {'min': round(min(ks), 1), 'max': round(max(ks), 1),
                          'median': round(float(np.median(ks)), 1),
                          'n_negative': int(np.sum(np.array(ks) < 0)), 'n': len(ks)}
        out['by_axis'][ax] = {
            'full_panel': round(full, 1),
            'min': round(float(arr.min()), 1), 'max': round(float(arr.max()), 1),
            'median': round(float(np.median(arr)), 1),
            'n_subsets_negative': neg, 'n_subsets': len(subsets),
            'sign_preserved_frac': round(neg / len(subsets), 3),
            'per_single_judge': {j: round(vals[(j,)], 1) for j in JUDGES},
            'by_panel_size': by_size,
        }
        bs = out['by_axis'][ax]['by_panel_size']
        print(f"{ax:16s}{full:>+7.1f}{arr.min():>+7.1f}{arr.max():>+7.1f}{np.median(arr):>+8.1f}"
              f"{neg:>6d}/{len(subsets)}  "
              f"{bs[1]['median']:+.0f}|{bs[2]['median']:+.0f}|{bs[3]['median']:+.0f}|{bs[4]['median']:+.0f}")

    json.dump(out, open(os.path.join(OUT, 'judge_subsets.json'), 'w'), indent=2)
    print("\nAll 15 subsets negative on every axis:",
          all(v['n_subsets_negative'] == v['n_subsets'] for v in out['by_axis'].values()))
    print("wrote out/judge_subsets.json  (FINITE-PANEL sensitivity, not population inference)")


if __name__ == '__main__':
    main()
