# Literature positioning for Outbreak Synth (OS), Case Study 1

Prepared 2026-10-07 from targeted web searches. Most papers were read from abstracts, publisher summaries or
PubMed Central pages; none was read in full. **This is not a systematic review.** Before any paper claims novelty,
the key references must be read in full and a structured search (e.g. PubMed, Scopus, arXiv) run and logged.

## 1. Verdict in one paragraph

The building blocks are **not new**:
- borrowing from earlier diseases to predict COVID-19 outcomes (Lichtner et al. 2021; Agarwal et al. 2022);
- Bayesian dynamic borrowing from historical or multiple sources (power, commensurate and robust MAP priors;
  multi-source exchangeability models);
- meta-learning across clinical tasks (MetaPred);
- choosing a synthetic-data generator by dataset traits (SYNTHONY);
- synthetic augmentation of small health tables (Liu, El Emam et al. 2025).

What this search did **not** find, and what OS could claim after a proper search:
1. **A time-respecting replay benchmark** over many real outbreaks (23 Brazilian, 2 Mexican) that measures *how
   many days* until a model is good enough.
2. **Choosing which past outbreaks to borrow from,** week by week at patient level, with a "none of the above"
   option (Stranger) and a lab-label fallback.
3. **A readiness signal (Green Light)** checked for honesty across outbreaks.
4. **Synthetic patient data released only after that signal,** with provenance and an interpretable report.

The paper should be framed around (1)–(4), **not** around a new borrowing formula or a new generator.

## 2. Related work by area

### A. Transferring from earlier diseases to COVID-19 outcomes
- **Lichtner et al. 2021, *Scientific Reports*.**
  - A gradient-boosted model trained on 718 critically ill **non-COVID viral pneumonia** patients (influenza,
    parainfluenza, metapneumovirus, other coronaviruses) predicted death in 1,054 COVID-19 ICU patients with
    **AUC 0.86**. It beat APACHE II, SAPS II, SOFA and COVID-specific models.
  - It is a single fixed transfer: no choice among past diseases and no time course.
  - *Relevance:* direct prior evidence that past diseases help. It contrasts with our Experiment 4 (borrowing from
    all past outbreaks ≈ age only). Theirs had 264 ICU and laboratory features; ours has admission-form fields only.
    The paper must discuss this.
- **Agarwal et al. 2022, *Scientific Reports* (TRANSMED).**
  - A hierarchical multimodal BERT pre-trained on 9,348 severe-respiratory-disease admissions, then applied to
    1,701 COVID-19 admissions. About +10–13% AUROC for length-of-stay and ventilation prediction.
  - It does not evaluate performance as a function of how many COVID patients are available or over time.
- **Wynants et al. 2020, *BMJ* (living review, PROBAST).** Almost all COVID-19 prediction models were at high or
  unclear risk of bias. Our time-respecting replay, later-period test sets and gold reference answer part of that
  critique and should be presented that way. A PROBAST self-assessment would help.

### B. Bayesian dynamic borrowing (clinical-trial statistics): the closest methods to the Kinship Vote and Handover Rule
- Power prior, commensurate prior, test-then-pool, and the **(robust) meta-analytic-predictive prior**
  (Schmidli et al. 2014; reviewed in the pharma dynamic-borrowing literature).
  - The robust MAP prior mixes an informative prior with a vague one. Its mixing weight should reflect how relevant
    the historical data are.
  - Our Stranger share plays that role, and our Handover Rule (normal prior, strength × (1 − Stranger)) is a simple
    member of this family.
- **Multi-source exchangeability models** (Kaizer, Koopmeiners et al.; R package `borrowr`) decide which of several
  supplemental sources are exchangeable with the primary one, and weight them. That is conceptually the Kinship
  Vote, though done on all the data at once rather than week by week on patient records.
- *Implication:* reviewers from statistics will see the borrowing maths as known. A **robust MAP or commensurate
  prior baseline** and a **multi-source exchangeability baseline** are needed, or a clear argument for why they
  don't apply.

### C. Meta-learning across clinical tasks
- **MetaPred** (Zhang et al. 2019, arXiv 1905.03218): meta-learns from related risk-prediction tasks (OHSU
  electronic health records), then fine-tunes on the few target samples.
- *Implication:* add a **MetaPred-style baseline** (meta-learned starting point across past outbreaks, fine-tuned on
  fob) and the simpler **"pooled past model, fine-tuned on fob"** baseline.

