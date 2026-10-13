"""Step 4: Synth Release on every outbreak's Green Light day, checked side by side against real patients.

For each outbreak that turned green (OS final rule, Exp. 8):
  * OS synthetic data: N rows from the Two-Part Recipe (synth.generate), labelled synthetic.
  * CTGAN baseline: trained on the same real records OS had on the green day (subsampled to ctgan_max_rows),
    run in the isolated .venv-ctgan environment (requirements-ctgan.txt), N rows, labelled synthetic.
  * Fidelity (synth.compare) against (a) the real records OS had, (b) the later real test window it never saw,
    plus early-real vs later-real as the natural drift reference.
  * Usefulness on the later real test window (AUC): OS's own model; ridge trained on the early real records;
    trained on OS synthetic only; on CTGAN synthetic only; on early real + OS synthetic; on early real + CTGAN.
Synthetic files go to data/synthetic/ (git-ignored, names start with SYNTHETIC_); results/synth_manifest.json
records their provenance and SHA-256.
Usage: PYTHONPATH=src python -m outbreak_synth.run_synth_release experiments/exp09_synth_release.toml"""
import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .library import OUT as LIB, TARGET, YESNO
from .os_core import CFG as OS_CFG, build_state, risk
from .analyse_os2 import final_paths
from .recipe import design, fit_map
from .synth import compare, generate, generate_chain

OUTDIR = Path("data/synthetic")


