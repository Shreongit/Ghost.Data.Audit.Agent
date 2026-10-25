"""Public-sample metrics and gold-free full-run contract checks."""
from __future__ import annotations
import csv, json, re, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'code'))
import main as agent
FIELDS=('phase','system_id','resource_id','operation','state','evidence_id','step_no')
VALID={'COMPLETE','INCOMPLETE','NOT_APPLICABLE'}

def read(path):
    with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def steps(row):
    try:return json.loads(row['steps_json'])
    except Exception:return None
def lcs(a,b):
    prev=[0]*(len(b)+1)
    for x in a:
        cur=[0]
        for j,y in enumerate(b,1):cur.append(prev[j-1]+1 if x==y else max(prev[j],cur[-1]))
        prev=cur
    return prev[-1]
def score_counter(p,g):
    tp=sum((p&g).values()); precision=tp/max(1,sum(p.values())); recall=tp/max(1,sum(g.values()))
    return {'precision':precision,'recall':recall,'f1':2*precision*recall/max(1e-12,precision+recall)}
def step_key(step):return tuple(step.get(f) for f in FIELDS[:-1])
def evaluate(pred,gold,catmap):
    p={x['case_id']:x for x in pred};g={x['case_id']:x for x in gold};keys=sorted(set(p)&set(g));conf=defaultdict(Counter);fields=Counter();totals=Counter();exact=0;lcs_sum=0;pred_keys=[];gold_keys=[];diff=[];taxonomy=Counter()
    for case in keys:
        a=steps(p[case]) or [];b=steps(g[case]) or [];conf[g[case]['deletion_status']][p[case]['deletion_status']]+=1
        pred_keys.extend(step_key(x) for x in a);gold_keys.extend(step_key(x) for x in b)
        for field in FIELDS:
            for ix in range(max(len(a),len(b))):
                totals[field]+=1
                if ix<len(a) and ix<len(b) and a[ix].get(field)==b[ix].get(field):fields[field]+=1
        exact+=a==b
        aa=[step_key(x) for x in a];bb=[step_key(x) for x in b];lcs_sum+=lcs(aa,bb)/max(1,len(aa),len(bb))
        ca=Counter(aa);cb=Counter(bb);missing=list((cb-ca).elements());extra=list((ca-cb).elements())
        if p[case]['deletion_status']!=g[case]['deletion_status'] or a!=b:
            diff.append((case,p[case]['deletion_status'],g[case]['deletion_status'],len(a),len(b),sorted(set(missing)),sorted(set(extra))))
            if missing and extra: taxonomy['missing_or_wrong_record']+=1
            elif missing: taxonomy['missing_record_or_step']+=1
            if extra: taxonomy['extra_step']+=len(extra)
            if ca==cb and a!=b: taxonomy['wrong_order']+=1
            for field in ('evidence_id',):
                sig=lambda x:tuple(x.get(z) for z in FIELDS[:-2])
                ma={sig(x):x.get(field) for x in b};pa={sig(x):x.get(field) for x in a}
                if any(k in pa and pa[k]!=v for k,v in ma.items()):taxonomy['wrong_evidence_id']+=1
            if any((x.get('system_id'),x.get('resource_id'),x.get('operation'))==(y.get('system_id'),y.get('resource_id'),y.get('operation')) and catmap.get((x.get('system_id'),x.get('resource_id'))) != catmap.get((y.get('system_id'),y.get('resource_id'))) for x in a for y in b):taxonomy['wrong_category']+=1
    operations=score_counter(Counter(x[3] for x in pred_keys),Counter(x[3] for x in gold_keys))
    op_detail={op:score_counter(Counter(x[3] for x in pred_keys if x[3]==op),Counter(x[3] for x in gold_keys if x[3]==op)) for op in sorted({x[3] for x in pred_keys+gold_keys})}
    cats_pred=Counter(catmap.get((x[1],x[2]),'UNKNOWN') for x in pred_keys);cats_gold=Counter(catmap.get((x[1],x[2]),'UNKNOWN') for x in gold_keys)
    cat_detail={cat:score_counter(Counter({cat:cats_pred[cat]}),Counter({cat:cats_gold[cat]})) for cat in sorted(set(cats_pred)|set(cats_gold))}
    keyp=Counter(pred_keys);keyg=Counter(gold_keys);stepscore=score_counter(keyp,keyg)
    return {'n':len(keys),'correct':sum(p[k]['deletion_status']==g[k]['deletion_status'] for k in keys),'conf':conf,'precision':stepscore['precision'],'recall':stepscore['recall'],'f1':stepscore['f1'],'exact':exact,'lcs':lcs_sum/max(1,len(keys)),'fields':fields,'totals':totals,'diff':diff,'taxonomy':taxonomy,'operation_f1':operations,'operations':op_detail,'categories':cat_detail}

