"""Step 3, second round: age-based recipes, a ranking-based safety alarm, and Green Light inputs for any rule.

Candidates (MAP logistic regression; intercept = fob's own death rate, never borrowed; strength lam0):
  kin        - vote-weighted kin coefficients for all columns (Step 2)
  consensus  - median kin coefficient where >= 3 kin collected the field and >= 80% agree on direction
  own        - no borrowing
  kin_age    - vote-weighted kin coefficients for the age bands only; every other column shrinks to 0
  age_trend  - one smooth age term ((age - 50) / 20) only; slope prior = median kin slope. Whenever the
               slope is positive its ranking is exactly "rank by age"; unlike plain ranking it gives risks.
Logged per day, so the selection rule and the Green Light can be chosen afterwards in analyse_os2.py:
  auc_<c>          test AUC of each candidate fitted on records up to day d
  fresh_auc_<c>    AUC of each candidate on fob's own *fresh* records (each week predicted by a model fitted on
                   earlier weeks only), pooled over complete weeks so far; fresh_deaths = deaths among them
  stab_<a>__<b>    rank correlation of candidate a's risk scores today vs candidate b's `stability_lag` days ago,
                   on fob's records so far (lets the Green Light follow any switching rule)
Usage: PYTHONPATH=src python -m outbreak_synth.run_os_replay2 experiments/exp08_os_replay.toml"""
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from .library import OUT as LIB, TARGET
from .recipe import collected_fields, design, fit_map, kin_prior
from .run_kinship_replay import KNOWN_COL, day0_of, known_days
from .run_os_replay import consensus_prior
from .run_recipe_replay import weekly_votes

CANDS = ["kin", "consensus", "own", "kin_age", "age_trend"]


def age_x(df, med):
    return ((df.age.fillna(med).to_numpy() - 50.0) / 20.0)[:, None]