def ridge_auc(train, test):
    tr = train.copy()
    tr["age"] = tr.age.astype(float).clip(0, 110)
    X, _ = design(tr)
    c0, c = fit_map(X, tr[TARGET].to_numpy().astype(int), lam=1.0)
    return float(roc_auc_score(test[TARGET], c0 + design(test)[0] @ c))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(cfg_path):
    cfg = tomllib.loads(Path(cfg_path).read_text())
    lib = pd.read_parquet(LIB)
    info = json.loads(Path("results", f"{cfg['os_run']}.json").read_text())["outbreaks"]
    paths = final_paths(cfg["os_run"], m=cfg.get("green_m", 20), s=cfg.get("green_s", 0.98))
    for sub in ("os", "ctgan", "inputs"):
        (OUTDIR / sub).mkdir(parents=True, exist_ok=True)
    results, manifest = {}, []
    only = cfg.get("only")
    for fob, (_, gday, _) in sorted(paths.items()):
        if gday is None or (only and fob not in only):
            continue
        s = build_state(fob, lib=lib, cfg={**OS_CFG, "os_run": cfg["os_run"],
                                           "kinship_run": cfg.get("kinship_run", OS_CFG["kinship_run"]),
                                           "kinship_analysis": cfg.get("kinship_analysis"),
                                           "vote_prior": cfg.get("vote_prior", "outbreak"),
                                           "outcome_timing": cfg.get("outcome_timing", "entry"),
                                           "green_m": cfg.get("green_m", 20), "green_s": cfg.get("green_s", 0.98)})
        lo, hi = info[fob]["info"]["test_days"]
        dd = (s.later.DT_DIGITA - s.t0).dt.days
        test = s.later[(dd >= lo) & (dd <= hi)]
        early = s.known if s.known is not None else s.records  # real records with an outcome OS could see
        gen = generate_chain if cfg.get("profile_model", "independent") == "chain" else generate
        syn = gen(s, cfg["n_rows"], seed=cfg["seed"])
        tag = "os_chain" if gen is generate_chain else "os"
        p_os = OUTDIR / "os" / f"SYNTHETIC_{tag}_{fob}_day{gday}.parquet"
        syn.to_parquet(p_os, index=False)
        manifest.append({"file": str(p_os), "rows": len(syn), "sha256": sha(p_os), "provenance": syn.synth_source.iloc[0]})

        if not cfg.get("ctgan", True):
            r = {"green_day": gday, "recipe": s.recipe, "early_n": len(early), "early_deaths": int(early[TARGET].sum()),
                 "test_n": len(test), "test_deaths": int(test[TARGET].sum()),
                 "fidelity": {"os_vs_early": compare(early, syn), "os_vs_later": compare(test, syn), "early_vs_later": compare(test, early)},
                 "auc": {"gold": info[fob]["info"]["gold_auc"], "age_only": info[fob]["info"]["age_only_auc"],
                         "os_model": float(roc_auc_score(test[TARGET], risk(s, test))), "real_early": ridge_auc(early, test),
                         "os_synth_only": ridge_auc(syn, test),
                         "real_plus_os_synth": ridge_auc(pd.concat([early, syn[early.columns.intersection(syn.columns)]]), test)}}
            results[fob] = r
            print(f"{fob}: day {gday} | OS-synth AUC {r['auc']['os_synth_only']:.3f} | corr gap vs early "
                  f"{r['fidelity']['os_vs_early']['corr_mean_abs_diff']:.3f} / {r['fidelity']['os_vs_early']['corr_max_abs_diff']:.3f}", flush=True)
            Path("results", f"{cfg['name']}.json").write_text(json.dumps({"config": cfg, "outbreaks": results}, indent=2, default=str))
            Path("results", f"{cfg['name']}_manifest.json").write_text(json.dumps(manifest, indent=2))
            continue
        cols = ["age", "CS_SEXO", "CS_RACA", "SG_UF_NOT"] + YESNO + [TARGET]
        inp = early[cols].copy()
        for f in YESNO:
            inp[f] = np.where(inp[f] == "yes", "yes", "no")
        if len(inp) > cfg["ctgan_max_rows"]:
            inp = inp.sample(cfg["ctgan_max_rows"], random_state=cfg["seed"])
        p_in = OUTDIR / "inputs" / f"{fob}_day{gday}.parquet"
        inp.to_parquet(p_in, index=False)
        p_ct = OUTDIR / "ctgan" / f"SYNTHETIC_ctgan_{fob}_day{gday}.parquet"
        log = subprocess.run([cfg["ctgan_python"], "-I", "scripts/ctgan_baseline.py", str(p_in), str(p_ct),
                              str(cfg["n_rows"]), str(cfg["ctgan_epochs"]), str(cfg["seed"])],
                             capture_output=True, text=True, check=True).stdout.strip()
        ct = pd.read_parquet(p_ct)
        ct["age"] = ct.age.astype(float).clip(0, 110)
        ct["synthetic"] = True
        ct["synth_source"] = (f"SYNTHETIC - CTGAN baseline; outbreak={fob}; trained on {len(inp)} of the {len(early)} real "
                              f"records entered up to day {gday}; epochs={cfg['ctgan_epochs']}; seed={cfg['seed']}. Not real patients.")
        ct.to_parquet(p_ct, index=False)
        manifest.append({"file": str(p_ct), "rows": len(ct), "sha256": sha(p_ct), "provenance": ct.synth_source.iloc[0]})

        r = {"green_day": gday, "recipe": s.recipe, "early_n": len(early), "early_deaths": int(early[TARGET].sum()),
             "test_n": len(test), "test_deaths": int(test[TARGET].sum()), "ctgan_log": log,
             "fidelity": {"os_vs_early": compare(early, syn), "ctgan_vs_early": compare(early, ct),
                          "os_vs_later": compare(test, syn), "ctgan_vs_later": compare(test, ct),
                          "early_vs_later": compare(test, early)},
             "auc": {"gold": info[fob]["info"]["gold_auc"], "age_only": info[fob]["info"]["age_only_auc"],
                     "os_model": float(roc_auc_score(test[TARGET], risk(s, test))),
                     "real_early": ridge_auc(early, test), "os_synth_only": ridge_auc(syn, test),
                     "ctgan_synth_only": ridge_auc(ct, test),
                     "real_plus_os_synth": ridge_auc(pd.concat([early, syn[early.columns.intersection(syn.columns)]]), test),
                     "real_plus_ctgan": ridge_auc(pd.concat([early, ct[early.columns.intersection(ct.columns)]]), test)}}
        results[fob] = r
        a = r["auc"]
        print(f"{fob}: day {gday}, {len(early)} real ({r['early_deaths']} deaths) | AUC gold {a['gold']:.3f} age {a['age_only']:.3f} "
              f"OS {a['os_model']:.3f} real {a['real_early']:.3f} OS-synth {a['os_synth_only']:.3f} CTGAN {a['ctgan_synth_only']:.3f} "
              f"real+OS {a['real_plus_os_synth']:.3f} real+CTGAN {a['real_plus_ctgan']:.3f} | {log}", flush=True)
        Path("results", f"{cfg['name']}.json").write_text(json.dumps({"config": cfg, "outbreaks": results}, indent=2, default=str))
        # Exp. 9 wrote results/synth_manifest.json; later runs use <name>_manifest.json so they never overwrite it.
        mname = "synth_manifest.json" if cfg["name"] == "exp09_synth_release" else f"{cfg['name']}_manifest.json"
        Path("results", mname).write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
