"""Randomly allocate REAL recruited physicians to exactly one arm, balanced by background/experience.

The reviewer IDs in the packets (REV-R##, REV-P##) guarantee separate arms, but NOT that the same real
person is only mapped to one ID. This tool takes your roster and produces a one-person -> one-arm ->
one-reviewer-ID allocation, randomly allocated but balanced by broad clinical background and experience band.

Roster CSV (--roster) must have columns: physician_id, background, years_experience.
Reads author_only/assignment_manifest.csv to learn how many rubric (REV-R##) and pairwise (REV-P##)
reviewer slots exist, then maps physicians onto them. Writes author_only/reviewer_allocation.csv:
  physician_id, background, years_experience, arm, reviewer_id   (author-only; do not send to reviewers)

Determinism: --seed (default 62). Balanced allocation: stratify by background x experience-band, then within
each stratum allocate to arms in proportion to the rubric:pairwise slot ratio, order randomised.

Usage: python3 allocate_reviewers.py --roster my_roster.csv
"""
import os, argparse
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
AUTHOR = os.path.join(HERE, 'author_only')


def exp_band(y):
    try:
        y = float(y)
    except Exception:
        return 'unknown'
    return '0-5' if y < 5 else ('6-15' if y < 15 else '16+')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--roster', required=True, help='CSV: physician_id, background, years_experience')
    ap.add_argument('--seed', type=int, default=62)
    a = ap.parse_args()

    asg = pd.read_csv(os.path.join(AUTHOR, 'assignment_manifest.csv'))
    rub_ids = sorted(asg.doctor_id.unique())                       # DR-## rubric doctors (essential arm D)
    pw_path = os.path.join(AUTHOR, 'pairwise_assignment_manifest.csv')
    pw_ids = sorted(pd.read_csv(pw_path).doctor_id.unique()) if os.path.exists(pw_path) else []  # DP-## (optional)
    need = len(rub_ids) + len(pw_ids)

    roster = pd.read_csv(a.roster)
    for c in ('physician_id', 'background', 'years_experience'):
        if c not in roster.columns:
            raise SystemExit(f"roster missing column '{c}'")
    if len(roster) < need:
        raise SystemExit(f"roster has {len(roster)} physicians but the design needs {need} "
                         f"({len(rub_ids)} rubric + {len(pw_ids)} pairwise). Recruit more, or rebuild the "
                         f"study with fewer pairs / more items per reviewer / fewer ratings per item.")

    roster = roster.copy()
    roster['exp_band'] = roster.years_experience.map(exp_band)
    # shuffle, then order by stratum so arms interleave across background x experience bands
    roster = roster.sample(frac=1.0, random_state=a.seed).sort_values(
        ['background', 'exp_band'], kind='stable').reset_index(drop=True)

    # take the first `need` as active (random, since pre-shuffled); rest are spares
    active = roster.iloc[:need].copy()
    frac_rub = len(rub_ids) / need
    # proportional arm within the stratum-ordered active list (largest-remainder on a running fraction)
    arm, r_used = [], 0
    for i in range(need):
        want_rub = round((i + 1) * frac_rub) - round(i * frac_rub)
        if want_rub and r_used < len(rub_ids):
            arm.append('rubric'); r_used += 1
        else:
            arm.append('pairwise')
    # fix any rounding drift so counts match exactly
    while arm.count('rubric') < len(rub_ids):
        arm[arm.index('pairwise')] = 'rubric'
    while arm.count('rubric') > len(rub_ids):
        arm[arm.index('rubric')] = 'pairwise'
    active['arm'] = arm
    rub_iter, pw_iter = iter(rub_ids), iter(pw_ids)
    active['reviewer_id'] = [next(rub_iter) if x == 'rubric' else next(pw_iter) for x in arm]

    spare = roster.iloc[need:].copy(); spare['arm'] = 'spare'; spare['reviewer_id'] = ''
    allocation = pd.concat([active, spare], ignore_index=True)
    out = os.path.join(AUTHOR, 'reviewer_allocation.csv')
    allocation[['physician_id', 'background', 'years_experience', 'exp_band', 'arm', 'reviewer_id']].to_csv(out, index=False)
    assigned = active
    print(f"allocated {len(assigned)} physicians ({len(rub_ids)} rubric, {len(pw_ids)} pairwise); "
          f"{len(spare)} spare")
    print(f"each physician -> one arm -> one reviewer_id. wrote {out} (author-only).")
    print("background x arm balance:")
    print(assigned.groupby(['background', 'arm']).size().to_dict())


if __name__ == '__main__':
    main()
