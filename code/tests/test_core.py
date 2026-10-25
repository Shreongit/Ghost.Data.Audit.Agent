"""Generic offline tests for the evidence and contract primitives."""
from __future__ import annotations

import sys
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'code'))
import main
from evidence_graph import EvidenceGraph
from llm import LLMClient, LLMError, validate_schema
from linking.trace import trace_facts
from linking.linker import ResourceCandidate, global_ownership
from linking.tools import EvidenceTools, verify_link_claim


def fact(source, at, resource, emails=(), users=(), hashes=(), phones=(), file_time=None, category='USER_PROFILE', system='account_service'):
    at = datetime.fromisoformat(at.replace('Z', '+00:00'))
    return {
        'file': source, 'time': at, 'file_time': file_time or at,
        'resource': resource, 'category': category, 'system': system,
        'data': {'resource_id': resource}, 'text': ' '.join([*emails, *users, *hashes, *phones]),
        'emails': set(emails), 'users': set(users), 'hashes': set(hashes), 'phones': set(phones),
        'direct': True,
    }


class EvidenceGraphTests(unittest.TestCase):
    def test_correction_and_explicit_non_deletion_are_not_authorized(self):
        self.assertFalse(main.deletion_intent('Correct my surname without removing any records.'))
        self.assertFalse(main.deletion_intent("I still use it, so please don't delete or change anything."))
        self.assertTrue(main.deletion_intent('Please delete my account and data.'))

    def test_absence_requires_positive_probe_not_activity_success(self):
        self.assertTrue(main.has_positive_absence_proof({'http_status':'404','rows':'0'}))
        self.assertTrue(main.has_positive_absence_proof({'result':'NOT_FOUND'}))
        self.assertFalse(main.has_positive_absence_proof({'reported_result':'SUCCESS','event_type':'DELETE_RECORD','_activity':True}))
        self.assertFalse(main.has_positive_absence_proof({'reported_result':'SUCCESS'}))

    def test_text_facts_keep_resource_context_local(self):
        text='resource_id: data_flow_9001\nowner: unrelated@example.test\n\n\nresource_id: data_flow_9002\nstatus: enabled'
        got=main.text_facts('evidence_image',text,datetime(2026,2,1,tzinfo=timezone.utc),ROOT/'image.png')
        first=next(x for x in got if x['resource']=='data_flow_9001')
        second=next(x for x in got if x['resource']=='data_flow_9002')
        self.assertIn('unrelated@example.test',first['emails'])
        self.assertNotIn('unrelated@example.test',second['emails'])

    def test_quoted_json_trace_joins_identity_to_absence_probe(self):
        path=ROOT/'code'/'.cache'/'test-trace.log'; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('\n'.join([
            '2026-02-01T00:00:00Z {"trace_id":"tr-a","event":"profile_lookup_started","lookup_key":"person@example.test"}',
            '2026-02-01T00:00:01Z {"trace_id":"tr-a","resource_id":"account_9001","event":"profile_lookup_completed","rows":"0","http_status":"404"}',
        ]),encoding='utf-8')
        got=trace_facts(path,'evidence_trace',datetime(2026,2,1,0,0,2,tzinfo=timezone.utc),fact_fn=main.fact,system_fn=main.system_from,category_fn=main.category_from)
        path.unlink(missing_ok=True)
        self.assertEqual(len(got),1)
        self.assertIn('person@example.test',got[0]['emails'])
        self.assertEqual(got[0]['resource'],'account_9001')
        self.assertEqual(got[0]['data']['http_status'],'404')

    def test_pod_timestamp_fallback_joins_complementary_events(self):
        path=ROOT/'code'/'.cache'/'test-proximity.log';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('\n'.join([
            '2026-02-01T00:00:00Z service=account_service pod=pod-1 event=lookup_started lookup_key=person@example.test',
            '2026-02-01T00:00:02Z service=account_service pod=pod-1 event=lookup_completed resource_id=account_9002 rows=0 http_status=404',
        ]),encoding='utf-8')
        got=trace_facts(path,'evidence_proximity',datetime(2026,2,1,0,0,3,tzinfo=timezone.utc),fact_fn=main.fact,system_fn=main.system_from,category_fn=main.category_from)
        path.unlink(missing_ok=True)
        self.assertEqual(len(got),1)
        self.assertIn('person@example.test',got[0]['emails'])

    def test_global_linker_keeps_best_ambiguous_owner_for_low_confidence_plan(self):
        a=ResourceCandidate('case_a','user_a','search_1','search_service',.98,('same_record_identity_resource',),('e1',))
        b=ResourceCandidate('case_b','user_b','search_1','search_service',.95,('same_record_identity_resource',),('e2',))
        assigned,ambiguous=global_ownership([a,b],margin=.10)
        self.assertEqual(assigned['search_1'].case_id,'case_a')
        self.assertTrue(assigned['search_1'].ambiguous)
        self.assertEqual(len(ambiguous),1)

    def test_global_matching_assigns_each_type_once_per_case(self):
        rows=[
            ResourceCandidate('case_a','u_a','search_1','search_service',.95,('time',),()),
            ResourceCandidate('case_a','u_a','search_2','search_service',.94,('time',),()),
            ResourceCandidate('case_b','u_b','search_1','search_service',.93,('time',),()),
            ResourceCandidate('case_b','u_b','search_2','search_service',.70,('time',),()),
        ]
        assigned,_=global_ownership(rows,margin=.01)
        self.assertEqual(set(assigned),{'search_1','search_2'})
        self.assertEqual({x.case_id for x in assigned.values()},{'case_a','case_b'})

    def test_resource_requires_a_visible_identity_link(self):
        unlinked = fact('evidence_a', '2026-01-01T00:00:00Z', 'account_9001')
        graph = EvidenceGraph([unlinked])
        matches, _ = graph.walk({'user_17'}, datetime(2026, 2, 1, tzinfo=timezone.utc))
        self.assertEqual(matches, [])

    def test_historical_email_and_hash_aliases_stop_at_cutoff(self):
        user={'user_id':'user_17','updated_at':'2026-02-01T00:00:00Z','email':'new@example.test','email_hash':main.email_hash('new@example.test'),'name':'Test Person','phone':'555-010-2020'}
        audits=[
            {'user_id':'user_17','field_name':'email','event_time':'2026-01-01T00:00:00Z','old_value':'old@example.test','new_value':'new@example.test'},
            {'user_id':'user_17','field_name':'email','event_time':'2026-06-01T00:00:00Z','old_value':'new@example.test','new_value':'future@example.test'},
        ]
        aliases=main.resolve_aliases(user,audits,datetime(2026,3,1,tzinfo=timezone.utc))
        self.assertIn('old@example.test',aliases)
        self.assertIn(main.email_hash('old@example.test'),aliases)
        self.assertNotIn('future@example.test',aliases)
        self.assertIn('5550102020',aliases)

    def test_phone_formatting_is_normalized_and_sync_reenables_flow(self):
        aliases=main.resolve_aliases({'user_id':'user_1','updated_at':'2026-01-01T00:00:00Z','phone':'+1 (555) 010-2020'},[],datetime(2026,1,2,tzinfo=timezone.utc))
        self.assertIn(main.digits('1-555-010-2020'),aliases)
        active={'event_type':'SYNC_RECORD','enabled':True}
        disabled={'event_type':'DISABLE_DATA_FLOW','enabled':False}
        self.assertFalse(main.flow_is_disabled(active))
        self.assertTrue(main.flow_is_disabled(disabled))

    def test_plan_is_stable_under_email_case_shuffle_and_post_cutoff_evidence(self):
        user={'user_id':'user_17','updated_at':'2026-01-01T00:00:00Z','email':'person@example.test','email_hash':main.email_hash('person@example.test'),'name':'Test Person','phone':'555-010-2020'}
        identities,aliases,owners=main.build_identity_maps([user],[])
        request={'case_id':'synthetic','email':'person@example.test','audit_at':'2026-02-01T00:00:00Z','request_text':'Please delete my profile.'}
        observed=fact('evidence_record','2026-01-10T00:00:00Z','search_99',users=('user_17',),category='SEARCH_INDEX_ENTRY',system='search_service')
        rules={x['data_category']:x for x in main.rows(ROOT/'dataset/deletion_rules.csv')}
        plan=main.plan_case(request,identities,aliases,owners,[observed],[],rules,[])
        upper={**request,'email':'PERSON@EXAMPLE.TEST'}
        shuffled=main.plan_case(upper,identities,aliases,owners,[observed],[],rules,[])
        later=fact('evidence_future','2026-02-10T00:00:00Z','search_100',users=('user_17',),category='SEARCH_INDEX_ENTRY',system='search_service')
        cutoff_added=main.plan_case(request,identities,aliases,owners,[observed,later],[],rules,[])
        self.assertEqual(plan,shuffled)
        self.assertEqual(plan,cutoff_added)

    def test_later_delete_and_sync_replace_prior_resource_state(self):
        copy=fact('evidence_1','2026-01-01T00:00:00Z','search_1',users=('user_1',),category='SEARCH_INDEX_ENTRY',system='search_service')
        deleted=fact('activity_1','2026-01-02T00:00:00Z','search_1',users=('user_1',),category='SEARCH_INDEX_ENTRY',system='search_service')
        deleted['data']['event_type']='DELETE_RECORD'
        reindexed=fact('activity_2','2026-01-03T00:00:00Z','search_1',users=('user_1',),category='SEARCH_INDEX_ENTRY',system='search_service')
        reindexed['data']['event_type']='INDEX_RECORD'
        state=main.latest_by_resource([copy,deleted,reindexed],datetime(2026,1,4,tzinfo=timezone.utc))
        self.assertEqual(len(state),1)
        self.assertEqual(state[0]['data']['event_type'],'INDEX_RECORD')

    def test_replica_records_remain_separate_by_system(self):
        primary=fact('sql_primary','2026-01-01T00:00:00Z','account_9',users=('user_9',),system='account_service')
        primary['data']['_state_scope']='customer_profiles_primary'
        replica=fact('sql_replica','2026-01-01T00:00:00Z','account_9',users=('user_9',),system='account_service')
        replica['data']['_state_scope']='customer_profiles_failover_replica'
        latest=main.latest_by_resource([primary,replica],datetime(2026,1,2,tzinfo=timezone.utc))
        self.assertEqual({x['data']['_state_scope'] for x in latest},{'customer_profiles_primary','customer_profiles_failover_replica'})

    def test_co_mentioned_resource_links_to_alias(self):
        linked = fact('evidence_a', '2026-01-01T00:00:00Z', 'account_9001', users=('user_17',))
        graph = EvidenceGraph([linked])
        matches, paths = graph.walk({'user_17'}, datetime(2026, 2, 1, tzinfo=timezone.utc))
        self.assertEqual([x['resource'] for x in matches], ['account_9001'])
        self.assertTrue(any(x.relation == 'co_mentioned_with' for x in paths))

    def test_name_alias_uses_word_boundaries_to_avoid_prefix_collision(self):
        unrelated=fact('evidence_other','2026-01-01T00:00:00Z','account_7204')
        unrelated['text']='Priya Ramanathan'
        graph=EvidenceGraph([unrelated])
        matches,_=graph.walk({'Priya Raman'},datetime(2026,2,1,tzinfo=timezone.utc))
        self.assertEqual(matches,[])

    def test_structured_full_name_requires_exact_alias_match(self):
        row=fact('sql','2026-01-01T00:00:00Z','account_9116')
        row['data']['full_name']='Mateo Rios Gil';row['text']='full_name Mateo Rios Gil'
        graph=EvidenceGraph([row])
        self.assertEqual(graph.walk({'Mateo Rios'},datetime(2026,2,1,tzinfo=timezone.utc))[0],[])

    def test_observation_and_manifest_capture_must_both_precede_cutoff(self):
        cutoff = datetime(2026, 1, 5, tzinfo=timezone.utc)
        future_observation = fact('evidence_a', '2026-01-06T00:00:00Z', 'account_1', users=('user_1',))
        future_capture = fact('evidence_b', '2026-01-02T00:00:00Z', 'account_2', users=('user_1',), file_time=datetime(2026, 1, 6, tzinfo=timezone.utc))
        graph = EvidenceGraph([future_observation, future_capture])
        matches, _ = graph.walk({'user_1'}, cutoff)
        self.assertEqual(matches, [])


