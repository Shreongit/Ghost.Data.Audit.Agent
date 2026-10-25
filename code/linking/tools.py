"""Cached, deterministic, read-only evidence tools for bounded link review."""
from __future__ import annotations
import hashlib, json, re, sqlite3
from pathlib import Path

class EvidenceTools:
    def __init__(self, root, facts, activities, requests, aliases_by_case):
        self.root=Path(root);self.facts=facts;self.activities=activities;self.requests={x['case_id']:x for x in requests};self.aliases=aliases_by_case
        self.cache=self.root/'code'/'.cache'/'linker_tools';self.cache.mkdir(parents=True,exist_ok=True)
        with open(self.root/'dataset'/'evidence_files.csv',encoding='utf-8-sig',newline='') as handle:
            self.manifest={x['file_id']:x for x in __import__('csv').DictReader(handle)}
        self.case_id=None
    def _cutoff(self):
        if not self.case_id:return None
        return self.requests[self.case_id]['audit_at']
    def _before_cutoff(self,fact):
        cutoff=self._cutoff()
        return cutoff is None or (fact.get('time').isoformat().replace('+00:00','Z')<=cutoff and fact.get('file_time',fact.get('time')).isoformat().replace('+00:00','Z')<=cutoff)
    def _cached(self,name,args,fn):
        digest=hashlib.sha256(json.dumps([name,args],sort_keys=True,default=str).encode()).hexdigest();path=self.cache/f'{digest}.json'
        if path.exists():return json.loads(path.read_text(encoding='utf-8'))
        value=fn();path.write_text(json.dumps(value,ensure_ascii=False,default=str),encoding='utf-8');return value
    def search_evidence(self,query):
        q=str(query).casefold()
        return self._cached('search_evidence',[self.case_id,q],lambda:[{'source_id':f['file'],'resource_id':f['resource'],'observed_at':f['time'].isoformat(),'text':f['text'][:1200]} for f in self.facts if self._before_cutoff(f) and q in f['text'].casefold()][:50])
    def get_trace_group(self,trace_id):
        key=str(trace_id).casefold()
        return self._cached('get_trace_group',[self.case_id,key],lambda:[{'source_id':f['file'],'resource_id':f['resource'],'observed_at':f['time'].isoformat(),'text':f['text'][:1500]} for f in self.facts if self._before_cutoff(f) and str(f.get('_trace_group',f.get('data',{}).get('_trace_group',''))).casefold().endswith(key)][:50])
    def activity_window(self,system,start,end):
        cutoff=self._cutoff()
        if cutoff and start>cutoff:return []
        if cutoff and end>cutoff:end=cutoff
        return self._cached('activity_window',[self.case_id,system,start,end],lambda:[x for x in self.activities if start<=x['event_time']<=end and system in (x.get('source_system'),x.get('target_system'))][:100])
    def sql_query(self,file_id,sql):
        if not re.match(r'^\s*(SELECT|WITH)\b',sql,re.I) or ';' in sql.rstrip().rstrip(';'):
            raise ValueError('Only one SELECT/WITH query is allowed.')
        if re.search(r'\b(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|ATTACH|DETACH|VACUUM|PRAGMA)\b',sql,re.I):
            raise ValueError('Only read-only SELECT/WITH queries are allowed.')
        entry=self.manifest.get(file_id)
        if not entry or not entry['file_path'].lower().endswith('.sql'):raise ValueError('file_id is not a manifested SQL evidence file')
        cutoff=self._cutoff()
        if cutoff and entry['captured_at']>cutoff:raise ValueError('SQL evidence was captured after the case audit cutoff')
        def run():
            db=sqlite3.connect(':memory:');db.executescript((self.root/'dataset'/entry['file_path']).read_text(encoding='utf-8',errors='replace'));db.execute('PRAGMA query_only=ON')
            db.set_authorizer(lambda action,*args: sqlite3.SQLITE_OK if action in (sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_TRANSACTION) else sqlite3.SQLITE_DENY)
            cur=db.execute(sql);cols=[x[0] for x in cur.description or []];result=[dict(zip(cols,row)) for row in cur.fetchmany(100)];db.close();return result
        return self._cached('sql_query',[file_id,sql],run)
    def get_alias_set(self,case_id):return sorted(self.aliases.get(case_id,set()))
    def get_resource_facts(self,resource_id):
        return self._cached('get_resource_facts',[self.case_id,resource_id],lambda:[{'source_id':f['file'],'observed_at':f['time'].isoformat(),'system_id':f['system'],'category':f['category'],'data':f['data']} for f in self.facts if f['resource']==resource_id and self._before_cutoff(f)])

def verify_link_claim(result,case_id,user_id,aliases_by_case,requests,source_facts):
    """Accept a model-suggested relation only when cited source facts prove it."""
    if not isinstance(result,dict) or not result.get('resource_id') or result.get('owner')!=user_id:return False
    req=next((r for r in requests if r['case_id']==case_id),None)
    if not req:return False
    cutoff=__import__('datetime').datetime.fromisoformat(req['audit_at'].replace('Z','+00:00'));ids=set(result.get('cited_ids',[]))
    if not ids:return False
    aliases={str(x).casefold() for x in aliases_by_case.get(case_id,set())}|{user_id.casefold()}
    cited=[f for f in source_facts if f.get('file') in ids and f.get('resource')==result['resource_id'] and f.get('time')<=cutoff and f.get('file_time',f.get('time'))<=cutoff]
    cited_ids={f.get('file') for f in cited}
    return bool(cited) and ids.issubset(cited_ids) and all(any(a in (f.get('emails',set())|f.get('users',set())|f.get('hashes',set())|f.get('phones',set())) for a in aliases) for f in cited)
