"""CTGAN baseline (runs in .venv-ctgan, see requirements-ctgan.txt).
Usage: .venv-ctgan/bin/python -I scripts/ctgan_baseline.py IN.parquet OUT.parquet N_ROWS EPOCHS SEED"""
import sys
import time

import numpy as np
import pandas as pd
import torch
from ctgan import CTGAN

src, dst, n, epochs, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
np.random.seed(seed)
torch.manual_seed(seed)
df = pd.read_parquet(src)
discrete = [c for c in df.columns if c != "age"]
df[discrete] = df[discrete].astype(str)
t = time.time()
m = CTGAN(epochs=epochs, verbose=False)
m.set_random_state(seed)
m.fit(df, discrete_columns=discrete)
out = m.sample(n)
out["death"] = out["death"].astype(int)
out.to_parquet(dst, index=False)
print(f"ctgan rows={len(df)} epochs={epochs} seconds={time.time() - t:.0f}")
