"""Glass Box Report: a readable HTML page explaining what OS knows and decides for an outbreak on a given day.
Everything above the "Replay check" section is information OS would have live on that day.
Usage: PYTHONPATH=src python -m outbreak_synth.glass_box covid_2020 [day ...]   (no day = Green Light day)
Writes reports/glass_box_<outbreak>_day<d>.html"""
import html
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .library import OUT as LIB, TARGET, YESNO
from .os_core import FINAL_CFG, build_state, risk

GM, GS = FINAL_CFG.get("green_m", 20), FINAL_CFG.get("green_s", 0.98)
from .recipe import design, fit_map
from .synth import band, generate_chain, LO, HI

LABELS = {"FEBRE": "fever", "TOSSE": "cough", "GARGANTA": "sore throat", "DISPNEIA": "shortness of breath",
          "DESC_RESP": "respiratory distress", "SATURACAO": "low oxygen saturation", "CARDIOPATI": "heart disease",
          "PNEUMOPATI": "chronic lung disease", "RENAL": "kidney disease", "IMUNODEPRE": "immunosuppression",
          "METABOLIC": "diabetes / metabolic", "HEPATICA": "liver disease", "NEUROLOGIC": "neurological disease",
          "OBESIDADE": "obesity", "PUERPERA": "postpartum", "SIND_DOWN": "Down syndrome"}
AGE_NAMES = ["<1", "1–4", "5–14", "15–29", "30–44", "45–59", "60–74", "75+"]
RACE = {"1": "white", "2": "black", "3": "asian", "4": "mixed (parda)", "5": "indigenous"}


def nice(col):
    if col.startswith("age_band_"):
        return f"age {AGE_NAMES[int(col.split('_')[-1])]} (vs under 1)"
    if col.startswith("sex_"):
        return {"sex_M": "male (vs sex not recorded)", "sex_F": "female (vs sex not recorded)"}[col]
    if col.startswith("race_"):
        return f"race: {RACE[col.split('_')[1]]} (vs not recorded)"
    if col.startswith("state_"):
        return f"state {col.split('_')[1]} (vs RO)"
    if col == "age_trend_per_20y":
        return "each 20 years of age"
    return LABELS.get(col.replace("_yes", ""), col)


def css():
    return """<style>
:root{--bg:#ffffff;--fg:#1f2328;--muted:#57606a;--line:#d0d7de;--soft:#f3f6f8;--ok:#1a7f37;--warn:#9a6700;--bad:#cf222e;--accent:#0b6e4f}
@media (prefers-color-scheme: dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#9da7b3;--line:#30363d;--soft:#161b22;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--accent:#3fb98a}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:24px 16px}
main{max-width:980px;margin:0 auto} h1{font-size:24px;margin:0 0 4px} h2{font-size:18px;margin:28px 0 8px;color:var(--accent)}
.sub{color:var(--muted);margin:0 0 16px} .pill{display:inline-block;padding:2px 10px;border-radius:999px;font-weight:600;font-size:13px}
.green{background:color-mix(in srgb,var(--ok) 18%,transparent);color:var(--ok)} .amber{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}
.card{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:8px 0}
table{border-collapse:collapse;width:100%;margin:6px 0 4px;font-size:14px} th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600} td.n{text-align:right;font-variant-numeric:tabular-nums} .scroll{overflow-x:auto}
.bar{display:inline-block;height:9px;background:var(--accent);border-radius:3px;vertical-align:middle} .muted{color:var(--muted)} details{margin:6px 0}
.note{font-size:13px;color:var(--muted)}
</style>"""


def table(df, num_cols=()):
    h = "<div class='scroll'><table><tr>" + "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns) + "</tr>"
    for _, r in df.iterrows():
        h += "<tr>" + "".join(f"<td class='{'n' if c in num_cols else ''}'>{r[c] if isinstance(r[c], str) and r[c].startswith('<') else html.escape(str(r[c]))}</td>" for c in df.columns) + "</tr>"
    return h + "</table></div>"


