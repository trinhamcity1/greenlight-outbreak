"""synthcity baselines (runs in .venv-synthcity, see requirements-synthcity.txt): tvae, ddpm (TabDDPM),
bayesian_network, arf. Same input table as the CTGAN baseline.
Usage: .venv-synthcity/bin/python -I scripts/synthcity_baseline.py PLUGIN IN.parquet OUT.parquet N_ROWS SEED [JSON_KWARGS]"""
import json
import sys
import time

import numpy as np
import pandas as pd
import torch
from synthcity.plugins import Plugins
from synthcity.plugins.core.dataloader import GenericDataLoader

plugin, src, dst, n, seed = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
kw = json.loads(sys.argv[6]) if len(sys.argv) > 6 else {}
np.random.seed(seed)
torch.manual_seed(seed)
df = pd.read_parquet(src)
cats = [c for c in df.columns if c not in ("age", "death")]
codes = {c: sorted(df[c].astype(str).unique()) for c in cats}
num = df.copy()
for c in cats:  # integer-code the categories; synthcity treats low-cardinality integer columns as discrete
    num[c] = num[c].astype(str).map({v: i for i, v in enumerate(codes[c])}).astype(int)
num["death"] = num["death"].astype(int)
num["age"] = num["age"].astype(float)
const = {c: num[c].iloc[0] for c in num.columns if num[c].nunique() == 1}  # synthcity drops these; added back as is
t = time.time()
m = Plugins().get(plugin, random_state=seed, **kw)
m.fit(GenericDataLoader(num.drop(columns=list(const))))  # unconditional, like CTGAN: death is an ordinary column
out = m.generate(count=n, random_state=seed).dataframe()
for c, v in const.items():
    out[c] = v
for c in cats:
    out[c] = [codes[c][int(np.clip(round(v), 0, len(codes[c]) - 1))] for v in out[c]]
out["death"] = out["death"].round().clip(0, 1).astype(int)
out = out[df.columns]
out.to_parquet(dst, index=False)
print(f"{plugin} rows={len(df)} kwargs={kw} seconds={time.time() - t:.0f}")
