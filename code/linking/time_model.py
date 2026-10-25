"""Cutoff-aware activity timing model, calibrated only on the public sample."""
from __future__ import annotations

from collections import Counter, defaultdict
from bisect import bisect_left, bisect_right
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
from statistics import median
from typing import Iterable
from dataclasses import replace

MODEL_PATH = Path(__file__).with_name("offsets.json")
EVENT_TYPES = {
    "account": {"DELETE_RECORD"},
    "analytics": {"ANONYMIZE_RECORD", "DELETE_RECORD"},
    "telemetry": {"ANONYMIZE_RECORD", "DELETE_RECORD"},
    "search": {"DELETE_RECORD"},
    "support": {"DELETE_RECORD", "REDACT_RECORD"},
    "export": {"DELETE_RECORD"},
    "backup": {"BLOCK_RESTORE"},
    "data": {"DISABLE_DATA_FLOW"},
    "tombstone": {"REDACT_RECORD"},
    "audit": {"RETAIN_RECORD"},
}
STATUS_RESULT = {
    "COMPLETE": {"SUCCESS"},
    "NOT_STARTED": {"FAILED"},
    "PARTIALLY_COMPLETE": {"PARTIAL", "SUCCESS"},
}


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _resource_type(resource_id: str) -> str:
    return str(resource_id).split("_", 1)[0].lower()


def _quartiles(values: list[float]) -> tuple[float, float]:
    ordered = sorted(values)
    if not ordered:
        return 0.0, 0.0
    def q(p: float) -> float:
        i = (len(ordered) - 1) * p
        lo = int(i); hi = min(len(ordered) - 1, lo + 1)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (i - lo)
    return q(.25), q(.75)


def _fit_distribution(values: list[float]) -> dict:
    q1, q3 = _quartiles(values)
    med = median(values)
    return {"n": len(values), "median_hours": round(med, 6),
            "q1_hours": round(q1, 6), "q3_hours": round(q3, 6),
            "sigma_hours": round(max(.08, (q3 - q1) / 1.349), 6),
            "min_hours": round(min(values), 6), "max_hours": round(max(values), 6)}


def _fit_offsets(requests: list[dict], answers: list[dict], activities: list[dict]) -> dict:
    request_by_id = {r["case_id"]: r for r in requests}
    activity_by_resource = defaultdict(list)
    for a in activities:
        activity_by_resource[a.get("resource_id", "")].append(a)
    seen = set()
    observations = defaultdict(list)
    status_counts = Counter()
    for answer in answers:
        req = request_by_id.get(answer["case_id"])
        if not req:
            continue
        for step in json.loads(answer["steps_json"]):
            rid = step.get("resource_id", "")
            key = (req["case_id"], rid)
            if key in seen:
                continue
            seen.add(key)
            cutoff=_dt(req.get('audit_at',req['reported_at']))
            matching = [a for a in activity_by_resource.get(rid, [])
                        if a.get("event_type") in EVENT_TYPES.get(_resource_type(rid), set())
                        and _dt(a.get('event_time',''))<=cutoff]
            if not matching:
                continue
            # Prefer the closest type-correct worker event; the sample contains
            # adjacent claims for the same resource at separate times.
            a = min(matching, key=lambda x: abs((_dt(req["reported_at"]) - _dt(x["event_time"])).total_seconds()))
            delta = (_dt(req["reported_at"]) - _dt(a["event_time"])).total_seconds() / 3600
            system = str(a.get("target_system") or a.get("source_system") or "unknown")
            base = f"{system}|{a.get('event_type', '')}"
            observations[base].append(delta)
            conditional = f"{base}|{a.get('reported_result', '')}"
            observations[conditional].append(delta)
            status_counts[f"{req.get('reported_status', '')}|{a.get('reported_result', '')}"] += 1
    fitted = {}
    for key, values in observations.items():
        # Worker timing is multimodal: fast retries and normal queue delays
        # coexist for the same operation. Retain the aggregate robust summary
        # and separate modes whose centers differ by at least 18 minutes.
        sorted_values = sorted(values); clusters=[]
        for value in sorted_values:
            if not clusters or value - clusters[-1][-1] > .30:
                clusters.append([value])
            else:
                clusters[-1].append(value)
        fitted[key] = _fit_distribution(values)
        fitted[key]["modes"] = [_fit_distribution(cluster) for cluster in clusters]
    return {"source": "participant-facing sample_output.csv; resource/activity joins only",
            "status_result_counts": dict(sorted(status_counts.items())), "groups": dict(sorted(fitted.items()))}


