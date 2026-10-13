# RESULTS

Running log of what was run, on which data, and what came out. Newest entry first.

> **Naming (2026-10-13):** the method formerly called **Outbreak Synth (OS)** is now **GreenLight**, and the
> day-by-day replay benchmark is **OutbreakReplay**. Its readiness signal, formerly "Green Light", is now the
> lowercase "green light". Entries below this note use the old names. The pre-registered plan
> (`docs/frozen_test_plan.md`) is left unchanged on purpose.

## 2026-10-13 — Exp. 19–21: checks for journal submission (calibration, copy check, outcome-timing sensitivity)

### Exp. 19: closure-date outcome timing (`exp19a_kinship_closure`, `exp19b_os_replay_closure`)
- An outcome counts only from the case-closure date (`DT_KNOWN_CLOSE`), a more cautious timing.
- Development set; otherwise as Exp. 5d / 8d.

| | Known timing (adopted) | Closure timing |
|---|---:|---:|
| Mean gap to gold, days 0–90 (label fallback, 20 deaths) | 0.0053 | 0.0068 |
| Days below rank by age | 66 | 94 |
| Green Light (10, 0.99): greens / false / median day | 22 / 0 / 38 | 22 / 1 (other virus 2017) / 41 |
| COVID 2020: green day; plateau OS / real data alone | 54; 36 / 36 | 58; 36 / 34 |

- Slightly weaker everywhere; the conclusions do not change.

### Exp. 20: calibration on the Green Light day (`analyse_calibration.py` → `results/calibration_{dev,frozen}.json`)
- Models: OS's released model; real data alone; pooled earlier outbreaks; stacking; gold.
- All scored on the later test patients.
- Mean over outbreaks with 95% bootstrap intervals:

| Model | Dev O/E | Dev slope | Dev Brier | Frozen O/E | Frozen slope | Frozen Brier |
|---|---:|---:|---:|---:|---:|---:|
| OS | 0.94 [0.84, 1.03] | 0.96 [0.90, 1.01] | 0.097 | 1.15 [1.05, 1.29] | 0.97 [0.92, 1.02] | 0.081 |
| Real data alone | 1.08 [0.93, 1.26] | 0.75 [0.67, 0.84] | 0.105 | 1.08 [0.97, 1.20] | 0.84 [0.75, 0.92] | 0.084 |
| Pooled earlier outbreaks | 0.80 [0.73, 0.87] | 0.89 [0.81, 0.96] | 0.102 | 0.70 [0.58, 0.83] | 1.04 [0.99, 1.09] | 0.082 |
| Stacking | 1.00 [0.90, 1.08] | 0.92 [0.87, 0.97] | 0.098 | 1.15 [1.03, 1.29] | 1.04 [0.99, 1.09] | 0.080 |
| Gold | 1.02 [0.97, 1.08] | 1.29 [1.16, 1.42] | 0.096 | 1.09 [1.03, 1.14] | 1.10 [1.06, 1.15] | 0.080 |

- **Plain reading:**
  - OS's risk ranking is well calibrated (slope ≈ 1). Real data alone gives risks that are too extreme
    (slope 0.75–0.84).
  - OS's overall level was right on average in development, but under-predicted deaths by about 15% on the frozen
    test. Stacking did the same, and gold under-predicted by 9%, so later patients in 2023–2025 died somewhat more
    often than earlier ones.
  - Pooled-only over-predicts deaths by 20–30%: it ignores fob's own, lower death rate.
  - Per outbreak, OS's O/E ranges from about 0.7 to 1.4. The level is the weak part early on.

### Exp. 21: copy check on synthetic data (`analyse_privacy.py` → `results/privacy_{dev,frozen}.json`)
- Record = age in years, sex, race, state, 16 yes/no fields, outcome.
- The check compares two shares:
  - the share of synthetic rows exactly matching a real record the generator saw;
  - the share of later, unseen real patients that match one by chance.

| | Development (22) | Frozen (9) |
|---|---:|---:|
| Unseen real patients matching (chance level) | 11.4% | 13.5% |
| OS synthetic | 12.7% (difference +0.013 [−0.009, 0.035]) | 11.3% (−0.022 [−0.052, 0.000]) |
| ARF / CTGAN / Bayesian network / TVAE | 6.4% / 5.5% / 7.0% / 12.1% | 5.7% / 6.3% / 3.9% / 9.3% |
| Bootstrap resampling | 100% | 100% |

- OS copies no more than chance. This is a copying check, not a privacy guarantee; the source data are public.
- A first version summarised the per-outbreak ratio. It blew up where an outbreak's chance share was 0, so the
  summary now uses differences.

### Correction
- Exp. 15 (and the plan PDF) said Riley's rule "never turns on in flu and other-virus seasons". That was wrong.
- In development it turned on for flu 2016 (day 66) and flu 2022 (day 24), as well as the 3 COVID seasons. Over all
  32 outbreaks it turned on in 8 (6 COVID, 2 flu) and never for other viruses.
- Corrected in RESULTS.md, the plan PDF and the paper.

### Paper
- `paper/main.tex` (TMLR style, preprint option) compiles to 11 pages with Table 1 (`make_tables.py`) and the
  figures.
- Remaining placeholder, in red, for the author: the anonymous code link.
- All references in `paper/refs.bib` must be checked against the publisher before submission.

---

## 2026-10-13 — Exp. 18: frozen final test on the 2023–2025 seasons

**Plan first:**
- `docs/frozen_test_plan.md`, with the analysis code (`analyse_frozen.py`) and configs (`exp18a`–`exp18e`), was
  committed in `6af1dd3` before any test data were downloaded.
- Before that commit, the analysis code was dry-run on the development results; it reproduced them exactly.

**Data:**
- SRAG files `INFLUD23/24/25-23-03-2026.parquet` in `data/raw/srag_frozen/` (SHA-256 in `SHA256SUMS` there:
  `3adfca92…`, `015135a3…`, `cb1653d3…`).
- Built with `library.py --frozen` → `library_frozen.parquet`. The 23 development outbreaks inside it are identical
  row for row (2,142,720 rows) to `library.parquet`.
- No loading fixes were needed.
- **9 test outbreaks, all scored, none excluded:** flu, other virus and COVID for each of 2023, 2024 and 2025.
- Settings exactly as frozen (τ = 0.01, Green Light 10 deaths / 0.99, all baselines as Exp. 15–16).

### Results, in the plan's order
**1. Who dies, accuracy (mean gap to gold, days 0–90; 9 outbreaks)**
- OS: **0.0067** [0.0027, 0.0114]. Development: 0.0052.
- The other method's gap minus OS's gap (95% paired bootstrap; above 0 = OS better):

| Method | Its mean gap | Minus OS [95% CI] | OS better in |
|---|---:|---:|---:|
| Real data alone | 0.0393 | +0.033 [0.020, 0.046] | 9/9 |
| Fine-tuning | 0.0070 | +0.0003 [−0.0007, 0.0013] | 5/9 |
| OS without the vote (equal weights) | 0.0074 | +0.0008 [−0.0004, 0.0018] | 7/9 |
| Source averaging | 0.0082 | +0.0015 [0.0010, 0.0021] | 9/9 |
| **Stacking (pooled past + new outbreak)** | **0.0006** | **−0.0061 [−0.0098, −0.0023]** | **1/9** |
| **Pooled past only (no new data at all)** | **0.0010** | **−0.0056 [−0.0095, −0.0015]** | **1/9** |
| Meta-analytic / robust / empirical Bayes / meta-learned start | 0.0097 / 0.0099 / 0.0086 / 0.0130 | all above 0 | 7–9/9 |

**2. Safety:** OS 0 days below "rank by age" in all 9 outbreaks; real data alone 86 days.

**3. Green Light:**
- 9 of 9 green; median day 34 [24, 52].
- **1 false green:** other virus 2023 on day 52. OS 0.778 against gold 0.799, a gap of 0.021, just over the 0.02
  line. Exact interval for the false-green rate: [0.3%, 48%].
- Patient level: 8 firmly correct, 1 uncertain (other virus 2023, gap above 0.02 in 54% of resamples), 0 firmly
  false.
- Riley's rule: ready in 3 of 9 (the COVID seasons, days 24–40), never in flu or other virus.

**4. Kinship Vote:** right group leads in 9/9 outbreaks in weeks 1, 2, 4 and 8 (exact interval [66%, 100%]).

**5. Synthetic data (9 outbreaks):**
- OS synthetic only: 0.803 [0.785, 0.819].
- Against the real records OS had: **+0.035 [0.013, 0.058]**, better in 8/9.
- Against the generators:
  - ARF +0.016 [0.008, 0.024], better in 8/9;
  - TVAE +0.079;
  - bootstrap +0.074;
  - Bayesian network +0.113;
  - CTGAN +0.209.

  The intervals for TVAE, bootstrap, Bayesian network and CTGAN are all above 0; OS is better in 9/9 for each.
- Real records + OS synthetic minus real alone: +0.036 [0.014, 0.058].

### The plan's criteria (stated before the data)
| Criterion | Result |
|---|---|
| Borrowing helps (OS vs real data alone, interval above 0) | **Holds** (+0.033) |
| No clear gain over fine-tuning (expected) | Holds (interval includes 0) |
| No clear gain over stacking (expected) | **Fails, in the negative direction: stacking is clearly better than OS** |
| Green Light honest (0 or 1 false greens) | Holds, at the limit (1 false green, a borderline 0.021 gap) |
| Safety comparable to development (2.9 days below age per outbreak) | Holds (0) |
| OS synthetic beats the real records OS had | **Holds** (+0.035) |

### Plain reading
- **The main negative result:** on these familiar seasons, simply pooling the earlier outbreaks beats OS's
  borrowing. That holds with fob's records added (stacking), and even without any fob data at all.
  - By 2023 the Atlas holds many seasons of each pathogen, and the season-to-season patient pattern is very stable
    (the novelty gaps are 0.01–0.17 nats/patient).
  - OS's Handover Rule hands over to fob's own few early records too quickly. With a borrowing strength of 10, a
    few dozen records already dominate the prior.
  - This was not visible in development, where the stacking interval included 0.
  - It is reported as found. The fixed settings were not changed.
- **What holds up:**
  - Borrowing beats real data alone.
  - OS never drops below "rank by age".
  - The vote finds the right group every week.
  - The Green Light has at most one borderline false green.
  - OS synthetic data beats the real records it was built from, and beats every standard generator.
- **What it means for the paper:**
  - OS's way of borrowing is not the best predictor once a rich past exists. Pooling is a strong, simple
    competitor and must be reported as such.
  - OS's distinct value is the parts the baselines lack: the safety fallback for a new pathogen, the readiness
    signal, and readiness-gated synthetic data.
  - An obvious next design would let the borrowing strength depend on how familiar fob is: stronger when the vote
    is confident, as in these seasons. That would be **new development work**, and would need a new held-out test.
- These seasons contain no new pathogen, so the test says nothing new about OS's behaviour for a new disease.

---

## 2026-10-08 — Exp. 17: confidence intervals, and figures

**What was run:**
- `analyse_ci.py 1000` → `results/ci_summary.json`.
- `make_figures.py` → `figures/fig1`–`fig7` (PNG and PDF), drawn only from committed results and the library.

**Two levels of interval:**
- **Patients:** on each Green Light day (10 deaths, 0.99), the later test patients are resampled.
  - 1,000 stratified paired resamples, seed 0.
  - Models compared: OS's released model (`os_core.FINAL_CFG`), gold (same design on all of fob's other records,
    strength 10) and real data alone (ridge on the records with a known outcome).
- **Outbreaks:** headline averages use 2,000 bootstrap resamples over outbreaks, seed 0; rates use exact
  Clopper–Pearson intervals.

### Outbreak level
| Result | Value | 95% CI |
|---|---:|---:|
| Kinship Vote right group, weeks 1 / 2 / 4 (21 outbreaks with an earlier group member) | 19/21 = 90% | [70%, 99%] |
| Right group, week 8 onwards | 20/21 = 95% | [76%, 100%] |
| Right when the vote is ≥ 95% sure (416 outbreak-weeks) | 97.6% | [95.6%, 98.8%] (weeks are not independent) |
| Green Light false greens, adopted rule, in-sample | 0/22 | [0%, 15%] |
| Green Light false greens, leave-one-outbreak-out | 1/22 | [0.1%, 23%] |
| Median Green Light day | 38 | [32, 46] |
| OS mean gap to gold, days 0–90 | 0.0052 | [−0.0035, 0.0153] |
| Real data alone, mean gap to gold | 0.0520 | [0.0393, 0.0664] |
| OS days below "rank by age", per outbreak | 2.9 | [0.3, 6.3] |
| Synthetic-only AUC: OS / ARF / real records OS had | 0.796 / 0.770 / 0.730 | [0.781, 0.811] / [0.749, 0.789] / [0.705, 0.753] |
| Outbreaks < 1,000 records: real + OS synthetic minus real alone (15) | +0.086 | [0.064, 0.109] |