def report(fob, day=None, lib=None):
    lib = pd.read_parquet(LIB) if lib is None else lib
    s = build_state(fob, day, cfg=FINAL_CFG, lib=lib)
    rec, y = s.known, s.known[TARGET].to_numpy()  # outcomes OS could see on that day
    date = (s.t0 + pd.Timedelta(days=s.day)).date()
    p = s.path.set_index("day")
    row = p.loc[p.index[p.index <= s.day][-1]]
    green = s.green_now
    status = (f"<span class='pill green'>GREEN LIGHT</span> since day {s.green_day}" if green else
              "<span class='pill amber'>NOT YET</span>")
    out = [f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>Glass Box: {fob}</title>{css()}</head><body><main>",
           f"<h1>Glass Box Report: {fob.replace('_', ' ')}</h1>",
           f"<p class='sub'>Day {s.day} of the outbreak ({date}; day 0 = {s.t0.date()}). GreenLight has seen {len(s.records):,} real "
           f"hospitalised patients; {len(rec):,} of them have a known outcome so far, with {int(y.sum()):,} deaths ({y.mean():.1%}). "
           f"GreenLight v1.</p>",
           f"<div class='card'>{status}<br>"]
    reasons = [f"deaths with a known outcome so far: {int(y.sum())} (needs at least {GM}) {'✓' if y.sum() >= GM else '✗'}",
               f"stability of the risk ranking vs 8 days earlier: {row.stability:.3f} (needs at least {GS} on two checks in a row) "
               f"{'✓' if pd.notna(row.stability) and row.stability >= GS else '✗'}" if pd.notna(row.stability) else
               "stability: not yet measurable (needs 8 days of history)",
               f"recipe in use: {'age-trend fallback (GreenLight does not yet trust what it borrowed)' if s.recipe == 'age_trend' else 'borrow from voted relatives'} "
               f"{'✗' if s.recipe == 'age_trend' else '✓'}"]
    out.append("<br>".join(html.escape(r).replace("✓", "<b style='color:var(--ok)'>✓</b>").replace("✗", "<b style='color:var(--bad)'>✗</b>") for r in reasons) + "</div>")

    # Kinship Vote
    v = sorted(s.votes.items(), key=lambda kv: -kv[1])[:6]
    kv = pd.DataFrame({"past outbreak": [k.replace("_", " ") for k, _ in v],
                       "share of the vote (among past outbreaks)": [f"<span class='bar' style='width:{max(2, int(140 * w))}px'></span> {w:.1%}" for _, w in v]})
    out += ["<h2>1. Kinship Vote: what is this outbreak related to?</h2>",
            f"<p>Each past outbreak in the Atlas predicted this outbreak's patients before seeing them; better predictions earn more votes. "
            f"<b>Stranger share: {s.stranger:.0%}</b>: the weight given to 'none of the above, learn from this outbreak alone'. "
            f"Borrowing strength is reduced by the same share.</p>", table(kv),
            f"<p class='note'>{'The pathogen group has no earlier member in the Atlas (lab label), so GreenLight starts on the age-trend fallback until 20 deaths have been scored on fresh data.' if s.new_group else 'The pathogen group has earlier members in the Atlas, so no label fallback applies.'}</p>"]

    # Risk table
    out.append("<h2>2. What GreenLight believes drives the risk of death</h2>")
    if s.recipe == "age_trend":
        out.append(f"<p>On the fallback GreenLight uses age only. Each 20 years of age multiplies the odds of death by "
                   f"<b>{np.exp(s.coef[0]):.2f}</b> (95% interval {np.exp(s.coef[0] - 1.96 * s.se[0]):.2f}–{np.exp(s.coef[0] + 1.96 * s.se[0]):.2f}); "
                   f"relatives suggested {np.exp(s.prior_mu[0]):.2f}.</p>")
    else:
        Xr, meta = design(rec)
        r0, rc = fit_map(Xr, y, lam=1.0)
        rows = []
        for j, (col, fld, borrowable) in enumerate(s.meta):
            if fld == "SG_UF_NOT":
                continue
            rows.append({"factor": nice(col),
                         "GreenLight odds ratio (95% interval)": f"{np.exp(s.coef[j]):.2f} ({np.exp(s.coef[j] - 1.96 * s.se[j]):.2f}–{np.exp(s.coef[j] + 1.96 * s.se[j]):.2f})",
                         "relatives said": f"{np.exp(s.prior_mu[j]):.2f}" if borrowable and s.prior_mu[j] != 0 else "—",
                         "this outbreak alone": f"{np.exp(rc[j]):.2f}",
                         "still borrowed": f"{s.borrowed_share[j]:.0%}",
                         "patients with it": f"{(Xr[:, j] > 0).sum():,}"})
        out += ["<p>Odds ratios above 1 raise the risk of death, below 1 lower it. 'Still borrowed' is how much of the estimate comes from "
                "the relatives rather than this outbreak's own patients (it falls as data arrive: the Handover Rule). "
                "The overall death rate and geography are never borrowed. Every factor is also gently pulled towards 'no effect' so that rare "
                "groups (e.g. 18 patients with Down syndrome) cannot produce extreme numbers; that pull is not borrowing.</p>",
                table(pd.DataFrame(rows), num_cols=("still borrowed", "patients with it")),
                "<p class='note'>Intervals are approximate (Laplace). Coefficients are adjusted for each other; they are associations in "
                "hospitalised patients, not causes. State effects are estimated but not shown.</p>"]

    # Recent evidence (live-knowable)
    hist = p.loc[p.index <= s.day].tail(8).reset_index()
    ev = pd.DataFrame({"day": hist.day, "patients": hist.n.map("{:,}".format), "deaths": hist.deaths.map("{:,}".format),
                       "deaths scored on fresh weeks": hist.fresh_deaths.astype(int),
                       "fresh-week AUC of recipe in use": [f"{r[f'fresh_auc_{r.chosen}']:.3f}" if pd.notna(r[f"fresh_auc_{r.chosen}"]) else "—" for _, r in hist.iterrows()],
                       "stability": hist.stability.map(lambda x: "—" if pd.isna(x) else f"{x:.3f}"), "recipe": hist.chosen})
    out += ["<h2>3. Recent evidence GreenLight can see</h2>",
            "<p>'Fresh-week AUC' scores the recipe on each week's patients using a model fitted only on earlier weeks.</p>", table(ev)]

    # Synthetic release
    out.append("<h2>4. Synth Release</h2>")
    if not green:
        out.append("<p><b>Not released.</b> GreenLight releases synthetic data only after the green light.</p>")
    else:
        syn = generate_chain(s, 20000, seed=0)
        rb, sb = band(rec.age.fillna(rec.age.median())), band(syn.age)
        rows = [{"measure": "patients", "real (seen by GreenLight)": f"{len(rec):,}", "synthetic": f"{len(syn):,}"},
                {"measure": "median age", "real (seen by GreenLight)": f"{rec.age.median():.0f}", "synthetic": f"{syn.age.median():.0f}"},
                {"measure": "death rate", "real (seen by GreenLight)": f"{y.mean():.1%}", "synthetic": f"{syn[TARGET].mean():.1%}"}]
        for k in range(len(AGE_NAMES)):
            if (rb == k).mean() >= 0.02:
                rows.append({"measure": f"death rate, age {AGE_NAMES[k]}", "real (seen by GreenLight)": f"{y[rb == k].mean():.1%} (n={int((rb == k).sum()):,})",
                             "synthetic": f"{syn[TARGET][sb == k].mean():.1%}"})
        for f in YESNO:
            if (rec[f] == "missing").mean() < 0.9:
                rows.append({"measure": f"{LABELS[f]} recorded", "real (seen by GreenLight)": f"{(rec[f] == 'yes').mean():.1%}", "synthetic": f"{(syn[f] == 'yes').mean():.1%}"})
        out += [f"<p>Released: synthetic patients drawn from GreenLight's Two-Part Recipe. Every row is labelled <code>synthetic=True</code> with this "
                f"provenance: <i>{html.escape(syn.synth_source.iloc[0])}</i></p>", table(pd.DataFrame(rows)),
                "<p class='note'>Symptoms and conditions are drawn as a dependency chain (each given age band, sex and the fields drawn before it), "
                "which keeps links such as shortness of breath with low oxygen (Exp. 10).</p>"]

    # Replay check (hindsight)
    info = __import__("json").loads(Path("results", f"{FINAL_CFG['os_run']}.json").read_text())["outbreaks"][fob]["info"]
    lo, hi = info["test_days"]
    dd = (s.later.DT_DIGITA - s.t0).dt.days
    test = s.later[(dd >= lo) & (dd <= hi)]
    if len(test) and test[TARGET].nunique() == 2:
        out += ["<h2>Replay check (hindsight, not available live)</h2>",
                f"<p class='note'>Scored on {len(test):,} later real patients entered on days {lo}–{hi}, which GreenLight had not seen. "
                f"GreenLight today: AUC <b>{roc_auc_score(test[TARGET], risk(s, test)):.3f}</b>. Ranking by age alone: {info['age_only_auc']:.3f}. "
                f"Best possible (gold, trained on all other records of this outbreak): {info['gold_auc']:.3f}.</p>"]
    out.append("<p class='note'>Data: SIVEP-Gripe SRAG, Ministério da Saúde (Brazil), CC-BY. Generated by outbreak-synth.</p></main></body></html>")
    dst = Path("reports") / f"glass_box_{fob}_day{s.day}.html"
    dst.parent.mkdir(exist_ok=True)
    dst.write_text("\n".join(out))
    return dst


if __name__ == "__main__":
    lib = pd.read_parquet(LIB)
    fob = sys.argv[1]
    days = [int(x) for x in sys.argv[2:]] or [None]
    for d in days:
        print(report(fob, d, lib))
