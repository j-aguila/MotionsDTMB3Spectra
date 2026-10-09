#!/usr/bin/env python3
# check_data.py
"""
Sanity check for MotionsAndWaveData/: verifies file counts, that every seed of every
sea state has H/P/R and the default probe locations, and that the sampling time step
matches the documented value. Run from the repository root:

    python check_data.py [--root ./MotionsAndWaveData]
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from motions_dtmb3_repo import MotionsDTMB3Repo
from plot_dtmb_appendix import SEA_STATES, PROBE_LOCATIONS

EXPECTED = {"n_files": 3212, "n_motion_files": 450, "n_probe_files": 2762}
N_SEEDS = 50


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="./MotionsAndWaveData")
    args = ap.parse_args()

    repo = MotionsDTMB3Repo(args.root)
    s = repo.summary()
    errors: list[str] = []

    for key, val in EXPECTED.items():
        if s[key] != val:
            errors.append(f"{key}: found {s[key]}, expected {val}")
    if s["state_codes"] != sorted(SEA_STATES):
        errors.append(f"state codes: found {s['state_codes']}, expected {sorted(SEA_STATES)}")

    for code, ss in SEA_STATES.items():
        for sig in "HPR":
            seeds = set(repo.select(kind="motion", signal=sig, state_code=code)["seed"])
            if missing := sorted(set(range(1, N_SEEDS + 1)) - seeds):
                errors.append(f"{sig} state {code}: missing seeds {missing}")
        for ax, locs in PROBE_LOCATIONS.items():
            sub = repo.select(kind="probe", axis=ax, state_code=code)
            have = set(zip(sub["seed"], sub["location"].astype(int)))
            missing = [(sd, l) for sd in range(1, N_SEEDS + 1) for l in locs if (sd, l) not in have]
            if missing:
                errors.append(f"{ax} probes state {code}: {len(missing)} missing, e.g. {missing[:3]}")
        try:
            t = repo._get_reference_motion_time(code)
            dt = float(np.median(np.diff(t)))
            n_probe = len(repo.load_probe("X", code, 1, PROBE_LOCATIONS["X"][-1]))
            print(f"state {code}: dt = {dt:.4g} s, motion samples = {len(t)}, "
                  f"probe samples = {n_probe}")
            if not np.isclose(dt, ss.dt, rtol=0.02):
                errors.append(f"state {code}: dt {dt:.4g} s, expected {ss.dt} s")
        except (ValueError, IndexError) as e:
            errors.append(f"state {code}: {e}")

    print(f"{s['n_files']} files: {s['n_motion_files']} motion, {s['n_probe_files']} probe")
    if errors:
        print("\nFAILED:")
        for e in errors:
            print("  -", e)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