### Patient level, on the Green Light day (22 outbreaks; `figures/fig7_green_day_ci.png`)
| | Count |
|---|---:|
| Green is firmly correct: gold − OS > 0.02 in under 2.5% of resamples | 14 |
| Verdict uncertain at this test size | 8 |
| Green is firmly false | 0 |
| OS beats real data alone with the interval above 0 | 18 |

- COVID 2020 on day 54: OS 0.756 [0.752, 0.758], gold 0.767; gap 0.012 [0.010, 0.012].
- Least certain: other virus 2017 on day 46. OS 0.778 against gold 0.796; gap 0.018 [−0.006, 0.047]; gap above
  0.02 in 42% of resamples.
- Other uncertain cases: other virus 2021 (28%), other virus 2014 (16%), other virus 2022 (15%), other virus 2016
  (11%).

- **Plain reading:**
  - The test windows of small seasons hold only a few hundred patients, so intervals there are wide (often ±0.05
    AUC).
  - No green is clearly false. About a third of them cannot be called clearly right either, mostly small
    other-virus seasons.
  - OS's mean gap to gold over days 0–90 is not distinguishable from 0. Real data alone's clearly is.
  - With 22–23 outbreaks, rate intervals stay wide: up to 15–23% false greens cannot be ruled out. The frozen test
    and more outbreaks are what narrow them.

### Figures
| File | Shows |
|---|---|
| `fig1_replay_curves` | AUC by day: OS, real data alone, fine-tuning baseline, with gold, rank by age and Green Light (4 outbreaks) |
| `fig2_kinship_vote` | Vote share by group and Stranger by week (COVID 2020, flu 2016) |
| `fig3_baselines_forest` | Exp. 15 gap vs OS with 95% intervals, with and without fallback |
| `fig4_readiness` | Ready day per outbreak: Green Light adopted and old, and Riley |
| `fig5_synthetic_generators` | Exp. 16 synthetic-only AUC per outbreak and mean with 95% interval |
| `fig6_outcome_timing` | COVID 2020: share of the outcomes the first replays used that were actually known |
| `fig7_green_day_ci` | Patient-level intervals on the Green Light day: gold, OS, real data alone |

---

## 2026-10-07 — Exp. 16: baselines for step 4 (synthetic data generators)

**What was run:** `run_synth_baselines.py` with `experiments/exp16_synth_baselines.toml` →
`results/exp16_synth_baselines.json`, `_manifest.json` (SHA-256 of every synthetic file) and `_summary.csv`.
- Same 22 outbreaks, Green Light days and real records as OS in Exp. 10d (outcomes only once known, Green Light
  10 deaths / 0.99).
- 50,000 rows per generator, seed 0.
- Model-based generators train on at most 10,000 of the real records; only the 3 COVID outbreaks are larger.

**Generators:**
- bootstrap resampling of the real records;
- Bayesian network, ARF and TVAE (300 epochs), via synthcity 0.2.12 in `.venv-synthcity`
  (`requirements-synthcity.txt`; opacus pinned to 1.5.2 so it imports with torch 2.2.2);
- CTGAN (300 epochs, `.venv-ctgan`).
- All are unconditional fits on age, sex, race, state, the 16 yes/no fields and death.
- Columns with a single value are left out of the synthcity fit and added back unchanged (they crashed the
  Bayesian network).
- **TabDDPM was not run:** on this 4-CPU machine a 1,000-step fit on 2,000 rows did not finish within an hour, and
  a 100-step test produced 0.3% deaths against 28% real.

**Scoring** is as in Exp. 10:
- a ridge model trained on each synthetic set, AUC on the later real test window;
- 95% paired bootstrap intervals over outbreaks (2,000 resamples, seed 0).

| Trained on | Mean AUC (22) | Outbreaks < 1,000 records (15) | OS minus it [95% CI] | OS better in | Link gap vs later real | Worst death-rate gap vs real records |
|---|---:|---:|---:|---:|---:|---:|
| **OS synthetic** | **0.796** | **0.804** | — | — | **0.032** | 0.020 |
| real records OS had | 0.730 | 0.718 | +0.066 [0.044, 0.086] | 21 | — | — |
| ARF | 0.770 | 0.768 | +0.026 [0.013, 0.042] | 17 | 0.042 | 0.009 |
| TVAE | 0.704 | 0.683 | +0.092 [0.060, 0.130] | 22 | 0.050 | 0.120 |
| bootstrap | 0.679 | 0.653 | +0.118 [0.082, 0.154] | 21 | 0.057 | 0.005 |
| Bayesian network | 0.676 | 0.663 | +0.120 [0.089, 0.153] | 22 | 0.071 | 0.237 |
| CTGAN | 0.613 | 0.585 | +0.183 [0.141, 0.222] | 22 | 0.057 | 0.233 |

- Link gap = mean absolute difference in correlations between the yes/no fields, age and death, against the
  later real patients.
- Adding synthetic rows to the real records, in outbreaks under 1,000 records: OS 0.718 → 0.804. ARF 0.768,
  TVAE 0.698, CTGAN 0.608, Bayesian network 0.664, bootstrap 0.653.

- **Plain reading:**
  - OS's synthetic data is the most useful in this comparison, and its links between fields are closest to later
    patients.
  - **The comparison is not like for like, and that is the point:** the other generators see only fob's own
    records, while OS's synthetic data also carries what it borrowed from earlier outbreaks. They show what a
    standard generator gives at the same moment, not a better generator for the same information.
  - **Where fob's own records are plentiful (COVID, flu 2022), the gap is small.** OS beats bootstrap by
    0.001–0.008, and in flu 2022 bootstrap (0.772) and ARF (0.774) beat OS (0.767).
  - **Bootstrap scores below the real records it copies.** 50,000 copies of a few hundred patients make the
    fixed ridge penalty relatively weak, so the model overfits. The same protocol applies to every generator,
    OS included, and is kept as in Exp. 9/10.
  - ARF is the strongest standard generator. CTGAN and the Bayesian network distort the death rate in small
    outbreaks (gaps up to 0.23).

---

## 2026-10-07 — Exp. 15: baselines for steps 2–3 and for the Green Light

**What was run:** `run_baselines.py` with `experiments/exp15_baselines.toml` → `results/exp15_baselines.json`.
- Same replay as Exp. 8d: Brazil library, 23 outbreaks, same day 0, test windows and 2-day grid. Outcomes are used
  only once known.
- Analysis: `analyse_baselines.py exp15_baselines exp08d_os_replay_known` → `results/exp15_baselines_analysis.json`
  and `_summary.csv`.