class ClassificationAndOrderingTests(unittest.TestCase):
    def test_support_attachment_metadata_overrides_generic_support_prefix(self):
        self.assertEqual(main.category_from({'resource_id': 'support_123', 'system': 'support_platform', 'attachment_id': 'att_1', 'file_name': 'id.pdf'}, {}), 'SUPPORT_ATTACHMENT')

    def test_shared_support_message_stays_message(self):
        self.assertEqual(main.category_from({'resource_id': 'support_123', 'record_type': 'SUPPORT_MESSAGE', 'conversation_id': 'conv_3'}, {}), 'SUPPORT_MESSAGE')

    def test_tombstone_with_email_needs_redaction_but_stable_user_id_is_allowed(self):
        self.assertTrue(main.has_prohibited_identifiers('ACCOUNT_TOMBSTONE',{'user_id':'user_17','email':'person@example.test'}))
        self.assertFalse(main.has_prohibited_identifiers('ACCOUNT_TOMBSTONE',{'user_id':'user_17','email':None,'phone':None,'name':None}))

    def test_legal_hold_category_uses_retain_policy(self):
        rules={x['data_category']:x for x in main.rows(ROOT/'dataset/deletion_rules.csv')}
        self.assertEqual(main.policy_action('LEGAL_HOLD_RECORD',{'hold_status':'active'},rules,datetime(2026,1,1,tzinfo=timezone.utc)),'RETAIN')
        self.assertEqual(main.policy_action('LEGAL_HOLD_RECORD',{'hold_status':'released'},rules,datetime(2026,1,1,tzinfo=timezone.utc)),'DELETE')

    def test_support_attachment_evidence_classifies_private_document_for_delete(self):
        document={'resource_id':'support_8','text':'Attachment properties\nUploader customer\nfile_name id_document.pdf'}
        self.assertEqual(main.category_from(document,{}),'SUPPORT_ATTACHMENT')
        rules={x['data_category']:x for x in main.rows(ROOT/'dataset/deletion_rules.csv')}
        self.assertEqual(main.policy_action('SUPPORT_ATTACHMENT',document,rules,datetime(2026,1,1,tzinfo=timezone.utc)),'DELETE')

    def test_validator_rejects_bad_state_and_empty_authorized_plan(self):
        self.assertTrue(main.validate_steps([],'INCOMPLETE'))
        bad=[{'step_no':1,'phase':'REMEDIATION','system_id':'x','resource_id':'r','operation':'DELETE_RECORD','state':'PRESENT','evidence_id':''}]
        self.assertTrue(main.validate_steps(bad,'INCOMPLETE'))

    def test_orderer_sorts_phases_operations_and_deduplicates(self):
        steps = [
            {'phase':'VERIFICATION','system_id':'z','resource_id':'r2','operation':'VERIFY_RECORD_ABSENT','state':'ABSENT','evidence_id':''},
            {'phase':'FINDING','system_id':'a','resource_id':'r1','operation':'REPORT_REMAINING_RECORD','state':'PRESENT','evidence_id':'e1'},
            {'phase':'FINDING','system_id':'a','resource_id':'r1','operation':'REPORT_REMAINING_RECORD','state':'PRESENT','evidence_id':'e1'},
        ]
        ordered = main.order_steps(steps)
        self.assertEqual([(x['phase'],x['step_no']) for x in ordered], [('FINDING',1),('VERIFICATION',2)])

    def test_intent_gate_custom_cases(self):
        self.assertTrue(main.deletion_intent('Je demande la suppression définitive de mon compte.'))
        self.assertFalse(main.deletion_intent('Please export and download a copy of my data.'))
        self.assertFalse(main.deletion_intent('Do not delete my account; only send me an export.'))

    def test_intent_uncertainty_only_for_ambiguous_or_negated_requests(self):
        self.assertTrue(main.intent_is_uncertain('Do not delete my account, only export my data.'))
        self.assertFalse(main.intent_is_uncertain('Please export a copy of my data.'))
        self.assertTrue(main.intent_is_uncertain('Please take care of my account.'))