def run_one(fob, cfg, kin_list, tau, weeks_path):
    prior = cfg.get("vote_prior", "outbreak")
    lib = pd.read_parquet(LIB)
    weeks = pd.read_csv(weeks_path)
    d = lib[lib.outbreak == fob]
    t0 = day0_of(d, fob, cfg["day0_mode"], cfg["season_threshold"])
    d = d[d.DT_DIGITA >= t0].sort_values(["DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable")
    day = (d.DT_DIGITA - t0).dt.days.to_numpy()
    timing = cfg.get("outcome_timing", "entry")
    kday = np.nan_to_num(known_days(d, t0, timing), nan=np.inf)  # day each outcome became usable
    spec = cfg.get("override", {}).get(fob, {})
    lo, hi = spec.get("test_from_day", cfg["test_from_day"]), spec.get("test_to_day", cfg["test_to_day"])
    X, meta = design(d)
    Xa = age_x(d, 50.0)
    y = d[TARGET].to_numpy()
    test = (day >= lo) & (day <= hi)
    if test.sum() < cfg["min_test"] or y[test].sum() < cfg["min_test_deaths"]:
        return fob, None
    yt = y[test]
    lam0 = cfg["lam0"]
    b0, b = fit_map(X[~test], y[~test], lam=lam0)
    gold = roc_auc_score(yt, b0 + X[test] @ b)
    age_only = roc_auc_score(yt, d.age[test].fillna(d.age.median()))

    kin_coefs, kin_fields, kin_slope = {}, {}, []
    for k in kin_list:
        kd = lib[(lib.outbreak == k) & (lib.DT_DIGITA < t0)]
        if timing != "entry":
            kd = kd[kd[KNOWN_COL[timing]] < t0]
        if len(kd) > cfg["max_fit_rows"]:
            kd = kd.sample(cfg["max_fit_rows"], random_state=0)
        Xk, _ = design(kd)
        kin_coefs[k] = fit_map(Xk, kd[TARGET].to_numpy())[1]
        kin_fields[k] = collected_fields(kd)
        kin_slope.append(fit_map(age_x(kd, 50.0), kd[TARGET].to_numpy())[1][0])
    slope_prior = float(np.median(kin_slope))
    votes = weekly_votes(weeks, fob, kin_list, tau, prior)
    mu_c, _ = consensus_prior(kin_coefs, kin_fields, meta, cfg["min_agree_kin"], cfg["agree_share"])
    is_age = np.array([m[1] == "age" for m in meta])

    def spec_of(c, wk):
        """(design matrix, prior mean, prior strength) for candidate c using votes up to week wk."""
        if c == "age_trend":
            return Xa, np.array([slope_prior]), np.array([float(lam0)])
        if c in ("kin", "kin_age"):
            past, stranger = votes[wk] if wk in votes else ({k: 1 / len(kin_list) for k in kin_list}, 1 / (len(kin_list) + 1))
            mu, have = kin_prior(kin_coefs, kin_fields, past, meta)
            if c == "kin_age":
                mu, have = np.where(is_age, mu, 0.0), have & is_age
            return X, mu, np.where(have, lam0 * (1 - stranger), lam0)
        if c == "consensus":
            return X, mu_c, np.full(len(meta), float(lam0))
        return X, np.zeros(len(meta)), np.full(len(meta), float(lam0))

    def fit(c, mask, wk):
        M, mu, lam = spec_of(c, wk)
        if mask.sum() == 0:
            return M, 0.0, mu
        c0, cc = fit_map(M[mask], y[mask], mu=mu, lam=lam)
        return M, c0, cc

    # Fresh predictions: week u predicted by a model fitted on weeks < u.
    n_weeks = cfg["max_day"] // 7 + 1
    fresh = {c: np.full(len(y), np.nan) for c in CANDS}
    for u in range(n_weeks):
        now = np.floor(kday / 7) == u       # outcomes that became usable in week u
        if not now.any():
            continue
        for c in CANDS:
            M, c0, cc = fit(c, kday < 7 * u, u - 1)
            fresh[c][now] = c0 + M[now] @ cc

    rows, betas = [], {}
    for dd in range(0, cfg["max_day"] + 1, cfg["day_step"]):
        tr = day <= dd                       # entered by day dd (used for stability)
        trk = tr & (kday <= dd)              # ... with an outcome usable by day dd (used for every fit)
        row = {"day": dd, "n": int(tr.sum()), "n_known": int(trk.sum()), "deaths": int(y[trk].sum())}
        k_ = row["deaths"]
        if min(k_, row["n_known"] - k_) >= cfg["min_class"]:
            c0, c = fit_map(X[trk], y[trk])
            row["real_only"] = roc_auc_score(yt, c0 + X[test] @ c)
        scored = kday < 7 * (dd // 7)
        row["fresh_n"], row["fresh_deaths"] = int(scored.sum()), int(y[scored].sum())
        both = 0 < y[scored].sum() < scored.sum()
        betas[dd] = {}
        for c in CANDS:
            M, c0, cc = fit(c, trk, dd // 7 - 1)
            betas[dd][c] = (M, cc)
            row[f"auc_{c}"] = roc_auc_score(yt, c0 + M[test] @ cc)
            row[f"fresh_auc_{c}"] = roc_auc_score(y[scored], fresh[c][scored]) if both else np.nan
        prev = dd - cfg["stability_lag"]
        if prev in betas and tr.sum() >= 2:
            now_s = {c: betas[dd][c][0][tr] @ betas[dd][c][1] for c in CANDS}
            prev_s = {c: betas[prev][c][0][tr] @ betas[prev][c][1] for c in CANDS}
            for a in CANDS:
                for bb in CANDS:
                    sa, sb = now_s[a], prev_s[bb]
                    row[f"stab_{a}__{bb}"] = float(spearmanr(sa, sb).statistic) if np.std(sa) > 0 and np.std(sb) > 0 else 0.0
        rows.append(row)
    info = {"day0": str(t0.date()), "test_days": [lo, hi], "test_n": int(test.sum()), "test_deaths": int(yt.sum()),
            "gold_auc": gold, "age_only_auc": age_only, "kin": kin_list, "slope_prior": slope_prior,
            "kin_slopes": dict(zip(kin_list, map(float, kin_slope)))}
    return fob, {"info": info, "days": rows}


def main(cfg_path):
    cfg = tomllib.loads(Path(cfg_path).read_text())
    src = cfg["kinship_run"]
    meta5 = json.loads(Path("results", f"{src}.json").read_text())
    ana = json.loads(Path("results", f"{cfg.get('kinship_analysis', src)}_analysis.json").read_text())
    jobs = [(f, list(m["kin"]), float(ana["tau_chosen"][f])) for f, m in meta5.items() if not cfg.get("only") or f in cfg["only"]]
    res = Parallel(n_jobs=cfg["n_jobs"])(delayed(run_one)(f, cfg, kin, tau, f"results/{src}_weeks.csv") for f, kin, tau in jobs)
    out = {f: r for f, r in res if r is not None}
    Path("results", f"{cfg['name']}.json").write_text(json.dumps(
        {"config": cfg, "skipped": [f for f, r in res if r is None], "outbreaks": out}, indent=2))
    print("done:", len(out), "outbreaks; skipped:", [f for f, r in res if r is None])


if __name__ == "__main__":
    main(sys.argv[1])
