"""OS (Outbreak Synth) final rule as one reusable piece: rebuild OS's full state for an outbreak on any day.

Rule (Step 3, Exp. 8): Severity Model = kin borrowing (vote-weighted relatives, strength lam0 * (1 - Stranger),
intercept and geography never borrowed); if fob's pathogen group has no earlier member in the Atlas, use the
age_trend recipe until `fallback_deaths` fresh deaths. Green Light: >= 20 deaths and stability >= 0.98 on two
checks in a row, not on the fallback (computed from the logged replay, results/exp08_os_replay.json).
The state includes a Laplace approximation of uncertainty and, per factor, how much of it is still borrowed.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

from .analyse_os2 import final_paths
from .library import OUT as LIB, TARGET, YESNO
from .recipe import collected_fields, design, fit_map, kin_prior
from .run_kinship_replay import KNOWN_COL, day0_of, known_days
from .run_recipe_replay import weekly_votes
from .run_os_replay2 import age_x

CFG = {"lam0": 10.0, "day0_mode": "threshold", "season_threshold": 20, "max_fit_rows": 100000,
       "kinship_run": "exp05b_kinship_replay", "os_run": "exp08_os_replay", "fallback_deaths": 20,
       # Minimum shrinkage even when the Stranger has the whole vote (lam0 * (1 - 1) = 0). Without it, rare
       # age bands and near-collinear columns get unbounded coefficients (e.g. -18.9, SE 4,597 for ages 1-4 in
       # COVID 2020), which ranking tolerates but a generator does not. 1.0 = the real-only ridge strength.
       "lam_floor": 1.0,
       "vote_prior": "outbreak", "kinship_analysis": None}
# OS as currently adopted (2026-10-07): Kinship Vote starts equal per pathogen group (Exp. 5c / 8c). CFG above
# keeps the settings behind Exp. 9, 10 and 12 so they still reproduce.
FINAL_CFG_ENTRY_TIMING = {**CFG, "os_run": "exp08c_os_replay_groupprior", "kinship_analysis": "exp05c_kinship_groupprior",
                          "vote_prior": "group"}
# Adopted 2026-10-07 (Exp. 14): outcomes usable only once known (DT_KNOWN). Replaces the entry-timing settings above.
FINAL_CFG = {**CFG, "os_run": "exp08d_os_replay_known", "kinship_run": "exp05d_kinship_known",
             "kinship_analysis": "exp05d_kinship_known", "vote_prior": "group", "outcome_timing": "known",
             "green_m": 10, "green_s": 0.99}  # Green Light re-chosen leave-one-outbreak-out on Exp. 8d
from .library import family as fam


@dataclass
class OSState:
    fob: str
    day: int
    t0: pd.Timestamp
    records: pd.DataFrame          # fob's records entered up to `day` (patient mix)
    later: pd.DataFrame            # fob's records entered after `day` (never seen by OS on that day)
    recipe: str                    # "kin" or "age_trend"
    votes: dict                    # past outbreak -> share (among past outbreaks)
    stranger: float
    new_group: bool
    intercept: float
    coef: np.ndarray
    se: np.ndarray                 # Laplace standard errors (coefficients)
    prior_mu: np.ndarray
    borrowed_share: np.ndarray     # prior precision / posterior precision, per coefficient
    meta: list                     # (column name, field, borrowable)
    green_day: int | None
    green_now: bool
    path: pd.DataFrame = field(repr=False, default=None)
    kin_profiles: dict = field(repr=False, default_factory=dict)
    known: pd.DataFrame = field(repr=False, default=None)  # records whose outcome was usable by `day` (who dies)


def _laplace(M, y, c0, c, lam):
    p = expit(c0 + M @ c)
    w = p * (1 - p)
    Z = np.column_stack([np.ones(len(M)), M])
    H = (Z * w[:, None]).T @ Z
    H[1:, 1:] += np.diag(lam)
    H[0, 0] += 1 / 100.0
    cov = np.linalg.pinv(H)
    data_prec = np.diag(H)[1:] - lam
    return np.sqrt(np.clip(np.diag(cov)[1:], 0, None)), lam / (lam + np.clip(data_prec, 0, None))


def build_state(fob, day=None, cfg=CFG, lib=None):
    """OS state for `fob` on `day` (default: its Green Light day)."""
    lib = pd.read_parquet(LIB) if lib is None else lib
    paths = final_paths(cfg["os_run"], E=cfg["fallback_deaths"], m=cfg.get("green_m", 20), s=cfg.get("green_s", 0.98))
    path, gday, new_group = paths[fob]
    day = gday if day is None else day
    if day is None:
        raise ValueError(f"{fob} never got a Green Light; pass a day explicitly")
    meta5 = json.loads(Path("results", f"{cfg['kinship_run']}.json").read_text())
    ana = json.loads(Path("results", f"{cfg.get('kinship_analysis') or cfg['kinship_run']}_analysis.json").read_text())
    weeks = pd.read_csv(Path("results", f"{cfg['kinship_run']}_weeks.csv"))
    kin_list = list(meta5[fob]["kin"])
    d = lib[lib.outbreak == fob]
    t0 = day0_of(d, fob, cfg["day0_mode"], cfg["season_threshold"])
    d = d[d.DT_DIGITA >= t0].sort_values(["DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable")
    dd = (d.DT_DIGITA - t0).dt.days.to_numpy()
    rec, later = d[dd <= day], d[dd > day]
    timing = cfg.get("outcome_timing", "entry")
    kd_ = np.nan_to_num(known_days(rec, t0, timing), nan=np.inf)
    known = rec[kd_ <= day]
    X, meta = design(known)
    y = known[TARGET].to_numpy()
    lam0 = cfg["lam0"]

    kin_coefs, kin_fields, kin_slope, kin_prof = {}, {}, [], {}
    for k in kin_list:
        kd = lib[(lib.outbreak == k) & (lib.DT_DIGITA < t0)]
        if timing != "entry":
            kd = kd[kd[KNOWN_COL[timing]] < t0]
        if len(kd) > cfg["max_fit_rows"]:
            kd = kd.sample(cfg["max_fit_rows"], random_state=0)
        Xk, _ = design(kd)
        kin_coefs[k] = fit_map(Xk, kd[TARGET].to_numpy())[1]
        kin_fields[k] = collected_fields(kd)
        kin_slope.append(fit_map(age_x(kd, 50.0), kd[TARGET].to_numpy())[1][0])
        kin_prof[k] = kd  # used by the profile generator (synth.py)
    wk = day // 7 - 1
    votes_all = weekly_votes(weeks, fob, kin_list, float(ana["tau_chosen"][fob]), cfg.get("vote_prior", "outbreak"))
    past, stranger = votes_all[wk] if wk in votes_all else ({k: 1 / len(kin_list) for k in kin_list}, 1 / (len(kin_list) + 1))
    recipe = path.loc[path.day <= day, "chosen"].iloc[-1]

    if recipe == "age_trend":
        M, mu, lam = age_x(known, 50.0), np.array([float(np.median(kin_slope))]), np.array([lam0])
        meta_used = [("age_trend_per_20y", "age", True)]
    else:
        mu, have = kin_prior(kin_coefs, kin_fields, past, meta)
        M, lam, meta_used = X, np.where(have, lam0 * (1 - stranger), lam0), meta
    # Where borrowing has faded below the floor, the floor only stabilises: it pulls towards "no effect" (0),
    # not towards the relatives, so a 100% Stranger really borrows nothing.
    weak = lam < cfg["lam_floor"]
    mu = np.where(weak, 0.0, mu)
    lam = np.maximum(lam, cfg["lam_floor"])
    c0, c = fit_map(M, y, mu=mu, lam=lam)
    se, share = _laplace(M, y, c0, c, lam)
    share = np.where(mu != 0, share, 0.0)  # "still borrowed" counts only pulls towards a relative's value
    return OSState(fob=fob, day=int(day), t0=t0, records=rec, later=later, recipe=recipe, votes=past,
                   stranger=float(stranger), new_group=new_group, intercept=float(c0), coef=c, se=se, prior_mu=mu,
                   borrowed_share=share, meta=meta_used, green_day=gday, green_now=gday is not None and day >= gday,
                   path=path, kin_profiles=kin_prof, known=known)


def risk(state, df):
    """OS's predicted death probability for patients in df."""
    M = age_x(df, 50.0) if state.recipe == "age_trend" else design(df)[0]
    return expit(state.intercept + M @ state.coef)