class StructuredLLMTests(unittest.TestCase):
    def test_evidence_tools_select_only_sql_and_citation_verifier(self):
        requests=[{'case_id':'case_x','audit_at':'2026-02-01T00:00:00Z'}]
        aliases={'case_x':{'person@example.test'}}
        tools=EvidenceTools(ROOT,[],[],requests,aliases)
        sql_id=next(k for k,v in tools.manifest.items() if v['file_path'].lower().endswith('.sql'))
        self.assertEqual(tools.sql_query(sql_id,'SELECT 1 AS one'),[{'one':1}])
        with self.assertRaises(ValueError):tools.sql_query(sql_id,'DELETE FROM anything')
        item=fact('evidence_x','2026-01-01T00:00:00Z','account_9',emails=['person@example.test']);item['file_time']=datetime(2026,1,2,tzinfo=timezone.utc)
        claim={'resource_id':'account_9','owner':'user_x','cited_ids':['evidence_x']}
        self.assertTrue(verify_link_claim(claim,'case_x','user_x',aliases,requests,[item]))
        future=dict(item);future['file']='evidence_future';future['time']=datetime(2026,2,2,tzinfo=timezone.utc);future['file_time']=future['time']
        claim['cited_ids']=['evidence_future']
        self.assertFalse(verify_link_claim(claim,'case_x','user_x',aliases,requests,[future]))

    def test_schema_rejects_missing_fields_and_wrong_types(self):
        schema={'type':'object','required':['ok'],'additionalProperties':False,'properties':{'ok':{'type':'boolean'}}}
        validate_schema({'ok':True},schema)
        with self.assertRaises(LLMError): validate_schema({'ok':'yes'},schema)
        with self.assertRaises(LLMError): validate_schema({},schema)

    def test_mocked_structured_call_caches_and_accounts_without_network(self):
        schema={'type':'object','required':['ok'],'additionalProperties':False,'properties':{'ok':{'type':'boolean'}}}
        with tempfile.TemporaryDirectory(dir=ROOT) as directory, patch.dict('os.environ',{'LLM_PROVIDER':'openai','OPENAI_API_KEY':'test-only','LLM_MODEL_FAST':'mock-model'},clear=False):
            client=LLMClient(Path(directory))
            with patch.object(client,'_request',return_value=(json.dumps({'ok':True}),{'input_tokens':10,'output_tokens':3})) as request:
                self.assertEqual(client.structured('unit','system','prompt',schema),{'ok':True})
                self.assertEqual(client.structured('unit','system','prompt',schema),{'ok':True})
                self.assertEqual(request.call_count,1)
            self.assertEqual(client.totals['calls'],1)
            self.assertEqual(client.totals['cache_hits'],1)


if __name__ == '__main__':
    unittest.main()