def fit_and_write(requests: list[dict], answers: list[dict], activities: list[dict], path: Path = MODEL_PATH) -> dict:
    model = _fit_offsets(requests, answers, activities)
    path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return model


def _offset_likelihood(model: dict, system: str, event_type: str, result: str, delta: float) -> tuple[float, str]:
    groups = model.get("groups", {})
    base = f"{system}|{event_type}"
    candidates=[]
    for key in (f"{base}|{result}",base):
        group=groups.get(key)
        if group and all(group is not prior for prior in candidates):candidates.append(group)
    if not candidates:
        return 0.0, "no_calibration_group"
    # Use result-conditioned distributions when present, while retaining the
    # pooled operation distribution as a backoff for sparse folds and rare modes.
    scored=[]
    for group in candidates:
        modes=group.get("modes") or [group]
        # Small held-out folds can omit a rare fast/slow worker mode entirely.
        # Keep fitted robust centers while using a conservative scale floor.
        for mode in modes:
            value=math.exp(-.5*((delta-mode["median_hours"])/max(.30,mode["sigma_hours"]))**2)
            scored.append((value,group))
    likelihood,group=max(scored,key=lambda x:x[0])
    return likelihood, f"offset:{base} modes={len(modes)} median={group['median_hours']}h iqr={group.get('q1_hours', group['median_hours'])}..{group.get('q3_hours', group['median_hours'])}h"


def _status_likelihood(model: dict, status: str, result: str) -> float:
    counts = model.get("status_result_counts", {})
    total = sum(v for k, v in counts.items() if k.startswith(status + "|"))
    if not total:
        return .5
    return (counts.get(f"{status}|{result}", 0) + .5) / (total + 1.5)


def build_activity_time_index(activities: Iterable[dict], *, parse_time) -> dict:
    grouped=defaultdict(list)
    for event in activities:
        typ=_resource_type(str(event.get('resource_id','')))
        when=parse_time(event.get('event_time',''))
        if typ and when:
            grouped[typ].append((when,event))
    index={}
    for typ,pairs in grouped.items():
        pairs.sort(key=lambda x:x[0]);index[typ]=([x[0] for x in pairs],[x[1] for x in pairs])
    return index


def build_resource_activity_index(activities: Iterable[dict]) -> dict[str,list[dict]]:
    out=defaultdict(list)
    for event in activities:
        if event.get('resource_id'):
            out[str(event['resource_id'])].append(event)
    return dict(out)


def rank_direct_candidate_by_activity(candidate, case: dict, activities: Iterable[dict], model: dict, *, parse_time,
                                       resource_index: dict[str,list[dict]] | None = None) :
    """Use worker timing only to distinguish duplicate requests for a known owner."""
    typ=_resource_type(candidate.resource_id)
    cutoff=parse_time(case['audit_at']);reported=parse_time(case['reported_at'])
    rows=[]
    event_rows=resource_index.get(candidate.resource_id,[]) if resource_index is not None else activities
    for event in event_rows:
        if event.get('resource_id')!=candidate.resource_id or str(event.get('event_type','')).upper() not in EVENT_TYPES.get(typ,set()):
            continue
        when=parse_time(event.get('event_time',''))
        if not when or when>cutoff:continue
        system=str(event.get('target_system') or event.get('source_system') or 'unknown')
        result=str(event.get('reported_result',''))
        delta=(reported-when).total_seconds()/3600
        likelihood,offset_signal=_offset_likelihood(model,system,str(event.get('event_type','')).upper(),result,delta)
        statuslike=_status_likelihood(model,str(case.get('reported_status','')),result)
        if likelihood:
            score=.98+.019*(.75*likelihood+.25*statuslike)
            rows.append((score,event,offset_signal,delta))
    if not rows:return candidate
    score,event,signal,delta=max(rows,key=lambda x:x[0])
    return replace(candidate,score=min(.999,score),
                   signals=tuple(sorted(set(candidate.signals)|{'activity_time_case_assignment'})),
                   source_ids=tuple(sorted(set(candidate.source_ids)|{str(event.get('activity_id','')),signal,f'delta_hours={delta:.6f}'})))


