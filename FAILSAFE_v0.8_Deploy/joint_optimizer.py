"""Capacity-aware optimization over *independent* synthetic care & queue models.

Every result is fictional. Staffing changes affect operational wait metrics;
they do NOT change clinical pathway completion probabilities in this model.
We combine two independent objectives with an explicit user-controlled weight.
No medical benefits, clinical causal effects, or real monetary costs implied.
"""
from __future__ import annotations

from statistics import mean

from capacity import capacity_run

# Fixed illustrative credits per additional worker across this synthetic window.
STAFF_COST_CREDITS = {"discharge_staff": 95, "booking_staff": 75}
STAFF_INCREMENTS = (0, 1, 2)


def optimize_joint(audit: dict, patients: int, seed: int,
                   base_capacity: dict, budget: float,
                   repetitions: int, completion_weight: int = 60) -> dict:
    """Exact search of 8 intervention bundles x up to 9 staffing pairs.

    Score = w * simulated pathway completion % +
            (1-w) * simulated operational wait <=120 minutes %.
    Queue metric is NOT patient medical safety and independent of pathway model.
    The same random seeds are compared across each option.
    """
    if type(completion_weight) is not int or not 0 <= completion_weight <= 100:
        raise ValueError("completion_weight must be a whole number from 0 to 100")
    if repetitions < 1 or repetitions > 8:
        raise ValueError("repetitions must be between 1 and 8")
    if budget < 0:
        raise ValueError("budget must be nonnegative")
    weight = completion_weight / 100
    baseline_capacity = capacity_run(patients, seed, **base_capacity)
    queue_cache = {}
    for d in STAFF_INCREMENTS:
        for b in STAFF_INCREMENTS:
            if base_capacity['discharge_staff'] + d > 30 or base_capacity['booking_staff'] + b > 30:
                continue
            settings = {**base_capacity,
                        'discharge_staff': base_capacity['discharge_staff'] + d,
                        'booking_staff': base_capacity['booking_staff'] + b}
            results = [capacity_run(patients, seed + r*31, **settings)
                       for r in range(repetitions)]
            queue_cache[(d, b)] = (settings, results, capacity_run(patients, seed, **settings))

    choices = []
    for original in audit['possible_plans']:
        # If repetitions is identical to the pathway model's repetitions,
        # validation percentage is the paired mean from that model.
        completion_pct = original['validation']['mean_completion_pct']
        for (add_d, add_b), (settings, repeats, demo_queue) in queue_cache.items():
            people_on_time = [100 * (patients - q['over_120min']) / patients for q in repeats]
            quality = [round(weight * completion_pct + (1-weight) * p, 6)
                       for p in people_on_time]
            staffing_cost = add_d * STAFF_COST_CREDITS['discharge_staff'] + add_b * STAFF_COST_CREDITS['booking_staff']
            cost = round(original['cost_credits'] + staffing_cost, 1)
            choices.append({
                'id': f"{original['id']}__d{add_d}_b{add_b}",
                'plan_id': original['id'],
                'labels': original['labels'],
                'added_discharge_staff': add_d,
                'added_booking_staff': add_b,
                'discharge_staff': settings['discharge_staff'],
                'booking_staff': settings['booking_staff'],
                'intervention_cost': original['cost_credits'],
                'staff_cost': staffing_cost,
                'total_cost': cost,
                'within_budget': cost <= budget + 1e-9,
                'mean_pathway_completion_pct': completion_pct,
                'mean_timely_queue_pct': round(mean(people_on_time), 2),
                'demo_mean_wait_minutes': demo_queue['mean_wait_minutes'],
                'demo_p90_wait_minutes': demo_queue['p90_wait_minutes'],
                'demo_over_120min': demo_queue['over_120min'],
                'score': round(mean(quality), 2),
                'score_range': [round(min(quality), 2), round(max(quality), 2)],
            })

    feasible = [p for p in choices if p['within_budget']]
    if not feasible:
        raise ValueError('No feasible solutions; zero-additional-resource baseline should always fit')
    # Full precision from source would be ideal, but displayed score is stable
    # to two decimals, so tie-breaks remain deterministic and explainable.
    ranked = sorted(choices, key=lambda p: (-p['score'], p['total_cost'], p['id']))
    winner = next(p for p in ranked if p['within_budget'])
    baseline = next(p for p in choices if p['id'] == 'baseline__d0_b0')
    return {
        'method': 'Exact exhaustive joint search (not a trained machine-learning model)',
        'objective': 'Weighted score = w × mean synthetic pathway completion % + (1-w) × mean synthetic queue waits <=120 minutes %; maximize subject to fictional credit budget.',
        'completion_weight_pct': completion_weight,
        'timeliness_weight_pct': 100 - completion_weight,
        'threshold_minutes': 120,
        'budget_credits': budget,
        'staff_cost_credits': STAFF_COST_CREDITS,
        'staff_increments': list(STAFF_INCREMENTS),
        'options_evaluated': len(choices),
        'feasible_options': len(feasible),
        'baseline': baseline,
        'recommended': winner,
        'baseline_queue': baseline_capacity,
        'plans': ranked,
        'replication_count': repetitions,
        'limitations': [
            'The care and staffing/queue modules are independent: added staff do NOT directly change model pathway completion.',
            'The weighted score reflects a subjective, explicit priority choice; it is not a clinical safety score.',
            'All effects, costs, arrival assumptions, patient traits and durations are hypothetical.',
            'Operations use continuous working minutes and simplified service stations, not actual hospital calendars.',
            'Synthetic replication shows sensitivity to model randomization, NOT clinical statistical confidence.'
        ],
    }
