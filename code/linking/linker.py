"""Evidence-grounded candidate links with provenance and global ownership checks."""
from __future__ import annotations

from dataclasses import dataclass, asdict, replace
from datetime import datetime
from collections import defaultdict
from bisect import bisect_left, bisect_right
from pathlib import Path
import json
from typing import Iterable

WEIGHTS = json.loads(Path(__file__).with_name('weights.json').read_text(encoding='utf-8'))


@dataclass(frozen=True)
class ResourceCandidate:
    case_id: str
    user_id: str
    resource_id: str
    system_id: str
    score: float
    signals: tuple[str, ...]
    source_ids: tuple[str, ...]
    ambiguous: bool = False

    def to_dict(self):
        return asdict(self)


def candidate_from_facts(case_id: str, user_id: str, facts: Iterable[dict], aliases: set[str], paths: Iterable, cutoff: datetime) -> list[ResourceCandidate]:
    """Score only observed identity/resource relations; timing is a weak feature."""
    path_sources = defaultdict(set)
    for edge in paths:
        path_sources[(edge.right, edge.source_id)].add(edge.relation)
    by_resource = defaultdict(list)
    for fact in facts:
        rid = str(fact.get('resource') or '')
        if not rid or fact.get('time') > cutoff or fact.get('file_time', fact.get('time')) > cutoff:
            continue
        by_resource[rid].append(fact)
    out = []
    for rid, rows in by_resource.items():
        signals = set()
        sources = set()
        score = 0.0
        system = rows[0].get('system', 'unknown_service')
        for fact in rows:
            identifiers = set(fact.get('emails', ())) | set(fact.get('users', ())) | set(fact.get('hashes', ())) | set(fact.get('phones', ()))
            match = identifiers & aliases
            # Direct same-record, SQL-row, or trace-group co-occurrence.
            if match:
                sources.add(fact['file'])
                if fact.get('_trace_group') or fact.get('data', {}).get('_trace_group'):
                    signals.add('trace_group_identity_resource')
                    score = max(score, WEIGHTS['trace_group_identity_resource'])
                elif fact.get('source_type') == 'evidence':
                    signals.add('same_record_identity_resource')
                    score = max(score, WEIGHTS['same_record_identity_resource'])
                elif fact.get('source_type') == 'activity':
                    event_type = str(fact.get('data', {}).get('event_type', '')).upper()
                    if event_type == 'LINK_RESOURCE_IDENTITY':
                        signals.add('identity_link_activity')
                        score = max(score, WEIGHTS['identity_link_activity'])
            # Stable subject references are strong only when the evidence also
            # includes a resource and matches the resolved subject id.
            if user_id.casefold() in identifiers:
                signals.add('subject_reference_user_id')
                sources.add(fact['file'])
                score = max(score, WEIGHTS['subject_reference_user_id'])
        if signals:
            out.append(ResourceCandidate(case_id, user_id, rid, system, score, tuple(sorted(signals)), tuple(sorted(sources))))
    return out


def build_weak_signal_index(all_facts: Iterable[dict], activity_rows: Iterable[dict], *, parse_time):
    facts_by_resource=defaultdict(list)
    for fact in all_facts:
        if fact.get('resource'): facts_by_resource[fact['resource']].append(fact)
    timed=sorted(((x['event_time'],x) for x in activity_rows),key=lambda pair:pair[0])
    return {'facts_by_resource':facts_by_resource,'activity_times':[x[0] for x in timed],'activities':[x[1] for x in timed]}


def weak_activity_candidates(case: dict, user_id: str, all_facts: Iterable[dict], activity_rows: Iterable[dict], *, parse_time, target_system_for_resource, index=None) -> list[ResourceCandidate]:
    """Retain combined activity+probe candidates as low-confidence, never as proof."""
    start=parse_time(case['requested_at']); end=parse_time(case['reported_at']); cutoff=parse_time(case['audit_at'])
    if start.tzinfo is None or end.tzinfo is None or cutoff.tzinfo is None: return []
    end=end.replace()  # datetime is immutable; retain a clear local boundary
    from datetime import timedelta
    end += timedelta(hours=24)
    if index is None:index=build_weak_signal_index(all_facts,activity_rows,parse_time=parse_time)
    facts_by_resource=index['facts_by_resource']
    lo=bisect_left(index['activity_times'],start.isoformat().replace('+00:00','Z'))
    hi=bisect_right(index['activity_times'],end.isoformat().replace('+00:00','Z'))
    output=[]
    for event in index['activities'][lo:hi]:
        when=parse_time(event.get('event_time','')); rid=event.get('resource_id','')
        if not rid or not (start<=when<=end): continue
        system=target_system_for_resource(rid)
        target=str(event.get('target_system',''))
        if system and target and system!=target: continue
        if str(event.get('event_type','')).upper() not in {'DELETE_RECORD','SYNC_RECORD','INDEX_RECORD','CREATE_EXPORT','RESTORE_BACKUP','REFRESH_CACHE','UPDATE_RECORD'}: continue
        probes=[]
        for fact in facts_by_resource.get(rid,[]):
            data=fact.get('data',{})
            is_probe=str(data.get('http_status',data.get('status_code','')))=='404' or str(data.get('rows',''))=='0' or str(data.get('result','')).casefold() in {'not_found','not found'}
            if is_probe and when<=fact['time']<=cutoff: probes.append(fact)
        if not probes: continue
        systems=[f.get('system','unknown_service') for f in probes]
        output.append(ResourceCandidate(case['case_id'],user_id,rid,systems[-1],WEIGHTS['weak_activity_window']+WEIGHTS['weak_probe_after_activity'],('weak_activity_window','weak_probe_after_activity'),tuple(sorted({event['activity_id']}|{f['file'] for f in probes}))))
    return output