**How the baselines were set up:**
- Every method is the same logistic regression design.
- Each uses only earlier outbreaks (records and outcomes known before fob's day 0).
- Each uses OS's borrowing strength of 10 where it needs one.
- **No baseline was tuned further. OS's settings were chosen on these same outbreaks (Exp. 6b, 8),** so this
  comparison favours OS somewhat. The frozen final test must settle it.

| Baseline | What it is |
|---|---|
| pooled | one model on the pooled earlier outbreaks; no fob data |
| stacked | pooled earlier outbreaks + fob's records in one fit, with a fob indicator |
| finetune | MAP towards the pooled model (L2 fine-tuning) |
| kin_equal | OS's Handover Rule with all earlier outbreaks weighted equally (= OS without the Kinship Vote) |
| map | meta-analytic prior (mean and between-outbreak variance of each coefficient) |
| rmap | robust meta-analytic prior: 0.8 map + 0.2 vague, weights updated by marginal likelihood (Schmidli et al. 2014) |
| eb | commensurate-style: borrowing strength chosen by marginal likelihood on fob's data |
| bma | one component per earlier outbreak + a no-borrowing component, weighted by marginal likelihood on fob's deaths (a simplification of multi-source exchangeability models) |
| meta_init | MetaPred-style: Reptile meta-learned starting point, then fine-tuning towards it |

### Results: who dies (23 outbreaks, days 0–90)
- Gap = gold AUC minus the method's AUC, averaged over days. Lower is better.
- "Gap vs OS" = the method's gap minus OS's, with a 95% paired bootstrap interval over outbreaks (2,000
  resamples, seed 0). Above 0 means OS is better.

| Method | Mean gap | Gap vs OS [95% CI] | OS better in | Days below age only |
|---|---:|---:|---:|---:|
| **OS** (Kinship Vote + Handover + label fallback) | **0.0052** | — | — | **66** |
| real data alone | 0.0520 | +0.047 [0.028, 0.065] | 19 | 644 |
| pooled | 0.0210 | +0.016 [0.003, 0.032] | 13 | 552 |
| stacked | 0.0101 | +0.005 [−0.002, 0.013] | 11 | 306 |
| finetune | 0.0085 | +0.003 [−0.001, 0.008] | 13 | 184 |
| kin_equal | 0.0087 | +0.004 [0.001, 0.006] | 18 | 222 |
| map | 0.0140 | +0.009 [0.004, 0.016] | 20 | 278 |
| rmap | 0.0166 | +0.011 [0.006, 0.019] | 21 | 296 |
| eb | 0.0146 | +0.009 [0.005, 0.014] | 20 | 332 |
| bma | 0.0081 | +0.003 [0.001, 0.005] | 16 | 138 |
| meta_init | 0.0124 | +0.007 [0.005, 0.010] | 20 | 276 |

With OS's Lab-Label Fallback added to each baseline (isolates the borrowing itself):

| Method + fallback | Mean gap | Gap vs OS [95% CI] | OS better in | Days below age only |
|---|---:|---:|---:|---:|
| stacked | 0.0083 | +0.003 [−0.002, 0.009] | 11 | 230 |
| finetune | 0.0072 | +0.002 [−0.001, 0.005] | 13 | 114 |
| kin_equal | 0.0081 | +0.003 [0.001, 0.005] | 17 | 166 |
| bma | 0.0070 | +0.002 [0.000, 0.003] | 15 | 82 |
| map / rmap / eb / meta_init | 0.011 / 0.013 / 0.014 / 0.012 | all above 0 | 18–20 | 220–284 |

- **Plain reading:**
  - Borrowing from earlier outbreaks in any form is far better than real data alone.
  - OS has the lowest mean gap and the fewest days below "rank by age".
  - Against the two simplest baselines, the margin is small and not statistically clear. These are stacking fob
    with the pooled past, and fine-tuning towards the pooled model. Their intervals include 0, and OS is better in
    only 11–13 of 23 outbreaks.
  - The Kinship Vote's own contribution (OS vs kin_equal) is small but consistent: +0.003, interval above 0,
    17–18 of 23 outbreaks.
  - Weighting sources by how well they explain fob's deaths (bma) comes closest. OS's vote also uses who gets
    sick, which arrives before deaths.
  - **The Lab-Label Fallback matters more than the vote** in the new-pathogen outbreaks. Without it, every
    borrowing baseline is below "rank by age" for 24–30 of COVID 2020's first 90 days (stacked 58, pooled 92);
    OS: 0 days.
  - The meta-analytic priors (map, rmap) borrow too firmly where earlier outbreaks agree. In other virus 2013
    they start at AUC 0.42.
- **What this means for the claim:** OS's gain over a good simple baseline is modest in accuracy. The stronger
  parts are safety (no days below age only in the new-pathogen outbreaks) and the readiness signal (below).

### Results: readiness rules (Exp. 8d rows; a ready day is false if the model is > 0.02 below gold)
| Rule | Outbreaks ready by day 90 | Median day | False, scoring OS's model | False, scoring real data alone |
|---|---:|---:|---:|---:|
| Green Light (10 deaths, 0.99), adopted | 22 | 38 | 0 (in-sample) | 17 (incl. 1 where real data could not train) |
| Green Light (20, 0.98), old | 23 | 46 | 2 | 18 |
| Riley et al. minimum sample size | 5 | 24 | 0 | 2 (COVID 2020 day 38, COVID 2021 day 14) |
| 10 events per predictor | 5 | 32 | 1 | 1 |

- **Riley settings:**
  - P = 56 predictor parameters; shrinkage 0.9; Nagelkerke optimism 0.05; overall risk within 0.05.
  - Anticipated R² = Nagelkerke R² of the pooled past model (0.21–0.30), rescaled to fob's current death share.
  - Riley requires 2,100–7,100 patients with a known outcome. 18 of 23 outbreaks never reach that in 90 days.
- **Plain reading:**
  - Sample-size rules are built for models fitted on fob's own data. They are mostly too strict here: they turn on
    in the three COVID seasons and two large flu seasons (2016 on day 66, 2022 on day 24), never in any other-virus
    season and in no other flu season, though OS is good from day 0 in those seasons. (Corrected 2026-10-13: this
    line first said "never in flu and other-virus seasons", which was wrong for flu 2016 and 2022.)
  - When they do turn on, real data alone is still not always ready (2 of 5).
  - The Green Light is a readiness signal for a model that borrows. That is a different question, which these
    rules do not answer.

---

## 2026-10-07 — Exp. 14: outcomes used only once known (Exp. 5d, 8d, 10d)

**Fix for the validity issue below.**
- New library columns: `DT_KNOWN` = later of entry and outcome date (`DT_EVOLUCA` / `DT_OBITO`), falling back to the
  closure date (`DT_ENCERRA`); `DT_KNOWN_CLOSE` = later of entry and closure date.
- `outcome_timing = "known"`: on day t a patient's outcome is used only if `DT_KNOWN` is on or before t. Patients
  without a known outcome still count for the profile (who is hospitalised) and for the stability check; past
  outbreaks in the Atlas use only outcomes known before fob's day 0.
- `outcome_timing = "entry"` (the default) reproduces every earlier output exactly (checked under the same parallel
  workers). Library rebuilt; the old columns are identical (2,142,720 rows).
- **Not covered:** Mexico has no outcome date for survivors, so Exp. 11/12 stay on entry timing (optimistic). A
  closure-date sensitivity run (`outcome_timing = "closure"`) has not been run yet.

**Runs** (Brazil library, same seeds and settings as Exp. 5c/8c/10c, `vote_prior = "group"`):
- `exp05d_kinship_known` (step 1, Kinship Vote);
- `exp08d_os_replay_known` (steps 2–3);
- `exp10d_synth_known` (step 4, dependency chain, 50,000 rows, seed 0) on the re-chosen Green Light days below.
- `os_core.FINAL_CFG` now uses these runs; Glass Box reports regenerated (COVID 2020 days 14 and 54, flu 2016 day 32).

### Results
| | Entry timing (8c/10c) | Known timing (8d/10d) |
|---|---:|---:|
| Step 1: right group, week 1 / 2 / 4 / 8+ | 86% / 90% / 90% / 95% | 90% / 90% / 90% / 95% |
| Step 1: right when 95% or more sure | 97.4% | 97.6% |
| Stranger over half, COVID 2020 | week 3–4 (749 patients) | week 4 (3,538 patients) |
| Steps 2–3: mean gap to gold, days 0–90 (label fallback, 20 deaths) | 0.0039 | 0.0053 |
| Steps 2–3: days below age only | 50 | 66 (flu 2021: 30) |
| COVID 2020: plateau OS / real data alone | 28 / 34 | **36 / 36** |
| COVID 2020: OS AUC on day 28 | 0.753 | 0.728 |
| Familiar flu and other-virus seasons: plateau | day 0 | day 0 (unchanged) |
| Green Light, old rule (20 deaths, 0.98): greens / false | 22 / 0 | 23 / **2** (flu 2013 day 54, other virus 2017 day 52) |
| Green Light, rule re-chosen leave-one-outbreak-out: greens / false / median day | 22 / 0 / 40 | 22 / 1 / 37 (other virus 2017 under 10, 0.98) |
| Green Light fixed at (10 deaths, 0.99), in-sample: greens / false / median day | — | 22 / 0 / 38 |
| COVID 2020 green day | 44 | 54 |
| Step 4: OS synthetic-only AUC (22 outbreaks) | 0.7942 | 0.7960 |
| Step 4: real records OS had (known outcomes in 10d) | 0.7305 | 0.7303 |
| Step 4: synthetic-only beats real records OS had | 20 / 22 | 21 / 22 |
| Step 4: outbreaks < 1,000 records, real → real + OS synthetic | 16: 0.723 → 0.804 | 15: 0.718 → 0.804 |
| Step 4: largest synthetic vs real death rate gap (early records) | 0.014 | 0.020 |

- **Plain reading:**
  - Part of the early COVID result came from outcomes that were not known yet. With realistic timing, OS reaches the
    plateau no earlier than real data alone for COVID 2020; its COVID advantage is gone.
  - The advantage on familiar seasons holds: OS is at the plateau from day 0.
  - The old Green Light settings gave 2 false greens, so the settings were re-chosen. Each outbreak's setting is
    chosen on the other 22. Under that held-out check, 1 false green remains (other virus 2017).
  - The adopted (10, 0.99) is clean only on the data it was chosen on. The final untouched test must confirm it.
  - Step 4 numbers barely move; they are scored on later patients against the real records OS had, which now hold
    only known outcomes.
- **Settings now adopted** (`FINAL_CFG`): Exp. 5d / 8d, group start, known timing, Green Light at 10 deaths with a
  known outcome and stability 0.99.

---

---

## 2026-10-07 — Literature positioning, and a validity issue found in the replays

**Full note:** `docs/literature_positioning.md` (targeted search, not systematic; references to verify before citing).

### Positioning
- **Already known:**
  - transfer from earlier diseases to COVID-19 outcomes (Lichtner et al. 2021; Agarwal et al. 2022, TRANSMED);
  - Bayesian dynamic borrowing (power, commensurate and robust MAP priors; multi-source exchangeability models);
  - meta-learning across clinical tasks (MetaPred);
  - choosing a generator from dataset traits (SYNTHONY);
  - synthetic augmentation of small health tables (Liu, El Emam et al. 2025).
- **Not found in this search** (OS's possible contribution):
  - a time-respecting replay benchmark over many real outbreaks;
  - choosing which past outbreaks to borrow from, week by week, with a "none of the above" option;
  - a readiness signal checked for honesty;
  - synthetic data release gated by it, with an interpretable report.

### Baselines reviewers will expect
- pooled past model + fine-tuning;
- robust MAP or commensurate prior, or multi-source exchangeability borrowing;
- a MetaPred-style meta-learner;
- TVAE, TabDDPM and a Bayesian network or ARF (via synthcity), plus bootstrap resampling;
- Riley et al.'s minimum sample size as a readiness baseline.

### Validity issue: the replays use outcomes before they were known
Every replay (Exp. 2–12) used each patient's final outcome as soon as the record was entered. In a live system,
patients still in hospital have no outcome yet. COVID-19 Brazil 2020, share of entered patients whose outcome date
(`DT_EVOLUCA`) had passed:

| Day | Patients used | Outcome known by then | Deaths used | Deaths known by then |
|---:|---:|---:|---:|---:|
| 21 | 88 | 22% | 35 | 10 |
| 28 | 1,084 | 32% | 363 | 127 |
| 44 | 9,333 | 59% | 2,822 | 1,645 |
| 90 | 79,854 | 79% | 29,790 | 25,083 |

- The real gap is larger: outcomes are typed in after they happen.
- **Early-day results so far are therefore optimistic,** for every method compared (OS, real data alone, the Green
  Light). Comparisons between methods may hold up better than absolute numbers, but this must be re-tested.
- **Fix before any paper:** use an outcome only after the date it became known (outcome or closure date). Leave out
  or explicitly model patients without an outcome yet.

---

## 2026-10-07 — Case Study 2 data check: vaccine adverse-event reports

### VAERS (United States)
- The yearly CSV files are public, but every download sits behind a **CAPTCHA** (`vaers.hhs.gov/eSubDownload`), so
  they cannot be fetched automatically. That will not be worked around.
- Options: the owner downloads the files by hand and adds them, or we use CDC WONDER's aggregate queries.

### Brazil ESAVI: usable (`scripts/download_esavi.sh`)
- **Source:** Ministério da Saúde (CGFAM/DPNI), dataset `esavi` on dadosabertos.saude.gov.br, **CC-BY**.
- **File:** a live snapshot; this download was last modified 2026-10-05; SHA-256 in `data/raw/esavi/SHA256SUMS`.
- **Size:** 396,980 notifications, one row each; 396,620 with a notification date from 2021 on. The few earlier
  dates are entry errors; the system effectively starts with the 2021 COVID-19 rollout.
- **Fields (73):** age, sex, state, pregnancy; vaccine(s), manufacturer, dose, lot, vaccination date; reaction text
  and code (MedDRA, version mostly "not defined"); onset date; seriousness (e.g. hospitalisation, death); outcome;
  causality assessment; notification and closure dates. The file is UTF-8.
- **Reports by vaccine (2021+):** AstraZeneca/Covishield 101,193; Pfizer 69,137; CoronaVac 56,672; Janssen 8,777;
  plus dengue, influenza and routine childhood vaccines.

### Known signals visible in the raw reports (simple text match on the reaction field)
| Signal | Reports | With the expected vaccine | Profile | Timing (expected vaccine) |
|---|---:|---:|---|---|
| Myocarditis / pericarditis | 125 | 95 Pfizer | **74% male, median age 30** | 2 in 2021 Q2, 10 in Q3, **47 in Q4**, 15 in 2022 Q1 |
| Thrombosis with thrombocytopenia | 64 | 45 AstraZeneca / Covishield | 56% female, median age 40 | 1 in 2021 Q1, 10 in Q2, **20 in Q3**, 3 in Q4 |
| Intussusception | 11 | 9 including rotavirus vaccine | – | – |
| Narcolepsy (Pandemrix, 2009) | 0 | – | – | outside this dataset's years |

**Verdict:** Case Study 2 is **feasible on Brazil's ESAVI data** for the COVID-19 signals.

**Caveats:**
- **Counts are small** (tens to about 100 reports per signal).
- **No dose counts** in this file. Standard disproportionality methods (PRR, ROR, BCPNN, MGPS) need only report
  counts. Observed-vs-expected methods need doses, which would come from Brazil's vaccination open data.
- **Reports are spontaneous:** they do not prove the vaccine caused the event. Reporting also rises after media
  coverage, and both signals were already known worldwide when most Brazilian reports arrived.
- **The reaction field is partly free text,** so the event definitions need care and a clinical check.

---

## 2026-10-07 — Adopted: Kinship Vote starts equal per pathogen group (Exp. 5c, 8c, 10c, 13 re-analysed)

**Change:** `kinship.start_shares(kin, "group")`.
- Each pathogen group (flu incl. H1N1 / other virus / COVID) gets an equal starting share of the vote, split
  equally among its members.
- The Stranger keeps its old starting share of 1/(K+1), so only fairness between groups changes.
- Before, every past outbreak started equal, so bigger groups started ahead.
- The old rule stays available as the default `"outbreak"` and reproduces every earlier output. Re-running the
  Exp. 5b analysis with it gave differences only in the 16th–17th significant digit; the committed files were kept.

**Runs (same weekly scores, Exp. 5b; only the starting shares change):**
- `exp05c_kinship_groupprior` (step 1 analysis; vote sharpness re-chosen leave-one-outbreak-out: 0.01 or 0.03);
- `exp08c_os_replay_groupprior` (steps 2–3, about 40 minutes);
- `exp10c_synth_chain_groupprior` (step 4, dependency-chain generator);
- small-outbreak votes re-analysed (`results/exp13*_votes_groupprior.csv`).
- `os_core.FINAL_CFG` holds the adopted settings; the Glass Box reports were regenerated with them.

### Results
| | Equal per outbreak (before) | Equal per group (adopted) |
|---|---:|---:|
| Step 1: right group, week 1 / 2 / 4 / 8+ | 86% / 81% / 95% / 95% | 86% / **90%** / 90% / 95% |
| Step 1: right when 95% or more sure | 99.3% | 97.4% |
| Steps 2–3: mean gap to gold, days 0–90 | 0.0040 | **0.0039** |
| Steps 2–3: days below age only (23 outbreaks × 90 days) | 64 | **50** |
| Green Light: greens / false / median day | 22 / 0 / 40 | 22 / 0 / 40 |
| COVID 2020: plateau / green day | 28 / 44 | 28 / 44 |
| Step 4: OS synthetic-only AUC (22 outbreaks) | 0.7945 | 0.7942 |
| Step 4: real + OS synthetic, outbreaks < 1,000 records | 0.805 | 0.804 |
| Step 4: worst link gap vs later real | 0.154 | 0.154 |
| Small outbreaks, present-day Atlas: MERS | flu 48%, COVID 47% | **COVID 66%**, flu 31% |
| Small outbreaks, present-day Atlas: H7N9 | flu 52%, COVID 28% | COVID 46%, flu 38% |
| Small outbreaks, present-day Atlas: Ebola | flu 57%, COVID 27% | COVID 44%, flu 42% |

- The fewer days below age come from flu 2021 (24 → 16) and other virus 2015 (14 → 8).
- **Plain reading:** in Brazil, where flu and other-virus groups are about the same size, the change is small and
  slightly positive, with nothing made worse. It matters when groups are uneven: in today's Atlas MERS now leans
  clearly COVID-like.
- **Not rerun:** the Mexico replays (Exp. 11/12) still use the old start. Mexico 2021's only COVID relatives already
  hold 100% of the vote, and Mexico 2020 has no COVID relatives, so their outcome should not change.

---

## 2026-10-07 — Vote-only test on small line lists: Ebola, H7N9, MERS (Exp. 13, 13b)

### Data (`scripts/download_small.sh`, SHA-256 recorded; `library.py --small` → `data/processed/library_small.parquet`)
| Outbreak | Source and licence | Patients used | Died | Ordered by |
|---|---|---:|---:|---|
| Ebola, Sierra Leone 2014 | Kenema Government Hospital (Schieffelin et al.), Zenodo 2614046, "other-open" | 83 EBOV-positive with known outcome | 74.7% | outcome date |
| H7N9 influenza, China 2013 | R package `outbreaks` 1.9.0 (GPL ≥ 2) | 74 with known outcome and a date | 40.5% | outcome date |
| MERS, South Korea 2015 | ECDC early-weeks data, R package `outbreaks` 1.9.0 (GPL ≥ 2) | 162 | 11.7% (provisional) | report date |

- **Fields:** age and sex only; their other fields do not match the Atlas. All patients are treated as hospitalised.
- **Too small for a full test:** these outbreaks cannot support a later test window or a gold AUC, so only the
  Kinship Vote and Stranger Flag are tested.
- **Two Atlas modes:**
  - Exp. 13, time-respecting: only outbreaks that started earlier;
  - Exp. 13b, present-day: every Brazil and Mexico outbreak, as if the pathogen appeared today (new
    `present_day_atlas` option; the default is unchanged).
- Vote sharpness 0.01, as in Brazil.

### Results (final week; full tables in `results/exp13*_votes.csv`)
| | Time-respecting Atlas | Present-day Atlas |
|---|---|---|
| **Ebola** | 5 relatives; Stranger 33%; flu 87% | Stranger 10%; flu 57%, COVID 27%; novelty gap 0.23 |
| **H7N9** | only H1N1 as relative; Stranger 51% → 66% | Stranger 5%; flu 52%, COVID 28%; closest single relative: **Mexico COVID 2021** |
| **MERS** | 7 relatives; Stranger 30%; flu 90% | Stranger 7%; **flu 48%, COVID 47%** (COVID 20% in week 0); closest: **COVID 2021** from week 1 |

### What this shows
1. **With a few hundred patients or fewer, the Stranger cannot win.**
   - Ebola, with 75% deaths among young adults and a novelty gap of 0.23, never got past 33%.
   - In Brazil and Mexico the Stranger needed 750–1,300 patients.
   - For small outbreaks, the **lab-label fallback** (new pathogen group → age trend) is the protection, not the Stranger Flag.
2. **The vote groups outbreaks by who gets sick and who dies, not by virus family.**
   - MERS (a coronavirus) moves towards COVID.
   - So does **H7N9 (an influenza)**: its patients are older with high mortality, like COVID's.
   - With age and sex only, that is all the vote can see. This is why the lab label stays a separate input.
3. **Design issue found: groups with more members start ahead.** Every past outbreak starts with an equal vote,
   so the group shares in week 0 simply reflect group size (flu 11, other virus 10, COVID 5 outbreaks: 43% / 38% / 20%).
   Recomputing with an equal start **per group** (offline, from the logged scores):

| Final week | Equal start per outbreak (as built) | Equal start per group |
|---|---|---|
| MERS | flu 48%, COVID 47% | **COVID 66%**, flu 31% |
| H7N9 | flu 52%, COVID 28% | COVID 46%, flu 38% |
| Ebola | flu 57%, COVID 27% | COVID 44%, flu 42% |

   Equal-per-group is fairer when groups differ in size, but switching would change every earlier vote and needs
   a rerun of Steps 1–3. **Proposed, not adopted.**

---

## 2026-10-07 — Out-of-country test: Synth Release on Mexico (Exp. 12)

**Run:** `OUTBREAK_LIB=data/processed/library_intl.parquet`, config `experiments/exp12_synth_mexico.toml`.
Dependency-chain generator, 50,000 rows; CTGAN as in Exp. 9. Outputs: `results/exp12_synth_mexico.json`,
`results/exp12_synth_mexico_manifest.json`.

| | Mexico 2020 (green day 48, 4,862 real records) | Mexico 2021 (green day 18, 33,830 real records) |
|---|---:|---:|
| Gold / age only | 0.698 / 0.693 | 0.680 / 0.674 |
| OS's own model | 0.691 | 0.679 |
| Real records OS had, alone | 0.691 | 0.679 |
| **OS synthetic only** | **0.689** | **0.679** |
| Real + OS synthetic | 0.689 | 0.679 |
| CTGAN synthetic only | 0.572 | 0.666 |
| Real + CTGAN | 0.603 | 0.679 |

| Fidelity (lower = closer) | OS vs real OS had | CTGAN vs real OS had | OS vs later real | Drift: early vs later real |
|---|---:|---:|---:|---:|
| **Mexico 2020:** death rate gap / worst age-band gap | 0.003 / 0.018 | 0.086 / 0.344 | 0.016 / 0.063 | 0.013 / 0.065 |
| **Mexico 2020:** worst correlation gap | 0.036 | 0.369 | 0.095 | 0.087 |
| **Mexico 2021:** death rate gap / worst age-band gap | 0.001 / 0.005 | 0.024 / 0.168 | 0.182 / 0.138 | 0.183 / 0.142 |
| **Mexico 2021:** worst correlation gap | 0.024 | 0.163 | 0.082 | 0.074 |

**Plain reading**
- **OS's synthetic patients match the real ones closely in another country and form.** Death rates are within
  0.3 points and links within 0.04. CTGAN is 3–10 times further off.
- **Against later patients,** OS synthetic is as far as the real early data itself. Mexico 2021's early patients
  (January 2021 wave) died far more often than later ones: 18 points of drift. OS reproduces the data it had and
  cannot anticipate that change.
- **Usefulness:** both Mexico outbreaks had plenty of real records by the green day (4,862 and 33,830), so synthetic
  data adds nothing over the real records (0.689 vs 0.691; 0.679 vs 0.679). This matches Brazil, where the gain from
  OS synthetic came in outbreaks with under 1,000 real records.
- **CTGAN** is clearly worse with about 5,000 records (0.572) and close to real with 20,000 (0.666).

---

## 2026-10-07 — Out-of-country test: Mexico COVID-19 2020 and 2021 (Exp. 11)

### Data
- Mexico, Secretaría de Salud / Dirección General de Epidemiología, open COVID-19 surveillance (SISVER),
  year-closure files 2020 and 2021 (`scripts/download_mexico.sh`, SHA-256 recorded).
- Terms: the DGE "Términos de Libre Uso de Datos Abiertos" (reuse with attribution).
- Cohort: hospitalised (TIPO_PACIENTE 2), confirmed COVID-19 (CLASIFICACION_FINAL 1–3); death = date of death recorded.
  - covid_mx_2020: 326,886 patients, 46.0% died.
  - covid_mx_2021: 297,685 patients, 47.5% died.
- **Field mapping:** diabetes → metabolic, cardiovascular → heart, EPOC (COPD) → chronic lung, chronic kidney → kidney,
  immunosuppression, obesity.
- **What the Mexican form lacks:** no symptoms (fever, cough, …), race, liver, neurological, postpartum or Down
  syndrome fields.
- **No data-entry date:** records are ordered by **admission date**, which ignores reporting delay. That is more
  optimistic than the Brazil replays.
- **Separate library:** Mexico lives in `data/processed/library_intl.parquet` (selected with `OUTBREAK_LIB`).
  The Brazil-only library and every earlier result are unchanged.
- **Settings:** all fixed from the Brazil experiments (vote sharpness 0.01, borrowing strength 10, fallback until
  20 fresh deaths, Green Light at 20 deaths and stability 0.98). Nothing was tuned on Mexico.

### Fix needed first: compare only fields fob's form collects
- The first vote gave Mexico 2020 a novelty gap of **7.08** (Brazil COVID 2020: 1.10). The cause was form, not
  disease: Mexico records no symptoms, so every patient looked like "no fever, no cough" against about 85% fever in Brazil.
- The Kinship profile now uses only the fields fob's form collects, which is known on day 0.
- Brazil replays are byte-identical after the change: flu 2016 and COVID 2020 weekly scores both differ by 0.0.

### Kinship Vote (`results/exp11_kinship_mexico*`)
- **Mexico 2020:**
  - novelty gap 0.75 (closest past outbreak in hindsight: flu 2019);
  - Stranger 6–7% in weeks 0–2, 27% in week 3 (474 patients), **97% in week 4** (1,262 patients);
  - Brazil COVID 2020 for comparison: 52% in week 3 (749 patients), 100% in week 4.
- **Mexico 2021:**
  - Mexico 2020 gets 100% of the vote from week 0, Stranger 0%;
  - in hindsight the runner-up is **Brazil COVID 2020** (−4.44 nats per patient), ahead of every flu season
    (−4.75 or lower), so same-disease similarity across countries is recognised.

### OS replay (`results/exp11_os_mexico.json`)
| | Mexico 2020 | Mexico 2021 |
|---|---|---|
| Test window (later patients) | July 2020: 48,868 (21,404 deaths) | days 91–182: 34,013 (13,368 deaths) |
| Gold / age only | 0.698 / **0.693** | 0.680 / 0.674 |
| OS on day 0 | 0.693 (age fallback) | 0.667 (borrowing from Mexico 2020) |
| Always borrowing, days 0–20 | 0.61–0.63 | – |
| Fallback ends | day 22 (20 fresh deaths) | – (not a new group) |
| OS days 22–34 | **0.635–0.685, below age only** | 0.679 from day 8 |
| Real data alone | 0.589 (day 18) → 0.685 (day 34) | 0.660 on day 0, 0.679 from day 8 |
| Green Light | **day 48**, AUC 0.691 (honest) | **day 18**, AUC 0.679 (honest) |

- **What replicated:**
  - the vote's timing on a new pathogen;
  - the label fallback (it kept OS about 0.07 above "always borrow" in the first three weeks);
  - honest Green Lights in both outbreaks.
- **What did not:** after leaving the fallback on day 22, OS sat below age only for 34 of the 90 days, by up to 0.058.
  - Real data alone was also below age only over the same days, so the early Mexican patients rank July's patients
    worse than age does. This is a shift between early and later patients, not a borrowing error.
  - A stricter exit rule ("leave the fallback only when borrowing beats age on fresh patients") would not have
    helped: on fresh early weeks borrowing looked better (0.736 vs 0.662). It would also have delayed Brazil COVID's
    plateau from 28 to 36, so it was not adopted.
- **With Mexico's fields** (age, sex and 6 conditions, no symptoms), age alone is within 0.005 of gold in both years.
  There is little room for any learner to beat it. The plateau measure ("within 0.02 of gold") is met by age alone
  on day 0, so it is not informative here.

---

## 2026-10-07 — Links between symptoms: dependency-chain generator (Exp. 10)

**Code:** `synth.py` (`fit_chain`, `generate_chain`); config `experiments/exp10_synth_chain.toml`. Same outbreaks,
green days, seed and 50,000 rows as Exp. 9; CTGAN not rerun. Output: `results/exp10_synth_chain.json`.
The Glass Box reports now use this generator.

**Method:** the 16 yes/no fields are drawn one after another, in a fixed clinical order (symptoms, then conditions).
Each is drawn from a logistic model on age band, sex and every field drawn before it. Each link model is fitted
like OS's Severity Model:
- prior = vote-weighted chain coefficients of the relatives (only relatives whose form collected both fields);
- strength 10 × (1 − Stranger), with a weak pull to 0 where that falls below 1;
- no borrowing on the new-pathogen-group fallback;
- a field fob's form did not collect is always "no".

### Results (mean over 22 outbreaks)
| Measure | Independent (Exp. 9) | Chain (Exp. 10) | Natural drift: early vs later real |
|---|---:|---:|---:|
| Worst link gap vs later real patients | 0.311 | **0.154** | 0.281 |
| Mean link gap vs later real patients | 0.044 | **0.032** | 0.053 |
| Worst link gap vs real records OS had | 0.389 | 0.273 | – |
| Yes/no rate gap vs real records OS had | 0.009 | **0.001** | – |
| AUC, trained on OS synthetic only | 0.795 | 0.795 | – |
| AUC, real records + OS synthetic | 0.795 | 0.795 | – |
| Synthetic only at least as good as real alone | 22 of 22 | 20 of 22 | – |

- **Links vs later real patients improve in 22 of 22 outbreaks.** For the 6 outbreaks with at least 1,000 real
  records on the green day, the chain's link gaps against later patients are about the same as the real data's own
  drift. For example, COVID 2020: worst gap 0.115 vs drift 0.119 (was 0.363).
- **Against the small real samples OS had,** the worst gap stays high for some outbreaks (other virus 2014–2016:
  about 0.5–0.58). Their real correlations come from 100–550 patients and are noisy. Against the larger later
  samples, the chain does better.
- **AUC is unchanged on average** (largest single drop 0.007). The two outbreaks where synthetic-only now falls just
  under real-only are flu 2022 (0.769 vs 0.775) and COVID 2022 (0.742 vs 0.743).

**Plain reading:** the chain fixes the generator's main weakness. Links between symptoms and conditions are now as
realistic as the real data's own change over time, with no loss of usefulness.

---

## 2026-10-07 — Step 4: Synth Release + Glass Box Report (Exp. 9)

**Code:**
- `os_core.py`: OS's final rule as one piece; rebuilds the state on any day.
- `synth.py`: the generator and side-by-side comparison.
- `run_synth_release.py`, `scripts/ctgan_baseline.py`, `glass_box.py`.

**Config:** `experiments/exp09_synth_release.toml`.

**Outputs:**
- `results/exp09_synth_release.json` and `results/synth_manifest.json` (provenance and SHA-256 of every synthetic file);
- synthetic files in `data/synthetic/` (git-ignored, names start with `SYNTHETIC_`);
- reports in `reports/glass_box_*.html`.

**CTGAN baseline:**
- runs in an isolated environment (`.venv-ctgan`, pinned in `requirements-ctgan.txt`), because installing it
  downgraded pandas 3.0.6 to 2.3.3 in the main environment; that was reverted;
- 300 epochs, trained on at most 20,000 of the real records OS had.

### Method
- **When:** each outbreak's Green Light day under OS's final rule (22 outbreaks).
- **Generator,** 50,000 rows per outbreak and per generator, from the Two-Part Recipe:
  - age band, sex and each yes/no field given age band: fob's counts plus pseudo-counts borrowed from the voted
    relatives, with strength 10 × (1 − Stranger), and none on the new-group fallback;
  - age: resampled from fob's ages in the band;
  - state: fob only;
  - race given state: from fob;
  - death drawn from OS's risk model.
- **Labels:** every row has `synthetic=True` and a provenance string (outbreak, day, number of real records and
  deaths learned from, recipe, seed).
- **Two fixes made while building this:**
  1. When the Stranger holds the whole vote, borrowing strength is 0 and rare groups had unbounded coefficients
     (ages 1–4 in COVID 2020: −18.9, SE 4,597). A minimum shrinkage of 1.0 fixes this with the AUC unchanged
     (0.758 → 0.758).
  2. That minimum first pulled towards the relatives' values, which quietly brought borrowing back. It now pulls
     towards "no effect", and "still borrowed" counts only pulls towards a relative.
- **Checks:**
  - fidelity against the real records OS had, and against the later real test window it never saw (with
    early-real vs later-real as the natural drift reference);
  - usefulness: AUC on the later window for a ridge model trained on each dataset.

### Usefulness (mean over 22 outbreaks; AUC on later real patients OS never saw)
| Trained on | Mean AUC |
|---|---:|
| Gold (all other real records of the outbreak) | 0.796 |
| OS's own model | 0.797 |
| **OS synthetic only** | **0.795** |
| **Real records OS had + OS synthetic** | **0.795** |
| Ranking by age alone | 0.733 |
| Real records OS had, alone | 0.730 |
| Real + CTGAN synthetic | 0.646 |
| CTGAN synthetic only | 0.619 |

- **OS synthetic only** is at least as good as the real records alone in **22 of 22** outbreaks, never below age
  only, and within 0.007 of OS's own model.
- **Real + OS synthetic** beats real alone in **22 of 22**. For the 16 outbreaks with fewer than 1,000 real
  records on the green day: 0.723 → 0.805.
- **CTGAN** (trained on the same real records) is below real alone in 22 of 22 and below age only in 18. Adding
  it to real data hurts in 21 of 22 (e.g. flu 2014: 131 records, CTGAN-only AUC 0.385). It cannot learn from
  100–300 patients, which matches the small-sample weakness noted in the brief.

### Fidelity (mean over 22 outbreaks; lower = closer)
| Comparison | Age KS | Death rate gap | Worst age-band death-rate gap | Yes/no rate gap | Correlation gap (mean / worst) |
|---|---:|---:|---:|---:|---:|
| OS synthetic vs real records OS had | 0.058 | 0.004 | 0.108 | 0.009 | 0.052 / 0.389 |
| CTGAN vs real records OS had | 0.389 | 0.044 | 0.196 | 0.030 | 0.066 / 0.406 |
| OS synthetic vs later real | 0.159 | 0.033 | 0.101 | 0.026 | 0.044 / 0.311 |
| Early real vs later real (natural drift) | 0.145 | 0.033 | 0.169 | 0.025 | 0.052 / 0.281 |

- OS synthetic is far closer to the real data than CTGAN on every measure. Its distance from later real patients
  is about the same as the real data's own drift over time.
- **Weak spot:** links between fields (worst correlation gap 0.31–0.39). Within an age band, symptoms and conditions
  are drawn independently.
- The age-band death-rate gap against early real (0.108) is mostly the Handover Rule at work in small outbreaks.
  For example, flu 2016 on day 20: babies under 1 get a 7.4% death rate from relatives, while the 8 real babies
  seen so far all survived.

### Glass Box Report (`reports/`)
Produced for COVID 2020 on days 14 and 44 and for flu 2016 on day 20.
- **Contents:** Green Light status with each condition ticked or crossed, the Kinship Vote and Stranger share, the
  label fallback, a risk table (OS odds ratio with 95% interval, relatives' value, this outbreak alone, share still
  borrowed, number of patients), recent fresh-week evidence and stability, and Synth Release side by side.
  Hindsight replay scores are in a separate, clearly marked section.
- **Example, COVID 2020 on day 44:**
  - Stranger 100%, so nothing is borrowed;
  - 75+ vs under 1: odds ratio 15.1 (8.5–26.8);
  - kidney disease 2.49, obesity 2.43, low oxygen saturation 1.99;
  - Green Light on (2,822 deaths, stability 0.992).

### Plain reading
- **Synthetic data from OS carries OS's understanding of the disease, no more and no less.**
  - It is as useful as OS's own model.
  - On top of a small real dataset it adds what OS borrowed from past outbreaks, which is where the gain over
    "real alone" comes from (0.723 → 0.805 for small outbreaks).
  - It adds no information OS does not have. The Green Light decides when that understanding is good enough to release.
- **A standard generator trained only on the early real records (CTGAN) fails at these sizes** and makes models
  worse. That supports the project's starting idea: early synthetic data is only useful if it brings in knowledge
  from outside the few early records.
- **Next:** model links between symptoms (e.g. condition on age band and one or two strongly linked fields), and
  test on non-Brazilian outbreaks.

---

## 2026-10-07 — Step 3, round 2: age recipes, safety alarm, Green Light redone (Exp. 8)

**Code:** `run_os_replay2.py`, `analyse_os2.py` (incl. `offline_variants`); config `experiments/exp08_os_replay.toml`
(same settings as Exp. 7). Outputs: `results/exp08_os_replay*.{json,csv}`. Runtime about 40 minutes.

### What was added
- **Two recipes:**
  - kin_age borrows only the age-band pattern from the voted relatives;
  - age_trend uses one smooth age term whose slope prior is the median relative's slope. Whenever the slope is
    positive it ranks exactly like "rank by age", but it also gives risk numbers.
- **Safety alarm** (the Fresh-Days Check repurposed): candidates compared by AUC on fob's fresh records (each week
  predicted by a model fitted on earlier weeks), pooled over complete weeks. The default recipe, the minimum number
  of fresh deaths before switching, and the recipes allowed to compete are chosen by leave-one-outbreak-out.
- **Stability logged for every pair of recipes,** so the Green Light follows whatever the final rule uses. The
  light cannot be green while OS is on the age_trend fallback.

### Result 1: neither new recipe nor the outcome-based alarm beats plain kin borrowing
| Always use | Mean gap to gold, days 0–90 |
|---|---:|
| **kin** | **0.0046** |
| consensus | 0.011 |
| kin_age | 0.022 |
| age_trend | 0.065 |
| own | 0.082 |

- The best alarm rule (switch after 100 fresh deaths) scores 0.0047, so it adds nothing.
- Leave-one-outbreak-out picked "always kin" for nearly every outbreak. The one variant it picked for COVID switched
  to age_trend on days 28–34, exactly when kin had overtaken age, which pushed COVID's plateau from 28 to 36.
- **Why the alarm cannot help early:** it needs outcomes. COVID 2020 has at most 1 fresh death up to day 20 and 8 by
  day 26, so no outcome-based check can tell in weeks 0–3 that borrowing from flu is wrong.
- kin_age did help flu 2013 early (smoke test: 0.705 vs 0.671 on day 8) but is worse overall.

### Result 2: a pathogen-label fallback fixes the truly new cases
Rule: if fob's pathogen group (flu including H1N1 / other virus / COVID) has no earlier member in the Atlas, use
age_trend until 20 fresh deaths, then kin. The label ("a new kind of virus") is external information a lab has on
day 0; it is not learned from fob's records.

| | Always kin | Label fallback (E = 20) |
|---|---:|---:|
| Mean gap to gold | 0.0046 | **0.0040** |
| Outbreaks ever below age only | 6 | 4 |
| Total days below age only (23 outbreaks × 90 days) | 110 | 64 |
| At least as good as age only on day 0 / 14 / 28+ | 17 / 19 / 23 | 19 / 21 / 23 |
| **COVID 2020, days 0–26** | 0.685–0.743 (24 days below age) | **0.727, never below age** |
| COVID 2020 plateau (real data alone: 34) | day 28 | day 28 |
| other virus 2013, days 0–28 | 0.714–0.775 (22 days below) | 0.747, never below |

- **Caveat:** only 2 outbreaks are a "new group" (COVID 2020 and other virus 2013), so E = 20 is a judgement call,
  not a tuned value. E = 100 left other virus 2013 on age_trend for all 90 days.
- **Still below age only on some days:**
  - flu 2013, 20 days: H1N1 is a same-group but misleading relative, so the label does not trigger;
  - flu 2021, 24 days, by about 0.01: here age only (0.798) beats even gold (0.774);
  - COVID 2021, 6 days around day 0;
  - other virus 2015, 14 days, by about 0.01.

### Result 3: Green Light, redone on the final rule
Rule: at least 20 deaths, and risk-score stability of at least 0.98 vs 8 days earlier, on two checks in a row, and
not on the age_trend fallback. (m, s) = (20, 0.98) was the leave-one-outbreak-out choice for 22 of 23 outbreaks.

| Rule path | Greens within 90 days | False greens | Median green day | COVID 2020 green |
|---|---:|---:|---:|---|
| Always kin | 22 of 23 | **0** | 40 | day 44 (AUC 0.757 vs gold 0.767) |
| Label fallback (E = 20) | 22 of 23 | **0** | 40 | day 44 |

- The only outbreak never green is other virus 2013.
- On the leave-one-outbreak-out rule path (`analyse_os2.main`): 22 greens, 1 false (other virus 2017, day 36: 0.774
  vs gold 0.796), median day 37.

### Plain reading
- **OS's current best form:**
  - borrow from voted relatives;
  - start on the age trend when the lab says the pathogen group is new;
  - turn green after 20 deaths once the risk ranking stops moving.
- In replays this was never worse than "rank by age" for a new pathogen group, and gave **no false green lights**
  across 22 outbreaks.
- **COVID 2020 under this rule:** OS matches age only for days 0–26, reaches the plateau on day 28 (real data alone:
  34), and turns green on day 44.
- **What did not work:**
  - outcome-based safety checks, which come too late because the early days have almost no deaths;
  - borrowing only the age pattern;
  - borrowing only what relatives agree on.
- **Open:**
  - a misleading relative within the same group (H1N1 for the 2013 flu season) is still not caught early;
  - the label-fallback evidence rests on only 2 new-group outbreaks.

---

## 2026-10-07 — Step 3: Fresh-Days Check, consensus fallback, Green Light (Exp. 5b, Exp. 7)

**Code:**
- `run_kinship_replay.py` (`day0_mode = "threshold"`), `run_os_replay.py`, `analyse_os.py` (incl. `min_evidence`).
- Configs: `experiments/exp05b_kinship_replay.toml`, `exp07_os_replay.toml`.
- Outputs: `results/exp05b_*`, `results/exp07_os_replay*.{json,csv}`. Runtime about 25 minutes.

### Changes agreed with the owner
- **Seasonal day 0:** for flu and other-virus seasons, the first week with at least 20 new records (knowable in
  real time). COVID and H1N1 keep their first record. For example, flu 2013 now starts on 2013-04-02, with 3,210
  patients in its first 90 days instead of 116.
- **Step 1 rerun (Exp. 5b)** with these start dates: right group 86% at week 1, 95% from week 4. Calibration is
  unchanged (votes of 0.95 or more are right 99% of the time).
- **Three candidate recipes,** all with borrowing strength 10 (from Exp. 6b):
  - kin: the vote-weighted relatives;
  - consensus: borrow a coefficient only if at least 3 past outbreaks collected the field and at least 80% agree
    on its direction;
  - own: borrow nothing.
- **Fresh-Days Check:** each week, every candidate is fitted on earlier records and scored (log score) on that
  week's records, which it has not seen. OS uses the best cumulative score; consensus is the default before any week is scored.
- **Green Light:** at least m deaths so far, and the rank correlation of OS's risk scores for fob's patients today
  vs 8 days earlier at least s, on two checks in a row. (m, s) is chosen by leave-one-outbreak-out. A green is false
  if OS is more than 0.02 below gold on that day.
- **Age only** is now a standing baseline.

### Result 1: the Fresh-Days Check as first built made things worse early
It switched recipes on tiny samples. In COVID week 1 there were about 5 scored patients, and "own" won by chance.
- COVID 2020 fell to 0.55–0.61 on days 8–20 (age only: 0.727).
- flu 2017, flu 2019, flu 2021 and other virus 2018 dropped by up to 0.2 in their early weeks.
- OS beat age only on day 14 in just 12 of 23 outbreaks.

### Result 2: requiring evidence before switching fixes that, but then the Check adds nothing
Re-scored from the logged replay (`min_evidence`): keep a default recipe until E deaths have been scored on fresh weeks.
Leave-one-outbreak-out chose E = 100 with default kin for every outbreak.

| Rule | Mean gap to gold, days 0–90 |
|---|---:|
| Fresh-Days Check as first built | 0.033 |
| Fresh-Days Check with E = 100, default kin | 0.005 |
| **Always kin** (no Fresh-Days Check) | **0.0046** |
| Always consensus | 0.011 |
| Always own (no borrowing) | 0.082 |

- The Fresh-Days Check with E = 100 differs from "always kin" in only 6 outbreaks, and is slightly worse there.
- **Consensus is worse than kin** (0.011 vs 0.005), including for COVID 2020 on day 0 (0.677 vs 0.685).
  The "borrow only what past outbreaks agree on" fallback did not fix COVID's early weeks.

### Result 3: where OS stands now (E = 100, default kin, seasonal threshold start)
| Day | 0 | 14 | 28 | 56 | 90 |
|---|---|---|---|---|---|
| OS beats age only | 17/23 | 18/23 | **23/23** | 23/23 | 23/23 |

- **COVID 2020:**
  - days 0–20 ≈ 0.685–0.69, still below age only (0.727), 24 of the first 90 days below;
  - plateau on day 28 (real data alone: 34);
  - day 28 0.753, day 90 0.762, gold 0.767.
- **2013 seasons** (H1N1 as the only kin), now that day 0 is the season start:
  - flu 2013: 0.628 on day 0, 0.763 on day 28, 0.828 on day 90 (gold 0.827);
  - other virus 2013: 0.715 on day 0, 0.851 on day 90.
  - Both are still below age only for about 3 weeks.
- **Familiar seasons:** at or near gold from day 0, in most cases far ahead of real data alone.

### Result 4: Green Light (computed on the first-built Fresh-Days choices; to be redone on the final rule)
- 13 outbreaks got a green light within 90 days, **2 of them false**:
  - flu 2013 on day 36: 0.788 vs gold 0.827;
  - flu 2017 on day 60: 0.759 vs gold 0.795.
- 10 never turned green, mostly small seasons that never reached 100 deaths in 90 days.
- **COVID 2020 turned green on day 44** (0.758 vs gold 0.767, honest; plateau was day 28).
- Rules chosen: mostly 100 deaths and stability 0.98. The light is conservative: median green day 56.

### Plain reading
- **The biggest gain in this step came from the seasonal start date, not from the Fresh-Days Check.**
  With seasons starting when they really start, plain kin borrowing reaches the plateau very early.
- **Neither the Fresh-Days Check nor the consensus fallback improved on plain kin borrowing.**
  The Check is only safe when it waits for 100 scored deaths, and by then all recipes agree.
- **Open problem:** a truly new disease (COVID 2020) and a misleading relative (H1N1 for the 2013 seasons). Every
  recipe is below age only for the first 3 weeks, so OS has no candidate that is as good as "rank by age" there.
- **Green Light:** looks promising (11 of 13 greens honest, COVID's honest) but must be recomputed on the final rule.

---

## 2026-10-06 — Death rate by age across the Outbreak Atlas (`age_profile.py` → `results/age_profile.csv`)

Crude in-hospital death rate (hospitalised patients, known outcome), not adjusted for conditions.

| Group | <1 | 1–4 | 5–14 | 15–29 | 30–44 | 45–59 | 60–74 | 75+ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| COVID 2020 | 8.9% | 4.3% | 6.9% | 10.0% | 12.8% | 22.7% | 40.6% | 57.8% |
| COVID 2021–22 | 4.9 | 3.2 | 5.8 | 11.7 | 16.9 | 27.1 | 41.2 | 50.3 |
| flu 2013–2020 | 5.9 | 5.0 | 5.8 | 9.5 | 17.0 | 29.4 | 26.7 | 27.3 |
| flu 2021–22 | 1.7 | 1.7 | 2.0 | 4.6 | 9.4 | 17.0 | 20.5 | 25.7 |
| other virus 2013–22 (58,211 patients under 1) | 1.8 | 1.8 | 2.8 | 8.2 | 14.1 | 18.5 | 22.3 | 26.5 |
| **H1N1 2009** | 4.5 | 4.0 | 3.8 | 8.3 | 15.0 | **17.4** | 12.5 | **10.1** |

- "Older patients die more often" is established knowledge, not a finding of this project, and our data confirms it
  for 5 of 6 groups. The shape differs: COVID keeps rising to 58% at 75+, while seasonal flu flattens after 45.
- **H1N1 2009 breaks it:** death peaks at 45–59 and falls for 60+. This is why borrowing H1N1's pattern hurt the
  2013 seasons (Exp. 6/6b).
- Babies under 1 do worse than 1–4-year-olds in several groups.
- Consequence for Step 3: the safe fallback must not assume "risk rises with age". It borrows only patterns that
  most past outbreaks agree on, computed from the Atlas.

---

## 2026-10-06 — Why OS got worse over time in 2013, and a fix (Exp. 6b)

**Diagnosis:** `scripts/diag_2013_decline.py`.

### Findings
1. **Not a steady decline.** OS dropped as soon as the first 2–5 deaths arrived, then recovered as data grew.
   flu 2013: 0.640 on day 0 → 0.554 on day 18 (16 patients, 3 deaths) → 0.707 on day 90 (116 patients, 21 deaths).
2. **Cause (implementation flaw): columns with nothing to borrow were almost unpenalised.** These were state and
   the fields H1N1's 2009 form never collected. They had penalty 1, against an effective 10 for borrowed columns,
   so a handful of deaths swung them.
   - By day 18 of flu 2013 (3 deaths: ages 87, 52, 15; states RS, SP, PR) OS had learned "low oxygen saturation
     lowers death risk" (−0.84) and "São Paulo lowers death risk" (−0.87). Both are artefacts of 3 deaths.
   - Dropping state alone helped a little. Giving these columns the same penalty as borrowed ones removed the dip.
3. **Borrowing from a misleading relative.** Even before any fitting, H1N1's borrowed risk pattern (0.641) is below
   ranking by age (0.664). H1N1's death risk peaked at ages 30–60 and was lower over 75 (age-band coefficients
   0.99, 1.56, 1.62, 1.05, 0.74), the reverse of seasonal flu. It was the only relative available in 2013.
4. **Seasonal day 0.** Day 0 = 1 January for yearly seasons. The 2013 flu season peaked mid-year: only 116 patients
   arrived by day 90, against 3,555 in the test window, and the early patients were younger (median 29 vs 36).
   This does not affect COVID or H1N1, which have real start dates.

### Exp. 6b: fix for finding 2 (`experiments/exp06b_recipe_replay.toml`, `lam_free = "lam0"`)
Columns with nothing to borrow now shrink towards "no effect" with the same strength as borrowed columns.
Everything else is identical to Exp. 6, whose results are kept unchanged.

| | Exp. 6 | Exp. 6b |
|---|---:|---:|
| Mean gap to gold, days 0–90 (all outbreaks) | 0.026 | **0.018** |
| Borrowing strength chosen (leave-one-out) | 10 for 22 of 23 | 10 for all 23 |
| Plateau earlier / same / later than real data alone | 21 / 2 / 0 | 20 / 3 / 0 |
| Beats age only on day 14 | 18 of 23 | 19 of 23 |
| COVID 2020 plateau (real data alone: 34) | day 30 | **day 28** |
| COVID 2020, day 14 / day 28 | 0.681 / 0.744 | 0.688 / 0.753 |
| flu 2013, day 14 / day 28 | 0.565 / 0.575 | **0.631 / 0.631** |
| other virus 2013, day 28 | 0.670 | 0.699 |

- **Worse with the fix:**
  - other virus 2021: plateau day 28 → 60; its worst same-day gap against real data alone is now −0.035.
  - flu 2021: plateau day 58 → never.
  - other virus 2014: day 58 → 86.
  - flu 2014: day 6 → 14.
- **Still open:** COVID 2020 days 0–20 (≈0.685) and both 2013 outbreaks stay **below age only**. That is finding 3,
  which the fix does not address.

### Decisions needed
- How to handle a misleading relative (finding 3). Proposed: a safe fallback that borrows only patterns shared by
  most past outbreaks until the vote is confident, plus the Fresh-Days Check, with age only as a permanent baseline.
- Seasonal day 0 (finding 4). Proposed: start each season when weekly cases cross a threshold.

---

## 2026-10-06 — Step 2: Severity Model + Handover Rule vs real data only

**Code:** `src/outbreak_synth/recipe.py`, `run_recipe_replay.py`, `analyse_recipe.py`; config
`experiments/exp06_recipe_replay.toml`. Outputs: `results/exp06_recipe_replay.json`, `_summary.csv`, `_analysis.json`.
Runtime 21 minutes on 4 CPUs.

### Method
- **Severity Model:** logistic regression for in-hospital death, fitted with a prior.
  - Each risk factor's prior mean = the Kinship-Vote-weighted average of the kin's coefficients. Votes come from
    Step 1, using only weeks completed before the day in question.
  - Never borrowed: the intercept (fob's overall death rate), state (geography), and fields a kin's form did not collect.
  - Fields: all 26 shared fields (age band, sex, race, state, 6 symptoms, 10 conditions; yes vs not-yes).
- **Handover Rule:** borrowing strength = λ0 × (1 − Stranger share). The prior is fixed while the data term grows,
  so fob's own data takes over as patients arrive.
  - λ0 ∈ {1, 10, 100, 1000}, chosen per outbreak by leave-one-outbreak-out (minimum mean gap to gold over days
    0–90 on the other outbreaks). λ0 = 10 was chosen for 22 of 23 outbreaks.
- **Real only:** the same model with no borrowing (ridge). It needs at least 10 deaths and 10 survivors, as in Exp. 2/3.
- **Replay:** every outbreak with earlier kin (23), days 0–90 in steps of 2 days.
  - Test set = records entered on days 91–182; for COVID 2020, July 2020, the same as Exp. 2/3.
  - Gold = the same model class trained on every record of the outbreak outside the test window.
- **Age only:** a zero-learning baseline that ranks test patients by age.

### Results (test AUC; plateau = first day within 0.02 of gold)
| Outbreak | Gold | Age only | OS day 0 | OS day 14 | OS day 28 | Real day 28 | Plateau, real | Plateau, OS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **COVID 2020** | 0.767 | **0.727** | 0.685 | 0.681 | 0.744 | 0.743 | 34 | **30** |
| COVID 2021 | 0.716 | 0.683 | 0.646 | 0.706 | 0.709 | 0.709 | 10 | 8 |
| COVID 2022 | 0.751 | 0.657 | 0.729 | 0.739 | 0.744 | 0.744 | 8 | 4 |
| flu 2013 (only H1N1 as kin) | 0.802 | 0.664 | 0.640 | 0.565 | 0.575 | – | never | never |
| flu 2014–2020 (7 seasons) | 0.77–0.81 | 0.65–0.75 | 0.78–0.81 | 0.78–0.81 | 0.75–0.81 | mostly none | 84–88 or never | **0–6** |
| flu 2021 (during COVID) | 0.715 | 0.713 | 0.674 | 0.686 | 0.673 | – | never | 58 |
| flu 2022 | 0.775 | 0.710 | 0.771 | 0.764 | 0.774 | 0.778 | 10 | 0 |
| other virus 2013 (only H1N1 as kin) | 0.785 | 0.749 | 0.689 | 0.690 | 0.670 | – | never | never |
| other virus 2014–2022 (9 seasons) | 0.82–0.86 | 0.69–0.83 | 0.76–0.85 | 0.78–0.85 | 0.78–0.84 | mostly none | 68–76 or never | 0–58 (6 of 9 on day 0) |

- **Plateau:** OS reaches it earlier in 21 of 23 outbreaks, at the same time in 2 (neither arm got there), and later in none.
  Median plateau day: real only 51 among those that reached it (most never did within 90 days); OS 0.
- **Compared with real only on the same day,** OS is at most 0.02 worse (other virus 2021) and is up to 0.15 better.
- **Compared with age only on day 0,** OS is better in 18 of 23 outbreaks.
- In 3 seasons OS beats the gold standard, because the gold model is trained on that season's own small dataset.
- The real-only arm needs at least 10 deaths. Many seasons have fewer than that early on, so "never" often means
  "never had enough data", not "trained but poor".

### Plain reading
**Familiar outbreaks: a strong win.** For seasonal flu and other-virus seasons, OS is already at the plateau on
day 0 by borrowing from past seasons. Real data alone usually could not even train a model within 90 days.

**Novel outbreaks: the method fails where it matters most.**
- **COVID 2020** technically meets the step's target: plateau on day 30 against 34 for real data alone.
  But that is only 4 days, and on days 0–20 OS (0.655–0.685) is **worse than ranking by age** (0.727).
  - Cause: in weeks 0–2 the Kinship Vote trusted flu (the Stranger had only 4%), and flu's risk pattern beyond
    age misleads for COVID. Borrowing only helps once COVID's own data takes over (from about day 26).
- **The same failure** appears in every outbreak with a high novelty gap in Step 1: flu 2013 and other virus 2013
  (H1N1 was the only kin), and flu 2021 (flu during COVID). OS is worse than age only in all of them.
  - flu 2013 and other virus 2013 get **worse over time** (0.64 → 0.58), which needs investigating.
- **COVID 2021** starts below age only on day 0 (0.646 vs 0.683) and recovers by day 14.

**What this means for the design:** borrowing is only as good as the Kinship Vote's early call, and the Stranger
Flag is too slow to protect novel outbreaks. Candidate fixes for Step 3, not yet tested:
1. A **safe fallback**: until the vote is confident, borrow only what is shared by almost every respiratory
   outbreak (age), not every risk factor.
2. Let the **Fresh-Days Check** catch a misleading prior on fob's own newest days and weaken borrowing then.
3. Add **age only** as a permanent baseline alongside real only.

---

## 2026-10-06 — Step 1: Kinship Vote + Stranger Flag, Time Machine Replay over the Outbreak Atlas

**Code:** `src/outbreak_synth/kinship.py`, `run_kinship_replay.py`, `analyse_kinship.py`; config
`experiments/exp05_kinship_replay.toml`. Outputs: `results/exp05_kinship_replay.json` (hindsight answers),
`_weeks.csv` (weekly scores), `_votes.csv` (weekly votes), `_analysis.json` (summary).
Runtime about 4 minutes on 4 CPUs.

### How the vote works
- **Candidates:** every outbreak that started before fob, using only the records entered before fob's day 0
  (at least 200 patients and 20 deaths), plus the **Stranger**, which learns only from fob's own earlier records.
- **Scoring:** every week, each candidate predicts fob's new patients before seeing them, on two parts:
  - **profile:** how likely these patients are under the candidate's patient mix (age band, sex, core fields);
  - **severity:** who dies, after shifting the candidate's overall death rate to fob's own (Handover Rule).
- **Votes** = softmax(τ × cumulative score). τ = 0.03 was chosen by leave-one-outbreak-out (the same value
  for every held-out outbreak).
- **Fields:** only the 9 yes/no fields collected by **every** form (fever, cough, sore throat, shortness of breath;
  heart, lung, kidney, immune, metabolic/diabetes) plus age band and sex, coded yes vs not-yes.
  - Check behind this: on the 2019+ form, blank conditions mostly come with a blank "any risk factor"
    (401,243 of 529,382 blank heart-disease rows in 2020), so blank means "no".
  - Fields missing from the 2009 form are left out entirely, so the form cannot make outbreaks look unrelated.
- **Groups for scoring:** flu (including H1N1), other respiratory virus, COVID. The vote never sees these labels;
  they are only used to score it.

### Hindsight answers (fit on each outbreak's full data)
- Flu seasons are closest to earlier flu seasons, other-virus seasons to other-virus seasons, and COVID 2021 to COVID 2020.
- **Novelty gap** = how much better fob's own model fits than its best kin (nats per patient):
  - familiar seasons: 0.01–0.07;
  - pandemic-era seasons: other virus 2020–21 0.26–0.28, flu 2021 0.48;
  - outbreaks whose only possible kin was H1N1: flu 2013 0.99, other virus 2013 1.76;
  - **COVID 2020: 1.10**.
- COVID 2022 (Omicron) is closest in hindsight to **flu 2021**, not COVID 2021 (novelty gap 0.30).

### Right group? (23 replayed outbreaks; 21 have an earlier member of their own group)
| Week | Top group correct | Average vote for the true group | Exact best single kin |
|---:|---:|---:|---:|
| 1 | 81% | 0.66 | 52% |
| 2 | 81% | 0.70 | 52% |
| 4 | 90% | 0.80 | 57% |
| 8 | 100% | 0.92 | 70% |
| 13 | 100% | 0.98 | 78% |
| 25 | 95% | 0.96 | 83% |

- The patient-profile part does most of the work: profile alone gets the group right 90% of the time at week 4,
  severity alone 67%.
- The exact best single season is much harder (52–83%), because seasons within a group are near-ties.
  Choosing within a group is left to the Fresh-Days Check, as planned.

### Honest confidence? (group level, all weeks)
| Vote for top group | Cases | Average said | Actually right |
|---|---:|---:|---:|
| 0.40–0.60 | 38 | 0.55 | 0.66 |
| 0.60–0.80 | 71 | 0.70 | 0.93 |
| 0.80–0.95 | 42 | 0.88 | 0.93 |
| 0.95–1.00 | 394 | 0.998 | 0.992 |

When OS is sure, it is right. When it hedges, it is right **more often** than it says (under-confident),
which is the safe direction.

### Stranger Flag
| Outbreak | Novelty gap | Week the Stranger first wins | Patients by then |
|---|---:|---:|---:|
| other virus 2013 (only H1N1 to compare with) | 1.76 | 0 | 2 |
| flu 2013 (only H1N1 to compare with) | 0.99 | 6 | 27 |
| flu 2021 (flu during COVID) | 0.48 | 18 | 254 |
| **COVID 2020** | **1.10** | **3** | **749** |
| other virus 2021 | 0.28 | 8 | 1,738 |
| flu 2015–2018, familiar seasons | 0.04–0.05 | 13–24, or never | 1,974–3,725, or never |
| COVID 2022 | 0.30 | 2 | 17,562 |
| COVID 2021 | 0.06 | 9 | 183,742 |
| 10 other familiar seasons | 0.01–0.07 | never in 26 weeks | – |

- Rank correlation between the novelty gap and "fewer patients before the Stranger wins": **0.67**.
- **COVID 2020 timeline:**

| Week | Patients | Stranger | Vote |
|---:|---:|---:|---|
| 0 | 2 | 4% | 57% flu |
| 2 | 39 | 4% | 87% flu (closest: flu 2019) |
| 3 | 749 | 52% | – |
| 4 | 3,538 | 100% | – |

### Plain reading
- **What works:** the vote finds the right group in 90% of outbreaks by week 4 and in all of them by week 8.
  Its high-confidence calls are right 99% of the time, and it flags COVID 2020 as new by week 3.
- **Limits:**
  - With fewer than about 40 patients, OS called COVID 2020 "flu-like". The Stranger needs a few hundred patients to win.
  - In familiar seasons the Stranger also wins eventually, after about 2,000 patients, because fob's own data
    becomes enough. So the flag is "the Stranger wins **early**". The cut-off is not tuned yet.
- **Caveats:** 23 outbreaks but 3 groups, with COVID the only truly new disease after 2009, so these numbers
  are encouraging, not proof. The groups used for scoring are lab-defined; the vote itself does not use them.
- **Next:** the Two-Part Recipe and Handover Rule (step 2), using these votes to decide what to borrow.

---

## 2026-10-05 — Outbreak library, H1N1 replay, and first test of learning from past outbreaks

### Owner decisions
- OS **learns** the new disease day by day. It generates synthetic data only once it judges that it understands
  the disease well enough. So the daily score is OS's understanding (AUC on later real patients), and
  synthetic data is checked once, when OS says it is ready.
- Start with Brazilian respiratory outbreaks only; mpox, Ebola and others come later.

### Outbreak library (`src/outbreak_synth/library.py` → `data/processed/library.parquet`, summary `results/library_summary.csv`)
- New data: SRAG 2009–2012 and 2013–2018 CSVs, same ministry portal, CC-BY (`scripts/download_srag_historic.sh`, SHA-256 recorded).
- Three form versions are harmonised to one schema: age, sex, race, state; 6 symptoms (fever, cough, sore throat,
  shortness of breath, respiratory distress, low oxygen saturation); 10 comorbidities (cardiac, lung, renal,
  immunosuppression, metabolic/diabetes, liver, neurological, obesity, postpartum, Down syndrome).
  Each is `yes` / `no` / `missing`.
- Mapping decisions (from the official dictionaries): age codes are `unit×1000 + value` on the old form;
  states are IBGE numbers on the old form and letters on the new one; old "chronic metabolic disease" = new "diabetes".
  On the 2009 pandemic form, `CLASSI_FIN 1` = new influenza subtype (H1N1pdm) and `EVOLUCAO 2` = death from influenza.
- Patients: hospitalised, outcome cure (1) vs death (2). 2010–2012 are skipped: the 2012 file mixes two outcome
  codings, and 2010–2011 are small.
- 24 outbreaks, ~2.15M patients. Examples: H1N1 2009 21,123 (9.5% death, median age 24); flu seasons
  1,257–11,824 each (13–19% death); other-virus seasons, mostly infants (median age 1, 3–7% death);
  COVID 2020–22 1.97M (28–33% death, median age 57–70).
- **Form effect:** the 2019+ form leaves 36–59% of yes/no fields blank, against 3–8% on the 2013–2018 form.
  That is a difference in the form, not the disease, so OS must not read it as a disease trait.

### Experiment 3: real data only, replayed day by day, on the shared fields (`run_replay_real.py`, `exp03_replay_real.toml`)
| Outbreak | Test set | Gold AUC | First day with enough data | First day within 0.02 of gold |
|---|---|---:|---|---|
| H1N1 2009 | entries 2009-09-08 to 12-31: 8,128 (620 deaths) | 0.761 | day 27 (123 pts, AUC 0.596) | **day 56** (7,315 pts, 0.753) |
| COVID 2020 | entries 2020-07: 93,635 (31,431 deaths) | 0.774 | day 21 (88 pts, 0.708) | **day 33** (2,824 pts, 0.756) |

- The shared fields lose almost nothing for COVID (gold 0.774 vs 0.776 with the full field set in Exp. 2).
- For H1N1, models from day 60 on beat the "gold" (0.771 vs 0.761) because the gold set includes 2010–2012
  entries from a different phase. The gold standard is a reference, not a strict ceiling.

### Experiment 4: does knowledge from past outbreaks help COVID early? (`run_prior_probe.py`, `exp04_prior_probe.toml`)
Past library = every outbreak that ended before 2020 (H1N1 2009, flu and other-virus 2013–2019; 93,643 patients).

| Day | COVID patients so far | New data only | Past outbreaks only | Past + new |
|---:|---:|---:|---:|---:|
| 0–20 | 1–15 | cannot train | 0.727 | cannot train |
| 21 | 88 | 0.708 | 0.727 | 0.716 |
| 24 | 306 | 0.717 | 0.727 | 0.720 |
| 26 | 553 | 0.738 | 0.727 | 0.742 |
| 28 | 1,084 | 0.740 | 0.727 | 0.742 |
| 33 | 2,824 | 0.756 | 0.727 | 0.757 |

**Plain reading:**
- The past-only model scores 0.727 with zero COVID patients, but **ranking COVID patients by age alone also scores 0.727**.
  So far, the past outbreaks are teaching only "older patients die more often", which is known on day 0 without any model.
- Adding the past model's risk score to the new data helps a little on days 21–28 (+0.002 to +0.009) and does not move the plateau day (33).
- **Death rate:** 11.5% in past outbreaks vs 33.6% in COVID. A generator built mainly from past outbreaks would understate
  COVID deaths about three times over. OS has to learn the new disease's own severity from its early rows.
- This is a negative first result for the simplest version of the idea. It does not rule out OS. It says the gain must come
  from learning more than age from past outbreaks (e.g. which comorbidities matter and how much), from choosing which past
  outbreaks to trust, and from learning the new disease's severity fast.

---

## 2026-10-05 — Experiment 2: days to plateau with real data only

**Why:** The owner's goal is a learner ("OS") that gives scientists useful data earlier in an outbreak.
The baseline it has to beat is how many days real data alone takes to reach its plateau.

- Code: `src/outbreak_synth/run_days_to_plateau.py`, config `experiments/exp02_days_to_plateau.toml`,
  output `results/exp02_days_to_plateau.json`. Logistic regression (the best small-N model in Exp. 1).
- Day 0 = 2020-02-26, the first hospitalised COVID-19 record entered. On day d, train on every record entered up to day d.
- Fixed test set: records entered 2020-07-01 to 2020-07-31 (93,635 patients, 31,431 deaths).
- Gold standard: trained on every record we hold today except the test month (1,876,969). **AUC 0.776.**
- Days with fewer than 10 deaths or 10 survivors are skipped (days 0–20: too few records to train at all).

| Day | Date | Records so far | AUC | Gap to gold |
|---:|---|---:|---:|---:|
| 21 | 2020-03-18 | 88 | 0.711 | 0.065 |
| 24 | 2020-03-21 | 306 | 0.721 | 0.055 |
| 28 | 2020-03-25 | 1,084 | 0.740 | 0.036 |
| **33** | **2020-03-30** | **2,824** | **0.757** | **0.019 (first day within 0.02)** |
| 42 | 2020-04-08 | 8,425 | 0.760 | 0.016 |
| 63 | 2020-04-29 | 27,880 | 0.764 | 0.011 |
| 120 | 2020-06-25 | 156,923 | 0.771 | 0.005 |

**Reading:** for this task, real data alone reaches its plateau about **one month** after the first record
(day 33). After that it improves very slowly. For OS to be useful on COVID-19 in Brazil, it must
produce useful data during **days 0–32**, especially days 0–20, when real data cannot train anything.
That window is narrow, and the gold-standard AUC itself is modest (0.776) with these admission-time fields.

---

## 2026-10-05 — Decisions and Experiment 1: real data only (no synthetic data)

### Decisions from the owner
1. Task: in-hospital death among hospitalised COVID-19 patients (`CLASSI_FIN=5`, `HOSPITAL=1`,
   `EVOLUCAO` 2 death vs 1 cure).
2. The earliest N records are chosen by **data-entry date** (`DT_DIGITA`), not symptom onset.
3. Test set: the **records entered right after the small sample** (owner: "earliest data point with
   date entries"). Implemented as every record entered in the 30 days after the last training day.
4. The "epsilon tuner" is the owner's separate `dp tuner` repo (differential privacy). It is out of scope here.

### Setup
- Code: `src/outbreak_synth/data.py`, `models.py`, `run_real_only.py`; config `experiments/exp01_real_only.toml`;
  output `results/exp01_real_only.json`. Data: the four SRAG files listed above (release 23-03-2026).
- Cohort 1,970,604 rows, ordered by entry date → onset date → notification id (deterministic).
- Training pool: first 3,000 records (entered 2020-02-26 to 2020-03-31). Records entered on the
  cutoff day after the 3,000th are left out of both sets.
- **Test set: 26,245 records entered 2020-04-01 to 2020-04-30, 9,227 deaths (35.2%).** The same for every N.
- Features (admission-time only, 25): age; sex, race, urban/rural zone, notifying state; 8 symptoms;
  12 comorbidities; hospital-acquired infection. Each yes/no field becomes `yes` / `no` / `missing`
  (blank or 9). ICU, ventilation, X-ray, antivirals and lab results are excluded because they happen
  after admission and would leak the outcome. Four symptoms added to the form later in 2020 are excluded (>90% blank early).
- Models: logistic regression (one-hot, standardised age); histogram gradient boosting (300 trees, lr 0.05).
- 95% CI: 1,000 bootstrap resamples of the test set. Both models turned out deterministic for a
  fixed training set, so seeds do not change these numbers. Seed variance will come in with the generators.
- Reference ceiling: trained on 537,778 records entered **after** the test window (May–Dec 2020). This is
  future data, so it is only an upper reference, not something available during an outbreak.

### Results: test AUC (95% bootstrap CI)

| Train N | Deaths in train | Logistic regression | Gradient boosting |
|---:|---:|---|---|
| 100 | 39 | 0.728 (0.722–0.734) | 0.720 (0.714–0.727) |
| 300 | 110 | 0.738 (0.732–0.744) | 0.709 (0.703–0.716) |
| 1,000 | 333 | 0.783 (0.777–0.788) | 0.756 (0.750–0.762) |
| 3,000 | 902 | 0.797 (0.792–0.802) | 0.774 (0.768–0.780) |
| Reference (537,778) | 177,830 | 0.807 (0.802–0.812) | 0.815 (0.811–0.821) |

### What this means
- **The room for synthetic data to help is small.** With 3,000 real records, logistic regression is
  already 0.010 below its ceiling and 0.018 below the best ceiling (0.815). It is within the brief's
  "0.02 of full data" target at N = 3,000 without any synthetic data.
- The real room is at **N = 100–300** (0.07–0.09 below the ceiling), and at N = 1,000 for gradient boosting (0.06).
  That is where the generator comparison is worth running.
- Logistic regression beats gradient boosting at every small N, which matches the JMIR sample-size study cited in the brief.
- I have not fitted the power-law learning curve yet. Four points are too few for it to mean much on its own; I'll fit it once the generator runs add points.

---

## 2026-10-05 — Step 1: data inspection (no models trained)

**Script:** `PYTHONPATH=src python -m outbreak_synth.inspect_srag` → `results/inspect_srag.json`
**Environment:** 4 CPU cores, 15 GB RAM, **no GPU**. Python 3.11, pandas 3.0.6, pyarrow 25.0.1.

### Data used
I used the **primary source** instead of the two derived files in the brief. The "derived file"
(3.4M records, `classi_fin`) and the "COVID-19 inpatient mortality" file are both cut from this
same surveillance system, so going to the source removes a layer of unknown preprocessing and
settles the license question.

| File (release 23-03-2026) | Rows | SHA-256 (first 12) |
|---|---:|---|
| INFLUD19 (symptoms 2018-12-30 to 2019-12-28) | 48,941 | 748519f593d4 |
| INFLUD20 (2019-12-29 to 2021-01-02) | 1,206,920 | 371723b91c0e |
| INFLUD21 (2021-01-03 to 2022-01-01) | 1,745,672 | ecad01062f23 |
| INFLUD22 (2022-01-02 to 2022-12-31) | 560,577 | 93aab4d4ef3a |

- Source: Ministério da Saúde open-data portal, dataset `srag-2019-a-2026`, **CC-BY**
  (license stated on the dataset page). The portal moved from opendatasus.saude.gov.br to
  dadosabertos.saude.gov.br; files are on the ministry's S3 bucket.
- 194 columns per file. No duplicate notification IDs across 3,562,110 rows.
- The SRAG form is for **hospitalised** severe respiratory illness, so `HOSPITAL = 1` for ~96%.
- Label codes checked against the official data dictionary:
  `CLASSI_FIN` 1 influenza, 2 other respiratory virus, 3 other agent, 4 unspecified, 5 COVID-19;
  `EVOLUCAO` 1 cure, 2 death, 3 death from other causes, 9 ignored.
- Data quirk: code fields are numeric in the 2019–20 files and strings in 2021–22. My first
  pass silently dropped 2021–22 from the counts. Fixed: all code fields are now converted to numbers on load.

### Candidate task A: in-hospital death among hospitalised COVID-19 (preferred in the brief)
Cohort: `CLASSI_FIN = 5`, `HOSPITAL = 1`, `EVOLUCAO ∈ {1, 2}` (excludes deaths from other causes and unknown outcomes).

- 1,970,604 records, death rate **32.3%** (2020–2022).
- Earliest-N samples, ordered by symptom-onset date:

| N | Deaths | Survivors | Last onset date in sample |
|---:|---:|---:|---|
| 100 | 35 | 65 | 2020-02-29 |
| 300 | 117 | 183 | 2020-03-06 |
| 1,000 | 329 | 671 | 2020-03-13 |
| 3,000 | 888 | 2,112 | 2020-03-19 |

Events are not scarce: even N = 100 has 35 deaths. Monthly volume goes from 102 (Feb 2020) to
11,855 (Mar) and 54,227 (Apr), so N = 3,000 covers roughly the first five weeks.

### Candidate task B: influenza vs COVID-19 classification
Hospitalised, known-outcome influenza: only **29,634** records (6,460 from 2019, before COVID).
This is a diagnosis task, not a prognosis task, and it does not fit the "new disease, few records" framing as well.

### Missingness (all 3.56M rows; blank or 9 = "ignored")
Demographics are almost complete (age 0.5%, sex 0%). Symptoms 14–20%. **Comorbidities are 54–64%
missing** (cardiac 54%, diabetes 57%, obesity 64%, renal 64%), because in many records the
comorbidity block is left blank instead of being marked "no". How to encode this
(blank = no, or a separate "missing" category) changes what the generators learn, so it needs
one fixed rule for every generator.

### Concerns to flag
1. **Reporting lag.** For records with onset before 2020-03-20, the median delay from onset to data
   entry is 12 days; the 90th percentile is 66 days and the 99th is 391 days. "Earliest N by onset date"
   from today's final file is not what an analyst actually had in March 2020. It is more complete
   and its outcomes are already resolved. Ordering by data-entry date (`DT_DIGITA`) instead would be more realistic.
2. **Distribution shift in the held-out set.** The death rate moves over time (36% Feb, 40% Apr,
   30% Sep 2020), and vaccines and variants arrive in 2021–22. A time-based test set that spans
   2020–2022 mixes these effects into the AUC. A narrower test window (e.g. Apr–Jun 2020) is cleaner.
3. **Past-disease side.** The 2019 file holds only ~6.5k hospitalised influenza records with known
   outcomes. The portal also has SRAG 2009–2012 (including the H1N1 pandemic) and 2013–2018. These
   are a natural, same-schema, same-source "past outbreaks" library. I have not downloaded or checked them yet.

### Not done yet (waiting on decisions)
Steps 2–6 (generators, predictors, learning curves). The brief makes the prediction task a decision point.
