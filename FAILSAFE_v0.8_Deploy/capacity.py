"""Reproducible illustrative queue/capacity simulator; no clinical validity."""
from __future__ import annotations
from heapq import heappush, heappop, heapify
from statistics import mean
import random


def capacity_run(patients, seed, discharge_staff=3, booking_staff=2,
                 arrivals_per_day=80, service_minutes=18, booking_minutes=12,
                 days=7, include_trace=False):
    """FCFS two-station service queue with independent deterministic synthetic arrivals.

    Arrivals uniformly spread through an 8-hour day. Service requests may spill
    over into subsequent shifts; waiting time is measured in working minutes.
    The outputs measure modeled operational delays, NOT medical outcomes.
    """
    if not 1 <= discharge_staff <= 30 or not 1 <= booking_staff <= 30:
        raise ValueError('Staff must be from 1 to 30')
    if not 10 <= arrivals_per_day <= 500 or not 5 <= service_minutes <= 90 or not 5 <= booking_minutes <= 90:
        raise ValueError('Capacity settings out of range')
    rng = random.Random(seed + 7751)
    # A continuous 'working minute' clock: one day is 480 working minutes.
    # Shift breaks and physical clinic opening hours are deliberately excluded.
    times = [j * 480 + i * 480 / arrivals_per_day
             for j in range((patients + arrivals_per_day - 1)//arrivals_per_day)
             for i in range(arrivals_per_day)][:patients]
    arrivals = sorted((t + rng.uniform(0, 2), ident) for ident, t in enumerate(times))
    # Pre-sample work by ID so staff scenarios have paired, identical demands.
    discharge_durations = [service_minutes * rng.uniform(.75, 1.35) for _ in range(patients)]
    booking_durations = [booking_minutes * rng.uniform(.8, 1.25) for _ in range(patients)]
    discharge_available = [0.] * discharge_staff
    booking_available = [0.] * booking_staff
    heapify(discharge_available)
    heapify(booking_available)
    records = [None] * patients
    for arrival, ident in arrivals:  # discharge FCFS
        available = heappop(discharge_available)
        start = max(arrival, available)
        finish = start + discharge_durations[ident]
        heappush(discharge_available, finish)
        records[ident] = [arrival, start, finish, None, None]
    # Booking FCFS must order by discharge completion, not original arrival.
    for ident in sorted(range(patients), key=lambda i: (records[i][2], i)):
        finish = records[ident][2]
        available = heappop(booking_available)
        start = max(finish, available)
        end = start + booking_durations[ident]
        heappush(booking_available, end)
        records[ident][3:] = [start, end]
    waits = [(r[1]-r[0]) + (r[3]-r[2]) for r in records]
    ordered_waits = sorted(waits)
    long_waits = sum(wait > 120 for wait in waits)
    late_booking = sum(r[3]-r[2] > 60 for r in records)
    time_window = patients / arrivals_per_day * 480
    total_simulated_minutes = max(r[4] for r in records)
    result = {
        'patients': patients,
        'mean_wait_minutes': round(mean(waits), 1),
        'p90_wait_minutes': round(ordered_waits[min(patients-1, int(.9*patients))], 1),
        'over_120min': long_waits,
        'over_120_pct': round(long_waits*100/patients,1),
        'booking_wait_over_60': late_booking,
        'discharge_utilization_pct': round(min(100., patients*service_minutes/(time_window*discharge_staff)*100),1),
        'booking_utilization_pct': round(min(100., patients*booking_minutes/(time_window*booking_staff)*100),1),
    }
    if include_trace:
        result['trace'] = [[round(v, 3) for v in row] for row in records]
        result['end_minute'] = round(total_simulated_minutes, 3)
        result['stations'] = ['Not arrived', 'Discharge queue', 'Discharge service',
                              'Booking queue', 'Booking service', 'Finished']
    return result
