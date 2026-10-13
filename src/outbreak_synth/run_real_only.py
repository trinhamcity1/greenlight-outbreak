"""Real-only baseline: AUC on the time-based test set as a function of N.
Usage: PYTHONPATH=src python -m outbreak_synth.run_real_only experiments/exp01_real_only.toml"""
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .data import CATEGORICAL, NUMERIC, TARGET, load_cohort, time_split
from .models import make_model

FEATS = NUMERIC + CATEGORICAL


def boot_ci(y, p, n, seed=0):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(y), (n, len(y)))
    aucs = [roc_auc_score(y[i], p[i]) for i in idx]
    return [float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5))]


def main(cfg_path):
    cfg = tomllib.loads(Path(cfg_path).read_text())
    df = load_cohort()
    pool, test, cutoff = time_split(df, max(cfg["n_values"]), cfg["test_days"])
    y_te = test[TARGET].to_numpy()
    out = {"config": cfg, "cohort_rows": len(df), "cutoff_entry_date": str(cutoff.date()),
           "test": {"n": len(test), "deaths": int(y_te.sum()),
                    "entry_from": str(test.DT_DIGITA.min().date()), "entry_to": str(test.DT_DIGITA.max().date())},
           "runs": []}

    ref = df[(df.DT_DIGITA > test.DT_DIGITA.max()) & (df.DT_DIGITA <= pd.Timestamp(cfg["reference_until"]))]
    train_sets = [(n, pool.iloc[:n]) for n in cfg["n_values"]] + [("reference", ref)]
    for n, tr in train_sets:
        for m in cfg["models"]:
            seeds = cfg["seeds"] if m != "logreg" else [0]  # logreg is deterministic
            aucs = []
            for s in seeds:
                model = make_model(m, s).fit(tr[FEATS], tr[TARGET])
                p = model.predict_proba(test[FEATS])[:, 1]
                aucs.append(roc_auc_score(y_te, p))
            row = {"n": n if n != "reference" else len(tr), "label": str(n), "model": m,
                   "train_deaths": int(tr[TARGET].sum()), "auc_mean": float(np.mean(aucs)),
                   "auc_seed_sd": float(np.std(aucs)), "auc_test_boot95": boot_ci(y_te, p, cfg["bootstrap"])}
            out["runs"].append(row)
            print(row, flush=True)
    dest = Path("results") / f"{cfg['name']}.json"
    dest.write_text(json.dumps(out, indent=2))
    print("wrote", dest, "| test", out["test"])


if __name__ == "__main__":
    main(sys.argv[1])
