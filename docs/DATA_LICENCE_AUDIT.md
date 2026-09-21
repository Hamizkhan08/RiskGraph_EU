# DATA_LICENCE_AUDIT.md

Date: 20 September 2026 · **Not legal advice.** Where a licence is unclear the entry says **UNRESOLVED**; nothing was guessed.

## 1. Summary

| Dataset | Licence status | May be used locally for research? | May raw or row-level data be published? |
|---|---|---|---|
| **IBM AMLworld** (Kaggle HI/LI × S/M/L) | **CDLA-Sharing-1.0** per IBM's repository; **full licence text read**; Kaggle page's own licence field **not read** | Yes | Only under CDLA-Sharing-1.0 with notices — see §2 |
| **SAML-D** | **UNRESOLVED** | Treat as local research use only until resolved | **No** (until resolved) |
| IBM AMLSim (generator code) | Apache-2.0 (code) | Yes | Code yes; generated data terms not stated — own responsibility |
| Elliptic 1 / 2 | **UNRESOLVED** (third-party mirrors claim MIT; not authoritative) | Not used | Not used |
| Tide, TransXion | **UNRESOLVED** | Not used | Not used |
| IBM data on Box (pre-Kaggle release) | Same repo note; superseded generator version | Not used | Not used |

## 2. IBM AMLworld — CDLA-Sharing-1.0

**Evidence.**
- IBM/AML-Data README: the repository is Apache-2.0, **"the actual data is released under the CDLA-Sharing-1.0 license"**, and it directs users to the Kaggle data as the improved release [P].
- NeurIPS paper supplement: data published on Kaggle "under a Community Data License Agreement"; Kaggle is the single source of distribution [P].
- Licence text: the full CDLA-Sharing-1.0 text was read from SPDX [P].
- **Not read:** the licence field displayed on the Kaggle page itself → **verify manually and paste it into this file**.

| Question | Answer from the licence text | Status |
|---|---|---|
| Licence name / version | Community Data License Agreement – Sharing – 1.0 | [V] (IBM README) |
| Permitted use | Worldwide, non-exclusive, irrevocable right to **Use and Publish** the Data, subject to §3 (§2.1). "Use" includes computational analysis | [V] |
| Commercial-use restrictions | None may be added; §3.3 forbids restricting commercial or non-commercial use of published Data | [V] |
| Attribution | If you Publish Data you received, **preserve all credit/attribution, notices and metadata** (§3.1c). Kaggle also asks users to cite the dataset paper | [V] |
| Derivative-data requirements | **Enhanced Data** (your Additions/Modifications) that you Publish must also be Published under this Agreement, and changed files must carry **prominent notices** of change (§3.1a–b) | [V] |
| Redistribution | Allowed, **only under an unmodified CDLA-Sharing-1.0**, including the licence text/name/hyperlink (§3.3) | [V] |
| Publication requirements for *results* | **None.** "Results" (outputs of computational use, not including more than a de minimis portion of the Data) carry no obligations (§3.5, §1.11) | [V] |
| Store raw data in a **public** GitHub repo | That is "Publishing" the Data. Allowed only with the licence text, attribution and no added restrictions | [V] reading; **legal interpretation unconfirmed** |
| Store raw data in a **private** repo | "Publish" = making Data available to anyone not employed/contracted by you. Sharing with a supervisor or examiner may count. **Ambiguous** | UNRESOLVED |
| Redistribute **derived** data | Depends on whether a derived table is "Results" (de minimis) or "Enhanced Data". A row-level account-day table with per-day aggregates retains a substantial portion of the information → **UNRESOLVED**; treat as Data | UNRESOLVED |
| Screenshots showing individual records | Displaying records publishes a subset of the Data ("all or a subset", §1.9) → permissible only with licence notice and attribution; aggregate charts (no records) are Results | [V] reading; UNRESOLVED as to "de minimis" |
| Privacy | Data are synthetic; §7.4 disclaims any expectation of privacy in published Data | [V] |
| Waiver / warranties | Data provided "as is" (§6) | [V] |

