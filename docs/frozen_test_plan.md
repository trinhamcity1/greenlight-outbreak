# Frozen final test: plan (written and committed before the test data were downloaded)

**Purpose.** Every result so far was obtained on the 23 Brazil outbreaks of 2013–2022, and OS's settings were
chosen on those same outbreaks. This test runs OS, unchanged, once, on Brazil seasons it has never seen, and
reports whatever comes out. The git commit holding this file is the proof that the plan came first.

## 1. Test data
- **Source:** SIVEP-Gripe SRAG, Ministério da Saúde, dataset `srag-2019-a-2026` (CC-BY), release `23-03-2026` (the
  same release as the development files), years **2023, 2024 and 2025**.
- **Not used:** 2026. That file holds only January–March, so no outbreak in it can have a 91–182-day test window.
- **Isolation:** the files go to `data/raw/srag_frozen/` (`scripts/download_srag_frozen.sh`, SHA-256 recorded).
  - The development library (`data/processed/library.parquet`) is never rebuilt with them.
  - The test library is `data/processed/library_frozen.parquet`: the development library unchanged, plus the
    new outbreaks (`library.py --frozen`).
- **Test outbreaks:** `flu_2023`, `othervirus_2023`, `covid_2023`, `flu_2024`, `othervirus_2024`, `covid_2024`,
  `flu_2025`, `othervirus_2025`, `covid_2025`.
  - Same definitions as in development: one outbreak per file year and laboratory class (CLASSI_FIN 1 influenza,
    2 other respiratory virus, 5 COVID-19); hospitalised patients with a known outcome (cure or death).
- **Inclusion rule (unchanged):** an outbreak is scored if its test window (days 91–182) holds at least 200
  patients and 20 deaths. Excluded outbreaks are listed, not dropped silently.
- **Known limitation:** the 2025 file was released in March 2026. Patients whose outcome was still open at release
  are not in the file, so late-2025 records may be slightly incomplete.

## 2. What is frozen (no change after this commit)
| Setting | Value | Chosen on |
|---|---|---|
| Day 0 | first week with ≥ 20 records (flu, other virus); first record (COVID) | Exp. 4–5 |
| Outcome timing | an outcome is used only once known (`DT_KNOWN`) | Exp. 14 |
| Kinship Vote | group start; vote sharpness τ = **0.01** for every test outbreak (the value minimising the development loss over all 23 outbreaks; no leave-one-out choice on test data) | Exp. 5d |
| Handover Rule | strength 10 × (1 − Stranger); floor 1 towards 0 | Exp. 6b, 8 |
| Recipe | kin; Lab-Label Fallback (age trend until 20 fresh deaths when the group has no earlier member) | Exp. 8 |
| Green Light | ≥ 10 deaths with a known outcome, stability ≥ 0.99 on two checks in a row, not on the fallback | Exp. 14 |
| Synth Release | dependency chain, 50,000 rows, seed 0 | Exp. 10 |
| Baselines | as Exp. 15 (strength 10) and Exp. 16 (bootstrap, Bayesian network, ARF, CTGAN, TVAE; 10,000-row cap) | Exp. 15–16 |
| Past outbreaks OS may borrow from | every outbreak (development and earlier test seasons) with records and known outcomes before the test outbreak's day 0 | — |

**Allowed after unblinding:**
- Purely technical fixes needed to *load* the new files (for example, a renamed column), logged in RESULTS.md.
- If a bug in the analysis code is found, both the original and the corrected numbers are reported.

**Not allowed:** changing any setting above, adding or dropping methods, or choosing which numbers to report.

## 3. Endpoints (all reported, in this order)
Analysis code: `src/outbreak_synth/analyse_frozen.py`, committed with this plan.

1. **Who dies, accuracy.** Mean gap to gold over days 0–90, with a 95% bootstrap interval over outbreaks. Paired
   differences (95% interval, outbreaks better) against: real data alone, fine-tuning, stacking, OS without the
   vote (equal weights), and source averaging.
2. **Safety.** Days below "rank by age", per outbreak and in total.
3. **Green Light.**
   - Greens by day 90, and the median day.
   - False greens (gold − OS > 0.02 on the green day, replay AUC), with an exact interval.
   - Patient-level verdicts: firm correct, uncertain or firm false, from 1,000 stratified resamples.
   - Riley's rule alongside.
4. **Kinship Vote.** Share of test outbreaks where the right pathogen group leads, weeks 1, 2, 4 and 8. All test
   outbreaks have earlier members of their group.
5. **Synthetic data.** AUC of a model trained on OS synthetic data only, against the real records OS had and each
   baseline generator: paired differences with 95% intervals. Also the gain from adding OS synthetic data to the
   real records.

## 4. What would count as the claims holding or failing (stated in advance)
- **Borrowing helps:** OS minus real data alone has a 95% interval above 0. Expected from development: +0.047.
- **No clear accuracy gain over simple borrowing (expected):** OS minus fine-tuning and OS minus stacking have
  intervals including 0. A clear OS advantage would be a positive surprise; a clear disadvantage a negative one.
- **Green Light honest:** 0 or 1 false greens. **Two or more false greens means the Green Light claim fails** on the
  test seasons.
- **Safety:** OS's days below rank by age per outbreak comparable to development (2.9 per outbreak).
- **Synthetic data useful:** OS synthetic-only beats the real records OS had (interval above 0).

These seasons are familiar pathogens. The test says nothing new about a truly new disease; that limitation stays
in the paper.