def time_activity_candidates(case: dict, user_id: str, activities: Iterable[dict], *, parse_time,
                             model: dict | None = None, sibling_activity_ids: set[str] | None = None,
                             burst_scores: dict[str,float] | None = None, activity_index: dict | None = None) -> list:
    """Score candidate (request, resource) links from calibrated time + result.

    Activity rows are linking signals only: the planner still requires an
    independent participant-facing evidence snapshot before reporting state.
    """
    from .linker import ResourceCandidate
    if model is None:
        model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    cutoff, reported = parse_time(case["audit_at"]), parse_time(case["reported_at"])
    if not cutoff or not reported:
        return []
    siblings = sibling_activity_ids or set()
    burst_scores=burst_scores or {}
    out = []
    if activity_index is not None:
        # Merge operation-bearing resource types in a bounded reported_at
        # window that covers every fitted offset mode.
        pairs=[]
        lower=reported-timedelta(hours=2.5)
        upper=reported+timedelta(hours=2.5)
        for kind in EVENT_TYPES:
            tvec,avec=activity_index.get(kind,([],[]))
            lo=bisect_left(tvec,lower);hi=bisect_right(tvec,upper)
            pairs.extend(avec[lo:hi])
        candidate_rows=pairs
    else:
        candidate_rows=activities
    for a in candidate_rows:
        rid = str(a.get("resource_id", "")); typ = _resource_type(rid)
        event_type = str(a.get("event_type", "")).upper()
        if not rid or event_type not in EVENT_TYPES.get(typ, set()):
            continue
        event_time = parse_time(a.get("event_time", ""))
        if not event_time or event_time > cutoff:
            continue
        system = str(a.get("target_system") or a.get("source_system") or "unknown")
        delta = (reported - event_time).total_seconds() / 3600
        likelihood, offset_signal = _offset_likelihood(model, system, event_type, str(a.get("reported_result", "")), delta)
        if likelihood < .10:
            continue
        result_likelihood = _status_likelihood(model, str(case.get("reported_status", "")), str(a.get("reported_result", "")))
        # Scores leave room for deterministic direct evidence (0.98+) while
        # retaining useful low-confidence activity-only assignments.
        burst_strength=burst_scores.get(str(a.get('activity_id','')),0.0)
        score = .62 + .20 * likelihood + .14 * result_likelihood + .03 * burst_strength
        signals = ["reported_at_offset_likelihood", "reported_status_result_likelihood"]
        if a.get("activity_id") in siblings or burst_strength:
            signals.append("same_burst_activity_anchor")
        score = min(.97, score)
        out.append(ResourceCandidate(case["case_id"], user_id, rid, system, score,
                                     tuple(signals), (str(a.get("activity_id", "")), offset_signal,
                                                     f"delta_hours={delta:.6f}",
                                                     f"burst_strength={burst_strength:.4f}",
                                                     f"reported_result={a.get('reported_result', '')}")))
    # If a resource has repeated activity rows, retain the strongest candidate
    # for this request and preserve the winning row's provenance.
    best = {}
    for candidate in out:
        prior = best.get(candidate.resource_id)
        if prior is None or candidate.score > prior.score:
            best[candidate.resource_id] = candidate
    return list(best.values())


