"""Kinship Vote and Stranger Flag.

Every past outbreak in the Atlas (as it stood on fob's day 0) is a candidate "kin". Each candidate predicts
fob's records as they arrive; its votes come from how well it predicted them (cumulative log score).
A candidate is scored on two parts, kept separate so the Glass Box Report can show both:
  profile  - how likely fob's patients are under the kin's patient mix (age band, sex, core symptoms
             and conditions; fields treated as independent),
  severity - how well the kin's risk model predicts who dies, after shifting its overall death rate
             to fob's own (Handover Rule: the overall rate is never borrowed).
The Stranger is a candidate that borrows nothing: it learns fob's profile and risk model from fob's own
earlier records only. Everything is prequential: records of week w are scored by models fitted on
records entered before week w.

Fields: only those collected by every form version (KIN_FIELDS), coded yes vs not-yes, because the
2019+ form leaves "no" blank (checked: blank comorbidities mostly come with a blank "any risk factor").
"""
import numpy as np
import pandas as pd
from scipy.special import expit, logsumexp
from sklearn.linear_model import LogisticRegression

KIN_FIELDS = ["FEBRE", "TOSSE", "GARGANTA", "DISPNEIA", "CARDIOPATI", "PNEUMOPATI", "RENAL", "IMUNODEPRE", "METABOLIC"]
AGE_BINS = [-1, 1, 5, 15, 30, 45, 60, 75, 200]
N_AGE = len(AGE_BINS) - 1


def encode(df, fields=None):
    """Return (age_band int array, sex int array, binary field matrix, design matrix for risk models).
    fields: the yes/no fields to use (default KIN_FIELDS); pass only those fob's form collects."""
    fields = KIN_FIELDS if fields is None else fields
    age = pd.cut(df.age.fillna(df.age.median() if df.age.notna().any() else 40), AGE_BINS, labels=False).to_numpy().astype(int)
    sex = df.CS_SEXO.map({"M": 0, "F": 1}).fillna(2).to_numpy().astype(int)
    yes = (df[fields].to_numpy() == "yes").astype(float).reshape(len(df), len(fields))
    X = np.hstack([np.eye(N_AGE)[age][:, 1:], np.eye(3)[sex][:, :2], yes])
    return age, sex, yes, X


class Profile:
    """Independent-fields patient-mix model with Dirichlet smoothing."""

    def __init__(self, alpha=1.0):
        self.alpha = alpha

    def fit(self, age, sex, yes):
        a = self.alpha
        self.p_age = (np.bincount(age, minlength=N_AGE) + a) / (len(age) + a * N_AGE)
        self.p_sex = (np.bincount(sex, minlength=3) + a) / (len(sex) + a * 3)
        self.p_yes = (yes.sum(0) + a) / (len(yes) + 2 * a)
        return self

    def logpdf(self, age, sex, yes):
        return (np.log(self.p_age[age]) + np.log(self.p_sex[sex])
                + yes @ np.log(self.p_yes) + (1 - yes) @ np.log(1 - self.p_yes))


def fit_risk(X, y, C):
    if y.min() == y.max():
        return None
    return LogisticRegression(C=C, max_iter=1000).fit(X, y)


def risk_logit(model, X):
    return model.decision_function(X) if model is not None else np.zeros(len(X))


def fit_offset(base_logit, y, prior_sd=1.0, iters=25):
    """Shift a kin's risk model to fob's own overall death rate (MAP, normal prior on the shift)."""
    b = 0.0
    if len(y) == 0:
        return b
    for _ in range(iters):  # Newton steps
        p = expit(base_logit + b)
        g = (y - p).sum() - b / prior_sd ** 2
        h = (p * (1 - p)).sum() + 1 / prior_sd ** 2
        b += g / h
    return b


def bernoulli_logpmf(logit, y):
    return -np.logaddexp(0, -logit) * y - np.logaddexp(0, logit) * (1 - y)


def votes_from_scores(scores, tau, log_prior=None):
    """scores: dict name -> cumulative log score. Returns dict name -> share (adds to 1).
    log_prior: optional dict name -> log starting share (default: every candidate starts equal)."""
    names = list(scores)
    s = tau * np.array([scores[n] for n in names])
    if log_prior is not None:
        s = s + np.array([log_prior[n] for n in names])
    return dict(zip(names, np.exp(s - logsumexp(s))))


def start_shares(kin, mode="outbreak", with_stranger=True):
    """Log starting shares for the Kinship Vote.
    outbreak - every candidate starts equal (Exp. 5-13): groups with more past outbreaks start ahead.
    group    - (adopted 2026-10-07) every pathogen group starts equal, split equally among its members; the
               Stranger keeps its old starting share 1/(K+1), so only group fairness changes."""
    from .library import family
    K = len(kin)
    if mode == "outbreak":
        out = {k: -np.log(K + (1 if with_stranger else 0)) for k in kin}
        if with_stranger:
            out["STRANGER"] = -np.log(K + 1)
        return out
    fams = [family(k) for k in kin]
    G = len(set(fams))
    size = {f: fams.count(f) for f in set(fams)}
    past_mass = K / (K + 1) if with_stranger else 1.0
    out = {k: np.log(past_mass) - np.log(G) - np.log(size[f]) for k, f in zip(kin, fams)}
    if with_stranger:
        out["STRANGER"] = -np.log(K + 1)
    return out
