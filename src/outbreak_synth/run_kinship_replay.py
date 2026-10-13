"""Time Machine Replay of the Kinship Vote and Stranger Flag over every outbreak in the Atlas.

For each target outbreak (fob) with at least one earlier outbreak in the Atlas:
  * kin candidates = earlier outbreaks, using only their records entered before fob's day 0;
  * every week, score fob's new records with each candidate (profile + severity) and with the Stranger;
  * hindsight answer = the kin that fits fob's FULL record set best (per patient), and the novelty gap
    = how much better fob's own model fits than that best kin (cross-validated).
Outputs results/<name>.json and a per-week table results/<name>_weeks.csv.
Usage: PYTHONPATH=src python -m outbreak_synth.run_kinship_replay experiments/exp05_kinship_replay.toml"""
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

from .kinship import (KIN_FIELDS, Profile, bernoulli_logpmf, encode, fit_offset, fit_risk, risk_logit, votes_from_scores)
from .library import OUT as LIB, TARGET


KNOWN_COL = {"known": "DT_KNOWN", "closure": "DT_KNOWN_CLOSE"}


def known_days(df, t0, timing):
    """Days from t0 until each record's outcome is usable. timing='entry' reproduces Exp. 2-13 (outcome usable
    as soon as the record is entered); 'known'/'closure' use the dates added in Exp. 14 (NaN = never usable)."""
    col = "DT_DIGITA" if timing == "entry" else KNOWN_COL[timing]
    return (df[col] - t0).dt.days.to_numpy(dtype=float)


