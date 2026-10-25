"""Unit checks for public-sample time calibration and cutoff-aware candidates."""
import sys
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'code'))
from linking.time_model import _fit_offsets,_offset_likelihood,_status_likelihood,time_activity_candidates,sample_oof,burst_activity_ids
from linking.linker import ResourceCandidate

def activity(aid='activity_1',when='2026-01-01T00:00:00Z',rid='account_1',event='DELETE_RECORD',result='SUCCESS',target='account_service'):
    return {'activity_id':aid,'event_time':when,'resource_id':rid,'event_type':event,'reported_result':result,'target_system':target,'source_system':'identity_service'}

class TimeModelTests(unittest.TestCase):
    def test_fit_offsets_records_robust_median_and_quartiles(self):
        req=[{'case_id':'c1','reported_at':'2026-01-01T01:00:00Z','reported_status':'COMPLETE'}]
        ans=[{'case_id':'c1','steps_json':'[{"resource_id":"account_1"}]'}]
        model=_fit_offsets(req,ans,[activity()])
        group=model['groups']['account_service|DELETE_RECORD']
        self.assertAlmostEqual(group['median_hours'],1.0)
        self.assertEqual(group['n'],1)
        self.assertIn('q1_hours',group);self.assertIn('q3_hours',group)

    def test_fit_offsets_excludes_activity_after_heldout_audit_cutoff(self):
        req=[{'case_id':'c1','reported_at':'2026-01-01T02:00:00Z','audit_at':'2026-01-01T01:00:00Z','reported_status':'COMPLETE'}]
        ans=[{'case_id':'c1','steps_json':'[{"resource_id":"account_1"}]'}]
        acts=[activity('before','2026-01-01T00:00:00Z'),activity('after','2026-01-01T01:30:00Z')]
        model=_fit_offsets(req,ans,acts)
        self.assertAlmostEqual(model['groups']['account_service|DELETE_RECORD']['median_hours'],2.0)

    def test_fit_offsets_emits_separate_worker_modes(self):
        requests=[]; answers=[]; acts=[]
        for i,delta in enumerate([0.0,.02,.04,.8,.82,.84]):
            cid=f'c{i}'; requests.append({'case_id':cid,'reported_at':f'2026-01-01T{int(delta):02d}:00:00Z','reported_status':'COMPLETE'})
            # Construct the event directly as ISO minutes around the common cutoff.
            hours=int(delta); minutes=round((delta-hours)*60)
            reported=f'2026-01-01T{hours:02d}:{minutes:02d}:00Z'
            requests[-1]['reported_at']=reported
            answers.append({'case_id':cid,'steps_json':json.dumps([{'resource_id':f'account_{i}'}])})
            acts.append(activity(f'a{i}', '2026-01-01T00:00:00Z',f'account_{i}'))
        model=_fit_offsets(requests,answers,acts)
        self.assertGreaterEqual(len(model['groups']['account_service|DELETE_RECORD']['modes']),2)

    def test_offset_likelihood_prefers_calibrated_delta(self):
        model={'groups':{'account_service|DELETE_RECORD':{'median_hours':1,'sigma_hours':.2,'modes':[]}}}
        near,_=_offset_likelihood(model,'account_service','DELETE_RECORD','SUCCESS',1.0)
        far,_=_offset_likelihood(model,'account_service','DELETE_RECORD','SUCCESS',2.0)
        self.assertGreater(near,far)

    def test_offset_likelihood_uses_result_conditioned_group(self):
        model={'groups':{
            'account_service|DELETE_RECORD':{'median_hours':0,'sigma_hours':1,'modes':[]},
            'account_service|DELETE_RECORD|FAILED':{'median_hours':2,'sigma_hours':.2,'modes':[]}}}
        v,_=_offset_likelihood(model,'account_service','DELETE_RECORD','FAILED',2)
        self.assertAlmostEqual(v,1)

    def test_sparse_result_group_backs_off_to_pooled_worker_modes(self):
        model={'groups':{
            'account_service|DELETE_RECORD':{'median_hours':.9,'sigma_hours':.2,'modes':[{'median_hours':-.05,'sigma_hours':.1},{'median_hours':.9,'sigma_hours':.2}]},
            'account_service|DELETE_RECORD|PARTIAL':{'median_hours':1.0,'sigma_hours':.08,'modes':[{'median_hours':1.0,'sigma_hours':.08}]}}}
        value,_=_offset_likelihood(model,'account_service','DELETE_RECORD','PARTIAL',-.08)
        self.assertGreater(value,.9)

    def test_offset_missing_group_has_zero_likelihood(self):
        self.assertEqual(_offset_likelihood({'groups':{}},'x','DELETE_RECORD','SUCCESS',1)[0],0)

    def test_status_result_likelihood_is_soft_and_bounded(self):
        model={'status_result_counts':{'COMPLETE|SUCCESS':16,'COMPLETE|FAILED':1}}
        good=_status_likelihood(model,'COMPLETE','SUCCESS')
        exception=_status_likelihood(model,'COMPLETE','FAILED')
        self.assertGreater(good,exception);self.assertGreater(exception,0);self.assertLess(good,1)

    def test_candidate_respects_audit_cutoff(self):
        case={'case_id':'c','reported_at':'2026-01-01T01:00:00Z','audit_at':'2026-01-01T00:30:00Z','reported_status':'COMPLETE'}
        acts=[activity(when='2026-01-01T00:00:00Z'),activity('later','2026-01-01T00:45:00Z','account_2')]
        model={'groups':{'account_service|DELETE_RECORD|SUCCESS':{'median_hours':1,'sigma_hours':1,'modes':[]}},'status_result_counts':{'COMPLETE|SUCCESS':2}}
        got=time_activity_candidates(case,'u',acts,parse_time=lambda x:datetime.fromisoformat(x.replace('Z','+00:00')),model=model)
        self.assertEqual([x.resource_id for x in got],['account_1'])

    def test_candidate_emits_activity_provenance_and_delta(self):
        case={'case_id':'c','reported_at':'2026-01-01T01:00:00Z','audit_at':'2026-01-02T00:00:00Z','reported_status':'COMPLETE'}
        model={'groups':{'account_service|DELETE_RECORD|SUCCESS':{'median_hours':1,'sigma_hours':1,'modes':[]}},'status_result_counts':{'COMPLETE|SUCCESS':2}}
        got=time_activity_candidates(case,'u',[activity()],parse_time=lambda x:datetime.fromisoformat(x.replace('Z','+00:00')),model=model)
        self.assertEqual(got[0].source_ids[0],'activity_1');self.assertIn('delta_hours=1.000000',got[0].source_ids)

    def test_candidate_filters_incompatible_operation_type(self):
        case={'case_id':'c','reported_at':'2026-01-01T01:00:00Z','audit_at':'2026-01-02T00:00:00Z','reported_status':'COMPLETE'}
        model={'groups':{},'status_result_counts':{}}
        self.assertEqual(time_activity_candidates(case,'u',[activity(event='SYNC_RECORD')],parse_time=lambda x:datetime.fromisoformat(x.replace('Z','+00:00')),model=model),[])

    def test_candidate_filters_unmodeled_system(self):
        case={'case_id':'c','reported_at':'2026-01-01T01:00:00Z','audit_at':'2026-01-02T00:00:00Z','reported_status':'COMPLETE'}
        model={'groups':{},'status_result_counts':{}}
        self.assertEqual(time_activity_candidates(case,'u',[activity(target='other')],parse_time=lambda x:datetime.fromisoformat(x.replace('Z','+00:00')),model=model),[])

    def test_same_burst_anchor_adds_signal_and_score(self):
        case={'case_id':'c','reported_at':'2026-01-01T01:00:00Z','audit_at':'2026-01-02T00:00:00Z','reported_status':'COMPLETE'}
        model={'groups':{'account_service|DELETE_RECORD|SUCCESS':{'median_hours':1,'sigma_hours':1,'modes':[]}},'status_result_counts':{'COMPLETE|SUCCESS':2}}
        parse=lambda x:datetime.fromisoformat(x.replace('Z','+00:00'))
        base=time_activity_candidates(case,'u',[activity()],parse_time=parse,model=model)[0]
        burst=time_activity_candidates(case,'u',[activity()],parse_time=parse,model=model,sibling_activity_ids={'activity_1'},burst_scores={'activity_1':1.0})[0]
        self.assertIn('same_burst_activity_anchor',burst.signals);self.assertGreater(burst.score,base.score)

    def test_duplicate_activity_rows_deduplicate_by_resource(self):
        case={'case_id':'c','reported_at':'2026-01-01T01:00:00Z','audit_at':'2026-01-02T00:00:00Z','reported_status':'COMPLETE'}
        model={'groups':{'account_service|DELETE_RECORD|SUCCESS':{'median_hours':1,'sigma_hours':1,'modes':[]}},'status_result_counts':{'COMPLETE|SUCCESS':2}}
        parse=lambda x:datetime.fromisoformat(x.replace('Z','+00:00'))
        got=time_activity_candidates(case,'u',[activity(),activity('a2','2026-01-01T00:01:00Z')],parse_time=parse,model=model)
        self.assertEqual(len(got),1)

    def test_oof_labels_excluded_from_protocol_summary(self):
        req=[{'case_id':'c1','reported_at':'2026-01-01T01:00:00Z','audit_at':'2026-01-02T00:00:00Z','reported_status':'COMPLETE'}]
        ans=[{'case_id':'c1','steps_json':'[{"resource_id":"account_1"}]'}]
        out=sample_oof(req,ans,[activity()])
        self.assertIn('31 other public sample cases',out['protocol'])
        self.assertEqual(out['per_type']['account']['gold'],1)

    def test_candidate_carries_request_and_owner_identity(self):
        case={'case_id':'c','reported_at':'2026-01-01T01:00:00Z','audit_at':'2026-01-02T00:00:00Z','reported_status':'COMPLETE'}
        model={'groups':{'account_service|DELETE_RECORD|SUCCESS':{'median_hours':1,'sigma_hours':1,'modes':[]}},'status_result_counts':{'COMPLETE|SUCCESS':2}}
        got=time_activity_candidates(case,'user_1',[activity()],parse_time=lambda x:datetime.fromisoformat(x.replace('Z','+00:00')),model=model)[0]
        self.assertEqual((got.case_id,got.user_id),('c','user_1'))

    def test_burst_anchor_uses_worker_adjacency_and_respects_cutoff(self):
        rows=[
            {**activity('activity_100','2026-01-01T00:00:00Z'),'source_system':'deletion_worker'},
            {**activity('activity_102','2026-01-01T00:30:00Z','analytics_2','ANONYMIZE_RECORD','SUCCESS','analytics_platform'),'source_system':'deletion_worker'},
            {**activity('activity_103','2026-01-02T00:00:00Z','analytics_3','ANONYMIZE_RECORD','SUCCESS','analytics_platform'),'source_system':'deletion_worker'},
        ]
        got=burst_activity_ids(rows,{'account_1'},datetime(2026,1,1,1,tzinfo=timezone.utc))
        self.assertIn('activity_102',got);self.assertNotIn('activity_103',got)

    def test_candidate_score_is_between_soft_and_direct_link_bounds(self):
        case={'case_id':'c','reported_at':'2026-01-01T01:00:00Z','audit_at':'2026-01-02T00:00:00Z','reported_status':'COMPLETE'}
        model={'groups':{'account_service|DELETE_RECORD|SUCCESS':{'median_hours':1,'sigma_hours':1,'modes':[]}},'status_result_counts':{'COMPLETE|SUCCESS':2}}
        got=time_activity_candidates(case,'u',[activity()],parse_time=lambda x:datetime.fromisoformat(x.replace('Z','+00:00')),model=model)[0]
        self.assertGreaterEqual(got.score,.68);self.assertLess(got.score,.98)

if __name__=='__main__': unittest.main()
