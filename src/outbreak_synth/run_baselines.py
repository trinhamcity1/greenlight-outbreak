"""Baselines for steps 2-3 (who dies), scored on exactly the Exp. 8d replay: same fob, day 0, test window, outcome
timing (an outcome is used only once known) and 2-day grid. Every method is a logistic regression on the same
design (recipe.design); the intercept (fob's own death rate) is fitted on fob's data and never borrowed.

  pooled       past only: one model on the pooled earlier outbreaks (equal rows per outbreak), no fob data
  stacked      pooled earlier outbreaks + fob's records so far in one fit, with a fob indicator column
  finetune     MAP towards the pooled model's coefficients with fixed strength lam0 (L2 fine-tuning)
  kin_equal    OS's Handover Rule with every past outbreak weighted equally and the Stranger fixed at 1/(K+1)
               (= OS without the Kinship Vote)
  map          meta-analytic prior: per coefficient, mean over past outbreaks and variance = between-outbreak
               variance + mean squared standard error (needs >= 2 outbreaks that collected the field)
  rmap         robust meta-analytic prior: mixture 0.8 x map + 0.2 x vague (mean 0, strength 1); component
               weights updated by Laplace marginal likelihood on fob's data (Schmidli et al. 2014)
  eb           commensurate-style empirical Bayes: prior mean = equal-weight past mean; borrowing strength chosen
               from a grid by Laplace marginal likelihood on fob's data
  bma          source averaging (a simplification of multi-source exchangeability models): one component per past
               outbreak (its coefficients, strength lam0) plus a no-borrowing component, equal prior weights,
               posterior weights by Laplace marginal likelihood on fob's data; risks are weight-averaged
  meta_init    MetaPred-style: Reptile meta-learning of a starting point over the past outbreaks, then MAP towards
               it with strength lam0 (the implicit-gradient form of fine-tuning from a meta-learned start)
Columns with no prior information shrink to 0 with strength lam0, as in OS.
Also logged per fob for the Riley readiness rule: P (predictor parameters) and the anticipated Nagelkerke R^2 of
the pooled past model on its own data.
Usage: PYTHONPATH=src python -m outbreak_synth.run_baselines experiments/exp15_baselines.toml"""
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.special import expit
from sklearn.metrics import roc_auc_score

from .library import OUT as LIB, TARGET
from .recipe import collected_fields, design, fit_map, kin_prior
from .run_kinship_replay import KNOWN_COL, day0_of, known_days

METHODS = ["pooled", "stacked", "finetune", "kin_equal", "map", "rmap", "eb", "bma", "meta_init"]
EB_GRID = [0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0]
ISD = 10.0  # intercept prior sd, as in fit_map


def loglik(X, y, b0, b):
    z = b0 + X @ b
    return float(y @ z - np.logaddexp(0, z).sum())


def hessian(X, b0, b, lam):
    """Posterior precision of (intercept, beta) at the MAP."""
    p = expit(b0 + X @ b)
    w = p * (1 - p)
    Xt = np.column_stack([np.ones(len(X)), X])
    return (Xt * w[:, None]).T @ Xt + np.diag(np.concatenate([[1 / ISD ** 2], lam]))


def evidence(X, y, mu, lam):
    """Laplace approximation to log p(y | prior N(mu, 1/lam)); returns (log evidence, intercept, beta)."""
    lam = np.broadcast_to(np.asarray(lam, float), (X.shape[1],))
    b0, b = fit_map(X, y, mu=mu, lam=lam, intercept_sd=ISD)
    if len(y) == 0:
        return 0.0, b0, b
    pen = 0.5 * (lam * (b - mu) ** 2).sum() + 0.5 * b0 ** 2 / ISD ** 2
    logdet_prior = np.log(lam).sum() - 2 * np.log(ISD)
    _, logdet_h = np.linalg.slogdet(hessian(X, b0, b, lam))
    return loglik(X, y, b0, b) - pen + 0.5 * (logdet_prior - logdet_h), b0, b


def mixture(X, y, comps, prior_w):
    """Posterior-weighted linear predictor coefficients over prior components [(mu, lam)]."""
    ev, fits = [], []
    for mu, lam in comps:
        e, b0, b = evidence(X, y, mu, lam)
        ev.append(e); fits.append((b0, b))
    lw = np.log(prior_w) + np.array(ev)
    w = np.exp(lw - lw.max()); w /= w.sum()
    b0 = sum(wi * f[0] for wi, f in zip(w, fits))
    b = sum(wi * f[1] for wi, f in zip(w, fits))
    return b0, b, w


