"""Diagnose why OS got worse over time on flu 2013 and other virus 2013 (Step 2).
Usage: PYTHONPATH=src python scripts/diag_2013_decline.py"""
import json, numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from outbreak_synth.library import OUT as LIB, TARGET
from outbreak_synth.recipe import design, fit_map, kin_prior, collected_fields
from outbreak_synth.run_kinship_replay import day0_of
from outbreak_synth.run_recipe_replay import weekly_votes
pd.set_option("display.width", 220)
lib = pd.read_parquet(LIB); weeks = pd.read_csv("results/exp05_kinship_replay_weeks.csv")
meta5 = json.load(open("results/exp05_kinship_replay.json")); ana = json.load(open("results/exp05_kinship_replay_analysis.json"))
for fob in ["flu_2013", "othervirus_2013"]:
    d = lib[lib.outbreak == fob]; t0 = day0_of(d, fob)
    d = d[d.DT_DIGITA >= t0].sort_values(["DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable")
    day = (d.DT_DIGITA - t0).dt.days.to_numpy(); X, meta = design(d); y = d[TARGET].to_numpy()
    te = (day >= 91) & (day <= 182); Xt, yt = X[te], y[te]
    kin = list(meta5[fob]["kin"]); tau = float(ana["tau_chosen"][fob]); votes = weekly_votes(weeks, fob, kin, tau)
    kc, kf = {}, {}
    for k in kin:
        kd = lib[(lib.outbreak == k) & (lib.DT_DIGITA < t0)]; Xk, _ = design(kd)
        kc[k] = fit_map(Xk, kd[TARGET].to_numpy())[1]; kf[k] = collected_fields(kd)
    state = np.array([m[1] == "SG_UF_NOT" for m in meta]); names = [m[0] for m in meta]
    print(f"\n===== {fob}: kin {kin}; test {te.sum()} pts, {yt.sum()} deaths; age-only {roc_auc_score(yt, d.age[te].fillna(40)):.3f}")
    early = d[day <= 90]; test = d[te]
    print("top states, days 0-90:", early.SG_UF_NOT.value_counts(normalize=True).head(4).round(2).to_dict())
    print("top states, test     :", test.SG_UF_NOT.value_counts(normalize=True).head(4).round(2).to_dict())
    print("median age days 0-90 / test:", early.age.median(), test.age.median(), "| death rate:", round(early.death.mean(), 3), round(test.death.mean(), 3))
    rows = []
    for dd in [0, 6, 12, 18, 30, 48, 72, 90]:
        tr = day <= dd; Xtr, ytr = X[tr], y[tr]
        wk = dd // 7 - 1
        past, stranger = votes[wk] if wk in votes else ({k: 1 / len(kin) for k in kin}, 1 / (len(kin) + 1))
        mu, have = kin_prior(kc, kf, past, meta)
        def run(lam_b, lam_free, drop_state=False):
            lam = np.where(have, lam_b, lam_free); cols = ~state if drop_state else np.ones(len(meta), bool)
            if len(ytr) == 0: return roc_auc_score(yt, Xt[:, cols] @ mu[cols])
            c0, c = fit_map(Xtr[:, cols], ytr, mu=mu[cols], lam=lam[cols]); return roc_auc_score(yt, c0 + Xt[:, cols] @ c)
        r = {"day": dd, "n": int(tr.sum()), "deaths": int(ytr.sum()), "stranger": round(stranger, 2),
             "current": run(10 * (1 - stranger), 1.0),
             "prior_only": roc_auc_score(yt, Xt @ mu),
             "no_stranger_cut": run(10, 1.0),
             "free_cols_lam10": run(10 * (1 - stranger), 10.0),
             "drop_state": run(10 * (1 - stranger), 1.0, drop_state=True),
             "drop_state+free10": run(10 * (1 - stranger), 10.0, drop_state=True)}
        rows.append(r)
        if dd == 18:
            c0, c = fit_map(Xtr, ytr, mu=mu, lam=np.where(have, 10 * (1 - stranger), 1.0))
            moved = pd.Series(c - mu, index=names); print("day 18: biggest moves away from the borrowed prior:", moved.abs().sort_values(ascending=False).head(6).index.tolist(),
                  moved.loc[moved.abs().sort_values(ascending=False).head(6).index].round(2).tolist())
            print("day 18 deaths: states", d[tr & (y == 1)].SG_UF_NOT.tolist(), "ages", d[tr & (y == 1)].age.round(0).tolist())
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print("borrowed prior (H1N1) age-band coefficients:", dict(zip([n for n in names if n.startswith("age")], mu[:7].round(2))))
