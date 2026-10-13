"""Replay an outbreak day by day with real data only (the baseline OS must beat).
Day 0 = first record entered. On day d, train on every record entered up to day d; score AUC on a
fixed later test window. Gold = trained on every record of that outbreak outside the test window.
Usage: PYTHONPATH=src python -m outbreak_synth.run_replay_real experiments/exp03_replay_real.toml"""
import json
import sys
import tomllib
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

from .library import CATEGORICAL, FEATURES, NUMERIC, OUT as LIB, TARGET
from .models import make_model


def replay(lib, spec, model_name, min_class):
    df = lib[lib.outbreak.isin(spec["outbreaks"])].sort_values(["DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable")
    t0 = pd.Timestamp(spec["day0"])
    df = df[df.DT_DIGITA >= t0]  # drop entry dates before the outbreak started (data-entry errors)
    in_test = df.DT_DIGITA.between(pd.Timestamp(spec["test_from"]), pd.Timestamp(spec["test_to"]))
    test, rest = df[in_test], df[~in_test]
    y = test[TARGET].to_numpy()
    mk = lambda: make_model(model_name, 0, NUMERIC, CATEGORICAL)
    gold_auc = roc_auc_score(y, mk().fit(rest[FEATURES], rest[TARGET]).predict_proba(test[FEATURES])[:, 1])
    rows = []
    for d in range(spec["max_day"] + 1):
        tr = df[df.DT_DIGITA <= t0 + pd.Timedelta(days=d)]
        k = int(tr[TARGET].sum())
        row = {"day": d, "date": str((t0 + pd.Timedelta(days=d)).date()), "n": len(tr), "deaths": k, "auc": None}
        if min(k, len(tr) - k) >= min_class:
            row["auc"] = roc_auc_score(y, mk().fit(tr[FEATURES], tr[TARGET]).predict_proba(test[FEATURES])[:, 1])
        rows.append(row)
    first = next((r for r in rows if r["auc"] is not None), None)
    plateau = next((r for r in rows if r["auc"] is not None and gold_auc - r["auc"] <= 0.02), None)
    return {"spec": spec, "test_n": len(test), "test_deaths": int(y.sum()), "gold_n": len(rest),
            "gold_auc": gold_auc, "first_trainable_day": first, "first_day_within_0.02": plateau, "days": rows}


def main(cfg_path):
    cfg = tomllib.loads(Path(cfg_path).read_text())
    lib = pd.read_parquet(LIB)
    out = {}
    for name, spec in cfg["outbreak"].items():
        r = replay(lib, spec, cfg["model"], cfg["min_class"])
        out[name] = r
        f, p = r["first_trainable_day"], r["first_day_within_0.02"]
        print(f"{name}: test {r['test_n']} ({r['test_deaths']} deaths) gold {r['gold_auc']:.3f} | "
              f"first trainable day {f and f['day']} (n={f and f['n']}, auc={f and round(f['auc'], 3)}) | "
              f"within 0.02 on day {p and p['day']} (n={p and p['n']}, auc={p and round(p['auc'], 3)})", flush=True)
    Path("results", f"{cfg['name']}.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
