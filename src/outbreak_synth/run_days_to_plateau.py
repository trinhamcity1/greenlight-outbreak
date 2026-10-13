"""How many days after the first record does a real-data-only model reach its plateau?
Usage: PYTHONPATH=src python -m outbreak_synth.run_days_to_plateau experiments/exp02_days_to_plateau.toml"""
import json
import sys
import tomllib
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

from .data import CATEGORICAL, NUMERIC, TARGET, load_cohort
from .models import make_model

FEATS = NUMERIC + CATEGORICAL


def main(cfg_path):
    cfg = tomllib.loads(Path(cfg_path).read_text())
    df = load_cohort()
    t0 = df.DT_DIGITA.min()
    in_test = df.DT_DIGITA.between(pd.Timestamp(cfg["test_from"]), pd.Timestamp(cfg["test_to"]))
    test, rest = df[in_test], df[~in_test]
    y = test[TARGET].to_numpy()

    gold = make_model(cfg["model"], 0).fit(rest[FEATS], rest[TARGET])
    gold_auc = roc_auc_score(y, gold.predict_proba(test[FEATS])[:, 1])
    print("gold", len(rest), gold_auc, flush=True)

    rows = []
    for d in range(cfg["max_day"] + 1):
        tr = df[df.DT_DIGITA <= t0 + pd.Timedelta(days=d)]
        k = int(tr[TARGET].sum())
        if min(k, len(tr) - k) < cfg["min_class"]:
            rows.append({"day": d, "n": len(tr), "deaths": k, "auc": None})
            continue
        m = make_model(cfg["model"], 0).fit(tr[FEATS], tr[TARGET])
        auc = roc_auc_score(y, m.predict_proba(test[FEATS])[:, 1])
        rows.append({"day": d, "date": str((t0 + pd.Timedelta(days=d)).date()), "n": len(tr), "deaths": k, "auc": auc})
        print(rows[-1], flush=True)
    within = [r for r in rows if r["auc"] is not None and gold_auc - r["auc"] <= 0.02]
    out = {"config": cfg, "first_entry": str(t0.date()), "test_n": len(test), "test_deaths": int(y.sum()),
           "gold_n": len(rest), "gold_auc": gold_auc,
           "first_day_within_0.02": within[0] if within else None, "days": rows}
    Path("results", f"{cfg['name']}.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
