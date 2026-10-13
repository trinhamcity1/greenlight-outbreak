"""Synth Release: draw synthetic patients from OS's Two-Part Recipe, and compare datasets side by side.

Profile Model (who is hospitalised), sampled in this order:
  age band  ~ fob's counts + borrowed pseudo-counts from the voted relatives
  age       ~ one of fob's real ages in that band, jittered by up to +/- 0.5 years (uniform in band if none)
  sex | band, each symptom/condition (yes vs not-yes) | band
            ~ fob's counts + borrowed pseudo-counts (relatives that collected the field)
  state     ~ fob's counts only (geography is never borrowed)
  race | state ~ fob's counts, backed off to fob's overall race mix
Borrowing strength for the profile follows the Handover Rule: alpha * (1 - Stranger share) pseudo-patients, and
none on the new-pathogen-group fallback. Severity Model: death ~ Bernoulli(OS risk), see os_core.risk.
Every synthetic row carries synthetic=True and a provenance string. "no" in a synthetic yes/no field means
"not recorded as yes" (the models use yes vs not-yes)."""
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from .library import YESNO, TARGET
from .os_core import fam, risk

BANDS = [-1, 1, 5, 15, 30, 45, 60, 75, 200]
LO = [0, 1, 5, 15, 30, 45, 60, 75]
HI = [1, 5, 15, 30, 45, 60, 75, 105]
NB = len(LO)


def band(age):
    return pd.cut(age, BANDS, labels=False).to_numpy()


def _rate(counts_yes, n, prior_rate, alpha):
    return (counts_yes + alpha * prior_rate + 0.5) / (n + alpha + 1.0)


def profile_tables(state, alpha=10.0):
    rec = state.records.copy()
    rec["band"] = band(rec.age.fillna(rec.age.median()))
    a = 0.0 if state.recipe == "age_trend" else alpha * (1 - state.stranger)
    kins = {k: kd.assign(band=band(kd.age.fillna(kd.age.median()))) for k, kd in state.kin_profiles.items()}
    w = state.votes

    def kin_rate(fn, field=None):
        num, den = 0.0, 0.0
        for k, kd in kins.items():
            if field is not None and (kd[field] == "missing").mean() >= 0.9:
                continue
            num += w.get(k, 0) * fn(kd)
            den += w.get(k, 0)
        return num / den if den > 0 else None

    t = {"alpha_eff": a}
    kb = kin_rate(lambda kd: np.bincount(kd.band, minlength=NB) / len(kd))
    cnt = np.bincount(rec.band, minlength=NB)
    t["p_band"] = (cnt + a * (kb if kb is not None else 1 / NB) + 0.1) / (cnt.sum() + a + 0.1 * NB)
    t["ages"] = {b: rec.age[rec.band == b].dropna().to_numpy() for b in range(NB)}
    t["p_male"], t["p_yes"] = np.zeros(NB), {f: np.zeros(NB) for f in YESNO}
    for b in range(NB):
        rb = rec[rec.band == b]
        km = kin_rate(lambda kd: (kd[kd.band == b].CS_SEXO == "M").mean() if (kd.band == b).any() else 0.5)
        t["p_male"][b] = _rate((rb.CS_SEXO == "M").sum(), (rb.CS_SEXO != "missing").sum(), 0.5 if km is None else km, a)
        for f in YESNO:
            kr = kin_rate(lambda kd: (kd[kd.band == b][f] == "yes").mean() if (kd.band == b).any() else 0.0, field=f)
            t["p_yes"][f][b] = _rate((rb[f] == "yes").sum(), len(rb), 0.0 if kr is None else kr, a if kr is not None else 0.0)
    st = rec.SG_UF_NOT.value_counts()
    t["states"] = (st.index.to_numpy(), ((st + 0.1) / (st + 0.1).sum()).to_numpy())
    overall = rec.CS_RACA.value_counts(normalize=True)
    t["race_by_state"] = {}
    for s_, g in rec.groupby("SG_UF_NOT"):
        c = g.CS_RACA.value_counts().reindex(overall.index, fill_value=0)
        p = (c + 5 * overall) / (c.sum() + 5)
        t["race_by_state"][s_] = (p.index.to_numpy(), p.to_numpy())
    t["race_overall"] = (overall.index.to_numpy(), overall.to_numpy())
    return t


