"""Step 4 baselines (Exp. 16): other synthetic data generators trained on exactly the real records OS had on its
Green Light day in Exp. 10d (outcomes only once known), scored the same way as OS's synthetic data.

  bootstrap         N rows resampled with replacement from the real records (no model)
  ctgan             CTGAN (scripts/ctgan_baseline.py, .venv-ctgan)
  tvae, ddpm,       synthcity plugins (scripts/synthcity_baseline.py, .venv-synthcity): TVAE, TabDDPM,
  bayesian_network, a Bayesian network and adversarial random forests
  arf
Model-based generators train on at most train_max_rows of the real records (subsample, seed fixed), like CTGAN in
Exp. 9. Results are saved after every generator; a rerun skips finished (outbreak, generator) pairs.
Usage: PYTHONPATH=src python -m outbreak_synth.run_synth_baselines experiments/exp16_synth_baselines.toml"""
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from .analyse_os2 import final_paths
from .library import OUT as LIB, TARGET, YESNO
from .os_core import CFG as OS_CFG, build_state
from .run_synth_release import OUTDIR, ridge_auc, sha
from .synth import compare

COLS = ["age", "CS_SEXO", "CS_RACA", "SG_UF_NOT"] + YESNO + [TARGET]


def main(cfg_path):
    cfg = tomllib.loads(Path(cfg_path).read_text())
    lib = pd.read_parquet(LIB)
    info = json.loads(Path("results", f"{cfg['os_run']}.json").read_text())["outbreaks"]
    paths = final_paths(cfg["os_run"], m=cfg["green_m"], s=cfg["green_s"])
    rpath, mpath = Path("results", f"{cfg['name']}.json"), Path("results", f"{cfg['name']}_manifest.json")
    results = json.loads(rpath.read_text())["outbreaks"] if rpath.exists() else {}
    manifest = json.loads(mpath.read_text()) if mpath.exists() else []
    for sub in ("baselines", "inputs"):
        (OUTDIR / sub).mkdir(parents=True, exist_ok=True)
    for fob, (_, gday, _) in sorted(paths.items()):
        todo = [g for g in cfg["generators"] if g not in results.get(fob, {}).get("logs", {})]
        if gday is None or not todo or (cfg.get("only") and fob not in cfg["only"]):
            continue
        s = build_state(fob, lib=lib, cfg={**OS_CFG, "os_run": cfg["os_run"], "kinship_run": cfg["kinship_run"],
                                           "kinship_analysis": cfg["kinship_analysis"], "vote_prior": cfg["vote_prior"],
                                           "outcome_timing": cfg["outcome_timing"], "green_m": cfg["green_m"],
                                           "green_s": cfg["green_s"]})
        assert s.day == gday
        lo, hi = info[fob]["info"]["test_days"]
        dd = (s.later.DT_DIGITA - s.t0).dt.days
        test = s.later[(dd >= lo) & (dd <= hi)]
        early = s.known
        inp = early[COLS].copy()
        for f in YESNO:  # as for CTGAN in Exp. 9: yes vs not yes
            inp[f] = np.where(inp[f] == "yes", "yes", "no")
        for c in ("CS_SEXO", "CS_RACA", "SG_UF_NOT"):
            inp[c] = inp[c].astype(str)
        inp["age"] = inp.age.astype(float)
        inp[TARGET] = inp[TARGET].astype(int)
        train = inp.sample(cfg["train_max_rows"], random_state=cfg["seed"]) if len(inp) > cfg["train_max_rows"] else inp
        p_in = OUTDIR / "inputs" / f"{fob}_day{gday}_known.parquet"
        train.to_parquet(p_in, index=False)
        r = results.get(fob) or {"green_day": gday, "early_n": len(early), "train_n": len(train), "test_n": len(test),
                                 "auc": {"gold": info[fob]["info"]["gold_auc"], "real_early": ridge_auc(early, test)},
                                 "fidelity": {}, "logs": {}}
        for g in todo:
            out = OUTDIR / "baselines" / f"SYNTHETIC_{g}_{fob}_day{gday}.parquet"
            if g == "bootstrap":
                syn = inp.sample(cfg["n_rows"], replace=True, random_state=cfg["seed"]).reset_index(drop=True)
                log, trained_on = "resampled", len(inp)
            else:
                if g == "ctgan":
                    cmd = [cfg["ctgan_python"], "-I", "scripts/ctgan_baseline.py", str(p_in), str(out),
                           str(cfg["n_rows"]), str(cfg["ctgan_epochs"]), str(cfg["seed"])]
                else:
                    cmd = [cfg["synthcity_python"], "-I", "scripts/synthcity_baseline.py", g, str(p_in), str(out),
                           str(cfg["n_rows"]), str(cfg["seed"]), json.dumps(cfg.get("kwargs", {}).get(g, {}))]
                log = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
                syn, trained_on = pd.read_parquet(out), len(train)
            syn["age"] = syn.age.astype(float).clip(0, 110)
            syn[TARGET] = syn[TARGET].astype(int)
            syn["synthetic"] = True
            syn["synth_source"] = (f"SYNTHETIC - {g} baseline; outbreak={fob}; trained on {trained_on} of the {len(early)} real "
                                   f"records with a known outcome on day {gday}; seed={cfg['seed']}. Not real patients.")
            syn.to_parquet(out, index=False)
            manifest.append({"file": str(out), "rows": len(syn), "sha256": sha(out), "provenance": syn.synth_source.iloc[0]})
            r["logs"][g] = log
            r["fidelity"][g] = {"vs_early": compare(early, syn), "vs_later": compare(test, syn)}
            r["auc"][f"{g}_synth_only"] = ridge_auc(syn, test)
            r["auc"][f"real_plus_{g}"] = ridge_auc(pd.concat([early, syn[early.columns.intersection(syn.columns)]]), test)
            results[fob] = r  # saved after every generator, so a rerun resumes
            rpath.write_text(json.dumps({"config": cfg, "outbreaks": results}, indent=2, default=str))
            mpath.write_text(json.dumps(manifest, indent=2))
            print(f"{fob} day {gday} {g}: synth-only {r['auc'][f'{g}_synth_only']:.3f} real+ {r['auc'][f'real_plus_{g}']:.3f} | {log}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
