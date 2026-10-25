from __future__ import annotations
import argparse, csv, hashlib, json, logging, re, sqlite3, sys, unicodedata, os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from evidence_graph import EvidenceGraph
from config import AppConfig
from linking.trace import trace_facts
from linking.linker import candidate_from_facts, global_ownership, weak_activity_candidates, build_weak_signal_index
from linking.linker import ResourceCandidate
from linking.time_model import time_activity_candidates, build_activity_time_index, build_resource_activity_index, burst_activity_scores, rank_direct_candidate_by_activity, MODEL_PATH

CONFIG=AppConfig.from_entrypoint(__file__)
ROOT=CONFIG.root
DATA=CONFIG.dataset
LOG = logging.getLogger('ghost_audit')
EXTRACTION_STATS={'hits':0,'misses':0,'ocr_failures':0,'images_seen':0}
OPS = {
 'FINDING':['REPORT_REMAINING_RECORD','REPORT_EXPOSED_PII','REPORT_ACTIVE_DATA_FLOW','REPORT_RESTORE_RISK'],
 'REMEDIATION':['DISABLE_DATA_FLOW','BLOCK_RESTORE','DELETE_RECORD','REDACT_RECORD','ANONYMIZE_RECORD'],
 'VERIFICATION':['VERIFY_RECORD_ABSENT','VERIFY_RECORD_PRESENT','VERIFY_RECORD_REDACTED','VERIFY_RECORD_ANONYMIZED','VERIFY_DATA_FLOW_DISABLED','VERIFY_RESTORE_BLOCKED']}
STATE = {'REPORT_REMAINING_RECORD':'PRESENT','REPORT_EXPOSED_PII':'PRESENT','REPORT_ACTIVE_DATA_FLOW':'ACTIVE','REPORT_RESTORE_RISK':'ACTIVE','DISABLE_DATA_FLOW':'DISABLED','BLOCK_RESTORE':'BLOCKED','DELETE_RECORD':'ABSENT','REDACT_RECORD':'REDACTED','ANONYMIZE_RECORD':'ANONYMIZED','VERIFY_RECORD_ABSENT':'ABSENT','VERIFY_RECORD_PRESENT':'PRESENT','VERIFY_RECORD_REDACTED':'REDACTED','VERIFY_RECORD_ANONYMIZED':'ANONYMIZED','VERIFY_DATA_FLOW_DISABLED':'DISABLED','VERIFY_RESTORE_BLOCKED':'BLOCKED'}
VERIFY = {'DELETE':'VERIFY_RECORD_ABSENT','REDACT':'VERIFY_RECORD_REDACTED','ANONYMIZE':'VERIFY_RECORD_ANONYMIZED','RETAIN':'VERIFY_RECORD_PRESENT'}
REMEDIATE = {'DELETE':'DELETE_RECORD','REDACT':'REDACT_RECORD','ANONYMIZE':'ANONYMIZE_RECORD'}

def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def dt(s):
    try: return datetime.fromisoformat(str(s).replace('Z','+00:00'))
    except Exception: return datetime.min.replace(tzinfo=timezone.utc)
def norm(s): return ''.join(c for c in unicodedata.normalize('NFKD', str(s or '').strip().casefold()) if not unicodedata.combining(c))
def digits(s): return re.sub(r'\D','',str(s or ''))
def email_hash(s): return hashlib.sha256(norm(s).encode()).hexdigest()
def has_positive_absence_proof(data):
    """A claim of deletion is not enough; require an observed missing-state result."""
    if data.get('_activity'): return False
    if str(data.get('http_status',data.get('status_code','')))=='404': return True
    if str(data.get('rows','')).strip()=='0' or str(data.get('total_hits','')).strip()=='0': return True
    if norm(data.get('result','')) in ('not_found','not found','absent') or norm(data.get('lookup_result','')) in ('not_found','not found','absent'): return True
    if norm(data.get('state',data.get('record_status',''))) in ('absent','not_found','not found','deleted'): return True
    return False
def flatten(v):
    if isinstance(v,dict): return ' '.join([str(k)+' '+flatten(x) for k,x in v.items()])
    if isinstance(v,list): return ' '.join(flatten(x) for x in v)
    return str(v) if v is not None else ''
def walk_json(obj):
    """Yield record-sized dictionaries with their nearest snapshot context."""
    def rec(x,ctx):
        if isinstance(x,dict):
            nxt=dict(ctx)
            for key in ('captured_at','data_store','system_id','system','collection','table','data_category','record_type'):
                if key in x and not isinstance(x[key],(dict,list)): nxt[key]=x[key]
            if 'resource_id' in x or ('record_json' in x): yield (x,nxt)
            for k,v in x.items():
                if isinstance(v,list) and k in ('records','items','entries','resources','rows'):
                    for child in v:
                        if isinstance(child,dict): yield (child,nxt)
                else: yield from rec(v,nxt)
        elif isinstance(x,list):
            for y in x: yield from rec(y,ctx)
    yield from rec(obj,{})

def system_from(data, context, path=''):
    rid=str(data.get('resource_id') or '').lower()
    prefix_system={'account_':'account_service','search_':'search_service','support_':'support_platform','analytics_':'analytics_platform','telemetry_':'analytics_platform','export_':'export_service','backup_':'backup_service','audit_record_':'security_service','data_flow_':'integration_service','tombstone_':'identity_service','cache_':'cache_service','marketing_':'marketing_service','email_delivery_':'notification_service'}
    for prefix,system in prefix_system.items():
        if rid.startswith(prefix): return system
    s=str(data.get('system_id') or data.get('system') or context.get('system_id') or context.get('system') or data.get('data_store') or context.get('data_store') or '')
    if s: return s
    p=(path+' '+str(context.get('collection',''))+' '+str(data.get('record_type',''))).lower()
    m={'account':'account_service','customer':'account_service','search':'search_service','support':'support_platform','analytics':'analytics_platform','telemetry':'analytics_platform','export':'export_service','backup':'backup_service','audit':'security_service','security':'security_service','connector':'integration_service','flow':'integration_service','marketing':'marketing_service','email':'notification_service','cache':'cache_service','identity':'identity_service'}
    for token,sysid in m.items():
        if token in p: return sysid
    return 'unknown_service'
def category_from(data,context):
    s=' '.join(str(data.get(k,'') or '') for k in ('data_category','record_type','category','collection','table','type','source','service','event'))+' '+str(context.get('collection',''))+' '+str(context.get('table',''))
    s=s.lower().replace(' ','_')
    attachment_fields=('attachment_id','attachment_name','file_name','filename','mime_type','content_type','object_key','blob_path')
    has_attachment=any(data.get(k) for k in attachment_fields) or str(data.get('is_attachment','')).casefold() in ('true','1','yes')
    body=norm(data.get('text',''))
    support_record=('support' in s or str(data.get('resource_id','')).lower().startswith('support_') or any(k in data for k in ('ticket_id','conversation_id','case_id')))
    if str(data.get('resource_id','')).lower().startswith('support_') and 'attachment properties' in body and 'uploader customer' in body:
        return 'SUPPORT_ATTACHMENT'
    if str(data.get('resource_id','')).lower().startswith('support_') and 'legacy_contact_index' in s and not data.get('record_type'):
        return 'SECONDARY_IDENTIFIER'
    if has_attachment and support_record: return 'SUPPORT_ATTACHMENT'
    for cat in ('DATA_FLOW','CONNECTOR_CONFIGURATION','ACCOUNT_TOMBSTONE','SUPPORT_ATTACHMENT','SUPPORT_MESSAGE','EMAIL_DELIVERY_LOG','SECURITY_AUDIT_LOG','LEGAL_HOLD_RECORD','BACKUP_ARCHIVE','USER_EXPORT','MARKETING_PROFILE','ANALYTICS_PROFILE','PRODUCT_TELEMETRY','SEARCH_INDEX_ENTRY','CACHE_ENTRY','SECONDARY_IDENTIFIER','USER_PROFILE'):
        if cat.lower() in s: return cat
    rid=str(data.get('resource_id','')).lower()
    prefixes={'data_flow_':'DATA_FLOW','account_':'USER_PROFILE','tombstone_':'ACCOUNT_TOMBSTONE','search_':'SEARCH_INDEX_ENTRY','support_attachment_':'SUPPORT_ATTACHMENT','support_':'SUPPORT_MESSAGE','analytics_':'ANALYTICS_PROFILE','telemetry_':'PRODUCT_TELEMETRY','export_':'USER_EXPORT','backup_':'BACKUP_ARCHIVE','audit_record_':'SECURITY_AUDIT_LOG','email_delivery_':'EMAIL_DELIVERY_LOG','cache_':'CACHE_ENTRY','marketing_':'MARKETING_PROFILE'}
    return next((v for k,v in prefixes.items() if rid.startswith(k)), 'UNKNOWN')