def _system_for_kind(kind: str) -> str:
    return {'account':'account_service','analytics':'analytics_platform','telemetry':'analytics_platform',
            'search':'search_service','support':'support_platform','export':'export_service',
            'backup':'backup_service','data':'integration_service','tombstone':'identity_service',
            'audit':'security_service'}.get(kind,'unknown')


def burst_activity_scores(activities: Iterable[dict], anchor_resources: set[str], cutoff: datetime) -> dict[str,float]:
    """Score worker rows by time and activity-id proximity to strong anchors."""
    rows=list(activities)
    anchors=[a for a in rows if a.get('resource_id') in anchor_resources
             and str(a.get('source_system','')).casefold()=='deletion_worker'
             and _dt(a.get('event_time',''))<=cutoff]
    anchor_times=[_dt(a['event_time']) for a in anchors]
    anchor_numbers=[]
    for a in anchors:
        try:anchor_numbers.append(int(str(a.get('activity_id','')).split('_')[-1]))
        except (TypeError,ValueError):pass
    out={}
    for a in rows:
        if str(a.get('source_system','')).casefold()!='deletion_worker' or _dt(a.get('event_time',''))>cutoff:
            continue
        try:number=int(str(a.get('activity_id','')).split('_')[-1])
        except (TypeError,ValueError):number=None
        time_score=max((math.exp(-abs((_dt(a['event_time'])-t).total_seconds())/(45*60))
                        for t in anchor_times if abs((_dt(a['event_time'])-t).total_seconds())<=45*60),default=0.0)
        id_score=max((math.exp(-abs(number-n)/8) for n in anchor_numbers
                      if number is not None and abs(number-n)<=8),default=0.0)
        value=max(time_score,id_score)
        if value:out[str(a.get('activity_id',''))]=value
    return out


def burst_activity_ids(activities: Iterable[dict], anchor_resources: set[str], cutoff: datetime) -> set[str]:
    return set(burst_activity_scores(activities,anchor_resources,cutoff))


