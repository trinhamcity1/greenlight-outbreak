"""Vote-only test on small line lists (Exp. 13 / 13b): Stranger share and group shares week by week.
Vote sharpness tau = 0.01, fixed from Brazil (chosen for 22 of 23 outbreaks in Exp. 5b).
Usage: PYTHONPATH=src python -m outbreak_synth.analyse_vote_small exp13_vote_small exp13b_vote_small_present"""
import json
import sys
from pathlib import Path

import pandas as pd

from .kinship import start_shares, votes_from_scores
from .library import family

TAU = 0.01
PRIOR = "outbreak"  # "--prior group" for the equal-per-group start (adopted 2026-10-07)


def table(name):
    meta = json.loads(Path("results", f"{name}.json").read_text())
    weeks = pd.read_csv(Path("results", f"{name}_weeks.csv"))
    rows = []
    for fob, g in weeks.groupby("fob"):
        kin = list(meta[fob]["kin"])
        for _, r in g.iterrows():
            v = votes_from_scores({n: r[f"score_total::{n}"] for n in kin + ["STRANGER"]}, TAU, start_shares(kin, PRIOR))
            past = votes_from_scores({k: r[f"score_total::{k}"] for k in kin}, TAU, start_shares(kin, PRIOR, with_stranger=False))
            groups = {}
            for k, p in past.items():
                groups[family(k)] = groups.get(family(k), 0) + p
            top = max(past, key=past.get)
            rows.append({"fob": fob, "week": int(r.week), "patients": int(r.n_so_far), "deaths": int(r.deaths_so_far),
                         "stranger": round(v["STRANGER"], 3),
                         "groups": ", ".join(f"{k} {p:.0%}" for k, p in sorted(groups.items(), key=lambda kv: -kv[1]) if p >= 0.01),
                         "top_kin": f"{top} {past[top]:.0%}"})
    return pd.DataFrame(rows), meta


def main(names):
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 80)
    out = {}
    for name in names:
        t, meta = table(name)
        print(f"\n===== {name}")
        for fob, g in t.groupby("fob"):
            m = meta[fob]
            print(f"-- {fob}: {m['n_total']} patients, {len(m['kin'])} possible relatives; hindsight best = {m['hindsight_best_kin']}, "
                  f"novelty gap = {m['novelty_gap']:.3f}")
            print(g.drop(columns="fob").to_string(index=False))
        t.to_csv(Path("results", f"{name}_votes{'_groupprior' if PRIOR == 'group' else ''}.csv"), index=False)
        out[name] = {f: {"hindsight_best": meta[f]["hindsight_best_kin"], "novelty_gap": meta[f]["novelty_gap"],
                         "final_week": t[t.fob == f].iloc[-1].to_dict()} for f in meta}
    Path("results", f"exp13_vote_small_summary{'_groupprior' if PRIOR == 'group' else ''}.json").write_text(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--prior" in args:
        i = args.index("--prior")
        PRIOR = args[i + 1]
        args = args[:i] + args[i + 2:]
    main(args)
