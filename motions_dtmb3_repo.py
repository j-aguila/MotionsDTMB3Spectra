# motions_dtmb3_repo.py
from __future__ import annotations

from pathlib import Path
import re
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt


MOTION_RE = re.compile(
    r"^(?P<signal>[HPR])_(?P<state_code>\d+)_(?P<seed>\d+)\.csv$"
)

PROBE_RE = re.compile(
    r"^WaveProve(?P<axis>[XY])_(?P<state_code>\d+)_(?P<seed>\d+)_(?P<location>-?\d+)\.csv$"
)

SIGNAL_NAME = {
    "H": "heave",
    "P": "pitch",
    "R": "roll",
}

SIGNAL_UNIT = {
    "H": "m",
    "P": "deg",
    "R": "deg",
}


@dataclass(frozen=True)
class FileMeta:
    kind: str
    path: str
    filename: str
    state_code: int
    seed: int
    signal: Optional[str] = None
    axis: Optional[str] = None
    location: Optional[int] = None


class MotionsDTMB3Repo:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"Repository root not found: {self.root}")

        self.catalog = self._build_catalog()
        self._time_cache: dict[int, np.ndarray] = {}

    def _parse_filename(self, path: Path) -> Optional[FileMeta]:
        name = path.name

        m = MOTION_RE.match(name)
        if m:
            return FileMeta(
                kind="motion",
                path=str(path),
                filename=name,
                signal=m.group("signal"),
                state_code=int(m.group("state_code")),
                seed=int(m.group("seed")),
            )

        m = PROBE_RE.match(name)
        if m:
            return FileMeta(
                kind="probe",
                path=str(path),
                filename=name,
                axis=m.group("axis"),
                location=int(m.group("location")),
                state_code=int(m.group("state_code")),
                seed=int(m.group("seed")),
            )

        return None

    def _build_catalog(self) -> pd.DataFrame:
        rows = []

        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue
            meta = self._parse_filename(path)
            if meta is None:
                continue

            rows.append({
                "kind": meta.kind,
                "path": meta.path,
                "filename": meta.filename,
                "state_code": meta.state_code,
                "seed": meta.seed,
                "signal": meta.signal,
                "axis": meta.axis,
                "location": meta.location,
            })

        if not rows:
            raise ValueError("No motion/probe files found in the repository.")

        df = pd.DataFrame(rows).sort_values(
            ["kind", "state_code", "seed", "signal", "axis", "location"],
            na_position="last"
        ).reset_index(drop=True)

        return df

    def summary(self) -> dict:
        motion_df = self.catalog[self.catalog["kind"] == "motion"]
        probe_df = self.catalog[self.catalog["kind"] == "probe"]

        return {
            "n_files": len(self.catalog),
            "n_motion_files": len(motion_df),
            "n_probe_files": len(probe_df),
            "state_codes": sorted(self.catalog["state_code"].unique().tolist()),
            "signals": sorted(motion_df["signal"].dropna().unique().tolist()),
            "probe_axes": sorted(probe_df["axis"].dropna().unique().tolist()),
        }

    def probe_locations(self) -> dict:
        probe_df = self.catalog[self.catalog["kind"] == "probe"]

        out: dict[str, dict[int, list[int]]] = {"X": {}, "Y": {}}
        for axis in ["X", "Y"]:
            for state_code in sorted(probe_df["state_code"].unique()):
                locs = sorted(
                    probe_df.loc[
                        (probe_df["axis"] == axis) &
                        (probe_df["state_code"] == state_code),
                        "location"
                    ].dropna().astype(int).unique().tolist()
                )
                if locs:
                    out[axis][int(state_code)] = locs

        return out

    def select(
        self,
        *,
        kind: Optional[str] = None,
        state_code: Optional[int] = None,
        seed: Optional[int] = None,
        signal: Optional[str] = None,
        axis: Optional[str] = None,
        location: Optional[int] = None,
    ) -> pd.DataFrame:
        df = self.catalog

        if kind is not None:
            df = df[df["kind"] == kind]
        if state_code is not None:
            df = df[df["state_code"] == state_code]
        if seed is not None:
            df = df[df["seed"] == seed]
        if signal is not None:
            df = df[df["signal"] == signal]
        if axis is not None:
            df = df[df["axis"] == axis]
        if location is not None:
            df = df[df["location"] == location]

        return df.reset_index(drop=True)

    def _get_reference_motion_time(self, state_code: int) -> np.ndarray:
        if state_code in self._time_cache:
            return self._time_cache[state_code]

        rows = self.select(kind="motion", state_code=state_code, signal="H")
        if rows.empty:
            rows = self.select(kind="motion", state_code=state_code)
        if rows.empty:
            raise ValueError(f"No motion file found for state_code={state_code}")

        path = Path(rows.iloc[0]["path"])
        raw = pd.read_csv(path)
        time = raw.iloc[:, 0].to_numpy(dtype=float)

        self._time_cache[state_code] = time
        return time

    def load_motion(self, signal: str, state_code: int, seed: int) -> pd.DataFrame:
        rows = self.select(
            kind="motion",
            signal=signal,
            state_code=state_code,
            seed=seed,
        )
        if len(rows) != 1:
            raise ValueError(
                f"Expected 1 motion file, found {len(rows)} "
                f"for signal={signal}, state_code={state_code}, seed={seed}"
            )

        path = Path(rows.iloc[0]["path"])
        raw = pd.read_csv(path)

        df = pd.DataFrame({
            "time_s": raw.iloc[:, 0].to_numpy(dtype=float),
            "value": raw.iloc[:, 1].to_numpy(dtype=float),
        })
        df["kind"] = "motion"
        df["signal"] = signal
        df["signal_name"] = SIGNAL_NAME.get(signal, signal)
        df["unit"] = SIGNAL_UNIT.get(signal, "")
        df["state_code"] = state_code
        df["seed"] = seed

        return df

    def load_probe(self, axis: str, state_code: int, seed: int, location: int) -> pd.DataFrame:
        rows = self.select(
            kind="probe",
            axis=axis,
            state_code=state_code,
            seed=seed,
            location=location,
        )
        if len(rows) != 1:
            raise ValueError(
                f"Expected 1 probe file, found {len(rows)} "
                f"for axis={axis}, state_code={state_code}, seed={seed}, location={location}"
            )

        path = Path(rows.iloc[0]["path"])
        raw = pd.read_csv(path, comment="#", header=None, names=["value"])

        time_ref = self._get_reference_motion_time(state_code)
        n = len(raw)

        if len(time_ref) < n:
            raise ValueError(
                f"Motion time vector too short for probe file {path.name}: "
                f"{len(time_ref)} < {n}"
            )

        df = pd.DataFrame({
            "time_s": time_ref[:n],
            "value": raw["value"].to_numpy(dtype=float),
            "sample": np.arange(n, dtype=int),
        })
        df["kind"] = "probe"
        df["axis"] = axis
        df["location"] = location
        df["signal_name"] = f"wave_probe_{axis.lower()}"
        df["unit"] = "m"
        df["state_code"] = state_code
        df["seed"] = seed

        return df

    def load_case(self, state_code: int, seed: int) -> xr.Dataset:
        ds = xr.Dataset()

        motion_rows = self.select(kind="motion", state_code=state_code, seed=seed)
        if motion_rows.empty:
            raise ValueError(f"No motion files for state_code={state_code}, seed={seed}")

        time_motion = None
        for signal in ["H", "P", "R"]:
            rows = motion_rows[motion_rows["signal"] == signal]
            if rows.empty:
                continue

            df = self.load_motion(signal=signal, state_code=state_code, seed=seed)
            if time_motion is None:
                time_motion = df["time_s"].to_numpy(dtype=float)
                ds = ds.assign_coords(time_motion=time_motion)

            ds[SIGNAL_NAME[signal]] = xr.DataArray(
                df["value"].to_numpy(dtype=float),
                dims=("time_motion",),
                coords={"time_motion": ds["time_motion"]},
                attrs={"unit": SIGNAL_UNIT[signal], "signal": signal},
            )

        probe_rows = self.select(kind="probe", state_code=state_code, seed=seed)

        for axis in ["X", "Y"]:
            sub = probe_rows[probe_rows["axis"] == axis]
            if sub.empty:
                continue

            locs = sorted(sub["location"].dropna().astype(int).unique().tolist())
            cols = []
            time_probe = None

            for loc in locs:
                dfp = self.load_probe(axis=axis, state_code=state_code, seed=seed, location=loc)
                if time_probe is None:
                    time_probe = dfp["time_s"].to_numpy(dtype=float)
                cols.append(dfp["value"].to_numpy(dtype=float))

            data = np.column_stack(cols)

            loc_dim = f"{axis.lower()}_location"
            time_dim = f"time_probe_{axis.lower()}"

            ds = ds.assign_coords({
                time_dim: time_probe,
                loc_dim: locs,
            })

            ds[f"probe_{axis.lower()}"] = xr.DataArray(
                data,
                dims=(time_dim, loc_dim),
                coords={time_dim: ds[time_dim], loc_dim: ds[loc_dim]},
                attrs={"unit": "m", "axis": axis},
            )

        ds.attrs["state_code"] = state_code
        ds.attrs["seed"] = seed
        return ds

    def load_motion_matrix(self, signal: str, state_code: int) -> xr.DataArray:
        rows = self.select(kind="motion", signal=signal, state_code=state_code)
        if rows.empty:
            raise ValueError(f"No files for signal={signal}, state_code={state_code}")

        seeds = sorted(rows["seed"].unique().tolist())
        series = []
        time = None

        for seed in seeds:
            df = self.load_motion(signal=signal, state_code=state_code, seed=seed)
            if time is None:
                time = df["time_s"].to_numpy(dtype=float)
            series.append(df["value"].to_numpy(dtype=float))

        arr = np.vstack(series)
        return xr.DataArray(
            arr,
            dims=("seed", "time"),
            coords={"seed": seeds, "time": time},
            name=SIGNAL_NAME.get(signal, signal),
            attrs={"unit": SIGNAL_UNIT.get(signal, "")},
        )

    @staticmethod
    def inspect_series(df: pd.DataFrame, rolling: Optional[int] = None) -> None:
        print(df.head())
        print()
        print(df[["time_s", "value"]].describe())

        plt.figure(figsize=(10, 4))
        plt.plot(df["time_s"], df["value"], lw=1, label="raw")

        if rolling is not None and rolling > 1:
            smooth = df["value"].rolling(rolling, center=True).mean()
            plt.plot(df["time_s"], smooth, lw=2, label=f"rolling mean ({rolling})")

        plt.xlabel("time [s]")
        plt.ylabel("value")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.show()

    @staticmethod
    def quick_spectrum(df: pd.DataFrame) -> pd.DataFrame:
        t = df["time_s"].to_numpy(dtype=float)
        y = df["value"].to_numpy(dtype=float)

        dt = np.mean(np.diff(t))
        y0 = y - np.mean(y)

        freqs = np.fft.rfftfreq(len(y0), d=dt)
        amp = np.abs(np.fft.rfft(y0)) / len(y0)

        return pd.DataFrame({"frequency_hz": freqs, "amplitude": amp})