### D. Synthetic tabular data: choosing a generator and small samples
- **SYNTHONY** (ICLR 2026; arXiv 2604.00293): chooses a generator family from dataset "stress" features (small
  samples among them); a k-NN selector beats random and zero-shot LLM selectors. It is the closest to the original
  "method chooser" idea in the brief.
- **Synthcity** (Qian et al., NeurIPS 2023 Datasets & Benchmarks): open benchmark library with CTGAN, TVAE,
  TabDDPM, Bayesian networks, ARF and others. A practical way to add generator baselines.
- **Liu, El Kababji, …, El Emam 2025** (arXiv 2501.18741):
  - On 7 small health datasets, generative augmentation raised AUC by **4.3–43.2%, 15.6% on average**, and beat
    plain resampling.
  - Gains were largest with fewer rows, lower baseline AUC and more balanced outcomes. No generator won consistently.
  - *Relevance:* it **conflicts with our CTGAN finding** (CTGAN hurt in 22 of 22 outbreaks). Likely reasons: our much
    smaller samples (100–300 patients), testing on a later period, and a single generator. The paper must test more
    generators and add a **resampling baseline** before drawing conclusions.

### E. Historical or synthetic data for emerging pathogens (population level)
- **Osthus et al. 2026, *PLOS Computational Biology*:** weekly COVID-19 case forecasts from models trained on
  pre-2020 respiratory surveillance (about 2,000 series) plus about 36,000 synthetic outbreaks from an agent-based
  model; synthetic training improved accuracy.
- The **synthetic method of analogues** (PLOS Computational Biology) works in the same spirit.
- These are **case-count** (population) methods. OS is the **patient-level** counterpart, a useful contrast.

### F. Severity in real time: a validity issue for OS
- The epidemiology of real-time case-fatality estimation (Nishiura et al. 2009; R package `cfr`) shows that early
  ratios are **biased because outcomes of recent cases are not yet known**.
- **Our replays use each patient's final outcome as soon as the record is entered.** A live system would not know
  the outcomes of patients still in hospital, so our early-day results are optimistic. The Brazilian forms record an
  outcome date (`DT_EVOLUCA`), so the replay can be fixed: only use an outcome once its date has passed.
  **This is the highest-priority fix before publication.**
- **Size of the problem (checked 2026-10-07, COVID-19 Brazil 2020 replay):**

| Replay day | Patients OS used | Outcome dated by that day | Deaths OS used | Deaths dated by that day |
|---:|---:|---:|---:|---:|
| 21 | 88 | 22% | 35 | 10 |
| 28 | 1,084 | 32% | 363 | 127 |
| 44 (green day) | 9,333 | 59% | 2,822 | 1,645 |
| 90 | 79,854 | 79% | 29,790 | 25,083 |

  The real gap is likely larger, because an outcome is typed into the system after it happens (closure date
  `DT_ENCERRA`). Using only resolved patients also risks bias, because deaths and discharges resolve at different
  speeds. The fix should use the date an outcome became known and handle unresolved patients (e.g. leave them out,
  or model time to outcome).

### G. "Enough data yet?": baselines for the Green Light
- **Riley et al. 2020, *BMJ*** (minimum sample size for prediction models; R/Stata `pmsampsize`): criteria based on
  overfitting and on how precisely key parameters are estimated.
- *Implication:* compare the Green Light with "green when n reaches Riley's minimum". If Riley's rule is as honest
  and as early, the Green Light adds little.

### H. Updating models as data shift
- Continual learning and dynamic updating of clinical models during COVID-19 (e.g. drift-triggered updating across
  Toronto hospitals; dynamically updated 28-day COVID survival models; TRACER, arXiv 2512.12795).
- *Relevance:* our Mexico finding (early patients rank later patients worse than age does) is a dataset-shift
  result and should be discussed in these terms.

### I. Case Study 2 (vaccine safety)
- **Haguinet, Painter, Powell, Callegaro, Bate 2025** (arXiv 2504.12052): Bayesian borrowing with a robust MAP prior
  across semantically similar MedDRA terms (FAERS 2015–2019). True signals found **on average 5 months earlier**
  than the standard information component. A direct competitor and baseline for Case Study 2.
- **US myocarditis timeline (CDC VaST work group):** on 24 May 2021, VAERS showed more myocarditis/pericarditis
  than expected after dose 2 of mRNA vaccines in 16–24-year-olds; the Vaccine Safety Datalink did not yet.
  This gives a dated reference point for a replay.

