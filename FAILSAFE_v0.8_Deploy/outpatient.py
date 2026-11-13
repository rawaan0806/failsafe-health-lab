"""FAILSAFE v1.1: educational single-day outpatient-clinic capacity model.

All data are aggregated, entirely synthetic and all costs/service times are
illustrative. No clinical advice, patient data or diagnoses.
"""
from __future__ import annotations

import random
from collections import defaultdict
from itertools import combinations
from math import isfinite

DEFAULT_COSTS = {
    'receptionists': 120, 'nurses': 180, 'general_doctors': 260,
    'specialist_doctors': 340, 'technicians': 170,
    'consult_rooms': 110, 'diagnostic_rooms': 130,
    'diagnostic_devices': 95, 'parking_spaces': 45,
}
LABELS = {
    'parking_spaces': '5 extra parking spaces',
    'receptionists': '1 additional receptionist',
    'nurses': '1 additional nurse',
    'general_doctors': '1 additional general clinician',
    'specialist_doctors': '1 additional specialist',
    'technicians': '1 additional diagnostic technician',
    'consult_rooms': '1 additional consultation room',
    'diagnostic_rooms': '1 additional diagnostics room',
    'diagnostic_devices': '1 additional diagnostic device',
}
STAGES = {'parking': 'Parking', 'reception': 'Reception', 'nursing': 'Nurse intake',
          'consultation': 'Consultations', 'diagnostics': 'Diagnostics'}


def parse_outpatient(raw):
    if not isinstance(raw, dict):
        raise ValueError('Send a configuration object')
    allowed = {'patients','routine_pct','diagnostic_pct','triage_pct','car_pct','hours','seed',
               'budget','receptionists','nurses','general_doctors','specialist_doctors',
               'technicians','consult_rooms','diagnostic_rooms','diagnostic_devices','parking_spaces','parking_reserved','routine_count','diagnostic_count','nurse_count','car_count','unit_costs'}
    if set(raw) - allowed:
        raise ValueError('Unknown field: '+sorted(set(raw)-allowed)[0])
    specs = {
        'patients':(100,20,300), 'routine_pct':(40,0,100), 'diagnostic_pct':(20,0,100),
        'triage_pct':(35,0,100), 'car_pct':(35,0,100), 'hours':(8,4,12),
        'seed':(42,0,1000000), 'budget':(650,0,5000),
        'receptionists':(2,0,24), 'nurses':(2,0,24), 'general_doctors':(2,0,24),
        'specialist_doctors':(2,0,24), 'technicians':(1,0,24),
        'consult_rooms':(4,0,30), 'diagnostic_rooms':(1,0,20),
        'diagnostic_devices':(1,0,20), 'parking_spaces':(80,0,1000), 'parking_reserved':(20,0,1000)
    }
    cfg={}
    for key,(default,lo,hi) in specs.items():
        v=raw.get(key,default)
        if type(v) is not int or not lo <= v <= hi:
            raise ValueError(f'{key} must be a whole number between {lo} and {hi}')
        cfg[key]=v
    if cfg['routine_pct'] + cfg['diagnostic_pct'] > 100:
        raise ValueError('Routine and diagnostic percentages cannot add up to more than 100')
    # Counts are the primary interface. Legacy percentages are still accepted for
    # backwards compatibility with earlier simulations and test scenarios.
    count_fields = {
        'routine_count': round(cfg['patients'] * cfg['routine_pct'] / 100),
        'diagnostic_count': round(cfg['patients'] * cfg['diagnostic_pct'] / 100),
        'nurse_count': round(cfg['patients'] * cfg['triage_pct'] / 100),
        'car_count': round(cfg['patients'] * cfg['car_pct'] / 100),
    }
    for key,default in count_fields.items():
        v=raw.get(key, default)
        if type(v) is not int or not 0 <= v <= cfg['patients']:
            raise ValueError(f'{key} must be a whole number between 0 and patients')
        cfg[key]=v
    if cfg['routine_count'] + cfg['diagnostic_count'] > cfg['patients']:
        raise ValueError('Routine and diagnostic visit counts cannot exceed total patients')
    if cfg['parking_reserved'] > cfg['parking_spaces']:
        raise ValueError('Reserved parking cannot exceed total parking spaces')
    costs = raw.get('unit_costs', {})
    if not isinstance(costs,dict) or set(costs)-set(DEFAULT_COSTS):
        raise ValueError('Invalid cost assumptions')
    cfg['unit_costs']=dict(DEFAULT_COSTS)
    for k,v in costs.items():
        if type(v) is not int or not 0 <= v <= 3000:
            raise ValueError('All illustrative costs must be whole numbers from 0 to 3000')
        cfg['unit_costs'][k]=v
    return cfg


