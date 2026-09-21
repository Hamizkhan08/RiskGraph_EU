# RESPONSIBLE USE

> RiskGraph EU is a research prototype for financial-risk and financial-crime alert prioritisation using public/synthetic data.
> It is not a replacement for AML investigators, compliance systems, law enforcement, or regulatory validation.

## What an alert means
A case is *prioritised for review* because a model scored it as **elevated risk** relative to other cases that day. It is **not** a finding that anyone committed a crime. Ground-truth labels appear only in the clearly marked *research annotation* panel of the case page, where they are synthetic generator labels and never a model input.

## Language used in the product
"elevated risk", "prioritised case", "requires review", "model evidence", "behavioural signal". The product avoids "criminal", "guilty", "confirmed money laundering" except when quoting the synthetic dataset's own label in that research panel.

## Not claimed
Real-world effectiveness · guaranteed detection · compliance with AMLD/AMLR/GDPR or any regulation · bank deployment readiness · savings · legal determination of criminal activity.

## If someone builds on this
* Keep a human decision-maker in the loop. Automatically closing alerts is a **research concept** here; a real deployment would need governance, model-risk validation, regulatory and legal review (including rules on automated decision-making), and documented tolerances agreed with compliance.
* Do not put real customer data into the demo, and do not type personal data into the decision note field — notes are stored as entered (≤ 500 characters).
* Re-validate on representative data; results on one synthetic generator do not transfer.
* Report negative and inconclusive results (this project does: see `RESULTS.md`).

## Data ethics
All data are synthetic and locally generated with the MIT-licensed Tide generator; no personal data are processed. AMLNet (CC BY-NC 4.0) is not redistributed by this project.
