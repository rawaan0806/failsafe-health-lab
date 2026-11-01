# FAILSAFE — 70-second jury demo (draft)

**0–12 sec · The problem**
"What if healthcare teams could stress-test their process before bottlenecks reach real patients? FAILSAFE is a synthetic simulation lab for hospital-to-home workflows."

**12–25 sec · Show setup**
"I can change patient barriers, available staff, arrival intensity, and a fictional resource budget. None of these are real patient records."

**25–43 sec · Run joint optimizer**
"With one click, we generate fictional pathways and simulate queues. Our exact optimizer evaluates 72 combinations of care support and staffing. It finds the highest weighted score within the budget."

**43–56 sec · Demonstrate trade-offs**
"Now I change the priority slider. This changes how much we value synthetic completion versus operational waiting. The optimizer can recommend a different allocation and explains why."

**56–70 sec · Show transparency**
"Every result is reproducible, inspectable, and downloadable. The system shows its assumptions, and it's not claiming clinical effectiveness. It's a prototype of explainable, testable healthcare workflow planning."

For Q&A: This is **mathematical/exact combinatorial optimization**, not an ML classifier. No hospital data or medical accuracy claims. Future research would add evidence-based calibration and interactions between staffing and care pathways.


## New 25-second Visual Lab segment (v0.6)

1. Scroll to **Patient flow · live replay**. Say: “This is an event-based replay—not a video. Every dot represents a synthetic person; the counts cover the entire cohort.”
2. Select **⚡ Try overload**. Say: “This sets one discharge worker and 90 fictional patient arrivals per synthetic working day.”
3. At the peak queue, point to the **Waiting for discharge** count. Say: “This is an operational bottleneck, not a predicted health risk.”
4. Click **Base staffing** / **Selected staffing** at the same time coordinate; show the backlog difference under paired patient demand.
5. Click one dot to reveal an actual simulation record; then press **Play**.
6. End with: “All inputs are hypothetical; our next milestone is validating the assumptions, not claiming clinical accuracy.”
