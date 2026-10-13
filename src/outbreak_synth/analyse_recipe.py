"""Score Step 2: does the Severity Model + Handover Rule reach the plateau sooner than real data alone?
Borrowing strength lam0 is chosen per outbreak by leave-one-outbreak-out (minimum mean gap to gold over
days 0-90 on all OTHER outbreaks). A day without a model counts as AUC 0.5 (nothing to act on).
Usage: PYTHONPATH=src python -m outbreak_synth.analyse_recipe exp06_recipe_replay"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CHECK = [0, 6, 14, 20, 28, 40, 60, 90]


def frame(r):
    d = pd.DataFrame(r["days"])
    if "real_only" not in d:  # real data never had enough deaths and survivors in 90 days
        d["real_only"] = np.nan
    return d


def gap_curve(d, col, gold):
    return gold - d[col].fillna(0.5)


def plateau_day(d, col, gold, tol=0.02):
    hit = d[(gold - d[col]) <= tol]
    return int(hit.day.iloc[0]) if len(hit) else None


def main(name):
    res = json.loads(Path("results", f"{name}.json").read_text())
    outs = res["outbreaks"]
    lams = res["config"]["lam0"]
    cols = [f"os_lam{l}" for l in lams]
    gaps = pd.DataFrame({f: {c: gap_curve(frame(r), c, r["info"]["gold_auc"]).mean() for c in cols + ["real_only"]}
                         for f, r in outs.items()}).T
    chosen = {f: gaps.drop(index=f)[cols].mean().idxmin() for f in gaps.index}
    rows = []
    for f, r in outs.items():
        d, g, c = frame(r), r["info"]["gold_auc"], chosen[f]
        both = d.dropna(subset=["real_only"])
        rows.append({
            "outbreak": f, "test_n": r["info"]["test_n"], "gold": round(g, 3), "lam0": c.replace("os_lam", ""),
            "plateau_real": plateau_day(d, "real_only", g), "plateau_os": plateau_day(d, c, g),
            "first_day_real_model": int(both.day.iloc[0]) if len(both) else None,
            "mean_gap_real": round(gaps.loc[f, "real_only"], 3), "mean_gap_os": round(gaps.loc[f, c], 3),
            "worst_os_minus_real": round(float((both[c] - both.real_only).min()), 3) if len(both) else None,
            **{f"os_d{k}": (round(float(d.loc[d.day == k, c].iloc[0]), 3) if (d.day == k).any() else None) for k in CHECK},
            **{f"real_d{k}": (round(float(d.loc[d.day == k, "real_only"].iloc[0]), 3)
                              if (d.day == k).any() and pd.notna(d.loc[d.day == k, "real_only"].iloc[0]) else None) for k in CHECK},
        })
    t = pd.DataFrame(rows).sort_values("outbreak")
    t.to_csv(Path("results", f"{name}_summary.csv"), index=False)
    pd.set_option("display.width", 250)
    print("mean gap to gold over days 0-90 (all outbreaks):")
    print(gaps.mean().round(4).to_string())
    print("lam0 chosen (leave-one-outbreak-out):", sorted(set(chosen.values())))
    print(t[["outbreak", "test_n", "gold", "lam0", "first_day_real_model", "plateau_real", "plateau_os",
             "mean_gap_real", "mean_gap_os", "worst_os_minus_real"]].to_string(index=False))
    pr = t.plateau_real.fillna(999); po = t.plateau_os.fillna(999)
    summary = {"lam0_chosen": chosen, "outbreaks": len(t),
               "os_plateau_earlier": int((po < pr).sum()), "same": int((po == pr).sum()), "os_later": int((po > pr).sum()),
               "median_plateau_real": float(t.plateau_real.median()), "median_plateau_os": float(t.plateau_os.median()),
               "mean_gap_real": float(t.mean_gap_real.mean()), "mean_gap_os": float(t.mean_gap_os.mean())}
    print(summary)
    c = outs.get("covid_2020")
    if c:
        d = frame(c)
        print("COVID 2020, gold", round(c["info"]["gold_auc"], 3), "test", c["info"]["test_n"])
        print(d[d.day <= 40][["day", "n", "deaths", "stranger", "real_only", chosen["covid_2020"]] + [x for x in cols if x != chosen["covid_2020"]]].round(3).to_string(index=False))
    Path("results", f"{name}_analysis.json").write_text(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main(sys.argv[1])


def age_only(name):
    """Zero-learning baseline: rank test patients by age (older = higher risk). Needs no fob data at all."""
    from sklearn.metrics import roc_auc_score
    from .library import OUT as LIB
    from .run_kinship_replay import day0_of
    res = json.loads(Path("results", f"{name}.json").read_text())
    lib = pd.read_parquet(LIB)
    out = {}
    for f, r in res["outbreaks"].items():
        d = lib[lib.outbreak == f]
        t0 = day0_of(d, f)
        lo, hi = r["info"]["test_days"]
        day = (d.DT_DIGITA - t0).dt.days
        t = d[(day >= lo) & (day <= hi)]
        out[f] = round(float(roc_auc_score(t.death, t.age.fillna(t.age.median()))), 3)
    return out
