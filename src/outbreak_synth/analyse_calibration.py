"""Calibration on each outbreak's Green Light day: do predicted death risks match what happened to later patients?

For the model OS releases on its Green Light day (os_core.build_state) and for comparison models fitted on the
same day, scored on the later test window:
  os       OS's released model
  real     ridge on fob's records with a known outcome by that day (real data alone)
  pooled   one model on the pooled earlier outbreaks (equal rows per outbreak, as Exp. 15), no fob data
  stacked  pooled earlier outbreaks + fob's known records with a fob indicator (as Exp. 15); fob's intercept
  gold     same design on all of fob's other records (hindsight reference)
Metrics: observed / expected deaths (O/E, 1 = right overall level), calibration intercept (logistic recalibration
with the model's logit as offset; 0 = right), calibration slope (1 = risks neither too extreme nor too flat),
Brier score, AUC. Per outbreak plus the mean over outbreaks with a 95% bootstrap interval (2,000, seed 0).
Usage: PYTHONPATH=src python -m outbreak_synth.analyse_calibration dev      (Exp. 8d, Brazil library)
       OUTBREAK_LIB=data/processed/library_frozen.parquet PYTHONPATH=src python -m outbreak_synth.analyse_calibration frozen"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit
from sklearn.metrics import roc_auc_score

from .analyse_ci import boot_mean
from .analyse_os2 import final_paths
from .library import OUT as LIB, TARGET
from .os_core import FINAL_CFG, build_state, risk
from .recipe import design, fit_map

RUNS = {"dev": {**FINAL_CFG},
        "frozen": {**FINAL_CFG, "os_run": "exp18b_os_replay_frozen", "kinship_run": "exp18a_kinship_frozen",
                   "kinship_analysis": "exp18a_kinship_frozen"}}
MODELS = ["os", "real", "pooled", "stacked", "gold"]


def recal(y, lp):
    """Calibration intercept (slope fixed at 1, logit as offset) and slope (logistic regression on the logit)."""
    def nll(w, slope_free):
        z = w[0] + (w[1] if slope_free else 1.0) * lp
        return float(np.logaddexp(0, z).sum() - y @ z)
    a = minimize(lambda w: nll([w[0], 1.0], False), [0.0], method="BFGS").x[0]
    b = minimize(lambda w: nll(w, True), [0.0, 1.0], method="BFGS").x[1]
    return float(a), float(b)


def metrics(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    a, b = recal(y, logit(p))
    return {"oe": float(y.mean() / p.mean()), "intercept": a, "slope": b, "brier": float(np.mean((p - y) ** 2)),
            "auc": float(roc_auc_score(y, p))}


def main(which):
    cfg = RUNS[which]
    lib = pd.read_parquet(LIB)
    info = json.loads(Path("results", f"{cfg['os_run']}.json").read_text())
    rcfg, outs = info["config"], info["outbreaks"]
    paths = final_paths(cfg["os_run"], E=cfg["fallback_deaths"], m=cfg["green_m"], s=cfg["green_s"])
    rows = []
    for fob, (_, gday, _) in sorted(paths.items()):
        if gday is None:
            continue
        s = build_state(fob, cfg=cfg, lib=lib)
        lo, hi = outs[fob]["info"]["test_days"]
        d = lib[lib.outbreak == fob]
        d = d[d.DT_DIGITA >= s.t0].sort_values(["DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable")
        day = (d.DT_DIGITA - s.t0).dt.days.to_numpy()
        test = (day >= lo) & (day <= hi)
        X, _ = design(d)
        y = d[TARGET].to_numpy()
        Xt, yt = X[test], y[test]
        Xk, yk = design(s.known)[0], s.known[TARGET].to_numpy()
        per_kin = max(1, rcfg["max_fit_rows"] // max(1, len(s.kin_profiles)))
        pool = []
        for k, kd in s.kin_profiles.items():
            i = np.random.default_rng(0).permutation(len(kd))[:per_kin]
            pool.append((design(kd.iloc[i])[0], kd[TARGET].to_numpy()[i]))
        Xp, yp = np.vstack([a for a, _ in pool]), np.concatenate([b for _, b in pool])
        p0, pb = fit_map(Xp, yp)
        Xs = np.column_stack([np.vstack([Xp, Xk]), np.r_[np.zeros(len(yp)), np.ones(len(yk))]])
        s0, sb = fit_map(Xs, np.r_[yp, yk])
        g0, g = fit_map(X[~test], y[~test], lam=rcfg["lam0"])
        r0, r = fit_map(Xk, yk)
        prob = {"os": risk(s, d[test]), "real": expit(r0 + Xt @ r), "pooled": expit(p0 + Xt @ pb),
                "stacked": expit(s0 + sb[-1] + Xt @ sb[:-1]), "gold": expit(g0 + Xt @ g)}
        row = {"outbreak": fob, "green_day": gday, "test_n": int(test.sum()), "test_death_rate": float(yt.mean()),
               "known_n": int(len(yk)), "known_death_rate": float(yk.mean()) if len(yk) else None}
        for m in MODELS:
            for k, v in metrics(yt, prob[m]).items():
                row[f"{m}_{k}"] = v
        rows.append(row)
        print(f"{fob} day {gday}: test deaths {yt.mean():.3f}, known-so-far deaths {yk.mean():.3f} | " +
              " | ".join(f"{m} O/E {row[f'{m}_oe']:.2f} slope {row[f'{m}_slope']:.2f}" for m in MODELS), flush=True)
    t = pd.DataFrame(rows)
    summ = {m: {k: boot_mean(t[f"{m}_{k}"]) for k in ["oe", "intercept", "slope", "brier", "auc"]} for m in MODELS}
    summ["os_brier_minus"] = {m: boot_mean(t[f"{m}_brier"] - t["os_brier"]) for m in MODELS if m != "os"}
    out = {"which": which, "os_run": cfg["os_run"], "per_outbreak": rows, "summary": summ}
    Path("results", f"calibration_{which}.json").write_text(json.dumps(out, indent=2))
    for m in MODELS:
        print(m, {k: (round(v["mean"], 3), [round(c, 3) for c in v["ci"]]) for k, v in summ[m].items()})


if __name__ == "__main__":
    main(sys.argv[1])
