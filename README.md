# MotionsDTMB3Spectra

Heave, pitch and roll time histories of the DTMB vessel, together with a network of wave-probe
elevation records, for 50 random realizations (seeds) of each of 3 Pierson–Moskowitz sea states.
That gives 150 realizations in total.

| Sea state | State code | H<sub>s</sub> [m] | T<sub>p</sub> [s] | Δt [s] |
|---|---|---|---|---|
| 1 | `97`  | 3.53  | 9.7  | 0.008 |
| 2 | `124` | 5.09  | 12.4 | 0.010 |
| 3 | `134` | 10.66 | 13.4 | 0.011 |

The state code in each filename is 10 × T<sub>p</sub>.

- Waves are long-crested (unidirectional) and oblique, propagating at 30° to the vessel's plane of symmetry.
- Forward speed is constant at 30 kn.
- The simulation setup, coordinate conventions and the use of these data are described in
  [del Aguila Ferrandis (2026), arXiv:2603.24431](https://arxiv.org/abs/2603.24431).
  The records are also plotted in Appendix A (Figs. A-1 to A-9) of the author's
  [PhD thesis (MIT, 2024)](https://hdl.handle.net/1721.1/156348). See [Citation](#citation).

## Quick start

From the repository root (Python ≥ 3.9):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python check_data.py                 # verify the dataset is complete (a few seconds)
python plot_dtmb_appendix.py --figs A-1 A-7 --formats png --combined ''   # first look (< 1 min)
python plot_dtmb_appendix.py         # all thesis figures A-1 to A-9 -> ./appendix_figs/
```

The second command plots the longitudinal wave probes (Fig. A-1) and the heave/pitch/roll
(Fig. A-7) for all seeds of sea state 1. To work with individual records in Python, see
[`MotionsDTMB3Repo`](#motionsdtmb3repo) below.

## Data: `MotionsAndWaveData/`

All 3,212 files sit flat in one directory.

### Motion files: `{H,P,R}_{state}_{seed}.csv`

| Signal | Meaning | Unit |
|---|---|---|
| `H` | heave | m |
| `P` | pitch | deg |
| `R` | roll | deg |

- `state` is one of `97`, `124`, `134`, and `seed` runs from 1 to 50. All 450 files are present.
- Format: one header row, then two columns, `time [s], value`.
- Example: `H_134_3.csv` is the heave for seed 3 of sea state 3 (T<sub>p</sub> = 13.4 s).

### Wave-probe files: `WaveProve{X,Y}_{state}_{seed}_{location}.csv`

The filenames use the spelling `WaveProve`, not `WaveProbe`.

- `X` is the longitudinal probe array and `Y` the transversal array.
- `location` is the probe coordinate in metres, measured from the aft perpendicular (AP) of the ship.
  For `X` it is the longitudinal coordinate and for `Y` the transverse coordinate.
  For the axis directions and probe layout, see the [paper](https://arxiv.org/abs/2603.24431).
- Format: one column of surface elevation [m], with no time column. Sample *k* shares the time
  stamp of sample *k* in the motion files of the same state.

**The set of probe locations is not the same for every seed.** Every seed of every state has these locations:

```
X: -250, -200, -150, -100, -50, 0
Y:    0,   50,  100,  150, 200, 250
```

Individual seeds have extra locations. The union over all seeds, per state:

| State | X locations | Y locations |
|---|---|---|
| `97`  | −250 … 0 (step 50), 50 | −50, 0 … 250 (step 50) |
| `124` | −400 … 50 (18 values, down to 25-step spacing near midships) | −50, −25, −20, −10, 0 … 250 (step 25), 300, 350, 400 |
| `134` | −400 … 50 (12 values, incl. −160, −140) | −50, −20, −10, 0 … 400 (step 50) |

Use `repo.probe_locations()` (see below) for the exact sets.

## Code

| File | Purpose |
|---|---|
| `motions_dtmb3_repo.py` | `MotionsDTMB3Repo`: indexes the data directory and loads series as pandas / xarray objects |
| `analyze_dtmb.py` | Short usage example of `MotionsDTMB3Repo` |
| `plot_dtmb_appendix.py` | Regenerates thesis Figs. A-1 to A-9 |
| `check_data.py` | Verifies file counts, seed and probe coverage, and Δt per sea state |
| `requirements.txt` | `numpy`, `pandas`, `xarray`, `matplotlib`; `pypdf` (optional, only for the merged PDF) |

Run the scripts from the repository root, so that `./MotionsAndWaveData` resolves.

### `MotionsDTMB3Repo`

```python
from motions_dtmb3_repo import MotionsDTMB3Repo

repo = MotionsDTMB3Repo("./MotionsAndWaveData")
repo.summary()            # file counts, state codes, signals, probe axes
repo.probe_locations()    # {"X": {state: [locs]}, "Y": {state: [locs]}}
repo.select(kind="probe", axis="X", state_code=124, seed=25)   # catalog rows

df = repo.load_motion(signal="R", state_code=124, seed=4)                  # time_s, value, ...
df = repo.load_probe(axis="Y", state_code=124, seed=25, location=350)      # time_s, value, sample, ...
ds = repo.load_case(state_code=124, seed=25)     # xarray.Dataset: heave/pitch/roll, probe_x, probe_y
da = repo.load_motion_matrix(signal="R", state_code=124)   # DataArray (seed, time)
```

### Regenerating the thesis figures

```bash
python plot_dtmb_appendix.py                       # all 9 figures -> ./appendix_figs/
python plot_dtmb_appendix.py --figs A-3 A-9 --caption
python plot_dtmb_appendix.py --x-locs -200 -150 -100 -50 0 --y-locs 0 50 100 150
```

| Figures | Content |
|---|---|
| A-1 to A-3 | Longitudinal probes, sea states 1–3 |
| A-4 to A-6 | Transversal probes, sea states 1–3 |
| A-7 to A-9 | Heave, pitch and roll, sea states 1–3 |

Each figure has one panel per seed on a 7-column grid, filled column-major. The x-axis is the
sample index.

Output: for each figure, `fig_A-k_*.pdf` and `fig_A-k_*.png`, plus a merged `appendix_A_all.pdf`.

| Option | Effect |
|---|---|
| `--root`, `--out` | Data directory and output directory |
| `--figs` | Subset of `A-1` … `A-9` |
| `--x-locs`, `--y-locs` | Probe locations drawn as WP1…WPn. The default is the common set above. |
| `--loc-labels` | Label probe lines by location instead of WPk |
| `--all-seeds` | Include seed 49. The thesis figures omit it; with all 50 seeds the grid becomes 7 × 8. |
| `--caption` | Print the thesis caption under each figure |
| `--formats`, `--dpi` | Output formats and raster resolution |
| `--combined` | Name of the merged PDF; pass `''` to skip it |

Sea-state parameters, the probe-location lists, colors and labels are in the `CONFIG` block at
the top of `plot_dtmb_appendix.py`.

## Citation

If you use this dataset or code, please cite:

```bibtex
@misc{ferrandis2026learningresponsestatisticshiftsparametric,
  title         = {Learning Response-Statistic Shifts and Parametric Roll Episodes from
                   Wave--Vessel Time Series via {LSTM} Functional Models},
  author        = {del Aguila Ferrandis, Jose},
  year          = {2026},
  eprint        = {2603.24431},
  archivePrefix = {arXiv},
  primaryClass  = {cs.LG},
  url           = {https://arxiv.org/abs/2603.24431}
}
```

The data also appear in Appendix A of:

```bibtex
@phdthesis{delaguilaferrandis2024thesis,
  title  = {Exploring Complex Problems in Fluid Dynamics: from {CFD} to Experiments Leveraging {ML}},
  author = {del Aguila Ferrandis, Jose},
  school = {Massachusetts Institute of Technology},
  year   = {2024},
  month  = may,
  url    = {https://hdl.handle.net/1721.1/156348}
}
```