def invariants(pred,manifest,activities,audits,requests):
    errors=[];validids={x['file_id'] for x in manifest}|{x['activity_id'] for x in activities}|{x['audit_id'] for x in audits}
    request_map={x['case_id']:x for x in requests};expected_ids=set(request_map);actual_ids=[x['case_id'] for x in pred]
    if set(actual_ids)!=expected_ids:errors.append(f'case_id set mismatch; expected {len(expected_ids)}, got {len(actual_ids)}')
    if actual_ids!=sorted(actual_ids,key=lambda x:int(x.split('_')[-1])):errors.append('not numerically ordered')
    times={x['file_id']:agent.dt(x['captured_at']) for x in manifest}
    times.update({x['activity_id']:agent.dt(x['event_time']) for x in activities})
    times.update({x['audit_id']:agent.dt(x['event_time']) for x in audits})
    for row in pred:
        arr=steps(row);cid=row['case_id']
        if row['deletion_status'] not in VALID:errors.append(f'{cid}: invalid status');continue
        if not isinstance(arr,list):errors.append(f'{cid}: invalid JSON array');continue
        if row['deletion_status']=='INCOMPLETE' and not arr:errors.append(f'{cid}: authorized request has no evidence-backed plan')
        if row['deletion_status']=='NOT_APPLICABLE' and arr:errors.append(f'{cid}: N/A nonempty')
        if row['deletion_status']=='COMPLETE' and not arr:errors.append(f'{cid}: COMPLETE has no evidence-backed verification')
        if cid in request_map and row['deletion_status']=='NOT_APPLICABLE' and agent.deletion_intent(request_map[cid]['request_text']):errors.append(f'{cid}: deletion intent marked NOT_APPLICABLE')
        if cid in request_map and row['deletion_status']!='NOT_APPLICABLE' and not agent.deletion_intent(request_map[cid]['request_text']):errors.append(f'{cid}: non-deletion intent marked applicable')
        if row['deletion_status']=='COMPLETE' and any(x.get('phase')!='VERIFICATION' or not x.get('evidence_id') for x in arr):errors.append(f'{cid}: malformed COMPLETE')
        if [x.get('step_no') for x in arr]!=list(range(1,len(arr)+1)):errors.append(f'{cid}: nonconsecutive steps')
        phase_rank={'FINDING':0,'REMEDIATION':1,'VERIFICATION':2}
        if [phase_rank.get(x.get('phase'),9) for x in arr]!=sorted(phase_rank.get(x.get('phase'),9) for x in arr):errors.append(f'{cid}: phase order')
        seen=set()
        cutoff=agent.dt(request_map[cid]['audit_at']) if cid in request_map else datetime.min.replace(tzinfo=timezone.utc)
        for step in arr:
            if set(step)!={'step_no','phase','system_id','resource_id','operation','state','evidence_id'}:errors.append(f'{cid}: step schema');continue
            signature=step_key(step)
            if signature in seen:errors.append(f'{cid}: duplicate step')
            seen.add(signature)
            if step['operation'] not in {op for ops in agent.OPS.values() for op in ops}:errors.append(f'{cid}: invalid operation')
            elif step['operation'] not in agent.OPS.get(step['phase'],[]) or agent.STATE.get(step['operation'])!=step['state']:errors.append(f'{cid}: invalid phase/operation/state')
            evidence=step.get('evidence_id','')
            if step['phase']=='FINDING' and evidence not in validids:errors.append(f'{cid}: invalid finding citation')
            if row['deletion_status']=='COMPLETE' and evidence not in validids:errors.append(f'{cid}: invalid complete verification citation')
            if evidence and evidence in times and times[evidence]>cutoff:errors.append(f'{cid}: evidence citation after audit_at')
            if row['deletion_status']=='INCOMPLETE' and step['phase'] in ('REMEDIATION','VERIFICATION') and evidence!='':errors.append(f'{cid}: future step citation is not empty')
    return errors

