"""Copy check for the released synthetic data: how often is a synthetic patient an exact copy of a real patient the
generator saw, compared with how often a genuinely new real patient matches one of them by chance?

Record = (age in whole years, sex, race, state, the 16 yes/no fields as yes / not yes, death).
  train     fob's records with a known outcome on the Green Light day (what OS saw; the other generators saw
            these, or a 10,000-row sample of them for COVID)
  holdout   later real patients from the test window (never seen): the chance-match reference
Per generator: share of synthetic rows that exactly match some train record, divided by the holdout's match share
(per outbreak: the ratio; summary: the difference, 0 = no more copying than chance; bootstrap resampling is the upper
reference, as it copies by design).
Usage: PYTHONPATH=src python -m outbreak_synth.analyse_privacy dev
       OUTBREAK_LIB=data/processed/library_frozen.parquet PYTHONPATH=src python -m outbreak_synth.analyse_privacy frozen"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .analyse_ci import boot_mean
from .library import OUT as LIB, TARGET, YESNO
from .run_kinship_replay import KNOWN_COL, day0_of

RUNS = {"dev": ("exp08d_os_replay_known", "exp10d_synth_known", "exp16_synth_baselines"),
        "frozen": ("exp18b_os_replay_frozen", "exp18d_synth_frozen", "exp18e_synth_baselines_frozen")}
GENS = ["bootstrap", "bayesian_network", "arf", "ctgan", "tvae"]
SYN = Path("data/synthetic")


def keys(df):
    k = pd.DataFrame({"age": np.floor(df.age.astype(float).fillna(-1)).astype(int).astype(str),
                      **{c: df[c].astype(str) for c in ("CS_SEXO", "CS_RACA", "SG_UF_NOT")},
                      **{c: np.where(df[c].astype(str) == "yes", "1", "0") for c in YESNO},
                      "death": df[TARGET].astype(int).astype(str)})
    out = k.iloc[:, 0]
    for c in k.columns[1:]:  # vectorised join (row-wise agg is far too slow on 100k+ rows)
        out = out + "|" + k[c]
    return out


def match_share(rows, ref):
    return float(rows.isin(set(ref)).mean())


def main(which):
    os_run, syn_run, base_run = RUNS[which]
    lib = pd.read_parquet(LIB)
    info = json.loads(Path("results", f"{os_run}.json").read_text())
    cfg = info["config"]
    sy = json.loads(Path("results", f"{syn_run}.json").read_text())["outbreaks"]
    out = []
    for fob, r in sorted(sy.items()):
        gday = r["green_day"]
        d = lib[lib.outbreak == fob]
        t0 = day0_of(d, fob, cfg["day0_mode"], cfg["season_threshold"])
        d = d[d.DT_DIGITA >= t0]
        day = (d.DT_DIGITA - t0).dt.days
        known = (d[KNOWN_COL["known"]] - t0).dt.days
        train = d[(day <= gday) & (known <= gday)]
        lo, hi = info["outbreaks"][fob]["info"]["test_days"]
        hold = d[(day >= lo) & (day <= hi)]
        kt = keys(train)
        row = {"outbreak": fob, "green_day": gday, "train_n": len(train), "holdout_match": match_share(keys(hold), kt)}
        files = {"os": SYN / "os" / f"SYNTHETIC_os_chain_{fob}_day{gday}.parquet",
                 **{g: SYN / "baselines" / f"SYNTHETIC_{g}_{fob}_day{gday}.parquet" for g in GENS}}
        for g, p in files.items():
            if p.exists():
                row[f"{g}_match"] = match_share(keys(pd.read_parquet(p)), kt)
                row[f"{g}_ratio"] = row[f"{g}_match"] / max(row["holdout_match"], 1e-9)
        out.append(row)
        print(f"{fob} day {gday} (train {len(train):,}): holdout {row['holdout_match']:.3f} | " +
              " ".join(f"{g} {row.get(f'{g}_match', float('nan')):.3f}" for g in files), flush=True)
    t = pd.DataFrame(out)
    summ = {"holdout_match": boot_mean(t.holdout_match),
            **{f"{g}_match": boot_mean(t[f"{g}_match"]) for g in ["os"] + GENS if f"{g}_match" in t},
            # Difference from the chance level (0 = no more copying than chance). A per-outbreak ratio is unstable when an
            # outbreak's holdout match share is 0, so the summary uses differences and the ratio of mean shares.
            **{f"{g}_minus_holdout": boot_mean(t[f"{g}_match"] - t.holdout_match) for g in ["os"] + GENS if f"{g}_match" in t},
            **{f"{g}_ratio_of_means": {"value": float(t[f"{g}_match"].mean() / t.holdout_match.mean())}
               for g in ["os"] + GENS if f"{g}_match" in t}}
    Path("results", f"privacy_{which}.json").write_text(json.dumps({"which": which, "per_outbreak": out, "summary": summ}, indent=2))
    for k, v in summ.items():
        print(k, {a: (round(b, 3) if isinstance(b, float) else [round(c, 3) for c in b] if isinstance(b, list) else b) for a, b in v.items()})


if __name__ == "__main__":
    main(sys.argv[1])