def reptile(tasks, p, seed, outer=300, inner=10, lr=0.5, eps0=0.5, batch=1024):
    """Reptile (Nichol et al. 2018) for logistic regression: learns a starting point (intercept + beta)."""
    rng = np.random.default_rng(seed)
    th = np.zeros(p + 1)
    for it in range(outer):
        Xk, yk = tasks[rng.integers(len(tasks))]
        ph = th.copy()
        for _ in range(inner):
            i = rng.integers(0, len(yk), min(batch, len(yk)))
            r = expit(ph[0] + Xk[i] @ ph[1:]) - yk[i]
            ph -= lr * np.concatenate([[r.mean()], Xk[i].T @ r / len(i)])
        th += eps0 * (1 - it / outer) * (ph - th)
    return th


def nagelkerke(X, y, b0, b):
    n, phi = len(y), y.mean()
    ll0 = n * (phi * np.log(phi) + (1 - phi) * np.log(1 - phi))
    r2cs = 1 - np.exp(2 * (ll0 - loglik(X, y, b0, b)) / n)
    return float(r2cs / (1 - np.exp(2 * ll0 / n)))


def run_one(fob, cfg, kin_list):
    part = Path("results", f"{cfg['name']}_parts", f"{fob}.json")  # finished outbreaks are kept, so a rerun resumes
    if part.exists():
        return fob, json.loads(part.read_text())
    res = _run_one(fob, cfg, kin_list)
    part.parent.mkdir(exist_ok=True)
    part.write_text(json.dumps(res))
    return fob, res


