"""Two-Part Recipe, Severity Model, with the Handover Rule.

Severity Model = logistic regression for in-hospital death, fitted as a MAP estimate:
    minimise  sum(log-loss)  +  (lam_j / 2) * (beta_j - mu_j)^2  summed over coefficients j
- mu (the prior mean) is the Kinship-Vote-weighted average of the kin's coefficients. Only fields the kin's
  form collected count; state (geography) is never borrowed (mu = 0).
- The intercept (fob's overall death rate) is never borrowed: weak prior centred on 0.
- lam (borrowing strength) = lam0 * (1 - Stranger share). Because the data term grows with every patient while
  the prior stays fixed, fob's own data takes over as records arrive. That is the Handover Rule.
With mu = 0 and lam = 1 the same code is plain ridge regression: the "real data only" arm.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

from .library import YESNO

AGE_BINS = [-1, 1, 5, 15, 30, 45, 60, 75, 200]
SEX = ["M", "F"]
RACE = ["1", "2", "3", "4", "5"]
UFS = ["RO", "AC", "AM", "RR", "PA", "AP", "TO", "MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA", "MG", "ES",
       "RJ", "SP", "PR", "SC", "RS", "MS", "MT", "GO", "DF"]


def design(df):
    """Same columns for every outbreak. Returns X and a list of (column name, source field, borrowable)."""
    age = pd.cut(df.age.fillna(df.age.median() if df.age.notna().any() else 40), AGE_BINS, labels=False).to_numpy()
    cols, meta = [], []
    for b in range(1, len(AGE_BINS) - 1):
        cols.append(age == b); meta.append((f"age_band_{b}", "age", True))
    for s in SEX:
        cols.append(df.CS_SEXO.to_numpy() == s); meta.append((f"sex_{s}", "CS_SEXO", True))
    for r in RACE:
        cols.append(df.CS_RACA.to_numpy() == r); meta.append((f"race_{r}", "CS_RACA", True))
    for u in UFS[1:]:
        cols.append(df.SG_UF_NOT.to_numpy() == u); meta.append((f"state_{u}", "SG_UF_NOT", False))
    for f in YESNO:
        cols.append(df[f].to_numpy() == "yes"); meta.append((f"{f}_yes", f, True))
    return np.column_stack(cols).astype(float), meta


def collected_fields(df, threshold=0.9):
    """Fields this outbreak's form actually collected (less than 90% 'missing')."""
    out = {"age", "CS_SEXO", "CS_RACA", "SG_UF_NOT"}
    out |= {f for f in YESNO if (df[f] == "missing").mean() < threshold}
    return out


def fit_map(X, y, mu=None, lam=1.0, intercept_sd=10.0):
    """MAP logistic regression with normal prior N(mu, 1/lam) per coefficient. Returns (intercept, beta)."""
    p = X.shape[1]
    mu = np.zeros(p) if mu is None else mu
    lam = np.broadcast_to(np.asarray(lam, float), (p,))

    def f(w):
        b0, b = w[0], w[1:]
        z = b0 + X @ b
        ll = np.logaddexp(0, z).sum() - y @ z
        pen = 0.5 * (lam * (b - mu) ** 2).sum() + 0.5 * b0 ** 2 / intercept_sd ** 2
        r = expit(z) - y
        g = np.concatenate([[r.sum() + b0 / intercept_sd ** 2], X.T @ r + lam * (b - mu)])
        return ll + pen, g

    w0 = np.concatenate([[0.0], mu])
    res = minimize(f, w0, jac=True, method="L-BFGS-B", options={"maxiter": 500})
    return res.x[0], res.x[1:]


def kin_prior(kin_coefs, kin_fields, weights, meta):
    """Vote-weighted average of kin coefficients, per column, over kin whose form collected that field."""
    p = len(meta)
    mu, have = np.zeros(p), np.zeros(p, bool)
    for j, (_, field, borrowable) in enumerate(meta):
        if not borrowable:
            continue
        ws = [(weights[k], kin_coefs[k][j]) for k in kin_coefs if field in kin_fields[k] and weights.get(k, 0) > 0]
        z = sum(w for w, _ in ws)
        if z > 0:
            mu[j] = sum(w * c for w, c in ws) / z
            have[j] = True
    return mu, have