## 3. What this means for the plan (in priority order)
1. **Fix outcome availability in the replays** (F). This changes every early-day number, so do it before anything else.
2. **Baselines:**
   - pooled past model + fine-tuning;
   - robust MAP or commensurate prior, or multi-source exchangeability borrowing;
   - MetaPred-style meta-learner;
   - generators via synthcity (TVAE, TabDDPM, Bayesian network or ARF) plus a bootstrap resampling baseline;
   - Riley's sample-size rule as a readiness baseline.
3. **Confidence intervals** on the main comparisons (bootstrap over test patients; spread across outbreaks).
4. **Freeze all settings, then one final untouched test.**
5. **Framing:** "readiness-gated, interpretable borrowing evaluated by time-respecting replay", not "a new generator".
6. **Discuss** Lichtner et al. (why our borrowing gains are smaller) and Liu et al. (why CTGAN hurt here).

## 4. Note on visibility
The project's GitHub repository (`trinhamcity1/outbreak-synth`) already shows up in web search with its
description. Consider whether to keep it public before submission (some venues have rules on prior public
versions) and post a preprint when the paper is ready.

## References (links as found; verify before citing)
- Lichtner G, et al. Predicting lethal courses in critically ill COVID-19 patients using a machine learning model trained on patients with non-COVID-19 viral pneumonia. *Sci Rep* 2021. https://pmc.ncbi.nlm.nih.gov/articles/PMC8225662/
- Agarwal K, et al. Preparing for the next pandemic via transfer learning from existing diseases with hierarchical multi-modal BERT: a study on COVID-19 outcome prediction. *Sci Rep* 2022. https://pmc.ncbi.nlm.nih.gov/articles/PMC9232529/
- Wynants L, et al. Prediction models for diagnosis and prognosis of covid-19: systematic review and critical appraisal. *BMJ* 2020;369:m1328. https://www.bmj.com/content/369/bmj.m1328
- Review of dynamic borrowing methods with applications in pharmaceutical research. https://researchinformation.umcutrecht.nl/en/publications/a-review-of-dynamic-borrowing-methods-with-applications-in-pharma/
- Kaizer AM, Koopmeiners JS, et al. Multi-source exchangeability models; R package `borrowr`. https://pmc.ncbi.nlm.nih.gov/articles/PMC5862286 ; https://conservancy.umn.edu/items/d1b24ac3-b3d8-4681-bf4e-cd217f1107f7
- Zhang X, et al. MetaPred: Meta-Learning for Clinical Risk Prediction with Limited Patient Electronic Health Records. arXiv 1905.03218. https://arxiv.org/pdf/1905.03218
- SYNTHONY: A Stress-Aware, Intent-Conditioned Agent for Deep Tabular Generative Models Selection. ICLR 2026. https://iclr.cc/virtual/2026/10017173 ; https://arxiv.org/html/2604.00293v1
- Qian Z, et al. Synthcity: a benchmark framework for diverse use cases of tabular synthetic data. NeurIPS 2023 Datasets & Benchmarks. https://papers.nips.cc/paper_files/paper/2023/hash/09723c9f291f6056fd1885081859c186-Abstract-Datasets_and_Benchmarks.html
- Liu D, El Kababji S, et al., El Emam K. Synthetic Data Generation for Augmenting Small Samples. arXiv 2501.18741 (2025). https://arxiv.org/abs/2501.18741
- Osthus D, et al. Leveraging synthetic and genetic data to improve epidemic forecasting. *PLOS Comput Biol* 2026. https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1014630
- Synthetic method of analogues for emerging infectious disease forecasting. *PLOS Comput Biol*. https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1013203
- Nishiura H, et al. 2009 (delay-adjusted case fatality); R package `cfr`. https://cran.r-project.org/web/packages/cfr/vignettes/cfr.html
- Riley RD, et al. Calculating the sample size required for developing a clinical prediction model. *BMJ* 2020;368:m441. https://dspace.library.uu.nl/handle/1874/457642
- TRACER: Transfer Learning based Real-time Adaptation for Clinical Evolving Risk. arXiv 2512.12795. https://arxiv.org/html/2512.12795v1
- Haguinet F, Painter JL, Powell GE, Callegaro A, Bate A. Semantic Similarity-Informed Bayesian Borrowing for Quantitative Signal Detection of Adverse Events. arXiv 2504.12052 (2025). https://arxiv.org/abs/2504.12052
- CDC COVID-19 Vaccine Safety Technical (VaST) Work Group report, 24 May 2021. https://archive.cdc.gov/www_cdc_gov/vaccines/acip/work-groups-vast/report-2021-05-24.html
