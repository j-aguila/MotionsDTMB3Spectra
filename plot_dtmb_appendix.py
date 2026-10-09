#!/usr/bin/env python3
# plot_dtmb_appendix.py
"""
Regenerate thesis Appendix A figures A-1 ... A-9 (DTMB wave probes and motions)
from the MotionsAndWaveData repository, using MotionsDTMB3Repo.

    A-1..A-3 : longitudinal wave probes (WP1..WPn), one figure per sea state
    A-4..A-6 : transversal wave probes  (WP1..WPn), one figure per sea state
    A-7..A-9 : heave / pitch / roll,               one figure per sea state

Each figure is a grid with 7 columns and one panel per seed, filled column-major
(column 1 = seeds 1-7, column 2 = seeds 8-14, ...), as in the thesis.

Assumptions (edit the CONFIG block if any are wrong):
  A1. state_code = 10*Tp  ->  97: Tp 9.7 s,  124: Tp 12.4 s,  134: Tp 13.4 s.
  A2. Longitudinal probes = axis "X" files, transversal probes = axis "Y" files.
  A3. The probe set differs between seeds on disk (6 to 18 locations), so every
      panel plots the same fixed list PROBE_LOCATIONS[axis]; WPk is the k-th entry,
      with the same color in every panel. The default is the set present for all
      seeds of all states. Locations are in metres from the aft perpendicular.
      The thesis shows 5 (X) and 4 (Y) probes, which subset is
      not recoverable from the files: override with --x-locs / --y-locs.
  A4. x-axis is the sample index ("Time Step"), not seconds, as in the originals.
  A5. All 50 seeds exist on disk; the thesis figures omit seed 49 (7x7 = 49 panels).
      EXCLUDE_SEEDS reproduces that; --all-seeds plots all 50 (7x8 grid).
  A6. dt in the captions is taken from the thesis and cross-checked against the
      motion-file time column; a warning is printed on mismatch.

Usage:
    python plot_dtmb_appendix.py --root ./MotionsAndWaveData --out ./figs
    python plot_dtmb_appendix.py --root ./MotionsAndWaveData --figs A-3 A-9 --caption
"""
from __future__ import annotations

import argparse
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from motions_dtmb3_repo import MotionsDTMB3Repo


# ============================== CONFIG ======================================

@dataclass(frozen=True)
class SeaState:
    code: int      # state_code in filenames
    Hs: float      # [m]
    Tp: float      # [s]
    dt: float      # [s], nominal (thesis caption)


SEA_STATES = {
    97:  SeaState(97,  3.53,  9.7, 0.008),
    124: SeaState(124, 5.09, 12.4, 0.010),
    134: SeaState(134, 10.66, 13.4, 0.011),
}
SPEED_KT = 30

# Figure number -> (kind, probe axis or None, state_code)
FIGURES = {
    "A-1": ("probe", "X", 97),  "A-2": ("probe", "X", 124), "A-3": ("probe", "X", 134),
    "A-4": ("probe", "Y", 97),  "A-5": ("probe", "Y", 124), "A-6": ("probe", "Y", 134),
    "A-7": ("motion", None, 97), "A-8": ("motion", None, 124), "A-9": ("motion", None, 134),
}

AXIS_WORD = {"X": "longitudinal", "Y": "transversal"}

# Probe locations plotted as WP1..WPn (filename location values). Default = the
# locations present for every seed in all three states.
PROBE_LOCATIONS = {
    "X": [-250, -200, -150, -100, -50, 0],
    "Y": [0, 50, 100, 150, 200, 250],
}
EXCLUDE_SEEDS = {49}           # omitted in thesis Figs. A-1..A-9

GRID_COLS = 7
PANEL_SIZE = (26.0 / 7, 17.0 / 7)   # inches per panel incl. legend; 7x7 -> 26 x 17 in
LW = 0.5
YLABEL_PROBE = "Wave Probe"    # original panels read "Wave Prove"; change if you want it verbatim
YLABEL_MOTION = "H,P,R"
PROBE_COLORS = ["tab:green", "red", "deepskyblue", "magenta", "gold",
                "tab:blue", "tab:orange", "tab:purple"]