def generate(state, n, seed=0, alpha=10.0):
    rng = np.random.default_rng(seed)
    t = profile_tables(state, alpha)
    b = rng.choice(NB, size=n, p=t["p_band"])
    age = np.empty(n)
    for k in range(NB):
        idx = np.where(b == k)[0]
        pool = t["ages"][k]
        if len(pool):
            age[idx] = np.clip(rng.choice(pool, len(idx)) + rng.uniform(-0.5, 0.5, len(idx)), LO[k] + 1e-3, HI[k])
        else:
            age[idx] = rng.uniform(LO[k] + 1e-3, HI[k], len(idx))
    df = pd.DataFrame({"age": age})
    df["CS_SEXO"] = np.where(rng.random(n) < t["p_male"][b], "M", "F")
    for f in YESNO:
        df[f] = np.where(rng.random(n) < t["p_yes"][f][b], "yes", "no")
    sv, sp = t["states"]
    df["SG_UF_NOT"] = rng.choice(sv, n, p=sp)
    race = np.empty(n, dtype=object)
    for s_ in np.unique(df.SG_UF_NOT):
        idx = np.where(df.SG_UF_NOT == s_)[0]
        rv, rp = t["race_by_state"].get(s_, t["race_overall"])
        race[idx] = rng.choice(rv, len(idx), p=rp)
    df["CS_RACA"] = race
    df[TARGET] = (rng.random(n) < risk(state, df)).astype(int)
    df["synthetic"] = True
    df["synth_source"] = (f"SYNTHETIC - GreenLight v1 (formerly Outbreak Synth); outbreak={state.fob}; day={state.day} "
                          f"(day 0 = {state.t0.date()}); learned from {len(state.records)} real records "
                          f"({int(state.records[TARGET].sum())} deaths) entered up to that day; recipe={state.recipe}; "
                          f"seed={seed}. Not real patients.")
    return df


def yes_matrix(df):
    m = pd.DataFrame({f: (df[f] == "yes").astype(float) for f in YESNO})
    m["age"] = df.age.astype(float)
    m["male"] = (df.CS_SEXO == "M").astype(float)
    m[TARGET] = df[TARGET].astype(float)
    return m


def compare(a, b):
    """Side-by-side fidelity of dataset b against reference a (lower = closer)."""
    ma, mb = yes_matrix(a), yes_matrix(b)
    ba, bb = band(a.age.fillna(a.age.median())), band(b.age.fillna(b.age.median()))
    pa, pb = np.bincount(ba, minlength=NB) / len(ba), np.bincount(bb, minlength=NB) / len(bb)
    da = pd.Series(a[TARGET].to_numpy()).groupby(ba).mean().reindex(range(NB))
    db = pd.Series(b[TARGET].to_numpy()).groupby(bb).mean().reindex(range(NB))
    big = [k for k in range(NB) if pa[k] >= 0.02 and pb[k] >= 0.02]
    yes_diff = (ma[YESNO].mean() - mb[YESNO].mean()).abs()
    ca, cb = ma.corr().to_numpy(), mb.corr().to_numpy()
    iu = np.triu_indices_from(ca, 1)
    cd = np.abs(np.nan_to_num(ca[iu]) - np.nan_to_num(cb[iu]))
    return {"age_mean_diff": float(ma.age.mean() - mb.age.mean()),
            "age_ks": float(ks_2samp(ma.age.dropna(), mb.age.dropna()).statistic),
            "age_band_tvd": float(0.5 * np.abs(pa - pb).sum()),
            "death_rate_diff": float(mb[TARGET].mean() - ma[TARGET].mean()),
            "death_by_band_max_diff": float(np.nanmax(np.abs((db - da)[big]))) if big else None,
            "yes_rate_mean_abs_diff": float(yes_diff.mean()), "yes_rate_max_abs_diff": float(yes_diff.max()),
            "yes_rate_worst_field": yes_diff.idxmax(),
            "corr_mean_abs_diff": float(cd.mean()), "corr_max_abs_diff": float(cd.max())}


