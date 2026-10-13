"""Step 1 of the first experiment: inspect the SIVEP-Gripe SRAG files.

Reports row counts, label distributions, date ranges, missingness, and the number
of outcome events in the earliest N COVID-19 hospitalised records.
Writes results/inspect_srag.json.  Usage: python -m outbreak_synth.inspect_srag
"""
import glob
import json
from pathlib import Path

import pandas as pd

RAW = Path("data/raw/srag")
OUT = Path("results/inspect_srag.json")

# Code meanings from dicionario-de-dados-2019-a-2025.pdf (Ministério da Saúde).
CLASSI_FIN = {1: "influenza", 2: "other_resp_virus", 3: "other_agent", 4: "unspecified", 5: "covid19"}
EVOLUCAO = {1: "cure", 2: "death", 3: "death_other_cause", 9: "ignored"}

COLS = ["DT_SIN_PRI", "DT_NOTIFIC", "DT_INTERNA", "DT_EVOLUCA", "CLASSI_FIN", "EVOLUCAO",
        "HOSPITAL", "UTI", "SUPORT_VEN", "NU_IDADE_N", "TP_IDADE", "CS_SEXO", "SG_UF_NOT",
        "FEBRE", "TOSSE", "DISPNEIA", "SATURACAO", "DESC_RESP", "CARDIOPATI", "DIABETES",
        "OBESIDADE", "RENAL", "PNEUMOPATI", "IMUNODEPRE", "NEUROLOGIC", "ASMA",
        "VACINA_COV", "CS_RACA", "CS_ESCOL_N", "CS_ZONA"]
CODE_COLS = [c for c in COLS if not c.startswith("DT_") and c != "SG_UF_NOT"]
SWEEP_N = [100, 300, 1000, 3000]


def load():
    frames = []
    for f in sorted(glob.glob(str(RAW / "INFLUD*.parquet"))):
        df = pd.read_parquet(f, columns=COLS)
        df["source_file"] = Path(f).name
        # Code fields are numeric in some yearly files and strings in others; normalise.
        for c in CODE_COLS:
            df[c] = pd.to_numeric(df[c].astype("string").str.strip(), errors="coerce")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def missing_frac(s):
    # Blank strings and 9 ("ignored") both count as missing for this report.
    if pd.api.types.is_numeric_dtype(s):
        return float((s.isna() | (s == 9)).mean())
    s = s.astype("string").str.strip()
    return float((s.isna() | (s == "") | (s == "9")).mean())


def main():
    df = load()
    rep = {"files": {}, "covid_hosp": {}}
    for name, g in df.groupby("source_file"):
        rep["files"][name] = {
            "rows": len(g),
            "DT_SIN_PRI_min": str(g.DT_SIN_PRI.min()), "DT_SIN_PRI_max": str(g.DT_SIN_PRI.max()),
            "CLASSI_FIN": {CLASSI_FIN.get(k, str(k)): int(v)
                           for k, v in g.CLASSI_FIN.value_counts(dropna=False).items()},
            "EVOLUCAO": {EVOLUCAO.get(k, str(k)): int(v)
                         for k, v in g.EVOLUCAO.value_counts(dropna=False).items()},
        }
    rep["missing_frac_all_rows"] = {c: round(missing_frac(df[c]), 4) for c in COLS if not c.startswith("DT_")}
    rep["missing_frac_all_rows"].update({c: round(float(df[c].isna().mean()), 4) for c in COLS if c.startswith("DT_")})

    # Candidate task: in-hospital death among hospitalised COVID-19 SRAG with a known outcome.
    cov = df[(df.CLASSI_FIN == 5)]
    hosp = cov[cov.HOSPITAL == 1]
    known = hosp[hosp.EVOLUCAO.isin([1, 2])].copy()  # cure vs death from SRAG; 3 and 9 excluded
    known = known.sort_values(["DT_SIN_PRI", "DT_NOTIFIC"], kind="stable")
    known["death"] = (known.EVOLUCAO == 2).astype(int)
    rep["covid_hosp"] = {
        "covid_rows": len(cov), "hospitalised": len(hosp),
        "known_outcome_cure_or_death": len(known),
        "death_rate": round(float(known.death.mean()), 4),
        "earliest_symptom_date": str(known.DT_SIN_PRI.iloc[0]),
        "earliest_N": {},
    }
    for n in SWEEP_N:
        head = known.head(n)
        rep["covid_hosp"]["earliest_N"][n] = {
            "deaths": int(head.death.sum()), "survivors": int(n - head.death.sum()),
            "last_symptom_date": str(head.DT_SIN_PRI.iloc[-1]),
        }
    # Monthly volume and death rate, to see how fast the early-outbreak window fills up.
    m = known.groupby(known.DT_SIN_PRI.dt.to_period("M")).death.agg(["size", "mean"])
    rep["covid_hosp"]["monthly"] = {str(k): {"n": int(r["size"]), "death_rate": round(float(r["mean"]), 4)}
                                    for k, r in m.head(8).iterrows()}
    # Influenza with the same definition (for the past-disease side and the alternative task).
    flu = df[(df.CLASSI_FIN == 1) & (df.HOSPITAL == 1) & df.EVOLUCAO.isin([1, 2])]
    rep["flu_hosp_known_outcome"] = {"n": len(flu), "deaths": int((flu.EVOLUCAO == 2).sum()),
                                     "by_file": flu.source_file.value_counts().to_dict()}

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2, default=str))
    print(json.dumps(rep, indent=2, default=str))


if __name__ == "__main__":
    main()
