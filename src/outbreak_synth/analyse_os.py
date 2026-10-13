"""Score Step 3: Fresh-Days Check choice, OS vs baselines, and Green Light honesty.
Green Light rule: green on day d if deaths so far >= m and stability >= s on day d and on the previous check.
(m, s) is chosen per outbreak by leave-one-outbreak-out: fewest false greens on the OTHER outbreaks, then
earliest green. A green is false if OS's test AUC on that day is more than 0.02 below gold.
Usage: PYTHONPATH=src python -m outbreak_synth.analyse_os exp07_os_replay"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TOL = 0.02
MS = [10, 20, 50, 100]
SS = [0.9, 0.95, 0.98, 0.99]
CHECK = [0, 14, 28, 56, 90]


def frame(r):
    d = pd.DataFrame(r["days"])
    for c in ("real_only", "stability"):
        if c not in d:
            d[c] = np.nan
    return d


def first_day(d, col, gold):
    hit = d[(gold - d[col]) <= TOL]
    return int(hit.day.iloc[0]) if len(hit) else None


def green_day(d, m, s):
    ok = (d.deaths >= m) & (d.stability >= s)
    ok2 = ok & ok.shift(1, fill_value=False)
    return int(d.day[ok2].iloc[0]) if ok2.any() else None


def green_eval(outs, m, s):
    res = {}
    for f, r in outs.items():
        d, g = frame(r), r["info"]["gold_auc"]
        gd = green_day(d, m, s)
        auc = float(d.loc[d.day == gd, "auc_os"].iloc[0]) if gd is not None else None
        res[f] = {"green_day": gd, "auc_at_green": auc, "false": gd is not None and g - auc > TOL}
    return res


def main(name):
    outs = json.loads(Path("results", f"{name}.json").read_text())["outbreaks"]
    pd.set_option("display.width", 250)
    rows = []
    for f, r in sorted(outs.items()):
        d, i = frame(r), r["info"]
        g = i["gold_auc"]
        both = d.dropna(subset=["real_only"])
        rows.append({"outbreak": f, "day0": i["day0"], "test_n": i["test_n"], "gold": round(g, 3), "age_only": round(i["age_only_auc"], 3),
                     **{f"os_d{k}": round(float(d.loc[d.day == k, "auc_os"].iloc[0]), 3) for k in CHECK if (d.day == k).any()},
                     "plateau_real": first_day(d, "real_only", g), "plateau_os": first_day(d, "auc_os", g),
                     **{f"plateau_{c}": first_day(d, f"auc_{c}", g) for c in ("kin", "consensus")},
                     "os_minus_age_worst": round(float((d.auc_os - i["age_only_auc"]).min()), 3),
                     "os_minus_real_worst": round(float((both.auc_os - both.real_only).min()), 3) if len(both) else None,
                     "days_below_age": int((d.auc_os < i["age_only_auc"]).sum() * 2),
                     "chosen_d14": d.loc[d.day == 14, "chosen"].iloc[0], "chosen_d56": d.loc[d.day == 56, "chosen"].iloc[0]})
    t = pd.DataFrame(rows)
    t.to_csv(Path("results", f"{name}_summary.csv"), index=False)
    print(t.to_string(index=False))

    # Share of outbreaks where OS beats age-only, by day; and candidate usage.
    by_day = []
    for k in CHECK:
        v = [(float(frame(r).loc[frame(r).day == k, "auc_os"].iloc[0]) > r["info"]["age_only_auc"]) for r in outs.values()]
        by_day.append({"day": k, "os_beats_age_only": f"{sum(v)}/{len(v)}"})
    use = pd.concat([frame(r).chosen for r in outs.values()]).value_counts(normalize=True).round(3).to_dict()
    print(pd.DataFrame(by_day).to_string(index=False)); print("candidate chosen (share of outbreak-days):", use)
    pr, po = t.plateau_real.fillna(999), t.plateau_os.fillna(999)
    summ = {"outbreaks": len(t), "os_plateau_earlier_than_real": int((po < pr).sum()), "same": int((po == pr).sum()),
            "later": int((po > pr).sum()), "os_beats_age_only_by_day": by_day, "candidate_use": use}

    # Green Light: leave-one-outbreak-out choice of (m, s).
    grid = {(m, s): green_eval(outs, m, s) for m, s in itertools.product(MS, SS)}
    def cost(ev, skip):
        ev = {f: v for f, v in ev.items() if f != skip}
        false = sum(v["false"] for v in ev.values())
        late = np.mean([v["green_day"] if v["green_day"] is not None else 120 for v in ev.values()])
        return (false, late)
    gl = []
    for f in sorted(outs):
        m, s = min(grid, key=lambda k: cost(grid[k], f))
        v = grid[(m, s)][f]
        d, g = frame(outs[f]), outs[f]["info"]["gold_auc"]
        gl.append({"outbreak": f, "rule_m": m, "rule_s": s, "green_day": v["green_day"],
                   "auc_at_green": None if v["auc_at_green"] is None else round(v["auc_at_green"], 3), "gold": round(g, 3),
                   "false_green": v["false"], "os_plateau_day": first_day(d, "auc_os", g),
                   "age_only": round(outs[f]["info"]["age_only_auc"], 3)})
    gl = pd.DataFrame(gl)
    gl.to_csv(Path("results", f"{name}_greenlight.csv"), index=False)
    print(gl.to_string(index=False))
    summ["green_light"] = {"rules_chosen": sorted(set(zip(gl.rule_m, gl.rule_s))), "greens": int(gl.green_day.notna().sum()),
                           "false_greens": int(gl.false_green.sum()), "never_green": int(gl.green_day.isna().sum()),
                           "median_green_day": float(gl.green_day.median())}
    print(summ["green_light"])
    c = outs.get("covid_2020")
    if c:
        d = frame(c)
        print("COVID 2020 gold", round(c["info"]["gold_auc"], 3), "age_only", round(c["info"]["age_only_auc"], 3))
        print(d[d.day <= 44][["day", "n", "deaths", "chosen", "auc_kin", "auc_consensus", "auc_own", "auc_os", "real_only", "stability"]].round(3).to_string(index=False))
    Path("results", f"{name}_analysis.json").write_text(json.dumps(summ, indent=2, default=str))


if __name__ == "__main__":
    main(sys.argv[1])


def min_evidence(name, E_grid=(0, 10, 30, 100), defaults=("kin", "consensus")):
    """Re-score the logged replay with a stricter Fresh-Days rule: keep the default candidate until at least E deaths
    have been scored on fresh weeks, then use the best cumulative fresh score. Uses only logged, prequential numbers:
    scored deaths on day d = deaths among records entered before the last complete week (from the logged grid)."""
    outs = json.loads(Path("results", f"{name}.json").read_text())["outbreaks"]
    res = {}
    for E, D in itertools.product(E_grid, defaults):
        per = {}
        for f, r in outs.items():
            d = frame(r)
            os_auc = []
            for _, row in d.iterrows():
                u = int(row.day) // 7
                prev = d[d.day < 7 * u]
                scored_deaths = int(prev.deaths.iloc[-1]) if len(prev) else 0
                if scored_deaths >= E and u > 0:
                    c = max(("kin", "consensus", "own"), key=lambda k: row[f"fresh_{k}"])
                else:
                    c = D
                os_auc.append(row[f"auc_{c}"])
            per[f] = d.assign(auc_rule=os_auc)
        res[(E, D)] = per
    return outs, res


def report_min_evidence(name):
    outs, res = min_evidence(name)
    gap = {k: {f: float((outs[f]["info"]["gold_auc"] - v.auc_rule).mean()) for f, v in per.items()} for k, per in res.items()}
    g = pd.DataFrame(gap)
    chosen = {f: g.drop(index=f).mean().idxmax() if False else g.drop(index=f).mean().idxmin() for f in g.index}
    rows = []
    for f in sorted(outs):
        k = chosen[f]
        d, i = res[k][f], outs[f]["info"]
        rows.append({"outbreak": f, "rule": f"E={k[0]},default={k[1]}", "gold": round(i["gold_auc"], 3), "age_only": round(i["age_only_auc"], 3),
                     **{f"d{x}": round(float(d.loc[d.day == x, "auc_rule"].iloc[0]), 3) for x in CHECK},
                     "plateau": first_day(d, "auc_rule", i["gold_auc"]),
                     "days_below_age": int((d.auc_rule < i["age_only_auc"]).sum() * 2)})
    t = pd.DataFrame(rows)
    print("mean gap to gold by rule (all outbreaks):"); print(g.mean().round(4).to_string())
    print(t.to_string(index=False))
    for x in CHECK:
        print(f"day {x}: rule beats age-only in {(t[f'd{x}'] > t.age_only).sum()}/{len(t)}")
    t.to_csv(Path("results", f"{name}_min_evidence.csv"), index=False)
