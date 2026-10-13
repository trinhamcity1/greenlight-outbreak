"""Outbreak library: every Brazilian SRAG outbreak harmonised to one schema.

One row per hospitalised patient with a known outcome (cure vs death), tagged with the outbreak
it belongs to. Old (2009-2018, CSV) and new (2019+, parquet) SIVEP-Gripe forms are mapped to the
same fields; a field the form did not collect is "missing".
Usage: PYTHONPATH=src python -m outbreak_synth.library  -> data/processed/library.parquet
"""
import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd

OLD = Path("data/raw/srag_historic")
NEW = Path("data/raw/srag")
# Brazil-only Atlas (Exp. 1-10). Set OUTBREAK_LIB=data/processed/library_intl.parquet to use the Atlas that
# also holds Mexico (Exp. 11+); building it never touches the Brazil-only file, so earlier results reproduce.
BRAZIL = Path("data/processed/library.parquet")
INTL = Path("data/processed/library_intl.parquet")
SMALL = Path("data/processed/library_small.parquet")  # INTL + three small line lists (vote-only test, Exp. 13)
# Frozen final test (docs/frozen_test_plan.md): the Brazil library unchanged + 2023-2025 seasons from a separate folder,
# so building the development library never picks the test files up.
FROZEN = Path("data/processed/library_frozen.parquet")
NEW_FROZEN = Path("data/raw/srag_frozen")
OUT = Path(os.environ.get("OUTBREAK_LIB", BRAZIL))
MEXICO = Path("data/raw/mexico/extracted")


def family(name):
    """Pathogen group of an outbreak: flu (incl. H1N1), othervirus, covid (Brazil or Mexico)."""
    f = name.split("_")[0]
    return "flu" if f == "h1n1" else f

SYMPTOMS = ["FEBRE", "TOSSE", "GARGANTA", "DISPNEIA", "DESC_RESP", "SATURACAO"]
# METABOLIC = old-form METABOLICA ("chronic metabolic disease / diabetes") = new-form DIABETES.
COMORB = ["CARDIOPATI", "PNEUMOPATI", "RENAL", "IMUNODEPRE", "METABOLIC", "HEPATICA",
          "NEUROLOGIC", "OBESIDADE", "PUERPERA", "SIND_DOWN"]
YESNO = SYMPTOMS + COMORB
OTHER_CAT = ["CS_SEXO", "CS_RACA", "SG_UF_NOT"]
CATEGORICAL = YESNO + OTHER_CAT
NUMERIC = ["age"]
FEATURES = NUMERIC + CATEGORICAL
TARGET = "death"

# IBGE state codes (old files) -> state abbreviations (new files).
UF = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO", 21: "MA", 22: "PI",
      23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA", 31: "MG", 32: "ES",
      33: "RJ", 35: "SP", 41: "PR", 42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}


def _num(s):
    return pd.to_numeric(s.astype("string").str.strip(), errors="coerce")


def _yesno(s):
    c = _num(s)
    yes = (c == 1).fillna(False).to_numpy(bool)
    no = (c == 2).fillna(False).to_numpy(bool)
    return pd.Series(np.select([yes, no], ["yes", "no"], "missing"), index=s.index)


def _finish(df, outbreak):
    for c in YESNO:
        df[c] = _yesno(df[c]) if c in df else "missing"
    df["CS_SEXO"] = df.CS_SEXO.astype("string").str.strip().replace({"I": pd.NA}).fillna("missing")
    df["CS_RACA"] = _num(df.CS_RACA).astype("Int64").astype("string").replace({"9": pd.NA}).fillna("missing")
    df["SG_UF_NOT"] = df.SG_UF_NOT.fillna("missing")
    df["age"] = df.age.clip(0, 110)
    df["outbreak"] = outbreak
    # When the outcome became usable (Exp. 14+). DT_KNOWN: the later of entry and outcome date (the outcome had
    # happened and the record existed), falling back to the closure date when no outcome date is recorded.
    # DT_KNOWN_CLOSE (cautious): the later of entry and closure date. Sources without these dates (Mexico, small
    # line lists) get the entry date, i.e. the old timing.
    out_d = df["DT_OUTCOME"] if "DT_OUTCOME" in df else pd.Series(pd.NaT, index=df.index)
    close_d = df["DT_CLOSE"] if "DT_CLOSE" in df else pd.Series(pd.NaT, index=df.index)
    if "DT_OUTCOME" in df or "DT_CLOSE" in df:
        df["DT_KNOWN"] = pd.concat([df.DT_DIGITA, out_d.fillna(close_d)], axis=1).max(axis=1, skipna=False)
        df["DT_KNOWN_CLOSE"] = pd.concat([df.DT_DIGITA, close_d], axis=1).max(axis=1, skipna=False)
    else:
        df["DT_KNOWN"] = df.DT_DIGITA
        df["DT_KNOWN_CLOSE"] = df.DT_DIGITA
    return df[["outbreak", "id", "DT_DIGITA", "DT_SIN_PRI"] + FEATURES + [TARGET, "DT_KNOWN", "DT_KNOWN_CLOSE"]]