def global_ownership(candidates: Iterable[ResourceCandidate], margin: float | None = None, *, focus_cases: set[str] | None = None) -> tuple[dict[str, ResourceCandidate], list[dict]]:
    """Maximum-weight case/resource matching, independently for each resource type."""
    if margin is None: margin=WEIGHTS['ambiguity_margin']
    minimum=WEIGHTS['minimum_assignment_score']
    by_type=defaultdict(dict)
    for item in candidates:
        parts=item.resource_id.split('_',1)
        kind=parts[0] if len(parts)<2 or parts[0]!='audit' else 'audit_record'
        if item.resource_id.startswith('audit_record_'): kind='audit_record'
        key=(item.case_id,item.resource_id)
        prior=by_type[kind].get(key)
        if prior is None or item.score > prior.score:
            by_type[kind][key]=item

    def hungarian(cost):
        """Pure-Python rectangular minimum-cost assignment (rows <= columns)."""
        n=len(cost);m=len(cost[0]) if n else 0
        u=[0.0]*(n+1);v=[0.0]*(m+1);p=[0]*(m+1);way=[0]*(m+1)
        for i in range(1,n+1):
            p[0]=i;j0=0;minv=[float('inf')]*(m+1);used=[False]*(m+1)
            while True:
                used[j0]=True;i0=p[j0];delta=float('inf');j1=0
                for j in range(1,m+1):
                    if used[j]:continue
                    cur=cost[i0-1][j-1]-u[i0]-v[j]
                    if cur<minv[j]:minv[j]=cur;way[j]=j0
                    if minv[j]<delta:delta=minv[j];j1=j
                for j in range(m+1):
                    if used[j]:u[p[j]]+=delta;v[j]-=delta
                    else:minv[j]-=delta
                j0=j1
                if p[j0]==0:break
            while True:
                j1=way[j0];p[j0]=p[j1];j0=j1
                if j0==0:break
        result={}
        for j in range(1,m+1):
            if p[j]:result[p[j]-1]=j-1
        return result

    assigned={};unresolved=[]
    for kind,edge_map in sorted(by_type.items()):
        eligible={k:x for k,x in edge_map.items() if x.score>=minimum}
        cases_by_resource=defaultdict(set);resources_by_case=defaultdict(set)
        for (case,rid),item in eligible.items():
            cases_by_resource[rid].add(case);resources_by_case[case].add(rid)
        unseen=set(resources_by_case) if focus_cases is None else (set(resources_by_case)&focus_cases)
        # Solve each disconnected bipartite component separately, keeping the
        # cubic Hungarian fallback bounded on the full 550-request run.
        while unseen:
            root=unseen.pop();case_nodes={root};resource_nodes=set();queue=[('case',root)]
            while queue:
                node_kind,node=queue.pop()
                if node_kind=='case':
                    for rid in resources_by_case[node]-resource_nodes:
                        resource_nodes.add(rid);queue.append(('resource',rid))
                else:
                    for case in cases_by_resource[node]-case_nodes:
                        case_nodes.add(case);unseen.discard(case);queue.append(('case',case))
            case_list=sorted(case_nodes);resource_list=sorted(resource_nodes)
            # One dummy column per case leaves unmatched slots available.
            huge=1e6
            cost=[]
            for case in case_list:
                row=[-eligible[(case,rid)].score if (case,rid) in eligible else huge for rid in resource_list]
                row.extend([0.0]*len(case_list));cost.append(row)
            chosen=hungarian(cost)
            for row,col in chosen.items():
                if col>=len(resource_list):continue
                case=case_list[row];rid=resource_list[col];item=eligible.get((case,rid))
                if item is not None:assigned[rid]=item

    for rid,item in sorted(assigned.items()):
        owners=sorted((x for (case,resource),x in by_type[next(k for k in by_type if (item.case_id,rid) in by_type[k])].items() if resource==rid),key=lambda x:(-x.score,x.case_id))
        other=max((x.score for x in owners if x.case_id!=item.case_id),default=0.0)
        gap=item.score-other
        if any(x.case_id!=item.case_id for x in owners) and gap<margin:
            marked=replace(item,ambiguous=True);assigned[rid]=marked
            unresolved.append({'resource_id':rid,'assigned_case':item.case_id,'margin':round(gap,6),
                               'ambiguity':True,'reason':'low_confidence_global_assignment',
                               'candidates':[x.to_dict() for x in owners]})
    assigned_ids=set(assigned)
    for kind,edge_map in sorted(by_type.items()):
        for rid in sorted({rid for (_,rid),x in edge_map.items() if x.score>=minimum}-assigned_ids):
            owners=sorted((x for (case,resource),x in edge_map.items() if resource==rid),key=lambda x:(-x.score,x.case_id))
            unresolved.append({'resource_id':rid,'ambiguity':True,'reason':'lost_type_capacity_or_global_match',
                               'candidates':[x.to_dict() for x in owners]})
    return assigned, unresolved