def _first_available(moment, staff):
    if not staff: return None
    j=min(range(len(staff)), key=lambda ix: staff[ix])
    return j, max(moment,staff[j])


def _pair_available(moment, people, rooms, third=None):
    if not people or not rooms or (third is not None and not third):
        return None
    thirds=range(len(third)) if third is not None else (None,)
    choice=None
    for a in range(len(people)):
        for b in range(len(rooms)):
            for c in thirds:
                t=max(moment,people[a],rooms[b],third[c] if c is not None else moment)
                key=(t,a,b,c if c is not None else -1)
                if choice is None or key < choice[0]: choice=(key,a,b,c,t)
    return choice[1:]


def _patients(cfg):
    rng=random.Random(cfg['seed'])
    close=cfg['hours']*60
    rows=[]
    # Exact synthetic patient counts: the form never asks users to calculate percentages.
    n=cfg['patients']
    kinds=(['routine']*cfg['routine_count'] + ['diagnostic']*cfg['diagnostic_count'] +
           ['specialist']*(n-cfg['routine_count']-cfg['diagnostic_count']))
    nurse=[True]*cfg['nurse_count']+[False]*(n-cfg['nurse_count'])
    car=[True]*cfg['car_count']+[False]*(n-cfg['car_count'])
    rng.shuffle(kinds);rng.shuffle(nurse);rng.shuffle(car)
    for i,typ in enumerate(kinds):
        # Morning-heavy arrivals. Assumed, not a measured hospital distribution.
        arrival=int(min(close-1, max(0,(0.60*rng.random()+0.40*rng.betavariate(2,4))*close)))
        rows.append((arrival,i,typ,nurse[i],car[i],
                     rng.randint(3,7),rng.randint(7,14),rng.randint(7,13),
                     rng.randint(15,26) if typ=='routine' else rng.randint(20,38),
                     rng.randint(15,29)))
    rows.sort()
    return rows


