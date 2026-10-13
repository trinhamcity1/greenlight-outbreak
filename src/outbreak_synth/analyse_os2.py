"""Score Step 3 round 2 (Exp. 8): selection rule with a ranking-based safety alarm, and the Green Light.

Rule (D, E, S): use default candidate D until at least E deaths are among fob's fresh (unseen-when-predicted)
records; then use the candidate in S with the best fresh AUC (pooled over complete weeks so far).
E = inf means "always D". The rule is chosen per outbreak by leave-one-outbreak-out (lowest mean gap to gold,
days 0-90, on the other outbreaks).
Green Light on the chosen rule's actual path: green on day d if deaths >= m, stability >= s (OS's risk scores
today vs 8 days earlier, whichever candidates were in use), on two checks in a row, and OS is not on the
age_trend fallback (falling back means OS does not yet trust its understanding). (m, s) is chosen by
leave-one-outbreak-out: fewest false greens, then earliest. A green is false if OS is > 0.02 below gold.
Usage: PYTHONPATH=src python -m outbreak_synth.analyse_os2 exp08_os_replay"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TOL = 0.02
CHECK = [0, 14, 28, 56, 90]
DEFAULTS = ["kin", "kin_age", "age_trend"]
ES = [0, 10, 20, 50, 100, np.inf]
SETS = {"kin|age": ["kin", "age_trend"], "kin|kin_age|age": ["kin", "kin_age", "age_trend"],
        "all": ["kin", "consensus", "own", "kin_age", "age_trend"]}
MS = [10, 20, 50, 100]
SS = [0.9, 0.95, 0.98, 0.99]


def frame(r):
    d = pd.DataFrame(r["days"])
    if "real_only" not in d:
        d["real_only"] = np.nan
    return d


def path(d, D, E, S):
    out = []
    for _, r in d.iterrows():
        if r.fresh_deaths >= E:
            vals = {c: r[f"fresh_auc_{c}"] for c in S if pd.notna(r[f"fresh_auc_{c}"])}
            out.append(max(vals, key=lambda c: (vals[c], c == D)) if vals else D)
        else:
            out.append(D)
    return out


def apply_rule(d, rule):
    D, E, S = rule
    ch = path(d, D, E, SETS[S])
    auc = [d.loc[i, f"auc_{c}"] for i, c in zip(d.index, ch)]
    stab = [np.nan] + [np.nan] * 0
    stab = []
    for i, c in zip(d.index, ch):
        j = d.index[(d.day == d.loc[i, "day"] - 8)]
        if len(j) and f"stab_{c}__{ch[d.index.get_loc(j[0])]}" in d:
            stab.append(d.loc[i, f"stab_{c}__{ch[d.index.get_loc(j[0])]}"])
        else:
            stab.append(np.nan)
    return d.assign(chosen=ch, auc_os=auc, stability=stab)


def first_day(d, col, gold):
    hit = d[(gold - d[col]) <= TOL]
    return int(hit.day.iloc[0]) if len(hit) else None


def green_day(d, m, s):
    ok = (d.deaths >= m) & (d.stability >= s) & (d.chosen != "age_trend")
    ok2 = ok & ok.shift(1, fill_value=False)
    return int(d.day[ok2].iloc[0]) if ok2.any() else None


def main(name):
    outs = json.loads(Path("results", f"{name}.json").read_text())["outbreaks"]
    frames = {f: frame(r) for f, r in outs.items()}
    gold = {f: r["info"]["gold_auc"] for f, r in outs.items()}
    age = {f: r["info"]["age_only_auc"] for f, r in outs.items()}
    rules = [(D, E, S) for D, E, S in itertools.product(DEFAULTS, ES, SETS) if not (E == np.inf and S != "kin|age")]
    applied = {rule: {f: apply_rule(d, rule) for f, d in frames.items()} for rule in rules}
    gap = pd.DataFrame({str(rule): {f: float((gold[f] - a.auc_os).mean()) for f, a in per.items()} for rule, per in applied.items()})
    key = {str(r): r for r in rules}
    chosen = {f: key[gap.drop(index=f).mean().idxmin()] for f in gap.index}
    pd.set_option("display.width", 250)
    fixed = {f"always {c}": float(np.mean([(gold[f] - frames[f][f"auc_{c}"]).mean() for f in frames]))
             for c in ["kin", "consensus", "own", "kin_age", "age_trend"]}
    print("mean gap to gold, fixed candidates:", {k: round(v, 4) for k, v in fixed.items()})
    print("best rules (mean gap, all outbreaks):"); print(gap.mean().sort_values().head(8).round(4).to_string())
    print("rule chosen (leave-one-outbreak-out):", sorted(set(map(str, chosen.values()))))

    final = {f: applied[chosen[f]][f] for f in frames}
    rows = []
    for f in sorted(final):
        d, g, a = final[f], gold[f], age[f]
        both = d.dropna(subset=["real_only"])
        rows.append({"outbreak": f, "gold": round(g, 3), "age_only": round(a, 3),
                     **{f"d{k}": round(float(d.loc[d.day == k, "auc_os"].iloc[0]), 3) for k in CHECK},
                     "plateau_real": first_day(d, "real_only", g), "plateau_os": first_day(d, "auc_os", g),
                     "days_below_age": int((d.auc_os < a - 1e-9).sum() * 2),
                     "worst_vs_age": round(float((d.auc_os - a).min()), 3),
                     "worst_vs_real": round(float((both.auc_os - both.real_only).min()), 3) if len(both) else None,
                     "uses": ",".join(f"{c}:{n*2}d" for c, n in d.chosen.value_counts().items())})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    by_day = {k: f"{int((t[f'd{k}'] >= t.age_only - 1e-9).sum())}/{len(t)}" for k in CHECK}
    print("OS at least as good as age only, by day:", by_day)
    pr, po = t.plateau_real.fillna(999), t.plateau_os.fillna(999)
    summ = {"fixed_candidates_mean_gap": fixed, "rule_chosen": {f: str(r) for f, r in chosen.items()},
            "mean_gap_final": float(np.mean([(gold[f] - final[f].auc_os).mean() for f in final])),
            "os_at_least_age_only_by_day": by_day, "plateau_earlier_same_later_vs_real":
            [int((po < pr).sum()), int((po == pr).sum()), int((po > pr).sum())],
            "outbreaks_ever_below_age": int((t.days_below_age > 0).sum())}

    # Green Light on the final path.
    def ev(m, s):
        res = {}
        for f, d in final.items():
            gd = green_day(d, m, s)
            auc = float(d.loc[d.day == gd, "auc_os"].iloc[0]) if gd is not None else None
            res[f] = {"green_day": gd, "auc": auc, "false": gd is not None and gold[f] - auc > TOL}
        return res
    grid = {(m, s): ev(m, s) for m, s in itertools.product(MS, SS)}
    def cost(e, skip):
        e = [v for f, v in e.items() if f != skip]
        return (sum(v["false"] for v in e), np.mean([v["green_day"] if v["green_day"] is not None else 120 for v in e]))
    gl = []
    for f in sorted(final):
        ms = min(grid, key=lambda k: cost(grid[k], f))
        v = grid[ms][f]
        gl.append({"outbreak": f, "m": ms[0], "s": ms[1], "green_day": v["green_day"],
                   "auc_at_green": None if v["auc"] is None else round(v["auc"], 3), "gold": round(gold[f], 3),
                   "false_green": v["false"], "plateau_os": first_day(final[f], "auc_os", gold[f])})
    gl = pd.DataFrame(gl)
    print(gl.to_string(index=False))
    summ["green_light"] = {"rules": sorted(set(zip(gl.m, gl.s))), "greens": int(gl.green_day.notna().sum()),
                           "false_greens": int(gl.false_green.sum()), "never_green": int(gl.green_day.isna().sum()),
                           "median_green_day": None if gl.green_day.isna().all() else float(gl.green_day.median())}
    print(summ["green_light"])
    if "covid_2020" in final:
        d = final["covid_2020"]
        print("COVID 2020 gold", round(gold["covid_2020"], 3), "age_only", round(age["covid_2020"], 3),
              "slope prior", round(outs["covid_2020"]["info"]["slope_prior"], 3))
        print(d[d.day <= 44][["day", "n", "deaths", "fresh_deaths", "chosen", "auc_kin", "auc_kin_age", "auc_age_trend",
                              "auc_os", "real_only", "stability"]].round(3).to_string(index=False))
    t.to_csv(Path("results", f"{name}_summary.csv"), index=False)
    gl.to_csv(Path("results", f"{name}_greenlight.csv"), index=False)
    Path("results", f"{name}_analysis.json").write_text(json.dumps(summ, indent=2, default=str))


if __name__ == "__main__":
    main(sys.argv[1])


def offline_variants(name):
    """Two offline variants on the logged Exp. 8 replay:
    A. always kin (the rule leave-one-outbreak-out picked for nearly every outbreak), with the Green Light;
    B. pathogen-label fallback: if fob's pathogen group (flu incl. H1N1 / other virus / COVID) has no earlier
       member in the Atlas, use age_trend until E fresh deaths, then kin. The label is external information a lab
       has on day 0 (e.g. "a new coronavirus"); it is not learned from fob's records."""
    outs = json.loads(Path("results", f"{name}.json").read_text())["outbreaks"]
    from .library import family as fam
    gold = {f: r["info"]["gold_auc"] for f, r in outs.items()}
    age = {f: r["info"]["age_only_auc"] for f, r in outs.items()}
    pd.set_option("display.width", 250)
    for label, E in [("A always kin", None), ("B label fallback E=20", 20), ("B label fallback E=100", 100)]:
        rows, final = [], {}
        for f, r in sorted(outs.items()):
            d = frame(r)
            new_group = not any(fam(k) == fam(f) for k in r["info"]["kin"])
            if E is None or not new_group:
                ch = ["kin"] * len(d)
            else:
                ch = ["age_trend" if fd < E else "kin" for fd in d.fresh_deaths]
            d = d.assign(chosen=ch, auc_os=[d.loc[i, f"auc_{c}"] for i, c in zip(d.index, ch)])
            st = []
            for i in range(len(d)):
                j = np.where(d.day.to_numpy() == d.day.iloc[i] - 8)[0]
                st.append(d.iloc[i][f"stab_{ch[i]}__{ch[j[0]]}"] if len(j) else np.nan)
            d = d.assign(stability=st)
            final[f] = d
            rows.append({"outbreak": f, "new_group": new_group, **{f"d{k}": round(float(d.loc[d.day == k, "auc_os"].iloc[0]), 3) for k in CHECK},
                         "age_only": round(age[f], 3), "plateau_os": first_day(d, "auc_os", gold[f]),
                         "days_below_age": int((d.auc_os < age[f] - 1e-9).sum() * 2), "gap": round(float((gold[f] - d.auc_os).mean()), 4)})
        t = pd.DataFrame(rows)
        gl = []
        for f, d in final.items():
            gd = green_day(d, 20, 0.98)
            auc = float(d.loc[d.day == gd, "auc_os"].iloc[0]) if gd is not None else None
            gl.append((f, gd, auc, gd is not None and gold[f] - auc > TOL))
        g = pd.DataFrame(gl, columns=["outbreak", "green_day", "auc_at_green", "false_green"])
        print(f"\n== {label}: mean gap {t.gap.mean():.4f}; outbreaks ever below age only {int((t.days_below_age > 0).sum())}; "
              f"total days below age {int(t.days_below_age.sum())}; at least age-only by day "
              f"{ {k: int((t[f'd{k}'] >= t.age_only - 1e-9).sum()) for k in CHECK} }")
        print(t[t.new_group | (t.days_below_age > 0)].to_string(index=False))
        print(f"Green Light (m=20, s=0.98): greens {g.green_day.notna().sum()}, false {g.false_green.sum()}, "
              f"median day {g.green_day.median()}; COVID 2020 green day {g.set_index('outbreak').loc['covid_2020','green_day']}")
        print("false greens:", g[g.false_green].to_dict("records"))
        t.to_csv(Path("results", f"{name}_variant_{label.split()[0]}{'' if E is None else E}.csv"), index=False)


def final_paths(name, E=20, m=20, s=0.98):
    """OS's final rule on the logged Exp. 8 replay: kin, or age_trend until E fresh deaths when fob's pathogen
    group has no earlier member. Returns {outbreak: (per-day frame with chosen/auc_os/stability, green day)}."""
    outs = json.loads(Path("results", f"{name}.json").read_text())["outbreaks"]
    from .library import family as fam
    res = {}
    for f, r in outs.items():
        d = frame(r)
        new_group = not any(fam(k) == fam(f) for k in r["info"]["kin"])
        ch = ["age_trend" if (new_group and fd < E) else "kin" for fd in d.fresh_deaths]
        d = d.assign(chosen=ch, auc_os=[d.loc[i, f"auc_{c}"] for i, c in zip(d.index, ch)])
        st = []
        for i in range(len(d)):
            j = np.where(d.day.to_numpy() == d.day.iloc[i] - 8)[0]
            st.append(d.iloc[i][f"stab_{ch[i]}__{ch[j[0]]}"] if len(j) else np.nan)
        d = d.assign(stability=st)
        res[f] = (d, green_day(d, m, s), new_group)
    return res