### Decisions for RiskGraph EU (conservative defaults)
1. **Raw IBM files never enter Git.** Repository contains a download script and expected file hashes.
2. Publish **only** code, aggregate metrics, figures without records, and tables of counts.
3. The public **DEMO_MODE** must not embed real rows unless every embedded data file carries the CDLA-Sharing-1.0 notice, attribution and change notices; otherwise use aggregated or re-derived illustrative structures **clearly labelled as such**. Decision deferred to the deployment phase.
4. Code licence (e.g. MIT/Apache-2.0) is separate from any Data files, which stay under CDLA-Sharing-1.0.
5. Attribution string to include: *IBM Transactions for Anti Money Laundering (AML), Altman et al., NeurIPS 2023 D&B; CDLA-Sharing-1.0.*

## 3. SAML-D — UNRESOLVED

| Question | Finding | Status |
|---|---|---|
| Licence name / version | **Not found.** The author repository lists only a README and a notebook (no licence file). The Kaggle licence field was not read | UNRESOLVED |
| Paper licence | The accepted manuscript at the university repository is CC BY-NC — this covers the **paper**, not the data | [V] — do not transfer to the data |
| Permitted use / commercial / attribution / derivative / redistribution / publication | Unknown. README asks users to **cite the paper** | UNRESOLVED |
| Raw data in GitHub / derived data / screenshots | Unknown → **assume not permitted** | UNRESOLVED |
| Version | Published paper: 9,411,384 tx; current README: 9,504,852 tx ("updated version"). **Pin by file hash** | [V] |

**Actions (for you):** (1) open the Kaggle page and copy the licence field here; (2) if it is missing or "Other", email the corresponding author (address in the paper) and ask for an explicit licence for research use and publication of aggregate results; (3) until then, use locally only and do not redistribute anything row-level.

## 4. Other datasets considered
- **Elliptic 1/2:** not used; original terms unverified. Third-party Hugging Face mirrors state MIT but are re-uploads and not authoritative.
- **Tide / TransXion (2026):** generators; licences unverified; not adopted.
- **AMLSim:** Apache-2.0 code; synthetic output terms unstated. If we generate our own data, the terms are ours — but we would then lose comparability with published results.

---

## Addendum 2026-09-21 — datasets considered for the final build

| Dataset | What was verified | What was NOT verified | Use in this build |
|---|---|---|---|
| **Tide generator** (github.com/mntijn/Tide) | Repository `LICENSE` is **MIT** (read in the clone); it runs locally and produces `generated_transactions.csv` + `generated_patterns.json` | — | **Used**: data are regenerated locally at reduced scale; the run manifest records the generator commit and file SHA-256s |
| **Tide dataset on Zenodo** (10.5281/zenodo.18804069) | Nothing: the record fetch was rate-limited and Zenodo is blocked from the build sandbox | Licence of the released files; the quoted ~36.6 k nodes / 7.6 M edges | **Not used** |
| **AMLNet v2.0** (zenodo.org/records/21237971) | Primary record read: ~1.09 M transactions, 195 days, 1,411 suspicious (0.13 %), **CC BY-NC 4.0**, ~765 MB single CSV, generator not included, typologies are laundering *stages*, includes a model-generated `fraud_probability` column, paper "under review" | Content of the file itself (not downloadable here) | **Not used for results.** Experimental adapter (`riskgraph/data/amlnet.py`) exists, untested on the real file. Non-commercial licence: do not redistribute derived data in a public demo without care |
| **TransXion** | Not checked by this build. A third-party summary claimed MIT software and an unclear data licence | Everything | Not used |
| **IBM AMLworld** | Licence CDLA-Sharing-1.0 and profile findings from Gate 0.5 (see above) | Not re-checked | Not used for results; legacy profiler kept in `ml/profiling/` |
| **SAML-D** | Licence unresolved (Gate 0.5) | — | Not used |

Because only locally generated data are used, no third-party data are redistributed by this repository.