MOTION_STYLE = {               # plotted in this order (R on top, as in originals)
    "H": ("H(m)", "red"),
    "P": ("P(\u00b0)", "deepskyblue"),
    "R": ("R(\u00b0)", "magenta"),
}

# ============================================================================


def caption(fig_id: str, kind: str, axis: str | None, ss: SeaState) -> str:
    params = (f"Each time step is $\\Delta t = {ss.dt:g}s$, $H_s = {ss.Hs:g}m$, "
              f"$T_p = {ss.Tp:g}s$, $v = {SPEED_KT}kt$.")
    if kind == "probe":
        return (f"Figure {fig_id}: Network wave probes along the {AXIS_WORD[axis]} direction "
                f"of the DTMB vessel. They are two-dimensional and represent a long crested "
                f"irregular oblique waves. " + params)
    return (f"Figure {fig_id}: Motion time histories of the DTMB vessel. Heave, pitch and roll "
            f"motions are provided for each sea state seed. " + params)


def check_dt(repo: MotionsDTMB3Repo, ss: SeaState) -> None:
    try:
        t = repo._get_reference_motion_time(ss.code)
    except ValueError:
        return
    if len(t) < 2:
        return
    dt = float(np.median(np.diff(t)))
    if not np.isclose(dt, ss.dt, rtol=0.02):
        warnings.warn(f"state {ss.code}: data dt = {dt:.5g} s, caption dt = {ss.dt:g} s")


