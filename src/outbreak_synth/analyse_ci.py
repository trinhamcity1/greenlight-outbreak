"""Confidence intervals for the headline results (adopted settings: Exp. 5d / 8d / 10d, baselines Exp. 15 / 16).

Two levels of uncertainty:
  patients   On each outbreak's Green Light day (10 deaths, 0.99), the later test patients are resampled
             (paired bootstrap, B resamples, seed 0) to give 95% intervals for the AUC of OS's released model
             (os_core.build_state, FINAL_CFG), the gold model (same design fitted on all of fob's other
             records, strength lam0, as in the replay) and real data alone (ridge on the records with a known
             outcome), and the paired differences. A green counts as false if gold - OS > 0.02; the share
             of resamples where that holds says how firm each verdict is.
  outbreaks  Headline averages over outbreaks: percentile bootstrap over outbreaks (2,000 resamples, seed 0).
             Rates (right group, false greens) use exact Clopper-Pearson intervals.
Usage: PYTHONPATH=src python -m outbreak_synth.analyse_ci [B]"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import beta
from sklearn.metrics import roc_auc_score

from .analyse_os2 import TOL, final_paths
from .library import OUT as LIB, TARGET
from .os_core import FINAL_CFG, build_state, risk
from .recipe import design, fit_map

OS_RUN = FINAL_CFG["os_run"]


def cp(k, n, a=0.05):
    lo = beta.ppf(a / 2, k, n - k + 1) if k > 0 else 0.0
    hi = beta.ppf(1 - a / 2, k + 1, n - k) if k < n else 1.0
    return [float(lo), float(hi)]


def boot_mean(x, B=2000, seed=0):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    i = np.random.default_rng(seed).integers(0, len(x), (B, len(x)))
    m = x[i].mean(1)
    return {"mean": float(x.mean()), "ci": [float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))], "n": int(len(x))}


def boot_median(x, B=2000, seed=0):
    x = np.asarray(x, float)
    i = np.random.default_rng(seed).integers(0, len(x), (B, len(x)))
    m = np.median(x[i], 1)
    return {"median": float(np.median(x)), "ci": [float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))], "n": int(len(x))}


def patient_level(B, cfg=FINAL_CFG):
    lib = pd.read_parquet(LIB)
    info = json.loads(Path("results", f"{cfg['os_run']}.json").read_text())
    cfg8, outs = info["config"], info["outbreaks"]
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
        g0, g = fit_map(X[~test], y[~test], lam=cfg8["lam0"])
        r0, r = fit_map(*_known_xy(s))
        yt = y[test]
        sc = {"os": risk(s, d[test]), "gold": g0 + X[test] @ g, "real": r0 + X[test] @ r}
        auc = {k: roc_auc_score(yt, v) for k, v in sc.items()}
        rng = np.random.default_rng(0)
        bs = {k: [] for k in sc}
        pos, neg = np.where(yt == 1)[0], np.where(yt == 0)[0]
        for _ in range(B):  # stratified: keeps the death count fixed
            i = np.r_[rng.choice(pos, len(pos)), rng.choice(neg, len(neg))]
            for k, v in sc.items():
                bs[k].append(roc_auc_score(yt[i], v[i]))
        bs = {k: np.array(v) for k, v in bs.items()}
        q = lambda a: [float(np.quantile(a, 0.025)), float(np.quantile(a, 0.975))]
        gap = bs["gold"] - bs["os"]
        rows.append({"outbreak": fob, "green_day": gday, "test_n": int(test.sum()), "test_deaths": int(yt.sum()),
                     "known_n": int(len(s.known)), "auc_os": auc["os"], "auc_os_ci": q(bs["os"]),
                     "auc_gold": auc["gold"], "auc_gold_ci": q(bs["gold"]),
                     "auc_real": auc["real"], "auc_real_ci": q(bs["real"]),
                     "gold_minus_os": auc["gold"] - auc["os"], "gold_minus_os_ci": q(gap),
                     "os_minus_real": auc["os"] - auc["real"], "os_minus_real_ci": q(bs["os"] - bs["real"]),
                     "share_false": float((gap > TOL).mean())})
        print(f"{fob} day {gday}: OS {auc['os']:.3f} {q(bs['os'])} gold {auc['gold']:.3f} gap {auc['gold'] - auc['os']:+.3f} "
              f"{q(gap)} P(false) {rows[-1]['share_false']:.2f}", flush=True)
    return rows


def _known_xy(s):
    X, _ = design(s.known)
    return X, s.known[TARGET].to_numpy()


def outbreak_level():
    out = {}
    k5 = json.loads(Path("results", "exp05d_kinship_known_analysis.json").read_text())
    out["right_group_by_week"] = []
    for r in k5["right_kin_by_week"]:
        n = 21  # outbreaks with an earlier member of their own group (COVID 2020 and other virus 2013 have none)
        k = int(round(r["group_right"] * n))
        out["right_group_by_week"].append({"week": r["week"], "right": k, "n": n, "share": k / n, "ci": cp(k, n)})
    top = [c for c in k5["calibration_group"] if c["bin"] == "[0.95, 1.0)"][0]
    n, sh = int(top["cases"]), float(top["right"])
    out["right_when_95pct_sure"] = {"share": sh, "n": n, "ci": cp(int(round(sh * n)), n)}

    paths = final_paths(OS_RUN, E=FINAL_CFG["fallback_deaths"], m=FINAL_CFG["green_m"], s=FINAL_CFG["green_s"])
    gdays = [g for _, g, _ in paths.values() if g is not None]
    out["green_light"] = {"greens": len(gdays), "outbreaks": len(paths), "median_day": boot_median(gdays),
                          "false_in_sample": {"k": 0, "n": len(gdays), "ci": cp(0, len(gdays))},
                          "false_leave_one_out": {"k": 1, "n": 22, "ci": cp(1, 22)}}

    bl = pd.read_csv(Path("results", "exp15_baselines_summary.csv"))
    pe = pd.DataFrame(json.loads(Path("results", "exp15_baselines_analysis.json").read_text())["per_outbreak"])
    pe["gap"] = pe.gap.astype(float)
    pe["days_below_age"] = pe.days_below_age.astype(float)
    os_ = pe[pe.method == "OS"]
    out["os_mean_gap"] = boot_mean(os_.gap)
    out["os_days_below_age_per_outbreak"] = boot_mean(os_.days_below_age)
    out["real_only_mean_gap"] = boot_mean(pe[pe.method == "real_only"].gap)
    out["baselines_gap_minus_os"] = bl[bl.method.ne("OS") & bl.gap_minus_OS.notna()][
        ["method", "mean_gap", "gap_minus_OS", "ci_lo", "ci_hi", "OS_better_in"]].to_dict("records")

    sy = pd.read_csv(Path("results", "exp16_synth_baselines_summary.csv"))
    gens = ["OS", "real", "bootstrap", "bayesian_network", "arf", "ctgan", "tvae"]
    out["synthetic_auc"] = {g: boot_mean(sy[g]) for g in gens}
    out["synthetic_os_minus"] = {g: boot_mean(sy.OS - sy[g]) for g in gens if g != "OS"}
    small = sy[sy.n < 1000]
    out["small_outbreaks_real_to_real_plus_os"] = {"n": int(len(small)), "real": boot_mean(small.real),
                                                   "real_plus_os": boot_mean(small["real+OS"]),
                                                   "gain": boot_mean(small["real+OS"] - small.real)}
    return out


def main(B=1000):
    res = {"outbreak_level": outbreak_level()}
    rows = patient_level(B)
    t = pd.DataFrame(rows)
    res["patient_level"] = {"B": B, "per_outbreak": rows,
                            "verdict_firm_correct": int((t.share_false < 0.025).sum()),
                            "verdict_uncertain": int(((t.share_false >= 0.025) & (t.share_false <= 0.975)).sum()),
                            "verdict_firm_false": int((t.share_false > 0.975).sum()),
                            "os_beats_real_ci_above_0": int((t.os_minus_real_ci.str[0] > 0).sum())}
    Path("results", "ci_summary.json").write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res["patient_level"].items() if k != "per_outbreak"}, indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