def sample_oof(requests: list[dict], answers: list[dict], activities: list[dict], direct_candidates: list | None = None,
               user_ids: dict[str,str] | None = None) -> dict:
    """Leave-one-case-out rank test; held-out resource labels never fit offsets."""
    by_case = {r["case_id"]: r for r in requests}
    answer_by_case = {a["case_id"]: a for a in answers}
    activity_index=build_activity_time_index(activities,parse_time=_dt)
    resource_index=build_resource_activity_index(activities)
    gold = defaultdict(set)
    for case, answer in answer_by_case.items():
        for step in json.loads(answer["steps_json"]):
            gold[case].add(step["resource_id"])
    per_type = defaultdict(lambda: {"gold": 0, "predicted": 0, "tp": 0})
    ablation_counts={name:defaultdict(lambda:{"gold":0,"predicted":0,"tp":0})
                     for name in ("S1","S1+S2","S1+S2+S3","S1+S2+S3+S4","S1+S2+S3+S4+global")}
    activities_by_id={str(a.get("activity_id","")):a for a in activities}
    status_result={"COMPLETE":{"SUCCESS"},"NOT_STARTED":{"FAILED"},"PARTIALLY_COMPLETE":{"PARTIAL","SUCCESS"}}
    heldout_misses=[]
    all_predictions = {}
    for heldout in sorted(answer_by_case):
        train_answers = [x for x in answers if x["case_id"] != heldout]
        model = _fit_offsets(requests, train_answers, activities)
        fold_direct=[]
        for candidate in direct_candidates or []:
            req=by_case.get(candidate.case_id)
            fold_direct.append(rank_direct_candidate_by_activity(candidate,req,activities,model,parse_time=_dt,resource_index=resource_index) if req else candidate)
        fold_time=[]
        for req in requests:
            strong = [x for x in fold_direct if x.case_id == req["case_id"]]
            strong_resources = {x.resource_id for x in strong}
            burst=burst_activity_scores(activities,strong_resources,_dt(req['audit_at']))
            fold_time.extend(time_activity_candidates(req, (user_ids or {}).get(req["case_id"],req["case_id"]), activities, parse_time=_dt,
                                                       model=model, sibling_activity_ids=set(burst),burst_scores=burst,
                                                       activity_index=activity_index))
        def time_score(candidate, include_status, include_burst):
            event=activities_by_id.get(candidate.source_ids[0] if candidate.source_ids else "")
            if not event:return candidate
            req=by_case[candidate.case_id]
            delta=(_dt(req['reported_at'])-_dt(event['event_time'])).total_seconds()/3600
            likelihood,_=_offset_likelihood(model,str(event.get('target_system') or event.get('source_system') or 'unknown'),
                                            str(event.get('event_type','')).upper(),str(event.get('reported_result','')),delta)
            result=_status_likelihood(model,str(req.get('reported_status','')),str(event.get('reported_result',''))) if include_status else 0.0
            burst_strength=0.0
            if include_burst:
                for source in candidate.source_ids:
                    if source.startswith('burst_strength='):
                        try:burst_strength=float(source.split('=',1)[1])
                        except ValueError:pass
            signals={'reported_at_offset_likelihood'}
            if include_status:signals.add('reported_status_result_likelihood')
            if include_burst and burst_strength:signals.add('same_burst_activity_anchor')
            score=min(.97,.62+.20*likelihood+.14*result+.10*burst_strength)
            return replace(candidate,score=score,signals=tuple(sorted(signals)))
        s1=[time_score(x,False,False) for x in fold_time]
        s12=[time_score(x,True,False) for x in fold_time]
        s123=[time_score(x,True,True) for x in fold_time]
        s1234=fold_direct+s123
        candidates = s1234
        candidates_by_resource=defaultdict(list);candidates_by_case_type=defaultdict(list)
        for candidate in candidates:
            candidates_by_resource[candidate.resource_id].append(candidate)
            candidates_by_case_type[(candidate.case_id,_resource_type(candidate.resource_id))].append(candidate)

        def top_per_type(pool, case_id):
            best={}
            for item in pool:
                if item.case_id!=case_id:continue
                kind=_resource_type(item.resource_id)
                prior=best.get(kind)
                if prior is None or (item.score,item.resource_id)>(prior.score,prior.resource_id):best[kind]=item
            return {x.resource_id for x in best.values()}

        stage_pools={"S1":s1,"S1+S2":s12,"S1+S2+S3":s123,"S1+S2+S3+S4":s1234}
        for stage,pool in stage_pools.items():
            ablation_pred=top_per_type(pool,heldout)
            for rid in gold[heldout]|ablation_pred:
                kind=_resource_type(rid)
                if rid in gold[heldout]:ablation_counts[stage][kind]['gold']+=1
                if rid in ablation_pred:
                    ablation_counts[stage][kind]['predicted']+=1
                    if rid in gold[heldout]:ablation_counts[stage][kind]['tp']+=1
        from .linker import global_ownership
        assigned, unresolved = global_ownership(candidates,focus_cases={heldout})
        ranked = sorted((x for x in candidates if x.case_id == heldout), key=lambda x: (-x.score, x.resource_id))
        all_predictions[heldout] = {"candidates": [x.to_dict() for x in ranked],
                                    "assigned": [x.to_dict() for x in assigned.values() if x.case_id == heldout],
                                    "ambiguous": [x for x in unresolved if any(c["case_id"] == heldout for c in x.get("candidates", []))]}
        predicted = {x.resource_id for x in assigned.values() if x.case_id == heldout}
        heldout_request=by_case[heldout]
        missed={rid for rid in gold[heldout]-predicted if _resource_type(rid) in ("account","analytics")}
        for gold_rid in sorted(missed):
            kind=_resource_type(gold_rid)
            local=sorted(candidates_by_case_type[(heldout,kind)],key=lambda x:(-x.score,x.resource_id))
            def describe_candidate(item):
                event_id=next((s for s in item.source_ids if s.startswith('activity_')),None)
                event=activities_by_id.get(event_id) if event_id else None
                if event:
                    delta=(_dt(heldout_request['reported_at'])-_dt(event['event_time'])).total_seconds()/3600
                    system=str(event.get('target_system') or event.get('source_system') or 'unknown')
                    like,offset=_offset_likelihood(model,system,str(event.get('event_type','')).upper(),str(event.get('reported_result','')),delta)
                    result=str(event.get('reported_result',''))
                    temporal={"activity_id":event_id,"event_time":event['event_time'],"event_type":event.get('event_type'),
                              "delta_hours":round(delta,6),"reported_result":result,
                              "status_result_match":result in status_result.get(heldout_request.get('reported_status',''),set()),
                              "offset_likelihood":round(like,6),"offset_group":offset}
                else:temporal=None
                peers=sorted(candidates_by_resource[item.resource_id],key=lambda x:(-x.score,x.case_id))
                return {"resource_id":item.resource_id,"score":round(item.score,6),"signals":list(item.signals),
                        "provenance":list(item.source_ids),"temporal":temporal,
                        "competing_cases":[{"case_id":x.case_id,"user_id":x.user_id,"score":round(x.score,6),
                                            "signals":list(x.signals),"provenance":list(x.source_ids)} for x in peers]}
            exact=[a for a in activities if a.get('resource_id')==gold_rid and _dt(a.get('event_time',''))<=_dt(heldout_request['audit_at'])]
            actual=[]
            for event in exact:
                delta=(_dt(heldout_request['reported_at'])-_dt(event['event_time'])).total_seconds()/3600
                system=str(event.get('target_system') or event.get('source_system') or 'unknown')
                like,offset=_offset_likelihood(model,system,str(event.get('event_type','')).upper(),str(event.get('reported_result','')),delta)
                result=str(event.get('reported_result',''))
                actual.append({"activity_id":event.get('activity_id'),"event_time":event.get('event_time'),
                               "event_type":event.get('event_type'),"delta_hours":round(delta,6),"reported_result":result,
                               "status_result_match":result in status_result.get(heldout_request.get('reported_status',''),set()),
                               "offset_likelihood":round(like,6),"offset_group":offset})
            heldout_misses.append({"case_id":heldout,"resource_type":kind,"gold_resource":gold_rid,
                                   "reported_status":heldout_request.get('reported_status'),
                                   "reported_at":heldout_request.get('reported_at'),"audit_at":heldout_request.get('audit_at'),
                                   "gold_activity":actual,"same_type_candidates":[describe_candidate(x) for x in local],
                                   "gold_resource_competing_cases":[{"case_id":x.case_id,"score":round(x.score,6),
                                       "signals":list(x.signals),"provenance":list(x.source_ids)} for x in candidates_by_resource.get(gold_rid,[]) ]})
        global_stage="S1+S2+S3+S4+global"
        for rid in gold[heldout] | predicted:
            kind = _resource_type(rid)
            if rid in gold[heldout]:ablation_counts[global_stage][kind]['gold']+=1
            if rid in predicted:
                ablation_counts[global_stage][kind]['predicted']+=1
                if rid in gold[heldout]:ablation_counts[global_stage][kind]['tp']+=1
            if rid in gold[heldout]:
                per_type[kind]["gold"] += 1
            if rid in predicted:
                per_type[kind]["predicted"] += 1
                if rid in gold[heldout]:
                    per_type[kind]["tp"] += 1
    for v in per_type.values():
        v["precision"] = v["tp"] / max(1, v["predicted"])
        v["recall"] = v["tp"] / max(1, v["gold"])
    cumulative={}
    for stage,types in ablation_counts.items():
        cumulative[stage]={}
        for kind,v in sorted(types.items()):
            v['precision']=v['tp']/max(1,v['predicted']);v['recall']=v['tp']/max(1,v['gold'])
            v['f1']=2*v['precision']*v['recall']/max(1e-12,v['precision']+v['recall'])
            cumulative[stage][kind]=dict(v)
    return {"protocol": "leave-one-case-out; offsets fit on 31 other public sample cases",
            "per_type": dict(sorted(per_type.items())), "cumulative_ablation":cumulative,
            "heldout_misses":heldout_misses,"predictions": all_predictions}