def seed_grid(seeds: list[int]):
    nc = GRID_COLS
    nr = max(GRID_COLS, -(-len(seeds) // nc))
    fig, axes = plt.subplots(nr, nc, figsize=(PANEL_SIZE[0] * nc, PANEL_SIZE[1] * nr),
                             squeeze=False, layout="constrained")
    slots = [(r, c) for c in range(nc) for r in range(nr)]          # column-major
    for r, c in slots[len(seeds):]:
        axes[r, c].set_visible(False)
    return fig, {s: axes[rc] for s, rc in zip(seeds, slots)}


def style_panel(ax, seed: int, ylabel: str) -> None:
    ax.set_title(f"Seed {seed}", fontsize=7, fontweight="bold", pad=2)
    ax.set_xlabel("Time Step", fontsize=6, fontweight="bold", labelpad=1)
    ax.set_ylabel(ylabel, fontsize=6, fontweight="bold", labelpad=1)
    ax.tick_params(labelsize=5, length=2, pad=1)
    ax.margins(x=0)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=5,
              frameon=False, handlelength=1.2, borderaxespad=0)


def select_seeds(sel, exclude: set[int]) -> list[int]:
    return [s for s in sorted(sel["seed"].unique().tolist()) if s not in exclude]


def plot_probe_figure(repo: MotionsDTMB3Repo, axis: str, ss: SeaState,
                      locations: list[int], exclude: set[int], loc_labels: bool):
    sel = repo.select(kind="probe", axis=axis, state_code=ss.code)
    if sel.empty:
        raise ValueError(f"no {axis}-probe files for state {ss.code}")
    seeds = select_seeds(sel, exclude)
    fig, panels = seed_grid(seeds)

    for seed in seeds:
        ax = panels[seed]
        on_disk = set(sel.loc[sel["seed"] == seed, "location"].astype(int))
        for i, loc in enumerate(locations):
            label = f"{axis.lower()}={loc} m" if loc_labels else f"WP{i + 1}"
            if loc not in on_disk:
                warnings.warn(f"state {ss.code} seed {seed}: no {axis}-probe at {loc}")
                continue
            try:
                y = repo.load_probe(axis=axis, state_code=ss.code, seed=seed,
                                    location=loc)["value"].to_numpy()
            except ValueError as e:
                warnings.warn(str(e))
                continue
            ax.plot(np.arange(y.size), y, lw=LW, label=label,
                    color=PROBE_COLORS[i % len(PROBE_COLORS)])
        style_panel(ax, seed, YLABEL_PROBE)
    return fig


def plot_motion_figure(repo: MotionsDTMB3Repo, ss: SeaState, exclude: set[int]):
    sel = repo.select(kind="motion", state_code=ss.code)
    if sel.empty:
        raise ValueError(f"no motion files for state {ss.code}")
    seeds = select_seeds(sel, exclude)
    fig, panels = seed_grid(seeds)

    for seed in seeds:
        ax = panels[seed]
        for sig, (label, color) in MOTION_STYLE.items():
            if sel[(sel["seed"] == seed) & (sel["signal"] == sig)].empty:
                continue
            y = repo.load_motion(signal=sig, state_code=ss.code, seed=seed)["value"].to_numpy()
            ax.plot(np.arange(y.size), y, lw=LW, label=label, color=color)
        style_panel(ax, seed, YLABEL_MOTION)
    return fig


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="./MotionsAndWaveData")
    ap.add_argument("--out", default="./appendix_figs")
    ap.add_argument("--figs", nargs="+", default=list(FIGURES), choices=list(FIGURES))
    ap.add_argument("--formats", nargs="+", default=["pdf", "png"])
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--x-locs", nargs="+", type=int, default=PROBE_LOCATIONS["X"],
                    help="longitudinal probe locations plotted as WP1..WPn")
    ap.add_argument("--y-locs", nargs="+", type=int, default=PROBE_LOCATIONS["Y"],
                    help="transversal probe locations plotted as WP1..WPn")
    ap.add_argument("--loc-labels", action="store_true",
                    help="label probe lines by location value instead of WPk")
    ap.add_argument("--all-seeds", action="store_true",
                    help="plot every seed on disk (thesis omits seed 49)")
    ap.add_argument("--caption", action="store_true",
                    help="print the thesis caption under each figure")
    ap.add_argument("--combined", default="appendix_A_all.pdf",
                    help="multi-page PDF merged from the per-figure PDFs ('' to skip; needs pypdf)")
    args = ap.parse_args()

    repo = MotionsDTMB3Repo(args.root)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    on_disk = set(repo.catalog["state_code"].unique().tolist())
    if extra := on_disk - set(SEA_STATES):
        warnings.warn(f"state codes on disk without a SEA_STATES entry: {sorted(extra)}")
    for code in {FIGURES[f][2] for f in args.figs}:
        if code in on_disk:
            check_dt(repo, SEA_STATES[code])

    locations = {"X": args.x_locs, "Y": args.y_locs}
    exclude = set() if args.all_seeds else EXCLUDE_SEEDS
    written_pdfs: list[Path] = []
    for fig_id in args.figs:
        kind, axis, code = FIGURES[fig_id]
        if code not in on_disk:
            warnings.warn(f"{fig_id}: state {code} not found on disk, skipped")
            continue
        ss = SEA_STATES[code]
        fig = (plot_probe_figure(repo, axis, ss, locations[axis], exclude, args.loc_labels)
               if kind == "probe" else plot_motion_figure(repo, ss, exclude))
        if args.caption:
            fig.get_layout_engine().set(rect=(0, 0.03, 1, 0.97))
            fig.text(0.5, 0.01, caption(fig_id, kind, axis, ss),
                     ha="center", va="bottom", fontsize=12, wrap=True)

        tag = f"{kind}{'_' + AXIS_WORD[axis] if axis else ''}_ss{code}"
        for fmt in args.formats:
            path = out / f"fig_{fig_id}_{tag}.{fmt}"
            fig.savefig(path, dpi=args.dpi)
            print(f"wrote {path}")
            if fmt == "pdf":
                written_pdfs.append(path)
        plt.close(fig)

    # Merge per-figure PDFs (keeps only one figure in memory at a time).
    if args.combined and written_pdfs:
        try:
            from pypdf import PdfWriter
        except ImportError:
            warnings.warn("pypdf not installed; combined PDF skipped (pip install pypdf)")
            return
        writer = PdfWriter()
        for path in written_pdfs:
            writer.append(str(path))
        with open(out / args.combined, "wb") as fh:
            writer.write(fh)
        print(f"wrote {out / args.combined}")

if __name__ == "__main__":
    main()
