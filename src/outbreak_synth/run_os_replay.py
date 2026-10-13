"""Step 3: Fresh-Days Check + Green Light, replayed day by day on every outbreak with earlier kin.

Three candidate recipes for the Severity Model (all MAP logistic regression, intercept never borrowed,
borrowing strength lam0 from Step 2 / Exp. 6b):
  kin       - prior = Kinship-Vote-weighted kin coefficients, strength lam0 * (1 - Stranger share)  (Step 2)
  consensus - prior = median kin coefficient, only where >= min_agree_kin past outbreaks collected the field and
              >= agree_share of them agree on its direction; everything else shrinks to "no effect"
  own       - no borrowing (everything shrinks to "no effect" with strength lam0)
Fresh-Days Check: every week u, each candidate is fitted on records entered before week u and scored (log score)
on week u's records, which it has not seen. On day d OS uses the candidate with the best cumulative score over
the complete weeks so far (default before any week is scored: consensus).
Green Light inputs logged per day: deaths so far, and stability = rank correlation between OS's risk scores for
fob's patients today and `stability_lag` days ago. The rule itself is set in analyse_os.py.
Baselines: real_only (ridge on fob only, needs min_class deaths and survivors) and age_only (rank by age).
Usage: PYTHONPATH=src python -m outbreak_synth.run_os_replay experiments/exp07_os_replay.toml"""
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from .kinship import bernoulli_logpmf
from .library import OUT as LIB, TARGET
from .recipe import collected_fields, design, fit_map, kin_prior
from .run_kinship_replay import day0_of
from .run_recipe_replay import weekly_votes

CANDS = ["kin", "consensus", "own"]


def consensus_prior(kin_coefs, kin_fields, meta, min_kin, share):
    p = len(meta)
    mu, have = np.zeros(p), np.zeros(p, bool)
    for j, (_, field, borrowable) in enumerate(meta):
        if not borrowable:
            continue
        vals = np.array([kin_coefs[k][j] for k in kin_coefs if field in kin_fields[k]])
        if len(vals) < min_kin:
            continue
        med = np.median(vals)
        if med != 0 and (np.sign(vals) == np.sign(med)).mean() >= share:
            mu[j], have[j] = med, True
    return mu, have