def day0_of(df, name, mode="jan1", threshold=20):
    """Day 0 of an outbreak.
    jan1      - first record, but not before 1 January of the outbreak's year (Exp. 5/6).
    threshold - for yearly seasons (flu_*, othervirus_*): the first week with at least `threshold` new
                records, counted from the jan1 day 0 (knowable in real time). COVID and H1N1 keep their
                first record, which is a real outbreak start."""
    year = int(name.split("_")[-1])
    t0 = max(df.DT_DIGITA.min(), pd.Timestamp(f"{year}-01-01"))
    if mode == "threshold" and name.split("_")[0] in ("flu", "othervirus"):
        wk = ((df.DT_DIGITA[df.DT_DIGITA >= t0] - t0).dt.days // 7).value_counts().sort_index()
        hit = wk[wk >= threshold]
        if len(hit):
            t0 = t0 + pd.Timedelta(weeks=int(hit.index[0]))
    return t0


def fob_fields(fob_df):
    """KIN_FIELDS that fob's form collects (known on day 0 from the form; here: < 90% missing). Comparing a field
    fob never records would make every relative look unlike fob for reasons of form, not disease. Every Brazilian
    form collects all KIN_FIELDS, so Brazil replays are unchanged."""
    return [f for f in KIN_FIELDS if (fob_df[f] == "missing").mean() < 0.9]


def kin_models(lib, starts, fob, cfg, fields=None):
    t0 = starts[fob]
    kins = {}
    present_day = cfg.get("present_day_atlas", False)
    for k, kd in lib.groupby("outbreak"):
        if k == fob:
            continue
        # Time-respecting (default): only outbreaks that started before fob, with records entered before fob's
        # day 0. Present-day Atlas (Exp. 13b): every other outbreak in full ("if this pathogen appeared today").
        if not present_day:
            if starts[k] >= t0:
                continue
            kd = kd[kd.DT_DIGITA < t0]
            if cfg.get("outcome_timing", "entry") != "entry":  # only outcomes already known on fob's day 0
                kd = kd[kd[KNOWN_COL[cfg["outcome_timing"]]] < t0]
        if len(kd) < cfg["min_kin_rows"] or kd[TARGET].sum() < cfg["min_kin_deaths"]:
            continue
        if len(kd) > cfg["max_fit_rows"]:
            kd = kd.sample(cfg["max_fit_rows"], random_state=0)
        age, sex, yes, X = encode(kd, fields)
        kins[k] = (Profile().fit(age, sex, yes), fit_risk(X, kd[TARGET].to_numpy(), C=1.0), len(kd))
    return kins


def hindsight(fob_df, kins, cfg, fields=None):
    """Per-patient fit of each kin on fob's full data, and fob's own cross-validated fit (novelty gap)."""
    d = fob_df.sample(min(len(fob_df), cfg["max_fit_rows"]), random_state=0)
    age, sex, yes, X = encode(d, fields)
    y = d[TARGET].to_numpy()
    per = {}
    for k, (prof, risk, _) in kins.items():
        base = risk_logit(risk, X)
        b = fit_offset(base, y)
        per[k] = {"profile": float(prof.logpdf(age, sex, yes).mean()),
                  "severity": float(bernoulli_logpmf(base + b, y).mean())}
        per[k]["total"] = per[k]["profile"] + per[k]["severity"]
    own_p, own_s = [], []
    for tr, te in KFold(5, shuffle=True, random_state=0).split(X):
        own_p.append(Profile().fit(age[tr], sex[tr], yes[tr]).logpdf(age[te], sex[te], yes[te]))
        own_s.append(bernoulli_logpmf(risk_logit(fit_risk(X[tr], y[tr], C=cfg["own_C"]), X[te]), y[te]))
    own = {"profile": float(np.concatenate(own_p).mean()), "severity": float(np.concatenate(own_s).mean())}
    own["total"] = own["profile"] + own["severity"]
    return per, own


def replay(fob_df, kins, cfg, fields=None):
    t0 = fob_df.DT_DIGITA.min()
    week = ((fob_df.DT_DIGITA - t0).dt.days // 7).to_numpy()
    # Severity is scored when an outcome becomes usable (same as entry week under the old timing).
    kweek = np.floor(known_days(fob_df, t0, cfg.get("outcome_timing", "entry")) / 7)
    age, sex, yes, X = encode(fob_df, fields)
    y = fob_df[TARGET].to_numpy()
    base = {k: risk_logit(r, X) for k, (_, r, _) in kins.items()}
    prof_ll = {k: p.logpdf(age, sex, yes) for k, (p, _, _) in kins.items()}
    names = list(kins) + ["STRANGER"]
    cum = {part: dict.fromkeys(names, 0.0) for part in ("profile", "severity")}
    rows = []
    for w in range(cfg["weeks"]):
        past, now = week < w, week == w            # patient mix: by entry week
        pastk, nowk = kweek < w, kweek == w         # who dies: by the week the outcome became usable
        if not now.any() and not nowk.any():
            continue
        yp = y[pastk]
        for k in kins:
            b = fit_offset(base[k][pastk], yp)
            cum["profile"][k] += prof_ll[k][now].sum()
            cum["severity"][k] += bernoulli_logpmf(base[k][nowk] + b, y[nowk]).sum()
        # Stranger: fob's own earlier records only (flat start when there are none).
        own_prof = Profile().fit(age[past], sex[past], yes[past])
        cum["profile"]["STRANGER"] += own_prof.logpdf(age[now], sex[now], yes[now]).sum()
        own_risk = fit_risk(X[pastk], yp, C=cfg["own_C"]) if pastk.sum() >= cfg["own_min_rows"] else None
        if own_risk is not None:
            lg = risk_logit(own_risk, X[nowk])
        else:  # base rate with a weak prior
            r = (yp.sum() + 1) / (len(yp) + 2)
            lg = np.full(nowk.sum(), np.log(r / (1 - r)))
        cum["severity"]["STRANGER"] += bernoulli_logpmf(lg, y[nowk]).sum()
        total = {n: cum["profile"][n] + cum["severity"][n] for n in names}
        rows.append({"week": w, "n_so_far": int((week <= w).sum()), "deaths_so_far": int(y[kweek <= w].sum()),
                     "outcomes_known_so_far": int((kweek <= w).sum()),
                     **{f"score_total::{n}": total[n] for n in names},
                     **{f"score_profile::{n}": cum["profile"][n] for n in names},
                     **{f"score_severity::{n}": cum["severity"][n] for n in names}})
    return rows


def main(cfg_path):
    cfg = tomllib.loads(Path(cfg_path).read_text())
    lib = pd.read_parquet(LIB)
    starts = {}
    parts = {}
    for name, d in lib.groupby("outbreak"):
        t0 = day0_of(d, name, cfg.get("day0_mode", "jan1"), cfg.get("season_threshold", 20))
        parts[name] = d[d.DT_DIGITA >= t0].sort_values(["DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable")
        starts[name] = t0
    out, week_rows = {}, []
    for fob in sorted(parts, key=lambda n: starts[n]):
        if cfg.get("only") and fob not in cfg["only"]:
            continue
        fields = fob_fields(parts[fob])
        kins = kin_models(lib, starts, fob, cfg, fields)
        if not kins:
            print(f"{fob}: no earlier outbreak in the Atlas, skipped", flush=True)
            continue
        fob_df = parts[fob]
        horizon = fob_df[fob_df.DT_DIGITA < starts[fob] + pd.Timedelta(weeks=cfg["weeks"])]
        per, own = hindsight(fob_df, kins, cfg, fields)
        best = max(per, key=lambda k: per[k]["total"])
        rows = replay(horizon, kins, cfg, fields)
        for r in rows:
            r["fob"] = fob
        week_rows += rows
        out[fob] = {"day0": str(starts[fob].date()), "n_total": len(fob_df), "fields": fields, "kin": {k: v[2] for k, v in kins.items()},
                    "hindsight_per_patient": per, "own_cv_per_patient": own, "hindsight_best_kin": best,
                    "novelty_gap": own["total"] - per[best]["total"]}
        print(f"{fob}: {len(kins)} kin, hindsight best = {best}, novelty gap = {out[fob]['novelty_gap']:.3f} nats/patient",
              flush=True)
    Path("results", f"{cfg['name']}.json").write_text(json.dumps(out, indent=2))
    pd.DataFrame(week_rows).to_csv(Path("results", f"{cfg['name']}_weeks.csv"), index=False)


if __name__ == "__main__":
    main(sys.argv[1])
