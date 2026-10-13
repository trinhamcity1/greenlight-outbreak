"""Score the step 2-3 baselines (Exp. 15) against OS (Exp. 8d final rule) and the Riley readiness rule.

Per method, over days 0-90 of each outbreak (2-day grid):
  mean gap to gold, days below age only, plateau day (first day within 0.02 of gold), AUC on days 0/14/28/56/90.
  'raw': the method as is. '+fallback': the same Lab-Label Fallback as OS (age trend until 20 fresh deaths when
  fob's pathogen group has no earlier member), so the comparison isolates the borrowing itself.
  Paired outbreak bootstrap (2,000 resamples, seed 0) of the mean-gap difference method - OS.
Readiness rules, on the Exp. 8d replay rows (outcomes counted only once known):
  green      OS Green Light, adopted (10 deaths, stability 0.99), and the old (20, 0.98)
  riley      Riley et al. (BMJ 2020) minimum sample size for a binary outcome, shrinkage 0.9, Nagelkerke optimism
             0.05, overall risk within 0.05; P = predictor parameters; anticipated R^2 = Nagelkerke R^2 of the
             pooled past model, rescaled to fob's current death share
  epv10      at least 10 events per predictor parameter (events = the rarer outcome)
  A ready day is 'false' if the model it releases is more than 0.02 AUC below gold. Riley and EPV are rules for
  a model developed on fob's own data, so they are scored on real data alone and, for comparison, on OS.
Usage: PYTHONPATH=src python -m outbreak_synth.analyse_baselines exp15_baselines exp08d_os_replay_known"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .analyse_os2 import CHECK, TOL, final_paths, first_day, green_day
from .run_baselines import METHODS

E_FALLBACK = 20


def riley_n(P, r2n, phi, S=0.9, delta=0.05, margin=0.05):
    max_cs = 1 - (phi ** phi * (1 - phi) ** (1 - phi)) ** 2
    r2cs = r2n * max_cs
    n1 = P / ((S - 1) * np.log(1 - r2cs / S))
    s2 = r2cs / (r2cs + delta * max_cs)
    n2 = P / ((s2 - 1) * np.log(1 - r2cs / s2))
    n3 = (1.96 / margin) ** 2 * phi * (1 - phi)
    return float(max(n1, n2, n3))


def main(bl_name, os_name):
    bl = json.loads(Path("results", f"{bl_name}.json").read_text())["outbreaks"]
    osr = json.loads(Path("results", f"{os_name}.json").read_text())["outbreaks"]
    paths = final_paths(os_name, E=E_FALLBACK, m=10, s=0.99)
    rows, series = [], {}
    for f in sorted(bl):
        b = pd.DataFrame(bl[f]["days"]).set_index("day")
        d, _, new_group = paths[f]
        d = d.set_index("day")
        gold, age = osr[f]["info"]["gold_auc"], osr[f]["info"]["age_only_auc"]
        fb = d.chosen == "age_trend"
        cols = {"OS": d.auc_os, "real_only": d.real_only, "age_only": pd.Series(age, index=d.index)}
        for m in METHODS:
            cols[m] = b[f"auc_{m}"]
            cols[f"{m}+fallback"] = b[f"auc_{m}"].where(~fb, d.auc_age_trend)
        series[f] = (pd.DataFrame(cols), gold, age, new_group)
        for name, s in cols.items():
            s = s.reindex(d.index)
            rows.append({"outbreak": f, "method": name, "gap": float((gold - s).mean()) if s.notna().any() else np.nan,
                         "days_below_age": int((s < age - 1e-9).sum() * 2),
                         "plateau": first_day(pd.DataFrame({"day": s.index, "a": s.values}).dropna(), "a", gold),
                         **{f"d{k}": float(s.get(k, np.nan)) for k in CHECK}})
    t = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    order = ["OS", "real_only", "age_only"] + [m for m in METHODS] + [f"{m}+fallback" for m in METHODS]
    rng = np.random.default_rng(0)
    outs = sorted(bl)
    piv = t.pivot(index="outbreak", columns="method", values="gap").loc[outs]
    boot = rng.integers(0, len(outs), (2000, len(outs)))
    summ = []
    for m in order:
        x = t[t.method == m]
        r = {"method": m, "mean_gap": x.gap.mean(), "outbreaks_below_age": int((x.days_below_age > 0).sum()),
             "days_below_age": int(x.days_below_age.sum()),
             "plateau_covid_2020": x.set_index("outbreak").plateau.get("covid_2020"),
             "median_plateau": x.plateau.fillna(120).median(),
             **{f"mean_d{k}": x[f"d{k}"].mean() for k in CHECK}}
        if m != "OS" and m != "age_only" and piv[m].notna().all():
            diff = (piv[m] - piv["OS"]).to_numpy()
            bs = diff[boot].mean(1)
            r.update({"gap_minus_OS": diff.mean(), "ci_lo": np.quantile(bs, 0.025), "ci_hi": np.quantile(bs, 0.975),
                      "OS_better_in": int((diff > 1e-9).sum())})
        summ.append(r)
    s = pd.DataFrame(summ)
    print(s.round(4).to_string(index=False))
    newg = [f for f in outs if series[f][3]]
    print("\nNew pathogen group outbreaks (no earlier member):", newg)
    print(t[t.outbreak.isin(newg) & t.method.isin(["OS", "real_only"] + METHODS)].pivot(
        index="method", columns="outbreak", values=["d0", "d14", "d28", "plateau", "days_below_age"]).round(3).to_string())

    # Readiness rules.
    rr = []
    for f in outs:
        d, _, _ = paths[f]
        gold = osr[f]["info"]["gold_auc"]
        P, r2n = bl[f]["info"]["P"], bl[f]["info"]["pooled_r2_nagelkerke"]
        phi = (d.deaths / d.n_known).where(d.n_known > 0)
        need = [riley_n(P, r2n, p) if pd.notna(p) and 0 < p < 1 else np.inf for p in phi]
        events = np.minimum(d.deaths, d.n_known - d.deaths)
        rules = {"green(10,0.99)": green_day(d, 10, 0.99), "green(20,0.98)": green_day(d, 20, 0.98),
                 "riley": next((int(dy) for dy, n, q in zip(d.day, d.n_known, need) if n >= q), None),
                 "epv10": next((int(dy) for dy, e in zip(d.day, events) if e >= 10 * P), None)}
        for rule, gd in rules.items():
            at = d[d.day == gd]
            a_os = float(at.auc_os.iloc[0]) if gd is not None else np.nan
            a_real = float(at.real_only.iloc[0]) if gd is not None and pd.notna(at.real_only.iloc[0]) else np.nan
            rr.append({"outbreak": f, "rule": rule, "day": gd, "auc_os": a_os, "auc_real": a_real, "gold": gold,
                       "false_os": gd is not None and gold - a_os > TOL,
                       "false_real": gd is not None and not (gold - a_real <= TOL),
                       "riley_n_day90": need[-1], "n_known_day90": int(d.n_known.iloc[-1])})
    r = pd.DataFrame(rr)
    rs = r.groupby("rule").agg(ready=("day", lambda x: int(x.notna().sum())), median_day=("day", "median"),
                               false_with_os=("false_os", "sum"), false_with_real=("false_real", "sum"))
    print("\nReadiness rules (23 outbreaks, days 0-90):"); print(rs.to_string())
    print(r.pivot(index="outbreak", columns="rule", values="day").to_string())
    out = {"summary": s.to_dict("records"), "per_outbreak": t.to_dict("records"), "readiness": rs.reset_index().to_dict("records"),
           "readiness_per_outbreak": r.to_dict("records"),
           "riley_settings": {"shrinkage": 0.9, "delta_r2": 0.05, "margin": 0.05, "P": int(bl[outs[0]]["info"]["P"])}}
    Path("results", f"{bl_name}_analysis.json").write_text(json.dumps(out, indent=2, default=lambda v: None if pd.isna(v) else str(v)))
    s.to_csv(Path("results", f"{bl_name}_summary.csv"), index=False)


if __name__ == "__main__":
    main(*sys.argv[1:3])
