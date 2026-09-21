# MODEL CARD — M3 graph-enhanced gradient boosting (T+B+G)

* **Purpose:** rank account-day cases for a limited review queue in a research setting. **Not** a detector, not for real decisions about people.
* **Type:** LightGBM (300 trees, 31 leaves, lr 0.05, fixed; no tuning), 45 features (T+B+G), trained on all positives + 4 % of negatives from the training block; Platt calibration on the validation block (new-scheme view).
* **Data:** synthetic Tide-format data (LI-like / HI-like), see DATA_CARD.md. Trained separately per condition.
* **Evaluation:** temporal hold-out; results and uncertainty in RESULTS.md (generated). Headline reading: graph context gave **no measurable gain** over T+B in H1; part of the signal is a generator artefact (transaction type); calibration skill vs a prevalence-only baseline is modest.
* **Explanations:** exact TreeSHAP per case; reason codes group features.
* **Known limitations:** 8 (LI) / 15 (HI) independent schemes in the test stream; synthetic generator artefacts; no external validation; scores are relative-risk signals, not probabilities of wrongdoing.
* **Out of scope / misuse:** any use on real customers, any compliance or regulatory claim, any automated adverse action.
* **Artifact:** `artifacts/demo/<LI|HI>/model/model_main.txt` (+ `feature_schema.json`, `calibration.json`).