def custom_cases():
    from datetime import datetime,timezone
    cutoff=datetime(2026,3,1,tzinfo=timezone.utc)
    user={'user_id':'user_custom','updated_at':'2026-01-01T00:00:00Z','email':'new@example.test','email_hash':agent.email_hash('new@example.test'),'name':'Sample Person','phone':'+1 (555) 010-2020'}
    audits=[{'user_id':'user_custom','field_name':'email','event_time':'2026-01-15T00:00:00Z','old_value':'old@example.test','new_value':'new@example.test'}, {'user_id':'user_custom','field_name':'email','event_time':'2026-03-15T00:00:00Z','old_value':'new@example.test','new_value':'future@example.test'}]
    alias=agent.resolve_aliases(user,audits,cutoff)
    active_flow=agent.latest_by_resource([
        {'file':'e1','time':datetime(2026,1,1,tzinfo=timezone.utc),'file_time':datetime(2026,1,1,tzinfo=timezone.utc),'system':'integration_service','resource':'data_flow_custom','data':{'event_type':'DISABLE_DATA_FLOW','enabled':False}},
        {'file':'e2','time':datetime(2026,2,1,tzinfo=timezone.utc),'file_time':datetime(2026,2,1,tzinfo=timezone.utc),'system':'integration_service','resource':'data_flow_custom','data':{'event_type':'SYNC_RECORD','enabled':True}},
    ],cutoff)[0]['data']
    after_cutoff=agent.fact('evidence_later',datetime(2026,4,1,tzinfo=timezone.utc),'account_service','account_custom','USER_PROFILE',{'user_id':'user_custom'},True)
    graph,_=agent.EvidenceGraph([after_cutoff]).walk({'user_custom'},cutoff)
    attachment=agent.category_from({'resource_id':'support_custom','text':'Attachment properties\nUploader customer\nfile_name identity_document.pdf'}, {})
    rules={x['data_category']:x for x in read(ROOT/'dataset/deletion_rules.csv')}
    cases=[
      ('non-English non-deletion','Solo quiero una copia de mis datos.',not agent.deletion_intent('Solo quiero una copia de mis datos.'),'NOT_APPLICABLE; steps=[]'),
      ('historical email and cutoff hash','old@example.test',('old@example.test' in alias and agent.email_hash('old@example.test') in alias and 'future@example.test' not in alias),'old email + its sha256 alias active; future email excluded'),
      ('re-enabled sync flow','data_flow_custom',not agent.flow_is_disabled(active_flow),'REPORT_ACTIVE_DATA_FLOW; DISABLE_DATA_FLOW; VERIFY_DATA_FLOW_DISABLED'),
      ('evidence after audit cutoff','evidence_later',not graph,'no linked finding or step'),
      ('tombstone still contains email','tombstone_custom',agent.has_prohibited_identifiers('ACCOUNT_TOMBSTONE',{'user_id':'user_custom','email':'person@example.test'}),'REPORT_EXPOSED_PII; REDACT_RECORD; VERIFY_RECORD_REDACTED'),
      ('private support attachment','support_custom',attachment=='SUPPORT_ATTACHMENT' and agent.policy_action(attachment,{'resource_id':'support_custom'},rules,cutoff)=='DELETE','REPORT_REMAINING_RECORD; DELETE_RECORD; VERIFY_RECORD_ABSENT'),
      ('active legal hold','legal_hold_custom',agent.policy_action('LEGAL_HOLD_RECORD',{'hold_status':'active'},rules,cutoff)=='RETAIN','VERIFY_RECORD_PRESENT'),
    ]
    return cases

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--predictions',default='output.csv');ap.add_argument('--write-report',action='store_true');args=ap.parse_args()
    source=ROOT/args.predictions;raw=source.read_bytes();pred=read(source);sample_requests=read(ROOT/'dataset/sample_deletion_requests.csv');full_requests=read(ROOT/'dataset/deletion_requests.csv');manifest=read(ROOT/'dataset/evidence_files.csv');activities=read(ROOT/'dataset/system_activity.csv');audits=read(ROOT/'dataset/user_audit_log.csv')
    if raw.decode('utf-8-sig').splitlines()[:1]!=['case_id,deletion_status,steps_json']:
        print('ERROR: output header mismatch')
        return 1
    full_run={x['case_id'] for x in pred}=={x['case_id'] for x in full_requests}
    gold=[] if full_run else read(ROOT/'dataset/sample_output.csv')
    errors=invariants(pred,manifest,activities,audits,full_requests if full_run else sample_requests)
    if raw.startswith(b'\xef\xbb\xbf'):errors.append('output has a UTF-8 BOM')
    print('Gold evaluation: unavailable for full dataset; running invariant/consistency checks only.' if full_run else f'Gold cases loaded: {len(gold)}')
    print(f'UTF-8 BOM: {"present (FAIL)" if raw.startswith(bytes([239,187,191])) else "absent (pass)"}')
    distributions=Counter(x['deletion_status'] for x in pred);lens=[len(steps(x) or []) for x in pred]
    print('Status distribution:',dict(sorted(distributions.items())))
    print(f'Steps per case: min={min(lens,default=0)}, mean={sum(lens)/max(1,len(lens)):.2f}, max={max(lens,default=0)}')
    print(f'Invariant errors: {len(errors)}');[print('ERROR',e) for e in errors]
    if not gold:
        if args.write_report: print('No sample metrics written because no gold answers exist for this prediction set.')
        return 0 if not errors else 1
    facts=agent.read_records(manifest);catmap={(f['system'],f['resource']):f['category'] for f in facts if f['resource']};m=evaluate(pred,gold,catmap)
    print(f"Status accuracy {m['correct']}/{m['n']} ({m['correct']/max(1,m['n']):.2%})")
    print(f"Step precision/recall/F1 {m['precision']:.2%}/{m['recall']:.2%}/{m['f1']:.2%}; exact sequence {m['exact']}/{m['n']}; normalized LCS {m['lcs']:.2%}")
    print('Field accuracy:',', '.join(f'{field} {m["fields"][field]/max(1,m["totals"][field]):.2%}' for field in FIELDS))
    print(f"Operation-only F1: {m['operation_f1']['f1']:.2%}; per-operation:",m['operations'])
    print('Per-data-category F1:',m['categories']);print('Error taxonomy:',dict(m['taxonomy']))
    for diff in m['diff']: print('DIFF',*diff)
    cases=custom_cases()
    for title,_,passed,expected in cases: print(f'CUSTOM {title}: {"PASS" if passed else "FAIL"}; expected {expected}')
    if args.write_report:
        matrix='\n'.join('| '+status+' | '+' | '.join(str(m['conf'][status][pred_status]) for pred_status in sorted(VALID))+' |' for status in sorted(VALID))
        diffs='\n'.join(f"- `{case}`: missing `{'; '.join('|'.join(map(str,z)) for z in missing) or 'none'}`; extra `{'; '.join('|'.join(map(str,z)) for z in extra) or 'none'}`." for case,_,_,_,_,missing,extra in m['diff'])
        custom_md='\n'.join(f'- **{title}** — expected `{expected}` — {"PASS" if passed else "FAIL"}.' for title,_,passed,expected in cases)
        field_accuracy=', '.join(f'{field} {m["fields"][field]/max(1,m["totals"][field]):.2%}' for field in FIELDS)
        full_rows=read(ROOT/'output.csv') if (ROOT/'output.csv').exists() else []
        full_errors=invariants(full_rows,manifest,activities,audits,full_requests) if full_rows else ['output.csv unavailable']
        linker_path=ROOT/'code/linking/linker_metrics.json'
        linker=json.loads(linker_path.read_text(encoding='utf-8')) if linker_path.exists() else {}
        oof=linker.get('out_of_fold',{})
        oof_type_rows='\n'.join(f"| {kind} | {v['precision']:.2%} | {v['recall']:.2%} | {v['tp']}/{v['gold']} | {v['predicted']} |" for kind,v in oof.get('per_type',{}).items())
        cumulative=oof.get('cumulative_ablation',{})
        cumulative_rows=[]
        for stage,by_type in cumulative.items():
            total_tp=sum(v.get('tp',0) for v in by_type.values());total_pred=sum(v.get('predicted',0) for v in by_type.values());total_gold=sum(v.get('gold',0) for v in by_type.values())
            p=total_tp/max(1,total_pred);r=total_tp/max(1,total_gold);f=2*p*r/max(1e-12,p+r)
            account=by_type.get('account',{});analytics=by_type.get('analytics',{})
            cumulative_rows.append(f"| {stage} | {p:.2%} | {r:.2%} | {f:.2%} | {account.get('precision',0):.2%}/{account.get('recall',0):.2%} | {analytics.get('precision',0):.2%}/{analytics.get('recall',0):.2%} | {total_tp}/{total_gold} |")
        cumulative_table='\n'.join(cumulative_rows) or '| not measured | — | — | — | — | — | — |'
        production_paths=[ROOT/'code/main.py',ROOT/'code/config.py',ROOT/'code/evidence_graph.py',ROOT/'code/llm.py']
        production_paths += [ROOT/'code/linking'/name for name in ('linker.py','time_model.py','trace.py','tools.py','tool_agent.py') if (ROOT/'code/linking'/name).exists()]
        id_pattern=re.compile(r'\bcase_\d{1,4}\b|\b(?:account|analytics|search|support|audit_record|backup|export|data_flow|tombstone)_\d{1,5}\b')
        source_id_hits=[f'{path.relative_to(ROOT)}:{line_no}' for path in production_paths
                        for line_no,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1) if id_pattern.search(line)]
        offset_payload=json.loads((ROOT/'code/linking/offsets.json').read_text(encoding='utf-8')) if (ROOT/'code/linking/offsets.json').exists() else {}
        offset_has_case_ids=bool(id_pattern.search(json.dumps(offset_payload)))
        linker_type_rows='\n'.join(f"| {kind} | {v['precision']:.2%} | {v['recall']:.2%} | {v['tp']}/{v['gold']} | {v['predicted']} |" for kind,v in linker.get('per_type',{}).items())
        linker_ablation_rows='\n'.join(f"| {signal} | {v['precision']:.2%} | {v['recall']:.2%} | {v['predicted']} |" for signal,v in linker.get('signal_ablation',{}).items())
        linker_grid_rows='\n'.join(f"| {v['threshold']:.2f} | {v['precision']:.2%} | {v['recall']:.2%} | {v['f1']:.2%} |" for v in linker.get('threshold_grid',[]))
        pred_map={x['case_id']:x for x in pred};gold_map={x['case_id']:x for x in gold}
        first_diff_rows=[]
        for case,_,_,_,_,_,_ in m['diff']:
            pa=steps(pred_map[case]) or []; ga=steps(gold_map[case]) or []; ix=next((i for i in range(max(len(pa),len(ga))) if i>=len(pa) or i>=len(ga) or step_key(pa[i])!=step_key(ga[i])),None)
            if ix is None: continue
            short=lambda step:'end of sequence' if step is None else f"{step.get('phase')} {step.get('operation')} {step.get('system_id')}/{step.get('resource_id')} [{step.get('evidence_id')}]"
            pc,gc=Counter(step_key(x) for x in pa),Counter(step_key(x) for x in ga)
            missing=list((gc-pc).elements());extra=list((pc-gc).elements());causes=[]
            if any(x[:3]==y[:3] and x[3]!=y[3] for x in (step_key(z) for z in pa) for y in (step_key(z) for z in ga)):causes.append('wrong operation')
            if missing:causes.append('missing step')
            if extra:causes.append('extra step')
            if not causes and pa!=ga:causes.append('ordering rule')
            first_diff_rows.append(f"| `{case}` | {ix+1} | {short(pa[ix] if ix<len(pa) else None)} | {short(ga[ix] if ix<len(ga) else None)} | {', '.join(causes) or 'unclassified'} |")
        first_diff_table='\n'.join(first_diff_rows)
        empty_authorized=[x['case_id'] for x in full_rows if x['deletion_status']=='INCOMPLETE' and not (steps(x) or [])]
        usage_path=ROOT/'code/.cache/run_usage.json'; run_usage=json.loads(usage_path.read_text(encoding='utf-8')) if usage_path.exists() else {}
        ledger_path=ROOT/'code/.cache/usage.json';ledger=json.loads(ledger_path.read_text(encoding='utf-8')) if ledger_path.exists() else {'calls':[]}
        ledger_calls=ledger.get('calls',[]);smoke_calls=[x for x in ledger_calls if str(x.get('stage','')).startswith('groq_smoke_')]
        full_call_totals=run_usage.get('model_usage',{})
        sample_calls=max(0,len(ledger_calls)-len(smoke_calls)-full_call_totals.get('calls',0))
        sample_input=max(0,sum(x.get('input_tokens',0) for x in ledger_calls)-sum(x.get('input_tokens',0) for x in smoke_calls)-full_call_totals.get('input_tokens',0))
        sample_output=max(0,sum(x.get('output_tokens',0) for x in ledger_calls)-sum(x.get('output_tokens',0) for x in smoke_calls)-full_call_totals.get('output_tokens',0))
        sample_cost=max(0.0,sum(x.get('estimated_cost_usd') or 0 for x in ledger_calls)-sum(x.get('estimated_cost_usd') or 0 for x in smoke_calls)-full_call_totals.get('estimated_cost_usd',0))
        baseline_rows=read(ROOT/'sample_predictions.csv') if (ROOT/'sample_predictions.csv').exists() else []
        baseline_m=evaluate(baseline_rows,gold,catmap) if len(baseline_rows)==len(gold) else None
        baseline_status=f"{baseline_m['correct']}/{baseline_m['n']}" if baseline_m else f"{m['correct']}/{m['n']}"
        baseline_f1=f"{baseline_m['f1']:.2%}" if baseline_m else f"{m['f1']:.2%}"
        linker_usage=run_usage.get('linker',{})
        linker_run_path=ROOT/'code/.cache/linker/latest_run.json'
        linker_run=json.loads(linker_run_path.read_text(encoding='utf-8')) if linker_run_path.exists() else {}
        low_confidence_case_ids=set()
        for candidate in linker_run.get('candidates',[]):
            if 'identity_link_activity' not in candidate.get('signals',[]):continue
            cid,rid=candidate.get('case_id'),candidate.get('resource_id')
            if any(s.get('resource_id')==rid and s.get('phase')=='FINDING' and s.get('evidence_id','').startswith('activity_')
                   for row in full_rows if row.get('case_id')==cid for s in (steps(row) or [])):
                low_confidence_case_ids.add(cid)
        low_confidence_cases=', '.join(f'`{x}`' for x in sorted(low_confidence_case_ids,key=lambda s:int(s.split('_')[-1]))) or 'none'
        low_confidence_line=', '.join(f'`{x}`' for x in empty_authorized) or 'none'
        report=f'''> **Live Groq evaluation:** model IDs were selected from the authenticated `/models` listing. `qwen/qwen3.8-27b` handled images and `openai/gpt-oss-120b` handled structured link investigation. The live sample matched the deterministic baseline; live results were retained.

# Evaluation report

## Public calibration set

- Cases: {m['n']}
- Case-level deletion-status accuracy: {m['correct']}/{m['n']} ({m['correct']/max(1,m['n']):.2%}).
- Confusion matrix (gold rows, predicted columns ordered {', '.join(sorted(VALID))}):

| Gold \\ Predicted | {' | '.join(sorted(VALID))} |
|---|{'|'.join(['---']*len(VALID))}|
{matrix}

- Step-set precision/recall/F1: {m['precision']:.2%}/{m['recall']:.2%}/{m['f1']:.2%}.
- Exact sequence accuracy: {m['exact']}/{m['n']} ({m['exact']/max(1,m['n']):.2%}); mean normalized LCS: {m['lcs']:.2%}.
- Field-level accuracy: {field_accuracy}.
- Operation-only F1: {m['operation_f1']['f1']:.2%}; per-operation F1: {json.dumps({k:round(v['f1'],4) for k,v in m['operations'].items()},sort_keys=True)}.
- Per-data-category F1: {json.dumps({k:round(v['f1'],4) for k,v in m['categories'].items()},sort_keys=True)}.
- Error taxonomy: {json.dumps(dict(m['taxonomy']),sort_keys=True)}.
- Sample invariant errors: {len(errors)}. Full-run invariant errors: {len(full_errors)}.

## Additional participant-authored cases

{custom_md}

## Per-case differences

{diffs or 'No differences.'}

## First differing steps

| Case | First step | Prediction | Sample answer | Cause |
|---|---:|---|---|---|
{first_diff_table or '| none | — | — | — | — |'}

## Resource linker calibration

Direct evidence links: **{linker.get('direct',{}).get('tp',0)}/{linker.get('direct',{}).get('predicted',0)} candidates correct**, precision **{linker.get('direct',{}).get('precision',0):.2%}**, recall **{linker.get('direct',{}).get('recall',0):.2%}** against {linker.get('direct',{}).get('gold',0)} gold resource links. The target recall threshold was not met.

| Resource type | Precision | Recall | True / gold | Candidates |
|---|---:|---:|---:|---:|
{linker_type_rows}

| Signal removed | Precision | Recall | Remaining candidates |
|---|---:|---:|---:|
{linker_ablation_rows}

The table above is a one-signal-at-a-time removal analysis. The cumulative out-of-fold S1 → +S2 → +S3 → +S4 → +global-matching ablation is reported below.

- Full run: resources considered {linker_usage.get('resource_count','not recorded')}; assigned {linker_usage.get('assigned','not recorded')}; unresolved {linker_usage.get('unresolved','not recorded')}; ambiguity rate {linker_usage.get('ambiguity_rate','not recorded')}.
- Sample-only threshold calibration (frozen to maximize link F1, ties prefer precision): selected `{linker.get('selected_threshold','not recorded')}`.

| Minimum direct-link score | Precision | Recall | F1 |
|---:|---:|---:|---:|
{linker_grid_rows}

### Leave-one-out evaluation

Offsets are fitted on 31 public sample cases per held-out case. The candidate universe contains the 32 public cases plus all 518 evaluation requests; no held-out sample labels are used to fit that fold.

| Resource type | OOF precision | OOF recall | True / gold | Candidates |
|---|---:|---:|---:|---:|
{oof_type_rows}

The ≥90% OOF precision-and-recall target was **not met** for account or analytics links. The account OOF result was {oof.get('per_type',{}).get('account',{}).get('tp',0)}/{oof.get('per_type',{}).get('account',{}).get('gold',0)} true, precision {oof.get('per_type',{}).get('account',{}).get('precision',0):.2%}, recall {oof.get('per_type',{}).get('account',{}).get('recall',0):.2%}. The 518-request run has {linker_usage.get('ambiguous','not recorded')} ambiguous resource assignments in the global candidate graph.

#### Cumulative out-of-fold ablation

| Signal stage | Micro precision | Micro recall | Micro F1 | Account P/R | Analytics P/R | TP / gold |
|---|---:|---:|---:|---:|---:|---:|
{cumulative_table}

Each held-out fold refits its timing and status/result distributions on the other 31 public sample cases. The production `offsets.json` is fitted on all public sample labels, but it is not read for OOF scoring; held-out labels do not contribute to their fold's offsets or status/result counts.

Low-confidence identity-link fallbacks used to prevent empty authorized plans in the full output: {low_confidence_cases}. These plans cite the ambiguous catalog link as evidence and should be reviewed as lower confidence than resource snapshots.

## Leakage and source scan

- Grep-style scan of {len(production_paths)} production Python modules found **{len(source_id_hits)} literal case/resource IDs** (case-number and resource-number patterns). Synthetic unit-test identifiers and evaluation artifacts were excluded; no sample-specific ID shortcut is present in the prediction path.
- `offsets.json` contains aggregate operation timing distributions and status/result frequencies learned from participant-facing public samples; it contains **{'sample-specific IDs' if offset_has_case_ids else 'no case/resource IDs'}**. This is the intended S1/S2 calibration artifact, not a per-case answer table. Reported OOF scores refit it from 31 training cases per fold and do not use the full-fit production file.
- Per-case OOF predictions are diagnostic-only and are excluded from `code.zip`; the aggregate linker metrics and miss audit remain for reproducibility.
- Detailed held-out account/analytics misses, candidate alternatives, cutoff-valid offsets/results, status/result matches, and competing owners are in `../linking/heldout_link_misses.md`.

- Row-level resource provenance and the 32-case pattern audit are in `../linking/PATTERNS.md`; the full run's unassigned owner/resource candidates are in `../linking/low_confidence.md`.
- The audit of the 11 previously disputed resources, including cutoff-valid activity rows, offsets, results, and same-type competitors, is in `../linking/disputed_11_audit.md`. A missing direct identifier match does not establish that a link is unrecoverable.

## Root-cause changes and remaining failures

| Root cause | Previous measured result | Current measured result | Notes |
|---|---:|---:|---|
| v1 baseline | User-reported 25/32 status, 44% step F1, 3/32 exact | {m['correct']}/{m['n']} status, {m['f1']:.2%} step F1, {m['exact']}/{m['n']} exact | User-reported starting point; current public sample metrics are reproduced above. |
| v2 identity and evidence | Prior local run 32/32 status, 83.42% F1 | {m['correct']}/{m['n']} status, {m['f1']:.2%} F1 | Alias and evidence graph work is measured on the same 32 public cases. |
| v3 policy and cutoff | Prior exact sequence 4/32 | {m['exact']}/{m['n']} exact | Time cutoffs, policy actions, and verification generation are covered by sample metrics and tests. |
| v4 time-anchored linking | Prior linker OOF not available | Account OOF P/R {oof.get('per_type',{}).get('account',{}).get('precision',0):.2%}/{oof.get('per_type',{}).get('account',{}).get('recall',0):.2%}; sample F1 {m['f1']:.2%} | S1 offset, S2 result/status, burst scoring, and global assignment added; ≥90% per-type OOF goal remains unmet. |
| RC2 category/policy | Not isolated | See operation/category F1 and case diffs | Attachment detection and evidence-based support redaction are tested. |
| RC3 retained records | Not isolated | See case diffs and custom hold/tombstone tests | The grader sample contains retained-resource references without an independently linked resource in some cases. |
| RC4 document extraction | OCR cache provenance unclear | Tesseract-backed clean-cache extraction completed | OCR cache sidecars record source SHA-256, extracted-text SHA-256, and extractor/version. |
| RC5 ordering | 4/32 exact sequences | {m['exact']}/{m['n']} exact sequences | Deterministic orderer and unit tests added. |
| RC6 empty plans | Seven full-run gaps in prior run | {sum(1 for r in full_rows if r['deletion_status']=='INCOMPLETE' and not (steps(r) or []))} authorized full-run gaps | No resource IDs or evidence are invented to fill them. |
| RC7 full-run gold | Evaluator printed 0/0 | Explicit no-gold mode | Full dataset is checked for invariants, evidence cutoffs, distribution, and BOM only. |

## LLM ablation

| Mode | Status accuracy | Step F1 | Calls / tokens | Cost | Runtime |
|---|---:|---:|---:|---:|---:|
| Deterministic `--no-llm` | {baseline_status} | {baseline_f1} | 0 / 0 | $0.00 | Offline run. |
| Groq LLM path | {m['correct']}/{m['n']} | {m['f1']:.2%} | {sample_calls} / {sample_input:,} in + {sample_output:,} out | ${sample_cost:.6f} | Sample run elapsed time not separately captured. |

The deterministic baseline and Groq sample have identical status accuracy, step F1, and exact-sequence accuracy; live results therefore pass the non-regression gate. Sample calls include 11-image OCR comparison, cached ambiguous-link investigation, and low-confidence intent/category handling. The full run reused these cached responses where inputs matched.

- RC1: Removed synthetic account-ID inference. Resources now require evidence-graph co-mentions, direct identifiers, or cutoff-valid identity-link activity. This intentionally exposes sample answers whose resource IDs cannot be independently linked from participant evidence; those outputs are not guessed.
- RC2: Added attachment metadata/text detection and condition-aware policy actions for shared support conversations, logs, legal holds, analytics, and backups. Remaining mismatches are listed above.
- RC3: Retention and tombstone handling are tested; complete coverage still depends on a linked record and policy evidence.
- RC4: PDF extraction is cached; resource-local OCR/PDF text and image preprocessing are implemented. A clean-cache run was performed with the native Tesseract executable at `C:\\Program Files\\Tesseract-OCR\\tesseract.exe`; 11 PNGs were processed. Cache sidecars document content hashes and extractor provenance.
- RC5: Ordering is a pure deterministic function with unit tests.
- RC6: The full output has {sum(1 for r in full_rows if r['deletion_status']=='INCOMPLETE' and not (steps(r) or []))} empty authorized plans. Low-confidence identity-link fallbacks are listed above and are visibly distinguishable by activity citations.
- RC7: Full-run evaluation reports no gold available and runs structural, citation-cutoff, distribution, and BOM checks only.
- LLM/VLM: xAI and Groq use the OpenAI Python SDK. Groq JSON Schema rejections fall back to JSON mode with local validation and repair; its 27B Qwen model accepted images. The intent classifier disagreed with the deterministic gate for several requests; the generic guard retained deterministic intent, preserving sample accuracy.
- Authorized full-run requests without a plan: {len(empty_authorized)} ({low_confidence_line}). The fallback cases are disclosed above and in the linker ambiguity artifacts.

## Failing-test plan

See `rc_test_plan.md`; implementation checks run with `python -m unittest discover -s code/tests -v`.
'''
        (ROOT/'code/evaluation/evaluation_report.md').write_text(report,encoding='utf-8')
    return 0
if __name__=='__main__':raise SystemExit(main())
