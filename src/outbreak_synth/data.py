"""Cohort, features and time-based split for the COVID-19 in-hospital mortality task.

Decisions (owner, 2026-10-05):
- Task: in-hospital death among hospitalised COVID-19 SRAG (CLASSI_FIN=5, HOSPITAL=1),
  outcome EVOLUCAO 2 (death) vs 1 (cure); 3 (other-cause death) and 9/blank excluded.
- Records are ordered by data-entry date (DT_DIGITA), i.e. when the record reached the system.
- The small sample is the earliest N records; the test set is the records entered right after it.
"""
import glob
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw/srag")

# Fields known at admission. In-hospital course (ICU, ventilation, X-ray, antivirals) and lab
# results are excluded to avoid leaking the outcome. DOR_ABD/FADIGA/PERD_OLFT/PERD_PALA are
# excluded because the form only added them later in 2020 (>90% blank in the early window).
SYMPTOMS = ["FEBRE", "TOSSE", "GARGANTA", "DISPNEIA", "DESC_RESP", "SATURACAO", "DIARREIA", "VOMITO"]
COMORB = ["PUERPERA", "CARDIOPATI", "HEMATOLOGI", "SIND_DOWN", "HEPATICA", "ASMA", "DIABETES",
          "NEUROLOGIC", "PNEUMOPATI", "IMUNODEPRE", "RENAL", "OBESIDADE"]
YESNO = SYMPTOMS + COMORB + ["NOSOCOMIAL"]
OTHER_CAT = ["CS_SEXO", "CS_RACA", "CS_ZONA", "SG_UF_NOT"]
CATEGORICAL = YESNO + OTHER_CAT
NUMERIC = ["age"]
TARGET = "death"

_READ = (["NU_NOTIFIC", "DT_DIGITA", "DT_SIN_PRI", "CLASSI_FIN", "HOSPITAL", "EVOLUCAO",
          "NU_IDADE_N", "TP_IDADE"] + YESNO + OTHER_CAT)


def _code(s):
    return pd.to_numeric(s.astype("string").str.strip(), errors="coerce")


def _yesno(s):
    # One rule for every model and generator: 1 yes, 2 no, anything else (blank, 9) missing.
    c = _code(s)
    return pd.Series(np.select([(c == 1).fillna(False).to_numpy(bool), (c == 2).fillna(False).to_numpy(bool)], ["yes", "no"], "missing"), index=s.index)


def load_cohort(files=None):
    files = files or sorted(glob.glob(str(RAW / "INFLUD*.parquet")))
    df = pd.concat([pd.read_parquet(f, columns=_READ) for f in files], ignore_index=True)
    df = df[(_code(df.CLASSI_FIN) == 5) & (_code(df.HOSPITAL) == 1)]
    evo = _code(df.EVOLUCAO)
    df = df[evo.isin([1, 2])].copy()
    df[TARGET] = (evo[df.index] == 2).astype(int)

    unit = _code(df.TP_IDADE).map({1: 1 / 365.25, 2: 1 / 12, 3: 1.0})
    df["age"] = (_code(df.NU_IDADE_N) * unit).clip(0, 110)
    for c in YESNO:
        df[c] = _yesno(df[c])
    for c in OTHER_CAT:
        df[c] = df[c].astype("string").str.strip().fillna("missing").replace("", "missing")
    df["CS_SEXO"] = df.CS_SEXO.replace({"I": "missing"})

    # Deterministic order: entry date, then onset date, then notification id (ties within a day).
    df = df.sort_values(["DT_DIGITA", "DT_SIN_PRI", "NU_NOTIFIC"], kind="stable").reset_index(drop=True)
    return df[["NU_NOTIFIC", "DT_DIGITA", "DT_SIN_PRI"] + NUMERIC + CATEGORICAL + [TARGET]]


def time_split(df, n_max, test_days):
    """Train pool = earliest n_max records. Test = records entered on the days after the last
    training day, for test_days days. Records sharing the cutoff day are left out of both."""
    cutoff = df.DT_DIGITA.iloc[n_max - 1]
    pool = df.iloc[:n_max]
    test = df[(df.DT_DIGITA > cutoff) & (df.DT_DIGITA <= cutoff + pd.Timedelta(days=test_days))]
    return pool, test, cutoff