def _run_one(fob, cfg, kin_list):
    lib = pd.read_parquet(LIB)
    timing = cfg["outcome_timing"]
    d = lib[lib.outbreak == fob]
    t0 = day0_of(d, fob, cfg["day0_mode"], cfg["season_threshold"])
    d = d[d.DT_DIGITA >= t0].sort_values(["DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable")
    day = (d.DT_DIGITA - t0).dt.days.to_numpy()
    kday = np.nan_to_num(known_days(d, t0, timing), nan=np.inf)
    spec = cfg.get("override", {}).get(fob, {})
    lo, hi = spec.get("test_from_day", cfg["test_from_day"]), spec.get("test_to_day", cfg["test_to_day"])
    X, meta = design(d)
    y = d[TARGET].to_numpy()
    test = (day >= lo) & (day <= hi)
    if test.sum() < cfg["min_test"] or y[test].sum() < cfg["min_test_deaths"]:
        return None
    yt, lam0, p = y[test], cfg["lam0"], X.shape[1]
    borrow = np.array([m[2] for m in meta])

    # Past outbreaks, time-respecting (records entered, and outcomes known, before fob's day 0).
    per_kin = max(1, cfg["max_fit_rows"] // max(1, len(kin_list)))
    kin_coefs, kin_se2, kin_fields, tasks, pool = {}, {}, {}, [], []
    for k in kin_list:
        kd = lib[(lib.outbreak == k) & (lib.DT_DIGITA < t0)]
        if timing != "entry":
            kd = kd[kd[KNOWN_COL[timing]] < t0]
        if len(kd) > cfg["max_fit_rows"]:
            kd = kd.sample(cfg["max_fit_rows"], random_state=0)
        Xk, _ = design(kd)
        yk = kd[TARGET].to_numpy()
        c0, ck = fit_map(Xk, yk)
        kin_coefs[k], kin_fields[k] = ck, collected_fields(kd)
        kin_se2[k] = np.diag(np.linalg.inv(hessian(Xk, c0, ck, np.ones(p))))[1:]
        tasks.append((Xk, yk))
        i = np.random.default_rng(0).permutation(len(yk))[:per_kin]
        pool.append((Xk[i], yk[i]))
    Xp, yp = np.vstack([a for a, _ in pool]), np.concatenate([b for _, b in pool])
    p0, pb = fit_map(Xp, yp)
    r2n = nagelkerke(Xp, yp, p0, pb)

    # Prior means and strengths, fixed for the whole replay.
    eq = {k: 1 / len(kin_list) for k in kin_list}
    mu_eq, have_eq = kin_prior(kin_coefs, kin_fields, eq, meta)
    lam_eq = np.where(have_eq, lam0 * (1 - 1 / (len(kin_list) + 1)), lam0)
    mu_ma, lam_ma = np.zeros(p), np.full(p, float(lam0))
    for j, (_, field, b_) in enumerate(meta):
        ks = [k for k in kin_list if b_ and field in kin_fields[k]]
        if len(ks) >= 2:
            v = np.array([kin_coefs[k][j] for k in ks])
            mu_ma[j] = v.mean()
            lam_ma[j] = 1 / (v.var(ddof=1) + np.mean([kin_se2[k][j] for k in ks]))
    lam_ma = np.minimum(lam_ma, cfg["max_lam"])
    comps_rmap = [(mu_ma, lam_ma), (np.zeros(p), np.ones(p))]
    comps_bma = []
    for k in kin_list:
        hk = borrow & np.array([m[1] in kin_fields[k] for m in meta])
        comps_bma.append((np.where(hk, kin_coefs[k], 0.0), np.full(p, float(lam0))))
    comps_bma.append((np.zeros(p), np.full(p, float(lam0))))
    th = reptile(tasks, p, cfg["seed"])
    mu_mi = np.where(borrow, th[1:], 0.0)
    mu_ft = np.where(borrow, pb, 0.0)

    rows = []
    for dd in range(0, cfg["max_day"] + 1, cfg["day_step"]):
        trk = (day <= dd) & (kday <= dd)
        Xf, yf = X[trk], y[trk]
        row = {"day": dd, "n_known": int(trk.sum()), "deaths": int(yf.sum())}
        coefs = {"pooled": pb}
        Xs = np.column_stack([np.vstack([Xp, Xf]), np.r_[np.zeros(len(yp)), np.ones(len(yf))]])
        coefs["stacked"] = fit_map(Xs, np.r_[yp, yf])[1][:p]
        coefs["finetune"] = fit_map(Xf, yf, mu=mu_ft, lam=lam0)[1]
        coefs["kin_equal"] = fit_map(Xf, yf, mu=mu_eq, lam=lam_eq)[1]
        coefs["map"] = fit_map(Xf, yf, mu=mu_ma, lam=lam_ma)[1]
        _, coefs["rmap"], w = mixture(Xf, yf, comps_rmap, np.array([0.8, 0.2]))
        row["rmap_w_informative"] = float(w[0])
        ev = [evidence(Xf, yf, mu_eq, np.where(have_eq, g, lam0)) for g in EB_GRID]
        best = int(np.argmax([e[0] for e in ev]))
        coefs["eb"], row["eb_lam"] = ev[best][2], EB_GRID[best]
        _, coefs["bma"], w = mixture(Xf, yf, comps_bma, np.full(len(comps_bma), 1 / len(comps_bma)))
        row["bma_w_own"] = float(w[-1])
        row["bma_top"] = (kin_list + ["own"])[int(np.argmax(w))]
        coefs["meta_init"] = fit_map(Xf, yf, mu=mu_mi, lam=lam0)[1]
        for m in METHODS:
            row[f"auc_{m}"] = roc_auc_score(yt, X[test] @ coefs[m])
        rows.append(row)
    info = {"day0": str(t0.date()), "test_days": [lo, hi], "kin": kin_list, "P": p, "pooled_r2_nagelkerke": r2n,
            "pooled_n": int(len(yp)), "pooled_death_rate": float(yp.mean())}
    print(fob, "done", flush=True)
    return {"info": info, "days": rows}


def main(cfg_path):
    cfg = tomllib.loads(Path(cfg_path).read_text())
    meta5 = json.loads(Path("results", f"{cfg['kinship_run']}.json").read_text())
    jobs = [(f, list(m["kin"])) for f, m in meta5.items() if not cfg.get("only") or f in cfg["only"]]
    jobs.sort(key=lambda j: (not j[0].startswith("covid"), j[0]))  # biggest outbreaks first
    from outbreak_synth.run_baselines import run_one as job  # by reference: workers cannot unpickle __main__'s ufuncs
    res = Parallel(n_jobs=cfg["n_jobs"])(delayed(job)(f, cfg, kin) for f, kin in jobs)
    out = {f: r for f, r in res if r is not None}
    Path("results", f"{cfg['name']}.json").write_text(json.dumps(
        {"config": cfg, "skipped": [f for f, r in res if r is None], "outbreaks": out}, indent=2))
    print("done:", len(out), "outbreaks; skipped:", [f for f, r in res if r is None])


if __name__ == "__main__":
    main(sys.argv[1])
