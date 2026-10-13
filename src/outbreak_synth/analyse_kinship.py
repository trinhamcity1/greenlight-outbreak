"""Score the Kinship Vote replay: right kin, honest confidence, Stranger Flag.
Usage: PYTHONPATH=src python -m outbreak_synth.analyse_kinship exp05_kinship_replay"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .kinship import start_shares, votes_from_scores

TAUS = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0]
CHECK_WEEKS = [1, 2, 4, 8, 13, 25]
from .library import family


PRIOR = "outbreak"  # set by main(); see kinship.start_shares


def vote_table(weeks, meta, tau, part="total"):
    rows = []
    for fob, g in weeks.groupby("fob"):
        kin = list(meta[fob]["kin"])
        best = meta[fob]["hindsight_best_kin"]
        for _, r in g.iterrows():
            v = votes_from_scores({n: r[f"score_{part}::{n}"] for n in kin + ["STRANGER"]}, tau, start_shares(kin, PRIOR))
            # Shares among past outbreaks only, computed directly so they never underflow.
            past = votes_from_scores({k: r[f"score_{part}::{k}"] for k in kin}, tau, start_shares(kin, PRIOR, with_stranger=False))
            top = max(past, key=past.get)
            fam_ok = any(family(k) == family(fob) for k in kin)
            groups = {}
            for k, p in past.items():
                groups[family(k)] = groups.get(family(k), 0.0) + p
            top_group = max(groups, key=groups.get)
            rows.append({"fob": fob, "week": r.week, "n_so_far": r.n_so_far, "top_kin": top, "top_share": past[top],
                         "best_share": past[best], "top_is_best": top == best,
                         "top_same_family": (family(top) == family(fob)) if fam_ok else np.nan,
                         "group_testable": fam_ok, "top_group": top_group, "top_group_share": groups[top_group],
                         "true_group_share": groups.get(family(fob), 0.0) if fam_ok else np.nan,
                         "top_group_right": (top_group == family(fob)) if fam_ok else np.nan,
                         "stranger": v["STRANGER"], "novelty_gap": meta[fob]["novelty_gap"]})
    return pd.DataFrame(rows)


def calibration(t, bins=(0, .2, .4, .6, .8, .95, 1.0001)):
    t = t.assign(bin=pd.cut(t.top_share, bins, right=False))
    return t.groupby("bin", observed=True).agg(cases=("top_is_best", "size"), said=("top_share", "mean"),
                                               right=("top_is_best", "mean")).round(3)


def main(name, prior="outbreak", out=None, fixed_tau=None):
    """out: name for the outputs (default: name). With prior="group", writes <out>_analysis.json / _votes.csv.
    fixed_tau: use this vote sharpness for every fob instead of choosing it (frozen test: no choice on test data)."""
    global PRIOR
    PRIOR = prior
    meta = json.loads(Path("results", f"{name}.json").read_text())
    weeks = pd.read_csv(Path("results", f"{name}_weeks.csv"))
    src, name = name, (out or name)
    # tau chosen by leave-one-outbreak-out: for each fob, the tau minimising -log(share of the hindsight
    # best kin) on all OTHER outbreaks.
    # Truth = fob's own disease group (flu incl. H1N1, other respiratory virus, COVID). Outbreaks whose
    # group has no earlier member (flu_2013, othervirus_2013, covid_2020) cannot be scored this way;
    # they are the Stranger tests.
    loss = {tau: vote_table(weeks, meta, tau).assign(nll=lambda d: -np.log(d.true_group_share.clip(1e-12))) for tau in TAUS}
    per_fob = pd.DataFrame({tau: d[d.group_testable].groupby("fob").nll.mean() for tau, d in loss.items()})
    all_fobs = sorted(weeks.fob.unique())
    chosen = {fob: fixed_tau if fixed_tau is not None else (per_fob.drop(index=fob) if fob in per_fob.index else per_fob).mean().idxmin()
              for fob in all_fobs}
    t = pd.concat([loss[chosen[f]][loss[chosen[f]].fob == f] for f in all_fobs]).assign(
        tau=lambda d: d.fob.map(chosen))
    report = {"tau_sweep_mean_nll": per_fob.mean().round(3).to_dict(), "tau_chosen": chosen}

    at = t[t.week.isin(CHECK_WEEKS)]
    report["right_kin_by_week"] = at.groupby("week").agg(
        outbreaks=("fob", "size"), group_right=("top_group_right", "mean"), true_group_share=("true_group_share", "mean"),
        exact_best_kin=("top_is_best", "mean")).round(3).reset_index().to_dict("records")
    tg = t[t.group_testable].assign(top_is_best=lambda d: d.top_group_right.astype(bool), top_share=lambda d: d.top_group_share)
    report["calibration_group"] = calibration(tg).reset_index().astype(str).to_dict("records")
    s = t.groupby("fob").apply(lambda g: pd.Series({
        "novelty_gap": g.novelty_gap.iloc[0],
        "stranger_wk1": g.loc[g.week == g.week.min(), "stranger"].iloc[0],
        "stranger_wk4": g.loc[g.week <= 4, "stranger"].iloc[-1],
        "first_week_stranger_over_half": g.loc[g.stranger > 0.5, "week"].min(),
        "n_at_that_week": g.loc[g.stranger > 0.5, "n_so_far"].min(),
        "top_kin_wk4": g.loc[g.week <= 4, "top_kin"].iloc[-1],
        "top_group_wk4": g.loc[g.week <= 4, "top_group"].iloc[-1],
        "hindsight_best": meta[g.name]["hindsight_best_kin"]}))
    report["stranger"] = s.reset_index().to_dict("records")
    report["stranger_rank_corr"] = float(s.novelty_gap.rank().corr(s.stranger_wk4.rank()))
    # Patients needed before the Stranger wins (never = infinite): fewer patients = more novel.
    need = s.n_at_that_week.astype(float).fillna(np.inf)
    report["stranger_patients_rank_corr"] = float(s.novelty_gap.rank().corr((-need).rank()))
    # Which part drives the vote? Same scoring with profile-only and severity-only scores.
    for part in ("profile", "severity"):
        tp = pd.concat([vote_table(weeks[weeks.fob == f], meta, chosen[f], part) for f in all_fobs])
        report[f"group_right_wk4_{part}_only"] = round(float(tp[tp.week == 4].top_group_right.mean()), 3)
    Path("results", f"{name}_analysis.json").write_text(json.dumps(report, indent=2, default=str))
    t.to_csv(Path("results", f"{name}_votes.csv"), index=False)
    pd.set_option("display.width", 200)
    print("tau sweep (mean -log share of hindsight-best kin):", report["tau_sweep_mean_nll"])
    print("tau chosen (leave-one-outbreak-out):", sorted(set(chosen.values())))
    print(pd.DataFrame(report["right_kin_by_week"]).to_string(index=False))
    print("group-level calibration (said = top group share, right = top group is fob's group):")
    print(calibration(tg).to_string())
    print(s.sort_values("novelty_gap").round(3).to_string())
    print("rank corr(novelty gap, Stranger share wk4) =", round(report["stranger_rank_corr"], 3))
    print("rank corr(novelty gap, fewer patients before Stranger wins) =", round(report["stranger_patients_rank_corr"], 3))
    print({k: v for k, v in report.items() if k.startswith("group_right_wk4")})


if __name__ == "__main__":
    args = sys.argv[1:]
    prior = args[args.index("--prior") + 1] if "--prior" in args else "outbreak"
    out = args[args.index("--out") + 1] if "--out" in args else None
    tau = float(args[args.index("--tau") + 1]) if "--tau" in args else None
    main(args[0], prior, out, tau)