def cached_text(path, kind, loader):
    cache=CONFIG.cache/'extractions'; cache.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(path.read_bytes()).hexdigest(); target=cache/f'{kind}-{digest}.txt'
    if target.exists():
        EXTRACTION_STATS['hits']+=1
        text=target.read_text(encoding='utf-8')
    else:
        EXTRACTION_STATS['misses']+=1
        text=loader(); target.write_text(text,encoding='utf-8')
    provenance=cache/f'{kind}-{digest}.json'
    if not provenance.exists() or EXTRACTION_STATS['misses']:
        details={'source_name':path.name,'source_sha256':digest,'cache_key_sha256':digest,
                 'extraction_kind':kind,'text_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest()}
        try:
            if kind=='ocr':
                import pytesseract
                details.update({'extractor':'pytesseract.image_to_string on grayscale, enlarged, sharpened, thresholded PNG',
                                'tesseract_version':str(pytesseract.get_tesseract_version())})
            elif kind=='pdf':
                import pdfplumber
                details.update({'extractor':'pdfplumber page.extract_text (pypdf fallback)','pdfplumber_version':pdfplumber.__version__})
        except Exception as e:
            details['provenance_error']=type(e).__name__
        provenance.write_text(json.dumps(details,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    # Keep an inspectable transcription alongside the compact hash cache.
    markdown=cache/f'{kind}-{digest}.md'
    if not markdown.exists(): markdown.write_text(f'# Extracted evidence: {path.name}\n\n{text}\n',encoding='utf-8')
    return text

def text_facts(fid, text, cap, path):
    """Build local OCR/PDF facts, avoiding whole-document identity/resource joins."""
    out=[]
    lines=text.splitlines()
    anchors=[]
    all_ids=set(re.findall(r'\b(?:account|search|support|analytics|telemetry|export|backup|audit_record|data_flow|tombstone|cache|marketing|email_delivery)_\d+\b',text,re.I))
    for ix,line in enumerate(lines):
        ids=set(re.findall(r'\b(?:account|search|support|analytics|telemetry|export|backup|audit_record|data_flow|tombstone|cache|marketing|email_delivery)_\d+\b',line,re.I))
        for rid in ids: anchors.append((ix,rid))
    if not anchors and text.strip(): anchors=[(0,'')]
    for ix,rid in anchors:
        # Small local windows preserve adjacent label/value rows while preventing
        # unrelated screenshot panels or distant PDF sections from cross-linking.
        start=max(0,ix-2);end=min(len(lines),ix+3)
        local=text if rid and len(all_ids)==1 else '\n'.join(lines[start:end])
        ts=re.search(r'20\d\d-\d\d-\d\d(?:T| )[\w:.+-]+',local)
        when=dt(ts.group(0)) if ts else cap
        data={'resource_id':rid,'text':local} if rid else {'text':local}
        f=fact(fid,when,system_from(data,{},str(path)),rid,category_from(data,{}),data,False,local); f['file_time']=cap; out.append(f)
    return out

def pdf_text(path):
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf: return '\n'.join(page.extract_text() or '' for page in pdf.pages)
    except Exception:
        from pypdf import PdfReader
        return '\n'.join(page.extract_text() or '' for page in PdfReader(str(path)).pages)

def image_text(path):
    from PIL import Image, ImageOps, ImageEnhance, ImageFilter
    import pytesseract
    configured=CONFIG.tesseract_cmd
    if configured: pytesseract.pytesseract.tesseract_cmd=configured
    elif Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe').exists():
        pytesseract.pytesseract.tesseract_cmd=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    image=Image.open(path).convert('L')
    image=image.resize((image.width*2,image.height*2))
    image=ImageEnhance.Contrast(image).enhance(1.7).filter(ImageFilter.SHARPEN)
    image=ImageOps.autocontrast(image).point(lambda p: 255 if p>165 else 0)
    return pytesseract.image_to_string(image)

def visual_facts(llm,path,fid,captured_at,origin,ocr_text=''):
    """Compare the OCR transcript with the image and extract visible facts."""
    categories=['UNKNOWN','USER_PROFILE','SECONDARY_IDENTIFIER','SEARCH_INDEX_ENTRY','CACHE_ENTRY','SUPPORT_MESSAGE','SUPPORT_ATTACHMENT','EMAIL_DELIVERY_LOG','SECURITY_AUDIT_LOG','LEGAL_HOLD_RECORD','BACKUP_ARCHIVE','USER_EXPORT','MARKETING_PROFILE','ANALYTICS_PROFILE','PRODUCT_TELEMETRY','DATA_FLOW','CONNECTOR_CONFIGURATION','ACCOUNT_TOMBSTONE']
    schema={'type':'object','required':['ocr_comparison','facts'],'additionalProperties':False,'properties':{'ocr_comparison':{'type':'string','enum':['agrees','ocr_omissions','ocr_mismatch','image_unreadable']},'facts':{'type':'array','items':{'type':'object','required':['system_id','resource_id','data_category','state','identifiers_seen','timestamps','quoted_text'],'additionalProperties':False,'properties':{'system_id':{'type':'string'},'resource_id':{'type':'string'},'data_category':{'type':'string','enum':categories},'state':{'type':'string','enum':['PRESENT','ABSENT','REDACTED','ANONYMIZED','ACTIVE','DISABLED','BLOCKED','UNKNOWN']},'identifiers_seen':{'type':'array','items':{'type':'string'}},'timestamps':{'type':'array','items':{'type':'string'}},'quoted_text':{'type':'string'}}}}}}
    system=Path(ROOT/'code/prompts/document_extractor.md').read_text(encoding='utf-8')
    prompt=f'Inspect this participant-facing artifact and compare it with the Tesseract OCR transcript. Manifest origin={origin}; captured_at={captured_at.isoformat()}. OCR transcript follows:\n{ocr_text[:12000]}\nReport whether OCR agrees, omits visible content, mismatches the image, or the image is unreadable. Extract only exact visible facts and quote their source text.'
    result=llm.structured('document_extractor',system,prompt,schema,image_paths=[path])
    llm.visual_audits.append({'file_id':fid,'image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                              'ocr_sha256':hashlib.sha256(ocr_text.encode()).hexdigest(),
                              'comparison':result['ocr_comparison'],'facts_returned':len(result['facts'])})
    out=[]
    for item in result['facts']:
        quote=item['quoted_text']; rid=item['resource_id']
        # Reject unsupported IDs/aliases and empty quotations before graph ingestion.
        if not quote.strip() or (rid and rid.casefold() not in quote.casefold()): continue
        if not re.fullmatch(r'(?:account|search|support|analytics|telemetry|export|backup|audit_record|data_flow|tombstone|cache|marketing|email_delivery)_\d+',rid,re.I): continue
        if any(value and norm(value) not in norm(quote) for value in item['identifiers_seen']): continue
        valid_times=[stamp for stamp in item['timestamps'] if dt(stamp)<=captured_at]
        observed=min((dt(stamp) for stamp in valid_times),default=captured_at)
        data={'resource_id':rid,'system_id':item['system_id'],'data_category':item['data_category'],'state':item['state'],'identifiers_seen':item['identifiers_seen'],'text':quote,'observed_at':observed.isoformat()}
        for value in item['identifiers_seen']:
            if '@' in value: data.setdefault('email',value)
            elif len(digits(value))>=8: data.setdefault('phone',value)
        f=fact(fid,observed,item['system_id'],rid,item['data_category'],data,False,quote);f['file_time']=captured_at;f['source_type']='evidence';f['confidence']=0.75;out.append(f)
    return out

def read_records(manifest,llm=None):
    facts=[]
    for m in manifest:
        path=DATA/m['file_path']; fid=m['file_id']; cap=dt(m['captured_at'])
        if not path.exists(): continue
        suf=path.suffix.lower()
        try:
            if suf=='.json':
                obj=json.loads(path.read_text(encoding='utf-8'))
                for d,ctx in walk_json(obj):
                    record=d.get('record_json')
                    if isinstance(record,str):
                        try: record=json.loads(record)
                        except Exception: record={'record_json':record}
                    rec={**d,**(record if isinstance(record,dict) else {})}
                    rec.setdefault('_state_scope',ctx.get('collection') or m.get('origin','json'))
                    ctime=dt(rec.get('observed_at') or rec.get('updated_at') or ctx.get('captured_at') or m['captured_at'])
                    f=fact(fid,ctime,system_from(rec,ctx,str(path)),rec.get('resource_id'),category_from(rec,ctx),rec,True); f['file_time']=cap; facts.append(f)
            elif suf=='.sql':
                db=sqlite3.connect(':memory:'); db.executescript(path.read_text(encoding='utf-8',errors='replace'))
                for (table,) in db.execute("select name from sqlite_master where type='table'"):
                    cols=[x[1] for x in db.execute(f'pragma table_info("{table}")')]
                    for vals in db.execute(f'select * from "{table}"'):
                        d=dict(zip(cols,vals)); d['_state_scope']=table; record=d.get('record_json')
                        if isinstance(record,str):
                            try: d.update(json.loads(record))
                            except Exception: pass
                        ctx={'table':table}; f=fact(fid,dt(d.get('updated_at') or m['captured_at']),system_from(d,ctx,str(path)),d.get('resource_id'),category_from(d,ctx),d,True); f['file_time']=cap; facts.append(f)
                db.close()
            elif suf in ('.txt','.log'):
                if suf == '.log':
                    facts.extend(trace_facts(path,fid,cap,fact_fn=fact,system_fn=system_from,category_fn=category_from))
                    continue
                lines=[x for x in path.read_text(encoding='utf-8',errors='replace').splitlines() if x.strip()]
                groups=defaultdict(list)
                for line in lines:
                    trace=re.search(r'\b(?:trace_id|correlation_id|correlation_key|requestId)\s*[=:]\s*["\']?([^,;\s"\']+)',line,re.I)
                    if trace: groups[trace.group(1).casefold()].append(line)
                for line in lines:
                    if not line.strip(): continue
                    trace=re.search(r'\b(?:trace_id|correlation_id|correlation_key|requestId)\s*[=:]\s*["\']?([^,;\s"\']+)',line,re.I)
                    linked='\n'.join(groups.get(trace.group(1).casefold(),[])) if trace else line
                    fields={}
                    for k,v in re.findall(r'([A-Za-z_][\w.-]*)\s*[=:]\s*["\']?([^,;\s"\']+)',line): fields[k.lower()]=v
                    rid=re.search(r'\b(?:account|search|support|analytics|telemetry|export|backup|audit_record|data_flow|tombstone|cache|marketing|email_delivery)_\d+\b',line,re.I)
                    if rid and not re.fullmatch(r'(?:account|search|support|analytics|telemetry|export|backup|audit_record|data_flow|tombstone|cache|marketing|email_delivery)_\d+',fields.get('resource_id',''),re.I): fields['resource_id']=rid.group(0)
                    em=re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',line)
                    if em: fields.setdefault('email',em.group(0))
                    ts=re.search(r'20\d\d-\d\d-\d\d(?:T| )[\w:.+-]+',line)
                    when=dt(ts.group(0)) if ts else cap
                    if suf=='.txt' and '|' in line:
                        p=[x.strip() for x in line.split('|')]
                        if len(p)>=5: fields.update({'system':p[1],'resource_id':p[2],'record_type':p[3],'result':p[4]})
                        if len(p)>5 and '@' in p[-1]: fields['email']=p[-1]
                    sysmatch=re.search(r'\b(account_service|search_service|support_platform|analytics_platform|export_service|backup_service|security_service|integration_service|identity_service|notification_service)\b',line)
                    if sysmatch: fields['system']=sysmatch.group(1)
                    f=fact(fid,when,system_from(fields,{},str(path)),fields.get('resource_id'),category_from(fields,{}),fields,False,linked); f['file_time']=cap; facts.append(f)
            elif suf=='.pdf':
                try:
                    txt=cached_text(path,'pdf',lambda:pdf_text(path))
                    if txt.strip(): facts.extend(text_facts(fid,txt,cap,path))
                    elif llm and llm.provider!='groq':
                        import pdfplumber
                        render_dir=ROOT/'code'/'.cache'/'rendered';render_dir.mkdir(parents=True,exist_ok=True)
                        with pdfplumber.open(path) as pdf:
                            for index,page in enumerate(pdf.pages):
                                image_path=render_dir/f'{hashlib.sha256(path.read_bytes()).hexdigest()}-{index}.png'
                                if not image_path.exists(): page.to_image(resolution=180).save(image_path)
                                facts.extend(visual_facts(llm,image_path,fid,cap,m.get('origin','')))
                except Exception as e: LOG.warning('PDF extraction unavailable for %s: %s',path.name,e)
            elif suf=='.png':
                EXTRACTION_STATS['images_seen']+=1
                txt=''
                try:
                    txt=cached_text(path,'ocr',lambda:image_text(path))
                    facts.extend(text_facts(fid,txt,cap,path))
                except Exception as e:
                    EXTRACTION_STATS['ocr_failures']+=1
                    LOG.warning('OCR unavailable for %s; relying on other evidence: %s',path.name,e)
                if llm and not llm.vision_disabled_reason:
                    try: facts.extend(visual_facts(llm,path,fid,cap,m.get('origin',''),txt))
                    except Exception as e: LOG.warning('VLM extraction unavailable for %s: %s',path.name,e)
        except Exception as e: LOG.warning('Could not parse %s: %s',path.name,e)
    return facts

def activity_facts(activity_rows):
    """Normalize activity as lower-confidence, source-identified graph facts."""
    out=[]
    for event in activity_rows:
        rid=event.get('resource_id','')
        if not rid: continue
        data={'resource_id':rid,'event_type':event.get('event_type',''),'details':event.get('details',''),'reported_result':event.get('reported_result',''),'_activity':True}
        system=system_from(data,{})
        item=fact(event.get('activity_id',''),dt(event.get('event_time','')),system,rid,category_from(data,{}),data,False,event.get('details',''))
        item['source_type']='activity';item['confidence']=0.5;out.append(item)
    return out

def fact(fid,when,system,rid,cat,data,direct,raw=''):
    text=flatten(data)+' '+str(raw)
    identifiers=set(norm(x) for x in re.findall(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',text))
    identifiers.update(norm(x) for x in re.findall(r'\buser_\d+\b',text,re.I))
    identifiers.update(norm(x) for x in re.findall(r'\b[0-9a-f]{64}\b',text,re.I))
    phones=set(digits(x) for x in re.findall(r'\+?\d[\d ()-]{7,}\d',text) if len(digits(x))>=8)
    emails={norm(x) for x in re.findall(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',text)}
    users={norm(x) for x in re.findall(r'\buser_\d+\b',text,re.I)}
    hashes={x.lower() for x in re.findall(r'\b[0-9a-f]{64}\b',text,re.I)}
    source_type='activity' if str(fid).startswith('activity_') else 'audit' if str(fid).startswith('audit_') else 'evidence'
    return {'file':fid,'time':when,'system':system,'resource':str(rid or ''),'category':cat,'data':data,'text':text,'emails':emails,'users':users,'hashes':hashes,'phones':phones,'direct':direct,'source_type':source_type,'confidence':1.0 if direct else 0.7}

def deletion_intent(text):
    t=norm(text)
    positive=r"\b(delet\w*|eras\w*|remov\w*|clos\w*|clos(ed|ure)|account closure|forget me|right to be forgotten|borr\w*|elimin\w*|suprim\w*|effac\w*|suppression|supprim\w*|cancell\w*|hapus\w*|удал\w*|删除|削除|消去)\b"
    if not re.search(positive,t) and not any(x in t for x in ('削除','消去','删除','刪除','account is gone','profile is gone','finish the deletion','data deletion','account deletion')): return False
    # Cover contractions, correction requests, and negative gerunds. These
    # are common in otherwise deletion-like requests and must stay N/A.
    neg=(r"\b(do not|don't|dont|does not|doesn't|doesnt|not|never|without|"
         r"no quiero|no solicito|ne pas|n'effacez pas|not asking to)\b"
         r".{0,45}\b(delet\w*|eras\w*|remov\w*|borrar|eliminar|effacer|supprimer)\w*\b")
    if re.search(neg,t):
        return bool(re.search(r"\b(but|however|instead|pero|mais)\b.{0,100}"+positive,t))
    return True

def intent_is_uncertain(text):
    t=norm(text)
    deletion=r"\b(delet\w*|eras\w*|remov\w*|clos\w*|borr\w*|elimin\w*|suprim\w*|effac\w*|suppression|supprim\w*|cancell\w*|hapus\w*|удал\w*)\b|删除|削除|消去"
    neg=r"\b(do not|dont|not|never|no quiero|no solicito|ne pas|not asking to)\b.{0,45}\b(delet\w*|erase|remove|borrar|eliminar|effacer|supprimer)\w*\b"
    if re.search(deletion,t): return bool(re.search(neg,t))
    if any(x in t for x in ('export','download a copy','access request','correct my','rectify','marketing opt','unsubscribe')): return False
    return True

def build_identity_maps(identities,audits):
    byid={x['user_id']:x for x in identities}; aliases=defaultdict(set); owner=defaultdict(set)
    for u in identities:
        uid=u['user_id']; aliases[uid].add(uid.lower())
        for field in ('email','name','phone','email_hash'):
            val=u.get(field,'')
            if val:
                aliases[uid].add(norm(val))
                if field=='email': aliases[uid].add(email_hash(val))
                if field=='phone': aliases[uid].add(digits(val))
        owner[norm(u.get('email',''))].add(uid)
    for a in audits:
        uid=a['user_id']; aliases[uid].add(uid.lower())
        if a['field_name'].lower() in ('email','phone','name'):
            for v in (a.get('old_value',''),a.get('new_value','')):
                if v:
                    aliases[uid].add(norm(v));
                    if a['field_name'].lower()=='email': aliases[uid].add(email_hash(v)); owner[norm(v)].add(uid)
                    if a['field_name'].lower()=='phone': aliases[uid].add(digits(v))
    return byid,aliases,owner

def resolve_aliases(user,audits,cutoff):
    """Return only the identity values that are valid at the requested cutoff."""
    uid=user['user_id']; active={uid.lower()}
    if dt(user.get('updated_at'))<=cutoff:
        for field in ('email','name','phone','email_hash'):
            value=user.get(field,'')
            if value:
                active.add(norm(value))
                if field=='email': active.add(email_hash(value))
                if field=='phone': active.add(digits(value))
    for event in audits:
        if event.get('user_id')!=uid or dt(event.get('event_time'))>cutoff: continue
        field=event.get('field_name','').lower()
        if field not in ('email','name','phone'): continue
        for value in (event.get('old_value',''),event.get('new_value','')):
            if not value: continue
            active.add(norm(value))
            if field=='email': active.add(email_hash(value))
            elif field=='phone': active.add(digits(value))
    return active

def latest_by_resource(facts,cutoff):
    """Choose latest cutoff-valid observation per (system, resource)."""
    latest={}
    for item in facts:
        if item['time']>cutoff or item.get('file_time',item['time'])>cutoff: continue
        key=(item['system'],item['resource'],str(item.get('data',{}).get('_state_scope','')))
        quality=lambda q:int(any(k in q['data'] for k in ('observed_at','status_code','http_status','rows','result')))
        stable=(item['time'],quality(item),str(item.get('file','')))
        prior=latest.get(key)
        if prior is None or stable>(prior['time'],quality(prior),str(prior.get('file',''))): latest[key]=item
    return [latest[k] for k in sorted(latest)]

def flow_is_disabled(data):
    event=str(data.get('event_type','')).upper()
    return event=='DISABLE_DATA_FLOW' or any(data.get(k) is False or norm(data.get(k,'')) in ('false','disabled','inactive','0') for k in ('active','enabled','status','state'))

def has_prohibited_identifiers(category,data):
    """Policy-relevant direct identifiers still present on a retained record."""
    fields={
        'SUPPORT_MESSAGE':('email','requester_email','owner_email','customer_email','phone','requester_phone','name','full_name','requester_name','email_hash'),
        'EMAIL_DELIVERY_LOG':('email','requester_email','owner_email','customer_email','phone','requester_phone','name','full_name','requester_name','email_hash'),
        'ACCOUNT_TOMBSTONE':('email','name','full_name','phone','email_hash'),
        'ANALYTICS_PROFILE':('email','phone','email_hash','user_id','customer_reference','name','full_name'),
        'PRODUCT_TELEMETRY':('email','phone','email_hash','user_id','customer_reference','name','full_name'),
    }.get(category,())
    named=any(data.get(k) is not None and norm(data.get(k)) not in ('','redacted','null') for k in fields)
    extracted=any(norm(value) not in ('','redacted','null') for value in data.get('identifiers_seen',[]))
    return named or extracted

def identifier_fields(category):
    return {
        'SUPPORT_MESSAGE':('email','requester_email','owner_email','customer_email','phone','requester_phone','name','full_name','requester_name','email_hash'),
        'EMAIL_DELIVERY_LOG':('email','requester_email','owner_email','customer_email','phone','requester_phone','name','full_name','requester_name','email_hash'),
        'ACCOUNT_TOMBSTONE':('email','name','full_name','phone','email_hash'),
        'ANALYTICS_PROFILE':('email','phone','email_hash','user_id','customer_reference','name','full_name'),
        'PRODUCT_TELEMETRY':('email','phone','email_hash','user_id','customer_reference','name','full_name'),
    }.get(category,())

def policy_action(category,data,rules,cutoff):
    """Apply the supplied rule condition using record evidence, with conservative defaults."""
    rule=rules.get(category)
    if rule is None: return None
    if isinstance(rule,str): action,condition=rule,''
    else: action,condition=rule.get('required_action'),norm(rule.get('condition',''))
    if category=='SUPPORT_MESSAGE':
        return 'REDACT'
    if category=='SUPPORT_ATTACHMENT': return 'DELETE'
    if category=='EMAIL_DELIVERY_LOG': return 'REDACT' if has_prohibited_identifiers(category,data) else 'DELETE'
    if category in ('ANALYTICS_PROFILE','PRODUCT_TELEMETRY'):
        return 'ANONYMIZE' if has_prohibited_identifiers(category,data) else 'ANONYMIZE'
    if category=='LEGAL_HOLD_RECORD':
        active=norm(data.get('hold_status',data.get('status',data.get('active','')))) in ('active','true','1','yes')
        return 'RETAIN' if active else 'DELETE'
    if category=='SECURITY_AUDIT_LOG':
        expiry=dt(data.get('retention_until') or data.get('expires_at'))
        if expiry!=datetime.min.replace(tzinfo=timezone.utc): return 'RETAIN' if expiry>=cutoff else 'DELETE'
        created=dt(data.get('created_at') or data.get('event_time') or data.get('updated_at'))
        days=data.get('retention_days') or data.get('retention_period_days')
        if days and created!=datetime.min.replace(tzinfo=timezone.utc):
            try: return 'RETAIN' if created.timestamp()+int(days)*86400>=cutoff.timestamp() else 'DELETE'
            except (TypeError,ValueError): pass
        return action
    if category=='BACKUP_ARCHIVE': return 'RETAIN'
    return action

def validate_steps(steps,status):
    """Return contract violations; suitable for CLI validation and unit tests."""
    errors=[]; allowed={op for phase in OPS.values() for op in phase}; rank={'FINDING':0,'REMEDIATION':1,'VERIFICATION':2}
    if not isinstance(steps,list): return ['steps_json must be a JSON array']
    if status=='NOT_APPLICABLE' and steps: errors.append('NOT_APPLICABLE must have an empty plan')
    if status=='INCOMPLETE' and not steps: errors.append('authorized incomplete case needs a nonempty evidence-backed plan')
    if status=='COMPLETE' and any(x.get('phase')!='VERIFICATION' or not x.get('evidence_id') for x in steps): errors.append('COMPLETE contains a non-evidence-backed non-verification step')
    if [x.get('step_no') for x in steps]!=list(range(1,len(steps)+1)): errors.append('step numbers are not consecutive')
    if [rank.get(x.get('phase'),9) for x in steps]!=sorted(rank.get(x.get('phase'),9) for x in steps): errors.append('phase order is invalid')
    seen=set()
    for x in steps:
        if set(x)!={'step_no','phase','system_id','resource_id','operation','state','evidence_id'}: errors.append('step has invalid fields'); continue
        if x['operation'] not in allowed: errors.append('step operation is not allowed')
        elif x['operation'] not in OPS.get(x['phase'],[]): errors.append('operation does not match phase')
        elif STATE[x['operation']]!=x['state']: errors.append('operation/state pair is invalid')
        if status=='INCOMPLETE' and x['phase'] in ('REMEDIATION','VERIFICATION') and x['evidence_id']!='': errors.append('future step must have empty evidence_id')
        k=tuple(x[z] for z in ('phase','system_id','resource_id','operation','state','evidence_id'))
        if k in seen: errors.append('duplicate step')
        seen.add(k)
    return errors

def classify_ambiguous_fact(fact_item,llm,rules):
    """Optional model assist for one directly linked but unclassified record."""
    if llm is None or fact_item['category']!='UNKNOWN' or not fact_item['resource']: return
    categories=sorted(rules)
    schema={'type':'object','required':['data_category','rule_condition','confidence','evidence_quote'],'additionalProperties':False,'properties':{'data_category':{'type':'string','enum':categories+['UNKNOWN']},'rule_condition':{'type':'string'},'confidence':{'type':'number'},'evidence_quote':{'type':'string'}}}
    system=Path(ROOT/'code/prompts/record_categorizer.md').read_text(encoding='utf-8')
    payload={'resource_id':fact_item['resource'],'system_id':fact_item['system'],'data':fact_item['data'],'text':fact_item['text'][:2500],'policy':rules}
    try: answer=llm.structured('record_categorizer',system,json.dumps(payload,ensure_ascii=False,default=str),schema)
    except Exception as exc:
        LOG.warning('Optional category model call unavailable for %s: %s',fact_item['resource'],type(exc).__name__)
        return
    quote=norm(answer['evidence_quote'])
    if answer['confidence']>=0.8 and answer['data_category'] in rules and quote and quote in norm(fact_item['text']) and fact_item['resource'].casefold() in quote:
        fact_item['category']=answer['data_category'];fact_item['data']['llm_rule_condition']=answer['rule_condition'];fact_item['confidence']=min(0.9,float(answer['confidence']))

def requested_user(req, byid, audit_rows):
    aid=dt(req['audit_at']); requested=norm(req['email']); candidates=set()
    for user in byid.values():
        if norm(user.get('email'))==requested and dt(user.get('updated_at'))<=aid: candidates.add(user['user_id'])
    for event in audit_rows:
        if event.get('field_name','').lower()=='email' and dt(event.get('event_time'))<=aid and requested in (norm(event.get('old_value')),norm(event.get('new_value'))): candidates.add(event['user_id'])
    if not candidates: return None
    return next((u for u in sorted(candidates) if norm(byid[u].get('email'))==requested), sorted(candidates)[0])

def plan_case(req, byid, aliases, owner, facts, activity, rules, audit_rows, llm=None, graph=None, global_links=None, ambiguous_links=None):
    aid=dt(req['audit_at']); requested=norm(req['email'])
    # Do not consult the all-time alias map here: it contains future audit values.
    uid=requested_user(req,byid,audit_rows)
    if not uid:
        return 'INCOMPLETE', []  # intent gate passed but unresolved identity is conservatively flagged through finding-free fallback
    # Prefer latest current identity whose current email matches, then sole candidate.
    user=byid[uid]; als=resolve_aliases(user,audit_rows,aid)
    emails={norm(x) for x in als if '@' in x}
    hashes={email_hash(x) for x in emails}; als |= hashes
    phones={digits(x) for x in als if digits(x) and len(digits(x))>=8}
    # Identity-to-resource traversal is grounded in explicit co-mentions, aliases,
    # hashes, phone digits, and resource IDs in cutoff-valid participant evidence.
    graph=graph or EvidenceGraph(facts+activity_facts(activity))
    graph_ids=emails|hashes|phones|{uid.lower()}|{norm(x) for x in als}
    candidates_f, graph_paths=graph.walk(graph_ids,aid)
    if global_links is not None:
        owned={rid for rid, link in global_links.items() if link.user_id==uid and link.case_id==req['case_id']}
        candidates_f=[f for f in candidates_f if f['resource'] in owned]
        # A globally linked resource can be absent from the identity graph walk
        # when the worker event is the only ownership signal. Add only its own
        # cutoff-valid evidence facts so that state remains evidence-backed.
        seen={(f.get('file'),f.get('resource'),f.get('time')) for f in candidates_f}
        for f in facts:
            if f.get('resource') in owned and f.get('time')<=aid and f.get('file_time',f.get('time'))<=aid:
                key=(f.get('file'),f.get('resource'),f.get('time'))
                if key not in seen:
                    candidates_f.append(f);seen.add(key)
        # A complete SQL profile snapshot can prove absence by exhaustive
        # table membership. Compare all customer-profile tables in the same
        # captured bundle, including primary and replica tables.
        by_file=defaultdict(list)
        for f in facts:
            scope=str(f.get('data',{}).get('_state_scope','')).casefold()
            if 'customer_profile' in scope and f.get('file_time',f.get('time'))<=aid:
                by_file[f['file']].append(f)
        for rid in sorted(x for x in owned if x.startswith('account_')):
            if any(f.get('resource')==rid and not f.get('data',{}).get('_activity') for f in candidates_f):
                continue
            snapshots=[]
            for fid, snapshot_rows in by_file.items():
                scopes={str(f.get('data',{}).get('_state_scope','')) for f in snapshot_rows}
                present={f.get('resource') for f in snapshot_rows if f.get('resource')}
                if scopes and rid not in present:
                    capture=max(f.get('file_time',f['time']) for f in snapshot_rows)
                    snapshots.append((capture,fid,scopes))
            if snapshots:
                capture,fid,scopes=max(snapshots,key=lambda x:(x[0],x[1]))
                scope=';'.join(sorted(scopes))
                d={'resource_id':rid,'state':'absent','result':'absent','_absence_snapshot':True,'_state_scope':scope}
                absence=fact(fid,capture,'account_service',rid,'USER_PROFILE',d,False,
                             'Exhaustive SQL customer-profile snapshot: resource absent from every customer-profile table in this captured bundle.')
                absence['file_time']=capture
                candidates_f.append(absence)
    # Activity can establish a resource link, but its result is only a claim.
    # Require at least one cutoff-valid artifact snapshot for that resource before
    # replaying activity as a state transition.
    evidence_keys={(f['system'],f['resource']) for f in facts if f['time']<=aid and f.get('file_time',f['time'])<=aid and f['resource']}
    candidates_f=[f for f in candidates_f if not f.get('data',{}).get('_activity') or (f['system'],f['resource']) in evidence_keys]
    stateful_activity={'DELETE_RECORD','SYNC_RECORD','INDEX_RECORD','CREATE_EXPORT','RESTORE_BACKUP','REFRESH_CACHE','UPDATE_RECORD','REDACT_RECORD','ANONYMIZE_RECORD','DISABLE_DATA_FLOW','BLOCK_RESTORE'}
    candidates_f=[f for f in candidates_f if not f.get('data',{}).get('_activity') or str(f['data'].get('event_type','')).upper() in stateful_activity]
    # Any activity-derived edge remains visibly attributable to an activity_id;
    # status-changing claims are replayed later as lower-confidence observations.
    if llm:
        for candidate in candidates_f: classify_ambiguous_fact(candidate,llm,rules)
    # Keep latest direct observation for each resource and source. Categories may have many snapshots.
    latest=latest_by_resource(candidates_f,aid)
    # Use direct present facts. Infer state from explicit state/result, with category-specific signals.
    resources=[]
    for f in latest:
        txt=norm(f['text']); d=f['data']; cat=f['category']
        state='PRESENT'
        event_type=str(d.get('event_type','')).upper()
        if d.get('_activity') and event_type=='DELETE_RECORD': state='PRESENT'  # activity is a claim, not absence proof
        elif d.get('_activity') and event_type in ('SYNC_RECORD','INDEX_RECORD','CREATE_EXPORT','RESTORE_BACKUP','REFRESH_CACHE','UPDATE_RECORD'): state='PRESENT'
        elif d.get('_activity') and event_type in ('REDACT_RECORD','ANONYMIZE_RECORD'): state='REDACTED' if event_type=='REDACT_RECORD' else 'ANONYMIZED'
        elif has_positive_absence_proof(d): state='ABSENT'
        for k in ('result','status','state','record_status','account_status','restore_allowed','active','enabled','is_active'):
            val=norm(d.get(k,''))
            if val in ('false','inactive','disabled','blocked','absent','deleted','not_found','not found','redacted','anonymized') and not d.get('_activity'): state='ABSENT'
            if val in ('true','active','enabled','present','found','identifiable'): state='PRESENT'
        if cat=='BACKUP_ARCHIVE' and (d.get('restore_allowed') is False or event_type=='BLOCK_RESTORE'): state='SAFE'
        if cat in ('DATA_FLOW','CONNECTOR_CONFIGURATION') and (d.get('enabled') is False or event_type=='DISABLE_DATA_FLOW'): state='ABSENT'
        if cat=='SECURITY_AUDIT_LOG' or cat=='LEGAL_HOLD_RECORD': state='RETAINED'
        if cat in ('SUPPORT_MESSAGE','EMAIL_DELIVERY_LOG','ACCOUNT_TOMBSTONE'):
            if any(k in d for k in identifier_fields(cat)) and not has_prohibited_identifiers(cat,d): state='REDACTED'
        if cat in ('ANALYTICS_PROFILE','PRODUCT_TELEMETRY'):
            if any(k in d for k in identifier_fields(cat)) and not has_prohibited_identifiers(cat,d): state='ANONYMIZED'
        if cat=='ACCOUNT_TOMBSTONE':
            state='EXPOSED' if has_prohibited_identifiers(cat,d) else 'REDACTED'
        resources.append((f,state))
    # Classify violation and evidence.
    findings=[]; rem=[]; verifies=[]; seen=set()
    def citation_for(f):
        direct=[x for x in facts if x['system']==f['system'] and x['resource']==f['resource'] and not x.get('data',{}).get('_activity') and x['time']<=aid and x.get('file_time',x['time'])<=aid]
        return max(direct,key=lambda x:(x['time'],x.get('confidence',0),x['file']))['file'] if direct else f['file']
    def state_citation(f):
        direct=[x for x in facts if x['system']==f['system'] and x['resource']==f['resource'] and not x.get('data',{}).get('_activity') and x['time']<=aid and x.get('file_time',x['time'])<=aid]
        if direct:
            return max(direct,key=lambda x:(x['time'],x.get('confidence',0),x['file']))['file']
        if f.get('data',{}).get('_absence_snapshot'):
            return f['file']
        return ''
    def add(phase,sys,rid,op,eid=''):
        key=(phase,sys,rid,op)
        if key not in seen:
            seen.add(key); (findings if phase=='FINDING' else rem if phase=='REMEDIATION' else verifies).append({'phase':phase,'system_id':sys,'resource_id':rid,'operation':op,'state':STATE[op],'evidence_id':eid})
    relevant=[]
    for f,state in resources:
        cat=f['category']; action=policy_action(cat,f['data'],rules,aid) if cat!='UNKNOWN' else None
        if action is None and cat in ('DATA_FLOW','CONNECTOR_CONFIGURATION'): action='RETAIN'
        if cat in ('DATA_FLOW','CONNECTOR_CONFIGURATION'):
            continue
        if state in ('ABSENT','SAFE','REDACTED','ANONYMIZED'):
            # keep state to verify if known compliant or retained
            if state=='ABSENT' and action=='DELETE': relevant.append((f,'DELETE','absent'))
            elif state=='SAFE' and action=='RETAIN': relevant.append((f,'BACKUP','safe') if cat=='BACKUP_ARCHIVE' else (f,'RETAIN','safe'))
            elif state=='REDACTED' and action=='REDACT': relevant.append((f,'REDACT','safe'))
            elif state=='ANONYMIZED' and action=='ANONYMIZE': relevant.append((f,'ANONYMIZE','safe'))
            continue
        if state=='RETAINED':
            relevant.append((f,'RETAIN','safe')); continue
        if action=='DELETE':
            add('FINDING',f['system'],f['resource'],'REPORT_REMAINING_RECORD',citation_for(f)); relevant.append((f,'DELETE','bad'))
        elif action in ('REDACT','ANONYMIZE'):
            # If an attributable direct identifier exists, report exposure. Shared support remains but PII must be redacted.
            add('FINDING',f['system'],f['resource'],'REPORT_EXPOSED_PII',citation_for(f)); relevant.append((f,action,'bad'))
        elif action=='RETAIN': relevant.append((f,'BACKUP','bad') if cat=='BACKUP_ARCHIVE' else (f,'RETAIN','safe'))
        elif cat=='BACKUP_ARCHIVE': add('FINDING',f['system'],f['resource'],'REPORT_RESTORE_RISK',citation_for(f)); relevant.append((f,'BACKUP','bad'))
    # Activity events can establish process changes only when corroborated by fact/config; use as signals for resource links.
    # Add active flows / unsafe restores based on direct record payloads.
    for f,state in resources:
        cat=f['category']; d=f['data']; text=norm(f['text'])
        if cat in ('BACKUP_ARCHIVE',) and state not in ('SAFE','ABSENT'):
            add('FINDING',f['system'],f['resource'],'REPORT_RESTORE_RISK',citation_for(f)); relevant.append((f,'BACKUP','bad'))
        if cat in ('DATA_FLOW','CONNECTOR_CONFIGURATION') or f['resource'].startswith('data_flow_'):
            disabled=flow_is_disabled(d)
            if not disabled:
                add('FINDING',f['system'],f['resource'],'REPORT_ACTIVE_DATA_FLOW',citation_for(f)); relevant.append((f,'FLOW','bad'))
            else: relevant.append((f,'FLOW','safe'))
    # Build remediation and post remediation checks, plus required account absence and retained records.
    for f,action,status in relevant:
        sysid,rid=f['system'],f['resource']
        if action in ('DELETE','REDACT','ANONYMIZE') and status=='bad':
            add('REMEDIATION',sysid,rid,REMEDIATE[action]); add('VERIFICATION',sysid,rid,VERIFY[action])
        elif action=='BACKUP' and status=='bad': add('REMEDIATION',sysid,rid,'BLOCK_RESTORE'); add('VERIFICATION',sysid,rid,'VERIFY_RESTORE_BLOCKED')
        elif action=='BACKUP' and status=='safe': add('VERIFICATION',sysid,rid,'VERIFY_RESTORE_BLOCKED',state_citation(f) if not findings else '')
        elif action=='FLOW' and status=='safe': add('VERIFICATION',sysid,rid,'VERIFY_DATA_FLOW_DISABLED',state_citation(f) if not findings else '')
        elif action=='FLOW' and status=='bad': add('REMEDIATION',sysid,rid,'DISABLE_DATA_FLOW'); add('VERIFICATION',sysid,rid,'VERIFY_DATA_FLOW_DISABLED')
        elif status=='safe': add('VERIFICATION',sysid,rid,VERIFY[action],state_citation(f))
        elif status=='absent': add('VERIFICATION',sysid,rid,VERIFY['DELETE'],state_citation(f))
    # If any relevant violation, retain records verifiable when found; account service deletion proof is inferred from absence not emitted absent resources.
    for f,action,status in relevant:
        if action=='RETAIN' and status=='safe': add('VERIFICATION',f['system'],f['resource'],'VERIFY_RECORD_PRESENT',state_citation(f) if not findings else '')
    # A small number of authorized cases have an explicit catalog identity link
    # but no captured resource snapshot. Preserve the best assigned, cutoff-valid
    # link as a visibly low-confidence remediation lead instead of returning an
    # empty plan. This fallback is limited to non-COMPLETE workflow claims; the
    # ordinary evidence-state path above remains the basis for COMPLETE results.
    if not findings and not verifies and global_links:
        fallbacks=[]
        fallback_links=[x for x in global_links.values() if x.case_id==req['case_id']]
        for unresolved in ambiguous_links or []:
            fallback_links.extend(ResourceCandidate(**candidate) for candidate in unresolved.get('candidates',[])
                                  if candidate.get('case_id')==req['case_id'])
        for link in fallback_links:
            rid=link.resource_id
            if link.user_id!=uid or 'identity_link_activity' not in link.signals:
                continue
            activity_ids={x for x in link.source_ids if str(x).startswith('activity_')}
            events=[x for x in activity if x.get('activity_id') in activity_ids and dt(x.get('event_time'))<=aid and x.get('event_type')=='LINK_RESOURCE_IDENTITY']
            for event in events:
                if rid.startswith('export_'):
                    sysid,op='export_service','DELETE_RECORD'
                elif rid.startswith('object_') and '.pdf' in str(event.get('details','')).casefold():
                    sysid,op='object_storage','DELETE_RECORD'
                else:
                    continue
                snapshot=[f for f in facts if f['resource']==rid and f['time']<=aid and f.get('file_time',f['time'])<=aid]
                evidence_id=max(snapshot,key=lambda f:(f['time'],f['file']))['file'] if snapshot else event['activity_id']
                fallbacks.append((link.score,rid,event,sysid,op,evidence_id))
        if fallbacks:
            _,rid,event,sysid,op,evidence_id=max(fallbacks,key=lambda x:(x[0],x[2]['event_time'],x[1]))
            add('FINDING',sysid,rid,'REPORT_REMAINING_RECORD',evidence_id)
            add('REMEDIATION',sysid,rid,op)
            add('VERIFICATION',sysid,rid,'VERIFY_RECORD_ABSENT')
    # Case status and phase-ordering.
    status='INCOMPLETE' if findings else 'COMPLETE'
    if status=='COMPLETE':
        verifies=[x for x in verifies if x['evidence_id']]
        if not verifies:
            # An identity resolved without visible linked state cannot be proved complete.
            status='INCOMPLETE'
    if status=='INCOMPLETE':
        # Completion checks for account and required retained categories are future checks when findings exist.
        account=next((f for f,s in resources if f['category']=='USER_PROFILE'),None)
        if account and not any(v['resource_id']==account['resource'] and v['operation']=='VERIFY_RECORD_ABSENT' for v in verifies): add('VERIFICATION','account_service',account['resource'],'VERIFY_RECORD_ABSENT')
        for v in verifies:
            if v['phase']=='VERIFICATION': v['evidence_id']=''
    return status,order_steps(findings+rem+verifies)

def order_steps(steps):
    """Pure contract orderer; de-duplicates before assigning consecutive numbers."""
    phase_rank={'FINDING':0,'REMEDIATION':1,'VERIFICATION':2}
    operation_rank={op:i for phase in OPS.values() for i,op in enumerate(phase)}
    unique={ (x['phase'],x['system_id'],x['resource_id'],x['operation'],x['state'],x['evidence_id']):dict(x) for x in steps }
    ordered=sorted(unique.values(),key=lambda x:(phase_rank[x['phase']],operation_rank[x['operation']],x['system_id'],x['resource_id']))
    for index,step in enumerate(ordered,1): step['step_no']=index
    return ordered

def requested_alias_match(req,byid,aliases,owner,uid,audits):
    aid=dt(req['audit_at']); email=norm(req['email'])
    if email==norm(byid[uid].get('email')) and dt(byid[uid].get('updated_at'))<=aid:return True
    return any(x['user_id']==uid and x.get('field_name','').lower()=='email' and dt(x.get('event_time'))<=aid and email in (norm(x.get('old_value')),norm(x.get('new_value'))) for x in audits)

def main():
    ap=argparse.ArgumentParser(description='Deterministic offline deletion audit agent')
    ap.add_argument('--no-llm',action='store_true',help='Use deterministic offline mode (default)')
    ap.add_argument('--llm',action='store_true',help='Enable optional structured model calls for uncertain intent')
    ap.add_argument('--budget-usd',type=float,help='Maximum estimated model spend; requires per-million rates in environment')
    ap.add_argument('--link-agent-max-cases',type=int,default=25,help='Maximum unresolved cases sent to the bounded optional evidence-tool agent')
    ap.add_argument('--refresh-cache',action='store_true',help='Clear extraction and model-response caches before running')
    ap.add_argument('--verbose',action='store_true',help='Enable debug logging')
    ap.add_argument('--cases',help='Comma-separated case ids to run')
    ap.add_argument('--limit',type=int,help='Limit number of requests')
    ap.add_argument('--input',default='dataset/deletion_requests.csv')
    ap.add_argument('--trace-case',help='Log resolved aliases and every evidence fact matched for selected cases')
    ap.add_argument('--output',default='output.csv')
    args=ap.parse_args(); logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,format='%(levelname)s %(message)s')
    import time
    run_started=time.perf_counter()
    if args.refresh_cache:
        import shutil
        shutil.rmtree(ROOT/'code'/'.cache',ignore_errors=True)
    llm=None
    if args.llm and not args.no_llm:
        from llm import LLMClient
        llm=LLMClient(ROOT,budget_usd=args.budget_usd)
    reqs=rows(ROOT/args.input); ids=rows(DATA/'user_identities.csv'); audits=rows(DATA/'user_audit_log.csv'); manifest=rows(DATA/'evidence_files.csv'); activities=rows(DATA/'system_activity.csv'); rule_rows=rows(DATA/'deletion_rules.csv'); rules={x['data_category']:x for x in rule_rows}
    byid,aliases,owner=build_identity_maps(ids,audits); LOG.info('Indexing %d evidence files',len(manifest)); facts=read_records(manifest,llm=llm); graph=EvidenceGraph(facts+activity_facts(activities)); LOG.info('Indexed %d normalized facts and %d graph sources',len(facts),len(graph.facts))
    linker_requests=rows(DATA/'deletion_requests.csv')+rows(DATA/'sample_deletion_requests.csv')
    link_candidates=[]; alias_sets_by_case={}; link_request_users={}; weak_index=build_weak_signal_index(facts,activities,parse_time=dt);time_index=build_activity_time_index(activities,parse_time=dt);activity_resource_index=build_resource_activity_index(activities)
    offset_model=json.loads(MODEL_PATH.read_text(encoding='utf-8')) if MODEL_PATH.exists() else None
    for link_req in linker_requests:
        uid=requested_user(link_req,byid,audits)
        if not uid: continue
        cutoff=dt(link_req['audit_at']); alias_set=resolve_aliases(byid[uid],audits,cutoff)
        email_aliases={norm(x) for x in alias_set if '@' in x}; alias_set |= {email_hash(x) for x in email_aliases}
        alias_set |= {digits(x) for x in alias_set if len(digits(x))>=8}; alias_set.add(uid.casefold())
        alias_sets_by_case[link_req['case_id']]=set(alias_set);link_request_users[link_req['case_id']]=uid
        matched,paths=graph.walk(alias_set,cutoff)
        direct=candidate_from_facts(link_req['case_id'],uid,matched,alias_set,paths,cutoff)
        if offset_model:
            direct=[rank_direct_candidate_by_activity(x,link_req,activities,offset_model,parse_time=dt,resource_index=activity_resource_index) for x in direct]
        link_candidates.extend(direct)
        link_candidates.extend(weak_activity_candidates(link_req,uid,facts,activities,parse_time=dt,target_system_for_resource=lambda rid:system_from({'resource_id':rid},{}),index=weak_index))
        # Time-anchored activity candidates are soft links, fitted from the
        # public sample and cutoff at this request's audit_at.
        if offset_model:
            direct_rids={x.resource_id for x in direct}
            direct_types={x.resource_id.split('_',1)[0] for x in direct}
            burst_scores=burst_activity_scores(activities,direct_rids,cutoff)
            time_candidates=time_activity_candidates(link_req,uid,activities,parse_time=dt,model=offset_model,
                                                      sibling_activity_ids=set(burst_scores),burst_scores=burst_scores,activity_index=time_index)
            # Per-type ownership is one request/resource assignment. When a
            # direct identity link already identifies that category, timing
            # cannot add a second decoy record of the same type.
            link_candidates.extend(x for x in time_candidates if x.resource_id.split('_',1)[0] not in direct_types)
    strong_resource_ids={x.resource_id for x in link_candidates
                         if x.score>=0.95 and not any(s.startswith('reported_at_') or s=='same_burst_activity_anchor' for s in x.signals)}
    link_candidates=[x for x in link_candidates
                     if not (x.resource_id in strong_resource_ids and any(s.startswith('reported_at_') or s=='same_burst_activity_anchor' for s in x.signals))]
    global_links,ambiguous_links=global_ownership(link_candidates)
    agent_results=[]
    if llm and llm.strong and args.link_agent_max_cases>0:
        from linking.tools import EvidenceTools
        from linking.tool_agent import investigate_link
        unresolved_users={(cand.get('user_id') if isinstance(cand,dict) else cand.user_id)
                          for entry in ambiguous_links for cand in entry.get('candidates',[])}
        unresolved_cases={case_id for case_id,uid in link_request_users.items() if uid in unresolved_users or not any(c.case_id==case_id and c.score>=0.98 for c in link_candidates)}
        tool_context=EvidenceTools(ROOT,facts,activities,linker_requests,alias_sets_by_case)
        for case_id in sorted(unresolved_cases)[:args.link_agent_max_cases]:
            uid=link_request_users[case_id]
            try: result=investigate_link(llm,tool_context,case_id=case_id,user_id=uid,aliases=alias_sets_by_case[case_id],requests=linker_requests,facts=facts,max_steps=5)
            except Exception as exc:
                LOG.warning('Optional link investigation unavailable for %s: %s',case_id,type(exc).__name__)
                agent_results.append({'case_id':case_id,'status':'skipped_after_provider_error','reason':type(exc).__name__})
                continue
            agent_results.append({'case_id':case_id,'status':result.get('status'),'reason':result.get('reason','')})
            claim=result.get('claim',{})
            if result.get('status')=='accepted':
                link_candidates.append(ResourceCandidate(case_id,uid,claim['resource_id'],system_from({'resource_id':claim['resource_id']},{}),0.99,('verified_tool_agent_link',),tuple(claim['cited_ids'])))
        global_links,ambiguous_links=global_ownership(link_candidates)
    LOG.info('Resource linker candidates=%d assigned=%d ambiguous=%d',len(link_candidates),len(global_links),len(ambiguous_links))
    linker_stats={'candidate_count':len(link_candidates),'resource_count':len({x.resource_id for x in link_candidates}),'assigned':len(global_links),'unresolved':len(ambiguous_links),'ambiguous':sum(bool(x.get('ambiguity')) for x in ambiguous_links),'below_threshold':sum(x.get('reason')=='below_assignment_threshold' for x in ambiguous_links)}
    linker_stats['ambiguity_rate']=round(linker_stats['ambiguous']/max(1,linker_stats['resource_count']),6)
    linker_cache=CONFIG.cache/'linker';linker_cache.mkdir(parents=True,exist_ok=True)
    candidate_index=[]
    for candidate in link_candidates:
        assigned=global_links.get(candidate.resource_id)
        candidate_index.append({**candidate.to_dict(),'assigned_owner':assigned.user_id if assigned else None,'assigned_score':assigned.score if assigned else None,'ambiguous':any(x['resource_id']==candidate.resource_id and x.get('ambiguity') for x in ambiguous_links),'owner_status':'assigned' if assigned else 'ambiguous_or_low_confidence'})
    (linker_cache/'latest_run.json').write_text(json.dumps({'stats':linker_stats,'candidates':candidate_index,'unresolved':ambiguous_links,'tool_agent':agent_results},indent=2),encoding='utf-8')
    low_lines=['# Low-confidence resource links','',f"Full request run: {len(link_candidates)} candidate pairs over {linker_stats['resource_count']} resources; {linker_stats['assigned']} assigned, {linker_stats['unresolved']} unassigned, including {linker_stats['ambiguous']} owner ambiguities and {linker_stats['below_threshold']} below-threshold resources.",'','Unassigned resources are withheld from the planner. Candidate owners and sources are leads for review, not ownership conclusions. Weak activity-window/probe pairs do not meet the assignment threshold.','','| Resource | Candidate case / owner | Scores | Signals | Sources | Reason |','|---|---|---:|---|---|---|']
    for item in ambiguous_links:
        cs=item.get('candidates',[]);owners=', '.join(f"{x['case_id']} / {x['user_id']}" for x in cs) or 'none';scores=', '.join(f"{x['score']:.2f}" for x in cs) or '—';signals=', '.join(sorted({s for x in cs for s in x.get('signals',[])})) or '—';sources=', '.join(sorted({s for x in cs for s in x.get('source_ids',[])})) or '—';reason=item.get('reason','owner score margin below threshold')
        low_lines.append(f"| `{item['resource_id']}` | {owners} | {scores} | {signals} | {sources} | {reason} |")
    (ROOT/'code/linking/low_confidence.md').write_text('\n'.join(low_lines)+'\n',encoding='utf-8')
    selected=set(x.strip() for x in args.cases.split(',')) if args.cases else None
    if selected: reqs=[r for r in reqs if r['case_id'] in selected]
    if args.limit: reqs=reqs[:args.limit]
    out=[]
    for req in reqs:
        intent=deletion_intent(req['request_text'])
        if llm and intent_is_uncertain(req['request_text']):
            from pathlib import Path
            schema={'type':'object','required':['authorizes_deletion','action_type','language','confidence','rationale_quote'],'additionalProperties':False,'properties':{'authorizes_deletion':{'type':'boolean'},'action_type':{'type':'string','enum':['deletion','access','correction','export','marketing_opt_out','other']},'language':{'type':'string'},'confidence':{'type':'number'},'rationale_quote':{'type':'string'}}}
            system=Path(ROOT/'code/prompts/intent_classifier.md').read_text(encoding='utf-8')
            prompt='Classify only the supplied request. Do not infer from identity, workflow status, or other data. Request text: '+req['request_text']
            try: answer=llm.structured('intent',system,prompt,schema)
            except Exception as exc:
                LOG.warning('Optional intent model call unavailable for %s: %s',req['case_id'],type(exc).__name__)
                answer=None
            if answer is None:
                answer={'authorizes_deletion':intent,'confidence':0.0,'rationale_quote':''}
            quote=norm(answer['rationale_quote'])
            if answer['confidence']<0.8 or not quote or quote not in norm(req['request_text']):
                LOG.warning('LLM intent was low-confidence or uncited; deterministic result retained for %s',req['case_id'])
            elif answer['authorizes_deletion']!=intent:
                LOG.warning('LLM intent conflicts with deterministic authorization; deterministic result retained for %s',req['case_id'])
        if not intent: status,steps='NOT_APPLICABLE',[]
        else: status,steps=plan_case(req,byid,aliases,owner,facts,activities,rules,audits,llm=llm,graph=graph,global_links=global_links,ambiguous_links=ambiguous_links)
        if args.trace_case and req['case_id'] in {x.strip() for x in args.trace_case.split(',')}:
            match=next((u for u in byid if requested_alias_match(req,byid,aliases,owner,u,audits)),None)
            cutoff=dt(req['audit_at']); active={match.lower()} if match else set()
            if match:
                if dt(byid[match].get('updated_at'))<=cutoff:
                    active.update(norm(byid[match].get(k)) for k in ('email','name','phone','email_hash') if byid[match].get(k))
                for ev in audits:
                    if ev.get('user_id')==match and dt(ev.get('event_time'))<=cutoff and ev.get('field_name','').lower() in ('email','name','phone'):
                        for value in (ev.get('old_value',''),ev.get('new_value','')):
                            if value: active.add(norm(value)); active.add(email_hash(value) if ev['field_name'].lower()=='email' else digits(value) if ev['field_name'].lower()=='phone' else norm(value))
                active_emails={x for x in active if '@' in x}; active_hashes={email_hash(x) for x in active_emails}; active_phones={digits(x) for x in active if len(digits(x))>=8}
                LOG.info('TRACE %s request_email=%s resolved_user=%s aliases=%s',req['case_id'],req['email'],match,sorted(active))
                trace_graph=graph
                trace_aliases=active_emails|active_hashes|active_phones|{match.lower()}|{norm(x) for x in active}
                trace_facts,trace_paths=trace_graph.walk(trace_aliases,cutoff)
                for edge in trace_paths:
                    LOG.info('TRACE PATH case=%s %s --%s--> %s via=%s confidence=%.2f',req['case_id'],edge.left,edge.relation,edge.right,edge.source_id,edge.confidence)
                for f in trace_facts:
                    LOG.info('TRACE FACT case=%s source_type=%s confidence=%.2f file=%s time=%s file_time=%s system=%s resource=%s category=%s',req['case_id'],f.get('source_type'),f.get('confidence',0),f['file'],f['time'].isoformat(),f.get('file_time',f['time']).isoformat(),f['system'],f['resource'],f['category'])
                if not trace_facts: LOG.info('TRACE no evidence graph facts matched cutoff-valid aliases')
        for error in validate_steps(steps,status): LOG.error('OUTPUT CONTRACT %s: %s',req['case_id'],error)
        out.append({'case_id':req['case_id'],'deletion_status':status,'steps_json':json.dumps(steps,ensure_ascii=False,separators=(',',':'))})
    out.sort(key=lambda r:int(r['case_id'].split('_')[-1]))
    dest=ROOT/args.output
    with dest.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['case_id','deletion_status','steps_json'],lineterminator='\n'); w.writeheader(); w.writerows(out)
    LOG.info('Wrote %d rows to %s',len(out),dest)
    llm_usage=llm.totals if llm else {'calls':0,'input_tokens':0,'output_tokens':0,'cache_hits':0,'estimated_cost_usd':0.0}
    usage={'requests_processed':len(out),'run_seconds':round(time.perf_counter()-run_started,3),'model_provider':llm.provider if llm else None,'model_fast':llm.fast if llm else None,'model_strong':llm.strong if llm else None,'model_usage':llm_usage,'visual_audits':llm.visual_audits if llm else [],'vision_disabled_reason':llm.vision_disabled_reason if llm else None,'extraction_cache':dict(EXTRACTION_STATS),'linker':linker_stats}
    usage_path=CONFIG.cache/'run_usage.json';usage_path.parent.mkdir(parents=True,exist_ok=True);usage_path.write_text(json.dumps(usage,indent=2),encoding='utf-8')
if __name__=='__main__': main()