def load_old(year):
    """2009-2018 CSV files. 2009-2011 use the pandemic form (CLASSI_FIN 1 = new influenza subtype,
    EVOLUCAO 2 = death from influenza); 2012-2018 use CLASSI_FIN 1 influenza, 2 other resp. virus."""
    df = pd.read_csv(OLD / f"INFLUD{year:02d}.csv", sep=";", dtype=str, encoding="latin-1")
    df = df[_num(df.HOSPITAL) == 1].copy()
    df["id"] = f"{year:02d}-" + df.index.astype(str)
    for c in ["DT_DIGITA", "DT_SIN_PRI", "DT_OBITO", "DT_ENCERRA"]:
        df[c] = pd.to_datetime(df[c], format="%d/%m/%Y", errors="coerce")
    # 2012+ forms: DT_OBITO = date of discharge or death; 2009 form: date of death only.
    df["DT_OUTCOME"], df["DT_CLOSE"] = df["DT_OBITO"], df["DT_ENCERRA"]
    raw_age = _num(df.NU_IDADE_N)
    unit = (raw_age // 1000).map({1: 1 / (365.25 * 24), 2: 1 / 365.25, 3: 1 / 12, 4: 1.0})
    df["age"] = (raw_age % 1000) * unit
    df["METABOLIC"] = df["METABOLICA"]
    df["SG_UF_NOT"] = _num(df.SG_UF_NOT).map(UF)
    evo = _num(df.EVOLUCAO)
    df = df[evo.isin([1, 2])].copy()
    df[TARGET] = (evo[df.index] == 2).astype(int)
    return df, _num(df.CLASSI_FIN)


def load_new(path):
    cols = ["NU_NOTIFIC", "DT_DIGITA", "DT_SIN_PRI", "DT_EVOLUCA", "DT_ENCERRA", "CLASSI_FIN", "HOSPITAL", "EVOLUCAO", "NU_IDADE_N",
            "TP_IDADE", "CS_SEXO", "CS_RACA", "SG_UF_NOT", "DIABETES"] + [c for c in YESNO if c != "METABOLIC"]
    df = pd.read_parquet(path, columns=cols)
    df = df[_num(df.HOSPITAL) == 1].copy()
    df["id"] = df.NU_NOTIFIC.astype(str)
    df["DT_OUTCOME"], df["DT_CLOSE"] = df["DT_EVOLUCA"], df["DT_ENCERRA"]
    unit = _num(df.TP_IDADE).map({1: 1 / 365.25, 2: 1 / 12, 3: 1.0})
    df["age"] = _num(df.NU_IDADE_N) * unit
    df["METABOLIC"] = df["DIABETES"]
    df["SG_UF_NOT"] = df.SG_UF_NOT.astype("string").str.strip()
    evo = _num(df.EVOLUCAO)
    df = df[evo.isin([1, 2])].copy()
    df[TARGET] = (evo[df.index] == 2).astype(int)
    return df, _num(df.CLASSI_FIN)


def build():
    parts = []
    # H1N1 pandemic 2009: confirmed new-subtype influenza.
    df, cls = load_old(9)
    parts.append(_finish(df[cls == 1].copy(), "h1n1_2009"))
    # Seasonal outbreaks 2013-2018 (same form as today). 2010-2012 skipped: the 2012 file mixes
    # the pandemic-form and 2012-form outcome codes, and 2010-2011 are small.
    for y in range(13, 19):
        df, cls = load_old(y)
        parts.append(_finish(df[cls == 1].copy(), f"flu_20{y}"))
        parts.append(_finish(df[cls == 2].copy(), f"othervirus_20{y}"))
    for f in sorted(glob.glob(str(NEW / "INFLUD*.parquet"))):
        y = int(Path(f).name[6:8])
        df, cls = load_new(f)
        parts.append(_finish(df[cls == 1].copy(), f"flu_20{y}"))
        parts.append(_finish(df[cls == 2].copy(), f"othervirus_20{y}"))
        if y >= 20:
            parts.append(_finish(df[cls == 5].copy(), f"covid_20{y}"))
    lib = pd.concat(parts, ignore_index=True)
    lib = lib.sort_values(["outbreak", "DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable").reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lib.to_parquet(OUT, index=False)
    return lib


def load_mexico(year):
    """Mexico SISVER COVID-19 year-closure file -> harmonised schema, outbreak covid_mx_<year>.
    Hospitalised (TIPO_PACIENTE 2), confirmed COVID-19 (CLASIFICACION_FINAL 1-3). Death = FECHA_DEF recorded.
    The file has no data-entry date, so DT_DIGITA is the ADMISSION date (FECHA_INGRESO): ordering ignores
    reporting delay, which is more optimistic than the Brazil replays. Symptoms are not collected (missing).
    Mapping: DIABETES->METABOLIC, CARDIOVASCULAR->CARDIOPATI, EPOC->PNEUMOPATI, RENAL_CRONICA->RENAL,
    INMUSUPR->IMUNODEPRE, OBESIDAD->OBESIDADE (1 yes, 2 no, 97-99 missing). State = 'MX-<ENTIDAD_UM>' (not borrowed)."""
    cols = ["ID_REGISTRO", "TIPO_PACIENTE", "FECHA_INGRESO", "FECHA_SINTOMAS", "FECHA_DEF", "EDAD", "SEXO",
            "CLASIFICACION_FINAL", "ENTIDAD_UM", "DIABETES", "CARDIOVASCULAR", "EPOC", "RENAL_CRONICA", "INMUSUPR", "OBESIDAD"]
    d = pd.read_csv(MEXICO / f"COVID19MEXICO{year}.csv", usecols=cols, dtype=str)
    d = d[(d.TIPO_PACIENTE == "2") & d.CLASIFICACION_FINAL.isin(["1", "2", "3"])].copy()
    out = pd.DataFrame({"id": "MX-" + d.ID_REGISTRO,
                        "DT_DIGITA": pd.to_datetime(d.FECHA_INGRESO, errors="coerce"),
                        "DT_SIN_PRI": pd.to_datetime(d.FECHA_SINTOMAS, errors="coerce"),
                        "age": _num(d.EDAD), "CS_SEXO": d.SEXO.map({"1": "F", "2": "M"}),
                        "CS_RACA": pd.NA, "SG_UF_NOT": "MX-" + d.ENTIDAD_UM.str.zfill(2)}, index=d.index)
    for src, dst in [("DIABETES", "METABOLIC"), ("CARDIOVASCULAR", "CARDIOPATI"), ("EPOC", "PNEUMOPATI"),
                     ("RENAL_CRONICA", "RENAL"), ("INMUSUPR", "IMUNODEPRE"), ("OBESIDAD", "OBESIDADE")]:
        out[dst] = d[src]
    out[TARGET] = (d.FECHA_DEF != "9999-99-99").astype(int)
    out = out[out.DT_DIGITA.notna()]
    return _finish(out, f"covid_mx_{year}")


def build_frozen():
    """Brazil library (unchanged) + SRAG 2023-2025 -> data/processed/library_frozen.parquet."""
    parts = [pd.read_parquet(BRAZIL)]
    for f in sorted(glob.glob(str(NEW_FROZEN / "INFLUD*.parquet"))):
        y = int(Path(f).name[6:8])
        df, cls = load_new(f)
        parts.append(_finish(df[cls == 1].copy(), f"flu_20{y}"))
        parts.append(_finish(df[cls == 2].copy(), f"othervirus_20{y}"))
        parts.append(_finish(df[cls == 5].copy(), f"covid_20{y}"))
    lib = pd.concat(parts, ignore_index=True)
    lib = lib.sort_values(["outbreak", "DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable").reset_index(drop=True)
    lib.to_parquet(FROZEN, index=False)
    return lib


def build_intl():
    """Brazil Atlas + Mexico COVID-19 2020 and 2021 -> data/processed/library_intl.parquet."""
    lib = pd.concat([pd.read_parquet(BRAZIL), load_mexico(2020), load_mexico(2021)], ignore_index=True)
    lib = lib.sort_values(["outbreak", "DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable").reset_index(drop=True)
    lib.to_parquet(INTL, index=False)
    return lib


def load_small():
    """Three small, public line lists, coded with age and sex only (their other fields do not match the Atlas).
    All patients are treated as hospitalised. Records are ordered by the date their outcome became known
    (the earliest a record is usable for the severity part); MERS has no such date for survivors, so it uses
    the report date. Sources (see scripts/download_small.sh):
      ebola_sl_2014 - Kenema Government Hospital, Sierra Leone, May-June 2014 (Schieffelin et al. 2014), Zenodo
                      record 2614046 (mirador/ebola-data v1.4, licence "other-open"); EBOV-positive, known outcome.
      h7n9_cn_2013  - influenza A(H7N9), China 2013, R package outbreaks 1.9.0 (GPL >= 2); known outcome only.
      mers_kr_2015  - MERS-CoV, South Korea 2015, ECDC data from the first weeks, R package outbreaks 1.9.0
                      (GPL >= 2). Outcome is provisional: "Alive" may include patients who died later."""
    import pyreadr
    import rdata
    base = Path("data/raw/small")
    parts = []
    e = pd.read_csv(base / "ebola/mirador-ebola-data-59f6ea0/sources/csv/DemographicsFromSim_schieffelin.csv")
    e = e[(e.Ebola_dem == "Positive") & e.Outcome.isin(["Died", "Discharged"])]
    when = pd.to_datetime(e.OutcomeDate, errors="coerce").fillna(pd.to_datetime(e.PreAdmissionDate, errors="coerce"))
    parts.append(pd.DataFrame({"outbreak": "ebola_sl_2014", "id": "SL-" + e.GID.astype(str), "DT_DIGITA": when,
                               "DT_SIN_PRI": when, "age": pd.to_numeric(e.Age, errors="coerce"),
                               "CS_SEXO": e.Sex.map({"Female": "F", "Male": "M"}), "SG_UF_NOT": "SL",
                               TARGET: (e.Outcome == "Died").astype(int)}))
    h = pyreadr.read_r(str(base / "outbreaks_pkg/outbreaks/data/fluH7N9_china_2013.RData"))["fluH7N9_china_2013"]
    h = h[h.outcome.notna()]
    when = pd.to_datetime(h.date_of_outcome, errors="coerce").fillna(pd.to_datetime(h.date_of_onset, errors="coerce"))
    parts.append(pd.DataFrame({"outbreak": "h7n9_cn_2013", "id": "CN-" + h.case_id.astype(str), "DT_DIGITA": when,
                               "DT_SIN_PRI": pd.to_datetime(h.date_of_onset, errors="coerce"),
                               "age": pd.to_numeric(h.age.astype(str), errors="coerce"),
                               "CS_SEXO": h.gender.astype(str).map({"f": "F", "m": "M"}),
                               "SG_UF_NOT": "CN-" + h.province.astype(str), TARGET: (h.outcome == "Death").astype(int)}))
    m = rdata.read_rda(str(base / "outbreaks_pkg/outbreaks/data/mers_korea_2015.RData"))["mers_korea_2015"]["linelist"]
    day = lambda x: pd.to_datetime("1970-01-01") + pd.to_timedelta(pd.to_numeric(x, errors="coerce"), unit="D")
    parts.append(pd.DataFrame({"outbreak": "mers_kr_2015", "id": "KR-" + m.id.astype(str), "DT_DIGITA": day(m.dt_report),
                               "DT_SIN_PRI": day(m.dt_onset), "age": pd.to_numeric(m.age, errors="coerce"),
                               "CS_SEXO": m.sex.astype(str).map({"F": "F", "M": "M"}), "SG_UF_NOT": "KR",
                               TARGET: (m.outcome.astype(str) == "Dead").astype(int)}))
    out = []
    for df in parts:
        name = df.outbreak.iloc[0]
        df = df[df.DT_DIGITA.notna()].copy()
        df["CS_RACA"] = pd.NA
        out.append(_finish(df.reset_index(drop=True), name))
    return pd.concat(out, ignore_index=True)


def build_small():
    lib = pd.concat([pd.read_parquet(INTL), load_small()], ignore_index=True)
    lib = lib.sort_values(["outbreak", "DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable").reset_index(drop=True)
    lib.to_parquet(SMALL, index=False)
    return lib


def summary(lib):
    g = lib.groupby("outbreak")
    s = pd.DataFrame({
        "patients": g.size(), "death_rate": g[TARGET].mean().round(3),
        "first_entry": g.DT_DIGITA.min().dt.date, "median_age": g.age.median().round(0),
        "fields_missing_share": g.apply(lambda x: (x[YESNO] == "missing").to_numpy().mean().round(2)),
    })
    return s


if __name__ == "__main__":
    import sys
    lib = (build_small() if "--small" in sys.argv else build_intl() if "--intl" in sys.argv else
           build_frozen() if "--frozen" in sys.argv else build())
    s = summary(lib)
    print(s.to_string())
    s.to_csv("results/library_frozen_summary.csv" if "--frozen" in sys.argv else
             "results/library_small_summary.csv" if "--small" in sys.argv else
             "results/library_intl_summary.csv" if "--intl" in sys.argv else "results/library_summary.csv")
