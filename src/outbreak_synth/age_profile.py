"""Crude in-hospital death rate by age band for each outbreak group (Outbreak Atlas).
Usage: PYTHONPATH=src python -m outbreak_synth.age_profile  -> results/age_profile.csv"""
import pandas as pd

from .library import OUT as LIB

BINS = [-1, 1, 5, 15, 30, 45, 60, 75, 200]
LABELS = ["<1", "1-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+"]


def group(o):
    if o == "h1n1_2009":
        return "H1N1 2009"
    if o == "covid_2020":
        return "COVID 2020"
    if o.startswith("covid"):
        return "COVID 2021-22"
    if o in ("flu_2021", "flu_2022"):
        return "flu 2021-22"
    if o.startswith("flu"):
        return "flu 2013-2020"
    return "other virus 2013-22"


if __name__ == "__main__":
    lib = pd.read_parquet(LIB)
    lib["band"] = pd.cut(lib.age, BINS, labels=LABELS)
    lib["group"] = lib.outbreak.map(group)
    t = lib.groupby(["group", "band"], observed=True).death.agg(["mean", "size"]).reset_index()
    t.to_csv("results/age_profile.csv", index=False)
    print((t.pivot(index="group", columns="band", values="mean") * 100).round(1).to_string())