def simulate(cfg, patient_rows=None):
    """Deterministic appointment-order queue/resource simulation, one operating day.

    Each stage reserves the earliest feasible resource(s). Parking is occupied
    until the visit finishes. All staff remain available during chosen hours:
    breaks, no-shows and clinical urgency are intentionally not modeled.
    """
    if patient_rows is None: patient_rows=_patients(cfg)
    resources={k:[0.0]*cfg[k] for k in ('receptionists','nurses','general_doctors','specialist_doctors',
                    'technicians','consult_rooms','diagnostic_rooms','diagnostic_devices')}
    # Reserved spaces remain unavailable for the whole fictional shift.
    resources['parking_spaces']=[0.0]*max(0,cfg['parking_spaces']-cfg['parking_reserved'])
    waits=defaultdict(list)
    blocked=defaultdict(int)
    stage_count=defaultdict(int)
    arrived_types=defaultdict(int)
    ended=[]
    completed=0
    after_close=0
    parking_at_capacity=0
    close=60*cfg['hours']
    for (arrival,pid,typ,needs_nurse,by_car,parking_min,checkin_min,triage_min,visit_min,diag_min) in patient_rows:
        arrived_types[typ]+=1
        t=float(arrival)
        parking_ix=None
        if by_car:
            r=_first_available(t,resources['parking_spaces'])
            if r is None:
                blocked['parking']+=1
                continue
            parking_ix,t0=r
            waits['parking'].append(t0-t)
            if t0>t+0.001: parking_at_capacity+=1
            stage_count['parking']+=1
            t=t0+parking_min
        r=_first_available(t,resources['receptionists'])
        if r is None:
            blocked['reception']+=1
            if parking_ix is not None: resources['parking_spaces'][parking_ix]=t+5
            continue
        ix,start=r
        waits['reception'].append(start-t)
        stage_count['reception']+=1
        resources['receptionists'][ix]=start+checkin_min
        t=start+checkin_min
        if needs_nurse:
            r=_first_available(t,resources['nurses'])
            if r is None:
                blocked['nursing']+=1
                if parking_ix is not None: resources['parking_spaces'][parking_ix]=t+5
                continue
            ix,start=r
            waits['nursing'].append(start-t)
            stage_count['nursing']+=1
            resources['nurses'][ix]=start+triage_min
            t=start+triage_min
        doc_key='general_doctors' if typ=='routine' else 'specialist_doctors'
        pair=_pair_available(t,resources[doc_key],resources['consult_rooms'])
        if pair is None:
            blocked['consultation']+=1
            if parking_ix is not None: resources['parking_spaces'][parking_ix]=t+5
            continue
        di,ri,_,start=pair
        waits['consultation'].append(start-t)
        stage_count['consultation']+=1
        end=start+visit_min
        resources[doc_key][di]=end
        resources['consult_rooms'][ri]=end
        t=end
        if typ=='diagnostic':
            triple=_pair_available(t,resources['technicians'],resources['diagnostic_rooms'], resources['diagnostic_devices'])
            if triple is None:
                blocked['diagnostics']+=1
                if parking_ix is not None: resources['parking_spaces'][parking_ix]=t+5
                continue
            ti,ri,ei,start=triple
            waits['diagnostics'].append(start-t)
            stage_count['diagnostics']+=1
            end=start+diag_min
            resources['technicians'][ti]=end
            resources['diagnostic_rooms'][ri]=end
            resources['diagnostic_devices'][ei]=end
            t=end
        ended.append(t)
        if parking_ix is not None: resources['parking_spaces'][parking_ix]=t+5
        if t<=close: completed+=1
        else: after_close+=1
    return {'patients':cfg['patients'],'completed_before_close':completed,
            'completed_percent':round(100*completed/cfg['patients'],1),
            'completed_after_close':after_close,
            'not_completed':cfg['patients']-completed,
            'average_wait_minutes':round(sum(map(sum, waits.values()))/len(ended),1) if ended else None,
            'mean_stage_wait':{k:round(sum(waits[k])/len(waits[k]),1) if waits[k] else None for k in STAGES},
            'blocked_stages':{k:blocked[k] for k in STAGES},
            'visits_by_type':dict(arrived_types),
            'stage_visits':{k:stage_count[k] for k in STAGES},
            'parking_queue_count':parking_at_capacity,
            'parking_spaces_available':max(0,cfg['parking_spaces']-cfg['parking_reserved']),
            'last_departure_minute':round(max(ended),1) if ended else None}


def _score(r):
    # Score prioritizes patients completing within hours; remaining wait is tie-break.
    avg=r['average_wait_minutes'] if r['average_wait_minutes'] is not None else 100000.0
    return r['completed_before_close']*10000 - avg


def _changes(plan):
    return tuple((k, 5 if k=='parking_spaces' else 1) for k in plan)