def run_one(fob, cfg, kin_list, tau, weeks_path):
    lib = pd.read_parquet(LIB)
    weeks = pd.read_csv(weeks_path)
    d = lib[lib.outbreak == fob]
    t0 = day0_of(d, fob, cfg["day0_mode"], cfg["season_threshold"])
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
    lam0 = cfg["lam0"]
    b0, b = fit_map(X[~test], y[~test], lam=lam0)
    gold = roc_auc_score(yt, b0 + Xt @ b)
    gold_ridge1 = roc_auc_score(yt, (lambda c: c[0] + Xt @ c[1])(fit_map(X[~test], y[~test])))
    age_only = roc_auc_score(yt, d.age[test].fillna(d.age.median()))

    kin_coefs, kin_fields = {}, {}
    for k in kin_list:
        kd = lib[(lib.outbreak == k) & (lib.DT_DIGITA < t0)]
        if len(kd) > cfg["max_fit_rows"]:
            kd = kd.sample(cfg["max_fit_rows"], random_state=0)
        Xk, _ = design(kd)
        kin_coefs[k] = fit_map(Xk, kd[TARGET].to_numpy())[1]
        kin_fields[k] = collected_fields(kd)
    votes = weekly_votes(weeks, fob, kin_list, tau)
    mu_c, have_c = consensus_prior(kin_coefs, kin_fields, meta, cfg["min_agree_kin"], cfg["agree_share"])

    def prior(cand, wk):
        if cand == "kin":
            past, stranger = votes[wk] if wk in votes else ({k: 1 / len(kin_list) for k in kin_list}, 1 / (len(kin_list) + 1))
            mu, have = kin_prior(kin_coefs, kin_fields, past, meta)
            return mu, np.where(have, lam0 * (1 - stranger), lam0)
        if cand == "consensus":
            return mu_c, np.full(len(meta), float(lam0))
        return np.zeros(len(meta)), np.full(len(meta), float(lam0))

    def fit(cand, mask, wk):
        mu, lam = prior(cand, wk)
        if mask.sum() == 0:
            return 0.0, mu
        return fit_map(X[mask], y[mask], mu=mu, lam=lam)

    # Fresh-Days Check: cumulative log score of each candidate on weeks it has not seen.
    n_weeks = cfg["max_day"] // 7 + 1
    fresh = {c: [0.0] for c in CANDS}  # fresh[c][u] = score over weeks < u
    for u in range(n_weeks):
        now = day // 7 == u
        for c in CANDS:
            s = 0.0
            if now.any():
                c0, cc = fit(c, day < 7 * u, u - 1)
                s = bernoulli_logpmf(c0 + X[now] @ cc, y[now]).sum()
            fresh[c].append(fresh[c][-1] + s)

    rows, scores_by_day = [], {}
    for dd in range(0, cfg["max_day"] + 1, cfg["day_step"]):
        tr = day <= dd
        row = {"day": dd, "n": int(tr.sum()), "deaths": int(y[tr].sum())}
        k_ = row["deaths"]
        if min(k_, row["n"] - k_) >= cfg["min_class"]:
            c0, c = fit_map(X[tr], y[tr])
            row["real_only"] = roc_auc_score(yt, c0 + Xt @ c)
        u = dd // 7  # complete weeks so far: 0..u-1
        scored = (day < 7 * u).sum()
        cum = {c: fresh[c][u] for c in CANDS}
        chosen = max(cum, key=cum.get) if scored > 0 else "consensus"
        row.update({f"fresh_{c}": cum[c] for c in CANDS})
        row["chosen"] = chosen
        fits = {}
        for c in CANDS:
            fits[c] = fit(c, tr, dd // 7 - 1)
            row[f"auc_{c}"] = roc_auc_score(yt, fits[c][0] + Xt @ fits[c][1])
        row["auc_os"] = row[f"auc_{chosen}"]
        # Stability: OS risk scores for fob's patients so far, today vs stability_lag days ago.
        sc = X[tr] @ fits[chosen][1]
        scores_by_day[dd] = (tr, chosen)
        prev = dd - cfg["stability_lag"]
        if prev in scores_by_day and tr.sum() >= 2:
            ptr, pch = scores_by_day[prev]
            pc0, pcc = fit(pch, ptr, prev // 7 - 1)
            ps = X[tr] @ pcc
            row["stability"] = float(spearmanr(sc, ps).statistic) if np.std(sc) > 0 and np.std(ps) > 0 else 0.0
        rows.append(row)
    info = {"day0": str(t0.date()), "test_days": [lo, hi], "test_n": int(test.sum()), "test_deaths": int(yt.sum()),
            "gold_auc": gold, "gold_auc_ridge1": gold_ridge1, "age_only_auc": age_only, "kin": kin_list,
            "consensus_columns": [meta[j][0] for j in range(len(meta)) if have_c[j]]}
    return fob, {"info": info, "days": rows}


def main(cfg_path):
    cfg = tomllib.loads(Path(cfg_path).read_text())
    src = cfg["kinship_run"]
    meta5 = json.loads(Path("results", f"{src}.json").read_text())
    ana = json.loads(Path("results", f"{src}_analysis.json").read_text())
    jobs = [(f, list(m["kin"]), float(ana["tau_chosen"][f])) for f, m in meta5.items()]
    res = Parallel(n_jobs=cfg["n_jobs"])(delayed(run_one)(f, cfg, kin, tau, f"results/{src}_weeks.csv") for f, kin, tau in jobs)
    out = {f: r for f, r in res if r is not None}
    Path("results", f"{cfg['name']}.json").write_text(json.dumps(
        {"config": cfg, "skipped": [f for f, r in res if r is None], "outbreaks": out}, indent=2))
    print("done:", len(out), "outbreaks; skipped:", [f for f, r in res if r is None])


if __name__ == "__main__":
    main(sys.argv[1])
