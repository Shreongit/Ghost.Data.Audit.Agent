"""Reproduce the cutoff-valid activity and competitor audit for the 11 prior misses."""
from __future__ import annotations
import csv, json, sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'code'))
import main as agent
from linking.time_model import MODEL_PATH,time_activity_candidates,_fit_offsets

def rows(path,delimiter=','):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f,delimiter=delimiter))

def main():
    d=ROOT/'dataset'; requests=rows(d/'sample_deletion_requests.csv'); activities=rows(d/'system_activity.csv')
    all_requests=rows(d/'deletion_requests.csv')+requests
    trace=rows(ROOT/'code/linking/sample_resource_trace.tsv','\t')
    request_by_id={x['case_id']:x for x in requests}
    answers=rows(d/'sample_output.csv')
    disputed=[x for x in trace if not x['ALIAS_HIT_FACTS'] and not x['SAME_FILE_RESOURCE_AND_ALIAS'] and not x['WINDOW_ACTIVITY']]
    out=['# Audit of the 11 prior “unrecoverable” public-sample links','',
         'This audit uses only sample requests, sample answers for selecting the disputed rows, system activity, and leave-one-case-out public-sample offsets. The disputed case is excluded when fitting its timing model. Candidate competitors are all same-resource-type activity candidates retained by the calibrated timing likelihood for that request. “Not in model” means no cutoff-valid, type-compatible activity edge met the likelihood floor; it does not prove the resource itself is absent.','']
    for item in disputed:
        model=_fit_offsets([x for x in requests if x['case_id']!=item['CASE']],
                           [x for x in answers if x['case_id']!=item['CASE']],activities)
        all_candidates=[]; by_case=defaultdict(list)
        for request in all_requests:
            for c in time_activity_candidates(request,request['case_id'],activities,parse_time=agent.dt,model=model):
                by_case[request['case_id']].append(c); all_candidates.append(c)
        req=request_by_id[item['CASE']]; rid=item['RESOURCE']; cutoff=agent.dt(req['audit_at']); reported=agent.dt(req['reported_at'])
        actual=[a for a in activities if a.get('resource_id')==rid and agent.dt(a.get('event_time',''))<=cutoff]
        actual.sort(key=lambda a:a['event_time'])
        out += [f"## {item['CASE']} — `{rid}`",'',f"Reported status/result context: `{req['reported_status']}`; `reported_at={req['reported_at']}`; `audit_at={req['audit_at']}`."]
        if actual:
            out.append('')
            out.append('| activity_id | event_time | Δ reported_at − event_time (h) | event_type | target_system | reported_result |')
            out.append('|---|---|---:|---|---|---|')
            for a in actual:
                delta=(reported-agent.dt(a['event_time'])).total_seconds()/3600
                out.append(f"| `{a['activity_id']}` | `{a['event_time']}` | {delta:+.3f} | `{a['event_type']}` | `{a['target_system']}` | `{a['reported_result']}` |")
        else:
            out.append('');out.append('No cutoff-valid `system_activity.csv` row names this resource ID.')
        typ=rid.split('_',1)[0]
        peers=sorted((c for c in by_case[item['CASE']] if c.resource_id.split('_',1)[0]==typ),key=lambda c:(-c.score,c.resource_id))
        out += ['',f"Candidate activity competitors for this request and resource type ({len(peers)}):"]
        if peers:
            out += ['', '| candidate resource | score | signals | provenance |','|---|---:|---|---|']
            for c in peers:
                out.append(f"| `{c.resource_id}` | {c.score:.4f} | `{', '.join(c.signals)}` | `{'; '.join(c.source_ids)}` |")
        else:
            out.append('None meet the cutoff and calibrated offset-likelihood floor.')
        owners=sorted((c for c in all_candidates if c.resource_id==rid),key=lambda c:(-c.score,c.case_id))
        out += ['',f"Competing request owners for this exact resource ({len(owners)}):"]
        if owners:
            out += ['', '| candidate case | score | signals | provenance |','|---|---:|---|---|']
            for c in owners:
                out.append(f"| `{c.case_id}` | {c.score:.4f} | `{', '.join(c.signals)}` | `{'; '.join(c.source_ids)}` |")
        else:
            out.append('No request in the 550-request candidate universe receives a calibrated activity candidate for this exact resource.')
        if actual and owners:
            winner=owners[0]
            out += ['',f"Assessment: activity exists and the highest scored owner in the 550-request candidate universe is `{winner.case_id}`. Margin over its runner-up is {winner.score-(owners[1].score if len(owners)>1 else 0):.4f}. This is a scored ownership signal, not direct identity evidence."]
        elif actual:
            out += ['', 'Assessment: activity names the resource, but its result/time is outside the learned candidate envelope. The activity row cannot establish subject ownership by itself.']
        else:
            out += ['', 'Assessment: this resource has no activity row in the participant-facing stream. The earlier blanket “unrecoverable” claim should be scoped to this specific evidence gap; timing cannot link a resource that never appears in the stream.']
        out.append('')
    target=ROOT/'code/linking/disputed_11_audit.md';target.write_text('\n'.join(out)+'\n',encoding='utf-8')
    print(f'Wrote {len(disputed)} disputed-resource sections to {target}')

if __name__=='__main__': main()
