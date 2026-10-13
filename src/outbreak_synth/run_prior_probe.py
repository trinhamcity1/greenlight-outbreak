"""Probe of the core OS hypothesis: does knowledge from past outbreaks help in the first days?
Target: COVID-19 2020 replayed day by day (same test month as Exp. 2/3).
Past library: every outbreak that ended before 2020 (H1N1 2009, flu and other-virus seasons 2013-2019).
Arms on each day d:
  new_only   - logistic regression on COVID rows entered up to day d (the Exp. 3 baseline)
  past_only  - trained once on the past library, never sees COVID rows
  past_prior - past model's risk score (logit) as an extra input, refit on COVID rows each day
Usage: PYTHONPATH=src python -m outbreak_synth.run_prior_probe experiments/exp04_prior_probe.toml"""
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit
from sklearn.metrics import roc_auc_score

from .library import CATEGORICAL, FEATURES, NUMERIC, OUT as LIB, TARGET
from .models import make_model


def main(cfg_path):
    cfg = tomllib.loads(Path(cfg_path).read_text())
    lib = pd.read_parquet(LIB)
    past = lib[lib.outbreak.isin(cfg["past"])]
    new = lib[lib.outbreak.isin(cfg["target"])].sort_values(["DT_DIGITA", "DT_SIN_PRI", "id"], kind="stable")
    t0 = pd.Timestamp(cfg["day0"])
    new = new[new.DT_DIGITA >= t0]
    test = new[new.DT_DIGITA.between(pd.Timestamp(cfg["test_from"]), pd.Timestamp(cfg["test_to"]))]
    y = test[TARGET].to_numpy()

    past_model = make_model("logreg", 0, NUMERIC, CATEGORICAL).fit(past[FEATURES], past[TARGET])
    score = lambda X: logit(np.clip(past_model.predict_proba(X[FEATURES])[:, 1], 1e-6, 1 - 1e-6))
    test = test.assign(past_logit=score(test))
    past_auc = roc_auc_score(y, test.past_logit)
    print(f"past library: {len(past)} patients; past_only AUC on COVID test = {past_auc:.3f}", flush=True)

    rows = []
    for d in range(cfg["max_day"] + 1):
        tr = new[new.DT_DIGITA <= t0 + pd.Timedelta(days=d)]
        k = int(tr[TARGET].sum())
        row = {"day": d, "n": len(tr), "deaths": k, "past_only": past_auc, "new_only": None, "past_prior": None}
        if min(k, len(tr) - k) >= cfg["min_class"]:
            m = make_model("logreg", 0, NUMERIC, CATEGORICAL).fit(tr[FEATURES], tr[TARGET])
            row["new_only"] = roc_auc_score(y, m.predict_proba(test[FEATURES])[:, 1])
            tr = tr.assign(past_logit=score(tr))
            m = make_model("logreg", 0, NUMERIC + ["past_logit"], CATEGORICAL).fit(tr[FEATURES + ["past_logit"]], tr[TARGET])
            row["past_prior"] = roc_auc_score(y, m.predict_proba(test[FEATURES + ["past_logit"]])[:, 1])
        rows.append(row)
        if d % 3 == 0 or d < 35 and row["new_only"]:
            print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
    Path("results", f"{cfg['name']}.json").write_text(json.dumps({"config": cfg, "past_n": len(past),
        "test_n": len(test), "past_only_auc": past_auc, "days": rows}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
