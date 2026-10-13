"""Step 2: Severity Model + Handover Rule, replayed day by day on every outbreak with earlier kin.

Arms, on each replay day d (records entered up to day d):
  real_only - ridge logistic regression on fob's records only (needs >= min_class deaths and survivors)
  os_lamX   - Severity Model borrowing from kin with borrowing strength lam0 = X (works from day 0)
Kinship Vote shares come from the Step 1 replay (results/exp05_kinship_replay_weeks.csv, tau from its
analysis): on day d OS uses the votes after the last complete week, i.e. only records entered before day d.
Test set per outbreak: records entered on days test_from..test_to (a fixed later window).
Gold standard: the same model class trained on every fob record outside the test window.
Usage: PYTHONPATH=src python -m outbreak_synth.run_recipe_replay experiments/exp06_recipe_replay.toml"""
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import roc_auc_score

from .kinship import start_shares, votes_from_scores
from .library import OUT as LIB, TARGET
from .recipe import collected_fields, design, fit_map, kin_prior
from .run_kinship_replay import day0_of


def weekly_votes(weeks, fob, kin, tau, prior="outbreak"):
    g = weeks[weeks.fob == fob].set_index("week")
    lp_all, lp_past = start_shares(kin, prior), start_shares(kin, prior, with_stranger=False)
    out = {}
    for w, r in g.iterrows():
        v = votes_from_scores({n: r[f"score_total::{n}"] for n in kin + ["STRANGER"]}, tau, lp_all)
        past = votes_from_scores({k: r[f"score_total::{k}"] for k in kin}, tau, lp_past)
        out[w] = (past, v["STRANGER"])
    return out


def run_one(fob, lib_path, cfg, kin_list, tau, weeks_path):
    lib = pd.read_parquet(lib_path)
    weeks = pd.read_csv(weeks_path)
    d = lib[lib.outbreak == fob]
    t0 = day0_of(d, fob)
    d = d[d.DT_DIGITA >= t0].sort_values(["DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable")
    day = (d.DT_DIGITA - t0).dt.days.to_numpy()
    spec = cfg.get("override", {}).get(fob, {})
    lo, hi = spec.get("test_from_day", cfg["test_from_day"]), spec.get("test_to_day", cfg["test_to_day"])
    X, meta = design(d)
    y = d[TARGET].to_numpy()
    test = (day >= lo) & (day <= hi)
    if test.sum() < cfg["min_test"] or y[test].sum() < cfg["min_test_deaths"]:
        return fob, None
    Xt, yt = X[test], y[test]
    rest = ~test
    b0, b = fit_map(X[rest], y[rest])
    gold = roc_auc_score(yt, b0 + Xt @ b)

    # Kin coefficients, fitted once on each kin's records entered before fob's day 0.
    kin_coefs, kin_fields = {}, {}
    for k in kin_list:
        kd = lib[(lib.outbreak == k) & (lib.DT_DIGITA < t0)]
        if len(kd) > cfg["max_fit_rows"]:
            kd = kd.sample(cfg["max_fit_rows"], random_state=0)
        Xk, _ = design(kd)
        kin_coefs[k] = fit_map(Xk, kd[TARGET].to_numpy())[1]
        kin_fields[k] = collected_fields(kd)
    votes = weekly_votes(weeks, fob, kin_list, tau)

    rows = []
    for dd in range(0, cfg["max_day"] + 1, cfg["day_step"]):
        tr = day <= dd
        Xtr, ytr = X[tr], y[tr]
        row = {"day": dd, "n": int(tr.sum()), "deaths": int(ytr.sum())}
        k_ = int(ytr.sum())
        if min(k_, len(ytr) - k_) >= cfg["min_class"]:
            c0, c = fit_map(Xtr, ytr)
            row["real_only"] = roc_auc_score(yt, c0 + Xt @ c)
        wk = dd // 7 - 1  # last complete week before day dd
        if wk in votes:
            past, stranger = votes[wk]
        else:
            past, stranger = {k: 1 / len(kin_list) for k in kin_list}, 1 / (len(kin_list) + 1)
        mu, have = kin_prior(kin_coefs, kin_fields, past, meta)
        row["stranger"] = stranger
        for lam0 in cfg["lam0"]:
            # Columns with nothing to borrow (state, fields the kin's form lacked) shrink towards 0.
            # "lam_free": "lam0" gives them the same strength as borrowed columns (Exp. 6b fix);
            # a number keeps it fixed (Exp. 6 used 1.0, which let 2-3 early deaths swing them).
            free = lam0 if cfg.get("lam_free", 1.0) == "lam0" else float(cfg.get("lam_free", 1.0))
            lam = np.where(have, lam0 * (1 - stranger), free)
            if len(ytr) == 0:
                score = Xt @ mu
            else:
                c0, c = fit_map(Xtr, ytr, mu=mu, lam=lam)
                score = c0 + Xt @ c
            row[f"os_lam{lam0}"] = roc_auc_score(yt, score)
        rows.append(row)
    info = {"day0": str(t0.date()), "test_days": [lo, hi], "test_n": int(test.sum()), "test_deaths": int(yt.sum()),
            "gold_auc": gold, "kin": kin_list}
    return fob, {"info": info, "days": rows}


def main(cfg_path):
    cfg = tomllib.loads(Path(cfg_path).read_text())
    meta = json.loads(Path("results/exp05_kinship_replay.json").read_text())
    ana = json.loads(Path("results/exp05_kinship_replay_analysis.json").read_text())
    jobs = [(f, list(m["kin"]), float(ana["tau_chosen"][f])) for f, m in meta.items()]
    res = Parallel(n_jobs=cfg["n_jobs"], verbose=0)(
        delayed(run_one)(f, str(LIB), cfg, kin, tau, "results/exp05_kinship_replay_weeks.csv") for f, kin, tau in jobs)
    out = {f: r for f, r in res if r is not None}
    skipped = [f for f, r in res if r is None]
    Path("results", f"{cfg['name']}.json").write_text(json.dumps({"config": cfg, "skipped": skipped, "outbreaks": out}, indent=2))
    print("done:", len(out), "outbreaks; skipped (test window too small):", skipped)


if __name__ == "__main__":
    main(sys.argv[1])
