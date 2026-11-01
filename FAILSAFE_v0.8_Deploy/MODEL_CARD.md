# Model card — FAILSAFE v0.6 (illustrative research prototype)

## Intended purpose
Demonstrate a reproducible and explainable approach to *synthetic* healthcare process stress-testing, resource allocation, and software prototyping. Educational hackathon use only.

## Not intended for
Clinical decisions, staffing allocations at actual facilities, patient triage, estimating patient harm, real financial budgeting, or direct patient-facing recommendations.

## Inputs
- Synthetic cohort size, seed, patient barrier frequencies (all generated, not records).
- Three binary hypothetical interventions.
- Arrivals per synthetic day, two staffing counts, service time assumptions.
- Fictional budget and subjective weight between pathway completion and modeled queue wait.

## Outputs
- Five-step synthetic pathway completion and failure checkpoints, broken down descriptively by simulated traits.
- Queue delays, working-minute metrics, share waiting <=120 min.
- Exact optimum under the fictional budget and user-selected 0–100% weighting.
- Candidate enumeration and repeated-seed score ranges.

## Methodology and validation
- Patient traits generated from independent Bernoulli draws.
- The pathway simulator applies fictional checkpoint transition probabilities.
- The queue simulator uses simplified FIFO queues and fixed-window worker availability with continuous working minutes.
- Both models are **independent**. No medical benefit of staffing is estimated.
- Joint optimizer enumerates up to 72 combinations, scores with a weighted mean of two unrelated synthetic outputs, and minimizes fictional credits on ties.
- Automated checks cover deterministic seeding, budget constraints, API input validation, and sensitivity to staffing or arrival changes.
- Results are **not validated** against hospital datasets or peer-reviewed estimates; model repetition is not external validation.

## Key limitations
1. Model probabilities and cost coefficients are illustrative inventions. Recommendations can change when these assumptions change.
2. No causal interaction between staffing and pathway completion is represented; real care processes can exhibit such interactions.
3. A 120-minute cutoff is illustrative, not a clinical or statutory standard.
4. The weighted score is neither calibrated nor clinically meaningful.
5. Queue model simplifies shifts, downtime, overtime, arrivals, capacity dependencies, absenteeism, and resources other than staff.
6. Independent trait generation misses correlated social determinants and illness complexity.
7. Demographic fairness, safety, robustness to distribution shifts, and real-world benefit cannot be inferred from fictional data.

## What would be needed next
Literature-supported parameter ranges, expert interviews, anonymized operational data with consent and governance, calibration and validation, confidence intervals on empirical estimates, realistic scheduling constraints, privacy threat modeling, safety/human oversight, and domain evaluation.