# ---------------------------------------------------------------------------------------------------------------
# Dependency chain for symptoms and conditions (Exp. 10). Fields are generated in CHAIN_ORDER; each one from a
# logistic model on age band, sex and every field generated before it, so pairwise links are kept. Each link model
# is fitted like OS's Severity Model: prior = vote-weighted relatives' chain coefficients (only relatives whose
# form collected the field and the conditioning field), strength lam0 * (1 - Stranger); where that falls below the
# floor, a weak pull to 0 instead; no borrowing on the new-pathogen-group fallback.
CHAIN_ORDER = ["FEBRE", "TOSSE", "GARGANTA", "DISPNEIA", "DESC_RESP", "SATURACAO", "CARDIOPATI", "METABOLIC",
               "OBESIDADE", "RENAL", "PNEUMOPATI", "IMUNODEPRE", "NEUROLOGIC", "HEPATICA", "PUERPERA", "SIND_DOWN"]


def chain_design(bands, male, prev):
    """bands: int array; male: 0/1 array; prev: (n, j) 0/1 matrix of fields already generated."""
    return np.column_stack([np.eye(NB)[bands][:, 1:], male[:, None], prev]).astype(float)


def _chain_inputs(df):
    b = band(df.age.fillna(df.age.median() if df.age.notna().any() else 40))
    male = (df.CS_SEXO == "M").to_numpy().astype(float)
    Y = np.column_stack([(df[f] == "yes").to_numpy() for f in CHAIN_ORDER]).astype(float)
    return b, male, Y


def fit_chain(state, lam0=10.0, lam_floor=1.0, max_kin_rows=20000):
    from .recipe import fit_map
    b, male, Y = _chain_inputs(state.records)
    collected_fob = [(state.records[f] == "missing").mean() < 0.9 for f in CHAIN_ORDER]
    borrow = state.recipe != "age_trend"
    kin_fits = {}
    if borrow:
        for k, kd in state.kin_profiles.items():
            if state.votes.get(k, 0) <= 0:
                continue
            kd = kd.sample(min(len(kd), max_kin_rows), random_state=0)
            kb, km, kY = _chain_inputs(kd)
            coll = [(kd[f] == "missing").mean() < 0.9 for f in CHAIN_ORDER]
            fits = []
            for j in range(len(CHAIN_ORDER)):
                if not coll[j] or kY[:, j].sum() == 0:
                    fits.append(None)
                    continue
                fits.append(fit_map(chain_design(kb, km, kY[:, :j]), kY[:, j], lam=1.0))
            kin_fits[k] = (fits, coll)
    models = []
    for j, f in enumerate(CHAIN_ORDER):
        Z = chain_design(b, male, Y[:, :j])
        p = Z.shape[1]
        mu, have = np.zeros(p), np.zeros(p, bool)
        if borrow and kin_fits:
            num, den = np.zeros(p), np.zeros(p)
            for k, (fits, coll) in kin_fits.items():
                if fits[j] is None:
                    continue
                ok = np.ones(p, bool)
                ok[NB - 1:] = [True] + [coll[i] for i in range(j)]  # sex column (NB-1), then earlier fields
                w = state.votes[k]
                num[ok] += w * fits[j][1][ok]
                den[ok] += w
            have = den > 0
            mu[have] = num[have] / den[have]
        lam = np.where(have, lam0 * (1 - state.stranger), lam0)
        weak = lam < lam_floor
        mu, lam = np.where(weak, 0.0, mu), np.maximum(lam, lam_floor)
        if not collected_fob[j]:
            models.append(None)  # fob's form did not collect it: always "no"
            continue
        models.append(fit_map(Z, Y[:, j], mu=mu, lam=lam))
    return models


def generate_chain(state, n, seed=0, alpha=10.0):
    """Like generate(), but symptoms and conditions come from the dependency chain."""
    from scipy.special import expit
    df = generate(state, n, seed=seed, alpha=alpha)  # age, sex, state, race (and placeholders)
    rng = np.random.default_rng(seed + 1)
    models = fit_chain(state)
    b = band(df.age)
    male = (df.CS_SEXO == "M").to_numpy().astype(float)
    Y = np.zeros((n, len(CHAIN_ORDER)))
    for j, f in enumerate(CHAIN_ORDER):
        if models[j] is not None:
            c0, c = models[j]
            Y[:, j] = rng.random(n) < expit(c0 + chain_design(b, male, Y[:, :j]) @ c)
        df[f] = np.where(Y[:, j] > 0, "yes", "no")
    df[TARGET] = (rng.random(n) < risk(state, df)).astype(int)
    df["synth_source"] = df.synth_source.str.replace("seed=", "profile=dependency chain; seed=", regex=False)
    return df
