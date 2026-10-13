"""Frozen final test: the endpoints of docs/frozen_test_plan.md, in its order, and the claims checked against the
criteria stated there in advance. Committed with the plan, before the test data were downloaded.

Needs (run with OUTBREAK_LIB=data/processed/library_frozen.parquet):
  exp18a_kinship_frozen (+ analyse_kinship ... --prior group --tau 0.01), exp18b_os_replay_frozen,
  exp18c_baselines_frozen (+ analyse_baselines), exp18d_synth_frozen, exp18e_synth_baselines_frozen.
Usage: OUTBREAK_LIB=data/processed/library_frozen.parquet PYTHONPATH=src python -m outbreak_synth.analyse_frozen [B]"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .analyse_ci import boot_mean, boot_median, cp, patient_level
from .analyse_os2 import TOL, final_paths, green_day
from .os_core import FINAL_CFG

KIN, OS_RUN, BL, SY, SYB = ("exp18a_kinship_frozen", "exp18b_os_replay_frozen", "exp18c_baselines_frozen",
                            "exp18d_synth_frozen", "exp18e_synth_baselines_frozen")
CFG = {**FINAL_CFG, "os_run": OS_RUN, "kinship_run": KIN, "kinship_analysis": KIN}
GENS = ["bootstrap", "bayesian_network", "arf", "ctgan", "tvae"]


def load(name):
    return json.loads(Path("results", f"{name}.json").read_text())


def paired(a, b, B=2000, seed=0):
    """Mean of a - b over outbreaks, 95% percentile bootstrap, and how many outbreaks a is better in."""
    d = np.asarray(a, float) - np.asarray(b, float)
    i = np.random.default_rng(seed).integers(0, len(d), (B, len(d)))
    m = d[i].mean(1)
    return {"diff": float(d.mean()), "ci": [float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))],
            "better_in": int((d > 1e-9).sum()), "n": int(len(d))}


def main(B=1000):
    res = {"plan": "docs/frozen_test_plan.md"}
    osr = load(OS_RUN)
    res["scored"] = sorted(osr["outbreaks"])
    res["excluded"] = osr.get("skipped", [])

    # 1-2. Who dies: accuracy and safety (per-outbreak values from analyse_baselines on the frozen runs).
    pe = pd.DataFrame(load(f"{BL}_analysis")["per_outbreak"])
    pe["gap"] = pe.gap.astype(float)
    pe["days_below_age"] = pe.days_below_age.astype(float)
    piv = pe.pivot(index="outbreak", columns="method", values="gap")
    res["os_mean_gap"] = boot_mean(piv["OS"])
    # Positive = OS better (the other method's gap minus OS's gap).
    res["gap_vs_os"] = {m: paired(piv[m], piv["OS"]) for m in ["real_only", "finetune", "stacked", "kin_equal", "bma"]}
    below = pe[pe.method == "OS"].set_index("outbreak").days_below_age
    res["os_days_below_age"] = {"total": int(below.sum()), "per_outbreak": boot_mean(below), "by_outbreak": below.to_dict()}

    # 3. Green Light.
    paths = final_paths(OS_RUN, E=CFG["fallback_deaths"], m=CFG["green_m"], s=CFG["green_s"])
    gl = {}
    for f, (d, gday, _) in paths.items():
        gold = osr["outbreaks"][f]["info"]["gold_auc"]
        auc = float(d.loc[d.day == gday, "auc_os"].iloc[0]) if gday is not None else None
        gl[f] = {"green_day": gday, "auc": auc, "gold": gold, "false": gday is not None and gold - auc > TOL}
    days = [v["green_day"] for v in gl.values() if v["green_day"] is not None]
    k = sum(v["false"] for v in gl.values())
    res["green_light"] = {"per_outbreak": gl, "greens": len(days), "outbreaks": len(gl),
                          "median_day": boot_median(days) if days else None,
                          "false": {"k": int(k), "n": len(days), "ci": cp(int(k), len(days)) if days else None}}
    rd = pd.DataFrame(load(f"{BL}_analysis")["readiness_per_outbreak"])
    res["riley"] = rd[rd.rule == "riley"][["outbreak", "day"]].to_dict("records")
    pl = patient_level(B, CFG)
    t = pd.DataFrame(pl)
    res["patient_level"] = {"B": B, "per_outbreak": pl,
                            "firm_correct": int((t.share_false < 0.025).sum()) if len(t) else 0,
                            "uncertain": int(((t.share_false >= 0.025) & (t.share_false <= 0.975)).sum()) if len(t) else 0,
                            "firm_false": int((t.share_false > 0.975).sum()) if len(t) else 0}

    # 4. Kinship Vote: right group leads, by week.
    v = pd.read_csv(Path("results", f"{KIN}_votes.csv"))
    res["right_group"] = []
    for w in (1, 2, 4, 8):
        x = v[(v.week == w) & v.group_testable.astype(bool)]
        kk, n = int(x.top_group_right.astype(bool).sum()), int(len(x))
        res["right_group"].append({"week": w, "right": kk, "n": n, "ci": cp(kk, n) if n else None})

    # 5. Synthetic data.
    sy, syb = load(SY)["outbreaks"], load(SYB)["outbreaks"]
    fs = sorted(set(sy) & set(syb))
    os_syn = [sy[f]["auc"]["os_synth_only"] for f in fs]
    res["synthetic"] = {"outbreaks": fs,
                        "os_synth_only": boot_mean(os_syn),
                        "os_minus_real_records": paired(os_syn, [sy[f]["auc"]["real_early"] for f in fs]),
                        "real_plus_os_minus_real": paired([sy[f]["auc"]["real_plus_os_synth"] for f in fs],
                                                          [sy[f]["auc"]["real_early"] for f in fs]),
                        **{f"os_minus_{g}": paired(os_syn, [syb[f]["auc"][f"{g}_synth_only"] for f in fs]) for g in GENS}}

    # Section 4 of the plan: criteria stated in advance.
    gv = res["gap_vs_os"]
    res["criteria"] = {
        "borrowing_helps (OS vs real data alone, interval above 0)": gv["real_only"]["ci"][0] > 0,
        "no_clear_gain_vs_finetune (interval includes 0; expected)": gv["finetune"]["ci"][0] <= 0 <= gv["finetune"]["ci"][1],
        "no_clear_gain_vs_stacked (interval includes 0; expected)": gv["stacked"]["ci"][0] <= 0 <= gv["stacked"]["ci"][1],
        "green_light_honest (0 or 1 false greens; 2+ = claim fails)": res["green_light"]["false"]["k"] <= 1,
        "os_synthetic_beats_real_records (interval above 0)": res["synthetic"]["os_minus_real_records"]["ci"][0] > 0,
        "safety_days_below_age_per_outbreak (development 2.9)": res["os_days_below_age"]["per_outbreak"]["mean"],
    }
    Path("results", "frozen_test_results.json").write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps({k: res[k] for k in ("scored", "excluded", "os_mean_gap", "gap_vs_os", "criteria")}, indent=1, default=str))
    print("green light:", {k: res["green_light"][k] for k in ("greens", "outbreaks", "median_day", "false")})
    print("patient level:", {k: v for k, v in res["patient_level"].items() if k != "per_outbreak"})
    print("right group:", res["right_group"])
    print("synthetic:", {k: v for k, v in res["synthetic"].items() if k != "outbreaks"})


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
