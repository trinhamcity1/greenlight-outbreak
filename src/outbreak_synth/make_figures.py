"""Figures for the paper and plan (figures/*.png and *.pdf), drawn only from committed results files and the
library. Palette: the validated default categorical order (blue, orange, aqua); reference lines in neutral ink.
Usage: PYTHONPATH=src python -m outbreak_synth.make_figures"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analyse_os2 import final_paths
from .kinship import start_shares, votes_from_scores
from .library import OUT as LIB, TARGET, family
from .os_core import FINAL_CFG

OUT = Path("figures")
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"            # categorical slots 1-3
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
GROUP_NAME = {"flu": "Flu (incl. H1N1)", "othervirus": "Other respiratory virus", "covid": "COVID-19"}
NICE = {"covid_2020": "COVID-19 2020 (new pathogen)", "othervirus_2013": "Other virus 2013 (no earlier relative)",
        "flu_2016": "Flu 2016 (familiar season)", "flu_2013": "Flu 2013 (misleading relative: H1N1)"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF,
    "savefig.facecolor": SURF, "lines.linewidth": 2, "lines.solid_capstyle": "round", "legend.frameon": False,
    "text.color": INK})


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / f"{name}.png")


def ref_line(ax, y, text, x_text):
    """Reference level in neutral ink, labelled in the right margin so it never sits on the data."""
    ax.axhline(y, color=INK2, lw=0.8, zorder=1)
    ax.text(x_text, y, text, color=INK2, fontsize=7.5, va="center", ha="left", clip_on=False)


def fig_replay():
    """AUC on later patients vs replay day: OS, real data alone, fine-tuning towards the pooled past."""
    paths = final_paths(FINAL_CFG["os_run"], E=FINAL_CFG["fallback_deaths"], m=FINAL_CFG["green_m"], s=FINAL_CFG["green_s"])
    osr = json.loads(Path("results", f"{FINAL_CFG['os_run']}.json").read_text())["outbreaks"]
    bl = json.loads(Path("results", "exp15_baselines.json").read_text())["outbreaks"]
    fig, axes = plt.subplots(2, 2, figsize=(9, 6), sharex=True)
    for ax, f in zip(axes.flat, NICE):
        d, gday, _ = paths[f]
        b = pd.DataFrame(bl[f]["days"])
        gold, age = osr[f]["info"]["gold_auc"], osr[f]["info"]["age_only_auc"]
        ax.plot(d.day, d.real_only, color=C2, label="Real data alone")
        ax.plot(b.day, b.auc_finetune, color=C3, label="Fine-tune pooled past (baseline)")
        ax.plot(d.day, d.auc_os, color=C1, label="GreenLight")
        ref_line(ax, gold, "gold", 91.5)
        ref_line(ax, age, "rank by age", 91.5)
        if gday is not None:
            ax.axvline(gday, color=INK, lw=0.8, zorder=1)
            ax.text(gday + 1, ax.get_ylim()[0], f" green light\n day {gday}", fontsize=7.5, color=INK, va="bottom")
        else:
            ax.text(89, ax.get_ylim()[0], "no green light by day 90", fontsize=7.5, color=INK, va="bottom", ha="right")
        ax.set_title(NICE[f])
        ax.set_xlim(0, 90)
    for ax in axes[:, 0]:
        ax.set_ylabel("AUC on later patients")
    for ax in axes[1]:
        ax.set_xlabel("Day of the outbreak (replay)")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h[::-1], l[::-1], loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.03))
    fig.suptitle("Who dies: how fast each method learns a new outbreak", x=0.01, ha="left", y=1.08, fontsize=12, weight="bold")
    fig.tight_layout()
    save(fig, "fig1_replay_curves")


def fig_votes():
    """Kinship Vote shares by pathogen group over the first weeks."""
    meta = json.loads(Path("results", "exp05d_kinship_known.json").read_text())
    ana = json.loads(Path("results", "exp05d_kinship_known_analysis.json").read_text())
    weeks = pd.read_csv(Path("results", "exp05d_kinship_known_weeks.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2), sharey=True)
    for ax, f in zip(axes, ["covid_2020", "flu_2016"]):
        kin = list(meta[f]["kin"])
        lp = start_shares(kin, "group")
        g = weeks[weeks.fob == f].set_index("week").sort_index()
        g = g[g.index <= 12]
        rows = []
        for w, r in g.iterrows():
            v = votes_from_scores({n: r[f"score_total::{n}"] for n in kin + ["STRANGER"]}, float(ana["tau_chosen"][f]), lp)
            row = {"week": w, "Stranger (none of the above)": v["STRANGER"]}
            for k in kin:
                grp = GROUP_NAME[family(k)]
                row[grp] = row.get(grp, 0) + v[k]
            rows.append(row)
        t = pd.DataFrame(rows).set_index("week").fillna(0)
        cols = [c for c in [GROUP_NAME["flu"], GROUP_NAME["othervirus"], GROUP_NAME["covid"]] if c in t] + ["Stranger (none of the above)"]
        colors = {GROUP_NAME["flu"]: C1, GROUP_NAME["othervirus"]: C2, GROUP_NAME["covid"]: C3, "Stranger (none of the above)": MUTED}
        ax.stackplot(t.index, *[t[c] for c in cols], colors=[colors[c] for c in cols], labels=cols,
                     edgecolor=SURF, linewidth=1.5, alpha=0.9)
        ax.set_xlim(0, t.index.max())
        ax.set_ylim(0, 1)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1], ["0%", "25%", "50%", "75%", "100%"])
        ax.set_title(NICE[f].split(" (")[0])
        ax.set_xlabel("Week of the outbreak")
        ax.grid(False)
    axes[0].set_ylabel("Share of the Kinship Vote")
    n = weeks[weeks.fob == "covid_2020"].set_index("week").n_so_far
    wk = int(n.index[n >= 700][0]) if (n >= 700).any() else None
    if wk is not None:
        axes[0].annotate(f"Stranger takes over\n(week {wk + 1}, {int(n[wk + 1]):,} patients)" if wk + 1 in n.index else "",
                         xy=(wk + 1, 0.5), xytext=(6, 0.55), fontsize=7.5, color=INK,
                         arrowprops=dict(arrowstyle="-", color=INK, lw=0.8))
    h, l = axes[1].get_legend_handles_labels()
    h0, l0 = axes[0].get_legend_handles_labels()
    seen = dict(zip(l0 + l, h0 + h))
    fig.legend(seen.values(), seen.keys(), loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.08))
    fig.suptitle("Kinship Vote: which earlier outbreaks the new one resembles", x=0.01, ha="left", y=1.17, fontsize=12, weight="bold")
    fig.tight_layout()
    save(fig, "fig2_kinship_vote")


LABEL = {"real_only": "Real data alone", "pooled": "Pooled past only", "stacked": "Pooled past + new outbreak",
         "finetune": "Fine-tune pooled past", "kin_equal": "GreenLight without the vote (equal weights)",
         "map": "Meta-analytic prior", "rmap": "Robust meta-analytic prior", "eb": "Empirical Bayes strength",
         "bma": "Source averaging (MEM-style)", "meta_init": "Meta-learned start (MetaPred-style)"}


def fig_baselines():
    s = pd.read_csv(Path("results", "exp15_baselines_summary.csv")).set_index("method")
    ms = [m for m in LABEL if m != "real_only"]
    order = sorted(ms, key=lambda m: s.loc[m, "gap_minus_OS"])
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = np.arange(len(order))
    for off, suffix, color, name in [(-0.16, "", C1, "Baseline as published"), (0.16, "+fallback", C2, "With GreenLight's Lab-Label Fallback added")]:
        rows = [s.loc[m + suffix] for m in order]
        x = np.array([r.gap_minus_OS for r in rows])
        lo, hi = np.array([r.ci_lo for r in rows]), np.array([r.ci_hi for r in rows])
        ax.errorbar(x, y + off, xerr=[x - lo, hi - x], fmt="o", color=color, ms=5, elinewidth=1.6, capsize=0,
                    mec=SURF, mew=1.5, label=name)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(y, [LABEL[m] for m in order])
    ax.invert_yaxis()
    ax.set_xlabel("Gap to gold minus GreenLight's gap (AUC, days 0-90, mean over 23 outbreaks)  ·  right of 0 = GreenLight better")
    ax.grid(axis="y", visible=False)
    r = s.loc["real_only"]
    fig.tight_layout()
    fig.text(0.01, -0.02, f"Not shown (off scale): real data alone, +{r.gap_minus_OS:.3f} [{r.ci_lo:.3f}, {r.ci_hi:.3f}]. "
             "GreenLight's own settings were tuned on these outbreaks; the baselines were not.", fontsize=7.5, color=INK2)
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=2, bbox_to_anchor=(0.55, 1.06))
    fig.suptitle("GreenLight vs 9 borrowing baselines (95% paired bootstrap intervals over 23 outbreaks)", x=0.01, ha="left",
                 y=1.13, fontsize=12, weight="bold")
    save(fig, "fig3_baselines_forest")


def fig_readiness():
    a = json.loads(Path("results", "exp15_baselines_analysis.json").read_text())
    r = pd.DataFrame(a["readiness_per_outbreak"])
    r["day"] = pd.to_numeric(r.day)
    piv = r.pivot(index="outbreak", columns="rule", values="day")
    false = r[r.false_os.astype(str) == "True"].set_index(["outbreak", "rule"]).index
    outs = sorted(piv.index, key=lambda f: (family(f) != "covid", family(f), f))
    fig, ax = plt.subplots(figsize=(8, 6))
    y = {f: i for i, f in enumerate(outs)}
    spec = [("green(10,0.99)", C1, "o", "Green light (adopted: 10 deaths, 0.99)"),
            ("green(20,0.98)", C2, "D", "Green light (old: 20 deaths, 0.98)"),
            ("riley", C3, "s", "Riley et al. minimum sample size")]
    for k, (rule, color, mk, name) in enumerate(spec):
        xs = [(piv.loc[f, rule], y[f] + (k - 1) * 0.22) for f in outs if pd.notna(piv.loc[f, rule])]
        ax.scatter([x for x, _ in xs], [v for _, v in xs], color=color, marker=mk, s=34, edgecolor=SURF, linewidth=1.5,
                   label=name, zorder=3)
        for f in outs:
            if (f, rule) in false:
                ax.annotate("false green", (piv.loc[f, rule], y[f] + (k - 1) * 0.22), xytext=(6, -2),
                            textcoords="offset points", fontsize=7, color=INK)
    for f in outs:
        if piv.loc[f].isna().all():
            ax.text(91, y[f], "none by day 90", fontsize=7, color=INK2, va="center")
    ax.set_yticks(range(len(outs)), [f.replace("othervirus", "other virus").replace("_", " ") for f in outs])
    ax.invert_yaxis()
    ax.set_xlim(0, 105)
    ax.set_xticks(range(0, 91, 10))
    ax.set_xlabel("Day the rule says 'ready'")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title("When is a model ready? GreenLight's green light vs a standard sample-size rule (23 outbreaks)")
    fig.tight_layout()
    save(fig, "fig4_readiness")


def fig_synthetic():
    s = pd.read_csv(Path("results", "exp16_synth_baselines_summary.csv"))
    gens = [("OS", "GreenLight synthetic"), ("arf", "ARF"), ("real", "Real records GreenLight had"), ("tvae", "TVAE"),
            ("bootstrap", "Bootstrap resample"), ("bayesian_network", "Bayesian network"), ("ctgan", "CTGAN")]
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for i, (g, name) in enumerate(gens):
        x = s[g].to_numpy()
        ax.scatter(x, i + rng.uniform(-0.18, 0.18, len(x)), s=14, color=C1, alpha=0.35, edgecolor="none", zorder=2)
        bs = x[rng.integers(0, len(x), (2000, len(x)))].mean(1)
        lo, hi = np.quantile(bs, [0.025, 0.975])
        ax.plot([lo, hi], [i, i], color=INK, lw=2, zorder=3)
        ax.scatter([x.mean()], [i], s=46, color=INK, edgecolor=SURF, linewidth=1.5, zorder=4)
        ax.text(1.01, i, f"mean {x.mean():.3f}  [{lo:.3f}, {hi:.3f}]", va="center", fontsize=7.5, color=INK2,
                transform=ax.get_yaxis_transform(), clip_on=False)
    ax.set_yticks(range(len(gens)), [n for _, n in gens])
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("AUC on later real patients of a model trained on the data set (22 outbreaks)")
    ax.set_title("Synthetic data on the green-light day: each dot an outbreak; black = mean with 95% interval")
    fig.tight_layout()
    save(fig, "fig5_synthetic_generators")


def fig_timing():
    """Share of the outcomes the first replays used that were actually known on that day (COVID-19 Brazil 2020)."""
    lib = pd.read_parquet(LIB, columns=["outbreak", "DT_DIGITA", "DT_KNOWN", TARGET])
    d = lib[lib.outbreak == "covid_2020"]
    osr = json.loads(Path("results", f"{FINAL_CFG['os_run']}.json").read_text())["outbreaks"]["covid_2020"]
    t0 = pd.Timestamp(osr["info"]["day0"])
    ent = (d.DT_DIGITA - t0).dt.days.to_numpy()
    kn = (d.DT_KNOWN - t0).dt.days.to_numpy()
    y = d[TARGET].to_numpy().astype(bool)
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for mask, color, name, dy in [(np.ones(len(d), bool), C1, "All patients", -0.06), (y, C2, "Patients who died", 0.11)]:
        days = [x for x in range(0, 91) if (mask & (ent <= x)).sum() >= 20]
        share = [(mask & (ent <= x) & (kn <= x)).sum() / (mask & (ent <= x)).sum() for x in days]
        ax.plot(days, share, color=color, label=name)
        i = days.index(28)
        ax.scatter([28], [share[i]], s=36, color=color, edgecolor=SURF, linewidth=1.5, zorder=3)
        ax.text(29.5, share[i] + dy, f"day 28: {share[i]:.0%}", fontsize=7.5, color=INK2, va="center")
    ax.set_ylim(0, 1)
    ax.set_xlim(0, 90)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_xlabel("Day of the outbreak (lines start once 20 records are in)")
    ax.set_ylabel("Outcome known by that day")
    ax.legend(loc="lower right")
    ax.set_title("COVID-19 Brazil 2020: share of outcomes the first replays used that were actually known that day")
    fig.tight_layout()
    save(fig, "fig6_outcome_timing")


def fig_patient_ci():
    p = Path("results", "ci_summary.json")
    if not p.exists():
        print("skip fig7: results/ci_summary.json missing (run analyse_ci)")
        return
    rows = pd.DataFrame(json.loads(p.read_text())["patient_level"]["per_outbreak"])
    rows = rows.iloc[sorted(range(len(rows)), key=lambda i: (family(rows.outbreak[i]) != "covid", rows.outbreak[i]))]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    y = np.arange(len(rows))
    for off, col, color, name in [(-0.15, "gold", INK2, "Gold (best possible, hindsight)"), (0.0, "os", C1, "GreenLight on its green-light day"),
                                  (0.15, "real", C2, "Real data alone, same day")]:
        x = rows[f"auc_{col}"].to_numpy()
        ci = np.array(rows[f"auc_{col}_ci"].tolist())
        ax.errorbar(x, y + off, xerr=[x - ci[:, 0], ci[:, 1] - x], fmt="o", ms=4.5, color=color, elinewidth=1.4,
                    capsize=0, mec=SURF, mew=1.2, label=name)
    ax.set_yticks(y, [f"{o.replace('othervirus', 'other virus').replace('_', ' ')} (day {g})" for o, g in zip(rows.outbreak, rows.green_day)])
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("AUC on later patients, with 95% bootstrap interval over test patients")
    fig.tight_layout()
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=3, fontsize=8, bbox_to_anchor=(0.55, 1.04))
    fig.suptitle("On the green-light day, GreenLight is close to the best possible model", x=0.01, ha="left", y=1.09,
                 fontsize=12, weight="bold")
    save(fig, "fig7_green_day_ci")


def main():
    fig_replay()
    fig_votes()
    fig_baselines()
    fig_readiness()
    fig_synthetic()
    fig_timing()
    fig_patient_ci()


if __name__ == "__main__":
    main()
