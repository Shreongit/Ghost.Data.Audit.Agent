"""Bounded structured tool loop for unresolved resource links (optional LLM)."""
from __future__ import annotations
import json
from pathlib import Path
from llm import LLMError
from linking.tools import verify_link_claim

SCHEMA={'type':'object','required':['action','tool','arguments','resource_id','owner','cited_ids','reasoning'],'additionalProperties':False,'properties':{
 'action':{'type':'string','enum':['tool','final','unresolved']},
 'tool':{'type':'string','enum':['search_evidence','get_trace_group','activity_window','sql_query','get_alias_set','get_resource_facts','none']},
 'arguments':{'type':'object','additionalProperties':{'type':'string'}},
 'resource_id':{'type':'string'},'owner':{'type':'string'},'cited_ids':{'type':'array','items':{'type':'string'}},'reasoning':{'type':'string'}}}

def investigate_link(llm,tools,*,case_id,user_id,aliases,requests,facts,max_steps=5):
    if not getattr(llm,'strong',''):return {'status':'skipped','reason':'strong model not configured'}
    tools.case_id=case_id
    system=(Path(__file__).parents[1]/'prompts'/'link_agent.md').read_text(encoding='utf-8')
    context={'case_id':case_id,'user_id':user_id,'audit_at':next(r['audit_at'] for r in requests if r['case_id']==case_id),'aliases':sorted(aliases)}
    history=[]
    handlers={'search_evidence':tools.search_evidence,'get_trace_group':tools.get_trace_group,'activity_window':tools.activity_window,'sql_query':tools.sql_query,'get_alias_set':tools.get_alias_set,'get_resource_facts':tools.get_resource_facts}
    for turn in range(max_steps):
        prompt=json.dumps({'case':context,'tools_available':sorted(handlers),'history':history,'turn':turn+1,'limit':max_steps},ensure_ascii=False,default=str)
        result=llm.structured('resource_link_agent',system,prompt,SCHEMA,tier='strong')
        if result['action']=='unresolved':return {'status':'unresolved','reason':result['reasoning'],'history':history}
        if result['action']=='final':
            ok=verify_link_claim(result,case_id,user_id,{case_id:set(aliases)},requests,facts)
            return {'status':'accepted' if ok else 'rejected','claim':result,'history':history}
        if result['tool'] not in handlers:return {'status':'rejected','reason':'unknown tool','history':history}
        try:
            value=handlers[result['tool']](**result['arguments'])
            history.append({'tool':result['tool'],'arguments':result['arguments'],'result':value})
        except Exception as exc:
            history.append({'tool':result['tool'],'error':type(exc).__name__})
    return {'status':'unresolved','reason':'bounded tool-call limit reached','history':history}
