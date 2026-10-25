"""Sample-only linker calibration. Never imported by the prediction pipeline."""
import csv,json,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'code'))
import main as agent
from evidence_graph import EvidenceGraph
from linking.linker import candidate_from_facts,global_ownership
from linking.time_model import fit_and_write, sample_oof

def rows(path):
 with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
D=ROOT/'dataset'; requests=rows(D/'sample_deletion_requests.csv'); gold=rows(D/'sample_output.csv')
users=rows(D/'user_identities.csv');audits=rows(D/'user_audit_log.csv');byid,_,_=agent.build_identity_maps(users,audits)
facts=agent.read_records(rows(D/'evidence_files.csv')); graph=EvidenceGraph(facts+agent.activity_facts(rows(D/'system_activity.csv')))
candidates=[];gold_pairs=set();types={}
prefixes={'account_':'account','search_':'search','export_':'export','support_':'support','analytics_':'analytics','telemetry_':'analytics','audit_record_':'audit','backup_':'backup','data_flow_':'flow','tombstone_':'tombstone'}
for req,answer in zip(requests,gold):
 uid=agent.requested_user(req,byid,audits)
 if not uid: continue
 cutoff=agent.dt(req['audit_at']); aliases=agent.resolve_aliases(byid[uid],audits,cutoff)
 emails={agent.norm(x) for x in aliases if '@' in x};aliases|={agent.email_hash(x) for x in emails};aliases|={agent.digits(x) for x in aliases if len(agent.digits(x))>=8};aliases.add(uid.casefold())
 matches,paths=graph.walk(aliases,cutoff); candidates.extend(candidate_from_facts(req['case_id'],uid,matches,aliases,paths,cutoff))
 for s in json.loads(answer['steps_json']):
  rid=s['resource_id'];gold_pairs.add((req['case_id'],rid));
  typ=next((v for k,v in prefixes.items() if rid.startswith(k)),'other');types[rid]=typ
fit_and_write(requests,gold,rows(D/'system_activity.csv'))
activities=rows(D/'system_activity.csv')
linker_requests=rows(D/'deletion_requests.csv')+requests
all_direct=[]
request_users={}
for req in linker_requests:
 uid=agent.requested_user(req,byid,audits)
 if not uid:continue
 request_users[req['case_id']]=uid
 cutoff=agent.dt(req['audit_at']);aliases=agent.resolve_aliases(byid[uid],audits,cutoff)
 emails={agent.norm(x) for x in aliases if '@' in x};aliases|={agent.email_hash(x) for x in emails};aliases|={agent.digits(x) for x in aliases if len(agent.digits(x))>=8};aliases.add(uid.casefold())
 matched,paths=graph.walk(aliases,cutoff)
 all_direct.extend(candidate_from_facts(req['case_id'],uid,matched,aliases,paths,cutoff))
candidate_pairs={(x.case_id,x.resource_id) for x in candidates}
assigned,ambiguous=global_ownership(candidates)
assigned_pairs={(case,rid) for case,rid in candidate_pairs if rid in assigned and assigned[rid].user_id==next((x.user_id for x in candidates if x.case_id==case and x.resource_id==rid),None)}
def metrics(pred,gold):
 tp=len(pred&gold);return {'precision':tp/max(1,len(pred)),'recall':tp/max(1,len(gold)),'tp':tp,'predicted':len(pred),'gold':len(gold)}
threshold_grid=[]
for threshold in (.90,.95,.97,.98,.99):
 pairs={(x.case_id,x.resource_id) for x in candidates if x.score>=threshold};metric=metrics(pairs,gold_pairs);metric['threshold']=threshold;metric['f1']=2*metric['precision']*metric['recall']/max(1e-12,metric['precision']+metric['recall']);threshold_grid.append(metric)