def analyze(raw):
    cfg=parse_outpatient(raw)
    cohort=_patients(cfg)
    baseline=simulate(cfg,cohort)
    all_opts=[()] + [(k,) for k in DEFAULT_COSTS] + list(combinations(DEFAULT_COSTS,2))
    eligible=[]
    for opt in all_opts:
        cost=sum(cfg['unit_costs'][k] for k in opt)
        if cost > cfg['budget']:continue
        updated={**cfg}
        for k,n in _changes(opt):updated[k]+=n
        res=simulate(updated,cohort)
        eligible.append((opt,cost,res))
    # Budget ties: cheaper choices first. Zero gain means retain current layout.
    eligible.sort(key=lambda v:(-_score(v[2]),v[1],len(v[0]),v[0]))
    best=eligible[0]
    improvement=best[2]['completed_before_close']-baseline['completed_before_close']
    # Expose the evidence for the recommendation, not just the action names.
    # The optimizer's ranking is (1) more completed visits, (2) less total wait,
    # (3) lower illustrative cost. This is a what-if rule, not a clinical claim.
    top_plans = [
        {
            'actions': [LABELS[k] for k in option],
            'cost_eur': cost,
            'completed': result['completed_before_close'],
            'average_wait_minutes': result['average_wait_minutes'],
        }
        for option, cost, result in eligible[:3]
    ]
    reception_options=[item for item in eligible if 'receptionists' in item[0]]
    best_reception_option = reception_options[0] if reception_options else None
    chosen_is_reception = 'receptionists' in best[0]
    stage_candidates=[(v,k) for k,v in baseline['mean_stage_wait'].items() if v is not None]
    stage_candidates.sort(reverse=True)
    worst=stage_candidates[0][1] if stage_candidates else None
    findings=[]
    for stage in STAGES:
        avg=baseline['mean_stage_wait'][stage]
        blocked=baseline['blocked_stages'][stage]
        if blocked:
            findings.append({'stage':stage,'title':f'{STAGES[stage]} unavailable','detail':f'{blocked} synthetic visits could not proceed because a required resource was unavailable.','level':'high'})
        elif avg is not None and avg>25:
            findings.append({'stage':stage,'title':f'{STAGES[stage]} queue','detail':f'Average modeled wait at this step: {avg:.0f} minutes.','level':'high' if avg>50 else 'moderate'})
    if baseline['not_completed']:
        findings.append({'stage':'hours','title':'Visits extend beyond opening hours','detail':f"{baseline['not_completed']} of {cfg['patients']} simulated visits did not finish before closing.",'level':'moderate'})
    if not findings: findings.append({'stage':'general','title':'No major issue in this scenario','detail':'The modeled queues appear manageable under these assumptions.','level':'low'})
    return {
        'version':'1.4','mode':'outpatient-clinic','synthetic_only':True,
        'scenario':{k:v for k,v in cfg.items() if k!='seed'},
        'baseline':baseline,'optimized':best[2],
        'recommendation':{
            'actions':[LABELS[k] for k in best[0]],
            'action_keys':list(best[0]),
            'estimated_cost_eur':best[1],
            'added_completed':improvement,
            'explanation':('Among the affordable options, FAILSAFE first ranks how many simulated visits finish before closing, then average modeled waiting time, then illustrative cost. This is not a clinical recommendation.'),
            'why_selected':(
                f'This plan completes {best[2]["completed_before_close"]} of {cfg["patients"]} simulated visits before closing, '
                f'compared with {baseline["completed_before_close"]} under the current plan. '
                f'The model prioritizes completed visits over reducing any single queue.'
                if improvement > 0 else
                f'This plan completes {best[2]["completed_before_close"]} of {cfg["patients"]} simulated visits before closing. '
                f'With no gain in completed visits, the optimizer prefers lower modeled total waiting time and then lower assumed cost.'
            ),
            'objective_order':['More visits completed before closing', 'Less average total modeled waiting time', 'Lower hypothetical resource cost'],
            'top_competing_plans':top_plans,
            'reception_alternative':(
                {'cost_eur':best_reception_option[1],
                 'completed':best_reception_option[2]['completed_before_close'],
                 'average_wait_minutes':best_reception_option[2]['average_wait_minutes']}
                if best_reception_option and not chosen_is_reception else None
            ),
        },
        'findings':findings[:5], 'largest_wait_stage':worst,
        'combinations_tested':len(eligible),'total_candidate_options':len(all_opts),
        'assumptions':[
            'Single fictional outpatient day. No actual patient data or diagnoses.',
            'Patient types and special care needs use exact counts; visit patterns and service durations are invented.',
            'All staff are available during the same opening hours. Shifts, breaks, urgency, no-shows and safety are not modeled.',
            'Parking spaces marked unavailable stay unavailable for the full modeled day. Other occupied spaces become free after each simulated visit.',
            'Illustrative daily costs in euros are placeholders, not actual prices or validated business estimates.',
            'Optimizer checks no changes, one change or two changes only. A plan that scores best in this model is not clinically validated.'
        ]
    }
