# FAILSAFE — Find the failures before patients experience them

**The problem:** Discharge from hospital is not one event. It is a chain of handoffs, instructions, medication access, follow-up booking and attendance. A small gap in one step can make the entire transition harder, but improving the process in real life can be expensive and sensitive.

**Our concept:** FAILSAFE is an interactive stress-testing lab for healthcare workflows. It creates entirely fictional patient profiles with different access barriers, simulates their journeys through five simplified stages, and spots where the workflow is most fragile. It then evaluates every available combination of three process interventions under a resource budget and explains why the best-scoring combination was selected.

**The technical core:** A deterministic, reproducible Python simulation; paired counterfactual comparisons between interventions; an exhaustive eight-combination resource-constrained optimizer; repeated-seed checks; and a live JSON API connected to a responsive browser interface.

**Demo to show a judge (60–90 seconds):**
1. Open the dashboard with 500 fictional patients. Show the baseline outcome.
2. Increase the transport barrier percentage, click Run, and point out that the results change.
3. Reduce the available budget; show that the recommended intervention set changes accordingly.
4. Inspect one patient’s five checkpoints and compare different candidate plans.
5. Explain the assumptions and model limitations transparently.

**Why it stands out:** Instead of asking AI to provide another answer to a patient, the product explores *where healthcare processes might fail before they affect anyone*. It makes system-level trade-offs explorable and explainable.

**Integrity note:** This prototype is a fictional sandbox and cannot claim reductions in medical errors, readmissions, or actual costs. It is not designed for real patients or clinical decision-making. Its probabilities and benefits require validation before real-world use.