best=max(threshold_grid,key=lambda x:(x['f1'],x['precision'],x['threshold']))
candidate_pairs={(x.case_id,x.resource_id) for x in candidates if x.score>=best['threshold']}
assigned,ambiguous=global_ownership([x for x in candidates if x.score>=best['threshold']])
assigned_pairs={(case,rid) for case,rid in candidate_pairs if rid in assigned and assigned[rid].user_id==next((x.user_id for x in candidates if x.case_id==case and x.resource_id==rid),None)}
report={'direct':metrics(candidate_pairs,gold_pairs),'global_assignment':metrics(assigned_pairs,gold_pairs),'selected_threshold':best['threshold'],'threshold_grid':threshold_grid,'ambiguous_resources':len(ambiguous),'per_type':{},'signal_ablation':{}}
oof=sample_oof(linker_requests,gold,activities,all_direct,user_ids=request_users)
report['out_of_fold']={'protocol':oof['protocol'],'per_type':oof['per_type'],'cumulative_ablation':oof['cumulative_ablation']}
oof_path=ROOT/'code/linking/out_of_fold_predictions.json'
oof_path.write_text(json.dumps(oof['predictions'],indent=2,sort_keys=True),encoding='utf-8')
def temporal_text(item):
 if not item:return 'no compatible activity row at/before audit_at'
 return (f"`{item['activity_id']}` {item['event_type']} at {item['event_time']}; Δ={item['delta_hours']:+.6f} h; "
         f"result=`{item['reported_result']}`; status/result match=`{item['status_result_match']}`; "
         f"offset likelihood={item['offset_likelihood']:.6f} ({item['offset_group']})")
miss_lines=['# Held-out account and analytics link misses','',
            'Leave-one-case-out; every model is fitted on the other 31 public sample cases. The request candidate universe includes all 518 evaluation requests plus the public sample. Candidate rows list timing, result/status compatibility, provenance, and other candidate owners for the same resource. These are diagnostic leads; absence from the candidate set is not evidence of deletion.','']
for miss in oof['heldout_misses']:
 miss_lines += [f"## {miss['case_id']} — `{miss['gold_resource']}` ({miss['resource_type']})",'',
                f"Reported status: `{miss['reported_status']}`; reported_at: `{miss['reported_at']}`; audit_at: `{miss['audit_at']}`."]
 if miss['gold_activity']:
  miss_lines += ['', 'Cutoff-valid activity rows naming the gold resource:']
  miss_lines += [f"- {temporal_text(x)}" for x in miss['gold_activity']]
 else:miss_lines += ['', 'No cutoff-valid activity row names this gold resource.']
 if miss['gold_resource_competing_cases']:
  miss_lines += ['', 'Candidates for the gold resource and competing request owners:']
  miss_lines += [f"- `{x['case_id']}` score={x['score']:.6f}; signals={', '.join(x['signals'])}; provenance={', '.join(x['provenance'])}" for x in miss['gold_resource_competing_cases']]
 else:miss_lines += ['', 'The gold resource has no candidate edge in this held-out fold.']
 miss_lines += ['', 'Same-type candidates for the held-out request:', '']
 if miss['same_type_candidates']:
  miss_lines += ['| Candidate | Score | Signals | Temporal offset/result/status | Provenance | Competing cases |','|---|---:|---|---|---|---|']
  for x in miss['same_type_candidates']:
   peers=', '.join(f"{p['case_id']} ({p['score']:.4f})" for p in x['competing_cases'] if p['case_id']!=miss['case_id']) or 'none'
   miss_lines.append(f"| `{x['resource_id']}` | {x['score']:.6f} | {', '.join(x['signals'])} | {temporal_text(x['temporal'])} | {', '.join(x['provenance'])} | {peers} |")
 else:miss_lines.append('No same-type candidate edge was emitted for the held-out case.')
 miss_lines.append('')
(ROOT/'code/linking/heldout_link_misses.md').write_text('\n'.join(miss_lines)+'\n',encoding='utf-8')
print('DIRECT',report['direct']);print('GLOBAL',report['global_assignment']);print('AMBIGUOUS_RESOURCES',len(ambiguous))
print('OOF',json.dumps(report['out_of_fold'],sort_keys=True))
for typ in sorted(set(types.values())):
 g={(c,r) for c,r in gold_pairs if types.get(r)==typ};p={(c,r) for c,r in candidate_pairs if types.get(r)==typ};report['per_type'][typ]=metrics(p,g);print('TYPE',typ,report['per_type'][typ])
# Signal ablation: remove candidates carrying exactly one listed signal and recalc pair metrics.
for signal in sorted({s for c in candidates for s in c.signals}):
 p={(c.case_id,c.resource_id) for c in candidates if c.score>=best['threshold'] and signal not in c.signals};report['signal_ablation'][signal]=metrics(p,gold_pairs);print('ABLATION_REMOVE',signal,report['signal_ablation'][signal])
(ROOT/'code/linking/linker_metrics.json').write_text(json.dumps(report,indent=2,sort_keys=True),encoding='utf-8')
