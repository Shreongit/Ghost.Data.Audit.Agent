"""Optional, provider-agnostic structured LLM/VLM calls with cache and accounting.

No provider is contacted unless explicitly enabled by the CLI. Credentials and
model names are read only from environment variables. Pricing is user supplied
so cost estimates are never invented or silently treated as zero.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import threading
import time
import random
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class LLMError(RuntimeError):
    pass


_SDK_CALLS = threading.BoundedSemaphore(2)


def validate_schema(value: Any, schema: dict[str, Any], path: str = '$') -> None:
    """Validate the JSON Schema subset used in our prompts without dependencies."""
    kind = schema.get('type')
    expected = {'object': dict, 'array': list, 'string': str, 'boolean': bool, 'integer': int, 'number': (int, float)}.get(kind)
    if expected and (not isinstance(value, expected) or (kind == 'integer' and isinstance(value, bool)) or (kind == 'number' and isinstance(value, bool))):
        raise LLMError(f'{path}: expected {kind}')
    if kind == 'object':
        missing = set(schema.get('required', ())) - value.keys()
        if missing:
            raise LLMError(f'{path}: missing required keys {sorted(missing)}')
        properties = schema.get('properties', {})
        if schema.get('additionalProperties') is False and value.keys() - properties.keys():
            raise LLMError(f'{path}: unexpected keys {sorted(value.keys() - properties.keys())}')
        for key, child in properties.items():
            if key in value:
                validate_schema(value[key], child, f'{path}.{key}')
    elif kind == 'array':
        for index, item in enumerate(value):
            validate_schema(item, schema.get('items', {}), f'{path}[{index}]')
    if 'enum' in schema and value not in schema['enum']:
        raise LLMError(f'{path}: value outside enum')


class LLMClient:
    def __init__(self, root: Path, budget_usd: float | None = None, timeout: int = 45):
        self.root = root
        self.provider = os.getenv('LLM_PROVIDER', '').strip().lower()
        self.fast = os.getenv('LLM_MODEL_FAST', '').strip()
        self.strong = os.getenv('LLM_MODEL_STRONG', '').strip()
        self.timeout = timeout
        self.budget = budget_usd
        self.cache_dir = root / 'code' / '.cache' / 'llm'
        self.trace_dir = root / 'code' / '.cache' / 'llm_trace'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.usage_path = root / 'code' / '.cache' / 'usage.json'
        self._lock = threading.Lock()
        self._last_call = 0.0
        self._usage = self._load_usage()
        self.visual_audits: list[dict[str, Any]] = []
        self.vision_disabled_reason: str | None = None
        self._start_call_count=len(self._usage['calls'])
        self._start_cache_hits=self._usage.get('cache_hits',0)
        self.rate_limit_retries=0
        self._key = self._get_key()
        if budget_usd is not None and (self._rate('LLM_INPUT_USD_PER_MILLION') is None or self._rate('LLM_OUTPUT_USD_PER_MILLION') is None):
            raise LLMError('Set LLM_INPUT_USD_PER_MILLION and LLM_OUTPUT_USD_PER_MILLION to use a hard budget guard.')

    def _get_key(self) -> str:
        names = {'openai':'OPENAI_API_KEY', 'anthropic':'ANTHROPIC_API_KEY', 'gemini':'GEMINI_API_KEY', 'xai':'XAI_API_KEY', 'groq':'GROQ_API_KEY'}
        if self.provider not in names:
            raise LLMError('Set LLM_PROVIDER to openai, anthropic, gemini, xai, or groq before using --llm.')
        key = os.getenv(names[self.provider], '')
        if not key:
            raise LLMError(f'{names[self.provider]} is not configured in the environment.')
        return key

    @staticmethod
    def _rate(name: str) -> float | None:
        try: return float(os.environ[name])
        except (KeyError, ValueError): return None

    @staticmethod
    def _model_rate(model: str, direction: str) -> float | None:
        try:
            prices=json.loads(os.environ.get('LLM_MODEL_PRICES_JSON','{}'))
            if model in prices and direction in prices[model]: return float(prices[model][direction])
        except (ValueError,TypeError): pass
        return LLMClient._rate(f'LLM_{direction.upper()}_USD_PER_MILLION')

    def _load_usage(self) -> dict[str, Any]:
        if self.usage_path.exists():
            try: return json.loads(self.usage_path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError): pass
        return {'calls': [], 'cache_hits': 0}

    def _save_usage(self) -> None:
        self.usage_path.parent.mkdir(parents=True, exist_ok=True)
        self.usage_path.write_text(json.dumps(self._usage, indent=2), encoding='utf-8')

    @property
    def totals(self) -> dict[str, Any]:
        calls = self._usage['calls'][self._start_call_count:]
        known=[x['estimated_cost_usd'] for x in calls if x['estimated_cost_usd'] is not None]
        return {'calls':len(calls), 'input_tokens':sum(x['input_tokens'] for x in calls), 'output_tokens':sum(x['output_tokens'] for x in calls), 'cache_hits':self._usage.get('cache_hits',0)-self._start_cache_hits, 'rate_limit_retries':self.rate_limit_retries, 'estimated_cost_usd':sum(known) if len(known)==len(calls) else None}

    def text_call(self, stage: str, prompt: str, *, tier: str = 'fast') -> str:
        """Issue one uncached plain-text xAI call and record provider usage."""
        if self.provider not in {'xai','groq'}: raise LLMError('text_call is only available for OpenAI-compatible providers.')
        model=self.fast if tier=='fast' else self.strong
        if not model: raise LLMError(f'LLM_MODEL_{tier.upper()} is not configured.')
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError('Install the openai package to use the OpenAI-compatible provider.') from exc
        digest=hashlib.sha256((stage+'\0'+model+'\0'+prompt).encode()).hexdigest()
        cached=self.cache_dir/f'{digest}.txt'
        if cached.exists():
            with self._lock:
                self._usage['cache_hits']=self._usage.get('cache_hits',0)+1;self._save_usage()
            return cached.read_text(encoding='utf-8')
        base_url='https://api.groq.com/openai/v1' if self.provider=='groq' else 'https://api.x.ai/v1'
        client=OpenAI(api_key=self._key,base_url=base_url,timeout=self.timeout,max_retries=0)
        response=self._sdk_completion(client,model=model,messages=[{'role':'user','content':prompt}],temperature=0)
        usage=response.usage
        self._record(stage,model,digest,{'input_tokens':int(getattr(usage,'prompt_tokens',0) or 0),
                                         'output_tokens':int(getattr(usage,'completion_tokens',0) or 0),
                                         'response_mode':'text'})
        text=response.choices[0].message.content or ''
        cached.write_text(text,encoding='utf-8')
        return text

    def _sdk_completion(self, client, **kwargs):
        """Apply a global concurrency cap and bounded backoff for HTTP 429."""
        from openai import RateLimitError
        gap=float(os.getenv('LLM_MIN_INTERVAL_SECONDS','2.0' if self.provider=='groq' else '0.2'))
        with self._lock:
            delay=gap-(time.monotonic()-self._last_call)
            if delay>0: time.sleep(delay)
            self._last_call=time.monotonic()
        for attempt in range(6):
            try:
                with _SDK_CALLS:
                    return client.chat.completions.create(**kwargs)
            except RateLimitError as exc:
                if attempt==5:
                    if any(isinstance(message.get('content'),list) and any(part.get('type')=='image_url' for part in message['content']) for message in kwargs.get('messages',[])):
                        self.vision_disabled_reason='image calls stopped after Groq rate-limit retry exhaustion'
                    raise
                self.rate_limit_retries+=1
                # Groq exposes retry-after and token-window reset headers. Honor
                # those before falling back to bounded exponential backoff.
                headers=getattr(getattr(exc,'response',None),'headers',{}) or {}
                delay=None
                try: delay=float(headers.get('retry-after'))
                except (TypeError,ValueError): pass
                if delay is None:
                    reset=str(headers.get('x-ratelimit-reset-tokens',''))
                    match=re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)(ms|s|m)',reset)
                    if match:
                        amount=float(match.group(1));unit=match.group(2)
                        delay=amount/1000 if unit=='ms' else amount*(60 if unit=='m' else 1)
                if delay is None: delay=min(30.0,1.0*(2**attempt))
                time.sleep(min(120.0,max(0.25,delay))+random.uniform(0,0.25))
        raise LLMError('Rate-limit retry limit exceeded.')

    def structured(self, stage: str, system: str, prompt: str, schema: dict[str, Any], *, tier: str = 'fast', image_paths: list[Path] | None = None) -> dict[str, Any]:
        model = self.fast if tier == 'fast' else self.strong
        if not model: raise LLMError(f'LLM_MODEL_{tier.upper()} is not configured.')
        images = image_paths or []
        payload_key = {'provider':self.provider,'model':model,'stage':stage,'system':system,'prompt':prompt,'schema':schema,'images':[hashlib.sha256(p.read_bytes()).hexdigest() for p in images]}
        digest = hashlib.sha256(json.dumps(payload_key,sort_keys=True).encode()).hexdigest()
        cached = self.cache_dir / f'{digest}.json'
        if cached.exists():
            with self._lock:
                self._usage['cache_hits'] = self._usage.get('cache_hits',0)+1; self._save_usage()
            return json.loads(cached.read_text(encoding='utf-8'))
        repair = ''
        for attempt in range(2):
            raw, usage = self._request(model, system + repair, prompt, schema, images)
            try:
                result = json.loads(raw)
                validate_schema(result, schema)
                self._record(stage, model, digest, usage)
                cached.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
                trace={'stage':stage,'provider':self.provider,'model':model,'input_hash':digest,'usage':usage,'result':result}
                (self.trace_dir/f'{digest}.json').write_text(json.dumps(trace,ensure_ascii=False,indent=2),encoding='utf-8')
                (self.trace_dir/f'{digest}.md').write_text(f'# {stage}\n\nProvider: {self.provider}\nModel: {model}\nInput hash: {digest}\n\n```json\n{json.dumps(result,ensure_ascii=False,indent=2)}\n```\n',encoding='utf-8')
                return result
            except (json.JSONDecodeError, LLMError) as exc:
                self._record(stage, model, digest, usage)
                if attempt: raise LLMError(f'Structured response invalid after repair: {exc}') from exc
                repair=f'\nReturn only valid JSON matching this schema exactly. Repair the prior response: {exc}. Schema: {json.dumps(schema)}.'
        raise LLMError('Structured call failed.')

    def _request(self, model: str, system: str, prompt: str, schema: dict[str, Any], images: list[Path]) -> tuple[str, dict[str,Any]]:
        with self._lock:
            gap=float(os.getenv('LLM_MIN_INTERVAL_SECONDS','0.2'))
            delay=gap-(time.monotonic()-self._last_call)
            if delay>0: time.sleep(delay)
            self._last_call=time.monotonic()
        if self.budget is not None:
            ir=self._rate('LLM_INPUT_USD_PER_MILLION');orate=self._rate('LLM_OUTPUT_USD_PER_MILLION')
            input_estimate=(len(system.encode('utf-8'))+len(prompt.encode('utf-8'))+sum(p.stat().st_size for p in images))//3
            max_cost=input_estimate*ir/1_000_000+2048*orate/1_000_000
            spent=sum(x['estimated_cost_usd'] for x in self._usage['calls'][self._start_call_count:] if x['estimated_cost_usd'] is not None)
            if spent+max_cost>self.budget: raise LLMError('LLM budget preflight denied a call that could exceed --budget-usd.')
        if self.provider in {'xai','groq'}:
            try:
                from openai import OpenAI, BadRequestError
            except ImportError as exc:
                raise LLMError('Install the openai package to use the OpenAI-compatible provider.') from exc
            base_url='https://api.groq.com/openai/v1' if self.provider=='groq' else 'https://api.x.ai/v1'
            client=OpenAI(api_key=self._key,base_url=base_url,timeout=self.timeout,max_retries=0)
            content: Any=[{'type':'text','text':prompt}]
            for path in images:
                mime='image/png' if path.suffix.lower()=='.png' else 'image/jpeg'
                content.append({'type':'image_url','image_url':{'url':f'data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}'}})
            messages=[{'role':'system','content':system+'\nReturn JSON conforming to this schema: '+json.dumps(schema)}, {'role':'user','content':content}]
            json_schema={'type':'json_schema','json_schema':{'name':'audit_response','strict':True,'schema':schema}}
            try:
                response=self._sdk_completion(client,model=model,messages=messages,temperature=0,response_format=json_schema)
                mode='json_schema'
            except BadRequestError:
                # Some account/model combinations do not support constrained schema output.
                # Fall back to JSON mode; structured() still validates and repairs locally.
                try:
                    response=self._sdk_completion(client,model=model,messages=messages,temperature=0,response_format={'type':'json_object'})
                except BadRequestError:
                    if images: self.vision_disabled_reason='image request rejected after JSON-mode fallback'
                    raise
                mode='json_object_fallback'
            usage=response.usage
            return (response.choices[0].message.content or '',
                    {'input_tokens':int(getattr(usage,'prompt_tokens',0) or 0),
                     'output_tokens':int(getattr(usage,'completion_tokens',0) or 0),
                     'response_mode':mode})
        for attempt in range(3):
            try:
                req=self._build_request(model,system,prompt,schema,images)
                with urllib.request.urlopen(req,timeout=self.timeout) as response:
                    body=json.loads(response.read().decode('utf-8'))
                return self._parse_response(body)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                if attempt==2: raise LLMError(f'{self.provider} request failed: {type(exc).__name__}') from exc
                time.sleep(0.5*(2**attempt))
        raise LLMError('Request failed.')

    def _build_request(self, model: str, system: str, prompt: str, schema: dict[str, Any], images: list[Path]) -> urllib.request.Request:
        if self.provider=='openai':
            content: Any=[{'type':'text','text':prompt}]
            for path in images:
                mime='image/png' if path.suffix.lower()=='.png' else 'image/jpeg'
                content.append({'type':'image_url','image_url':{'url':f'data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}'}})
            body={'model':model,'temperature':0,'response_format':{'type':'json_object'},'messages':[{'role':'system','content':system},{'role':'user','content':content}]}
            headers={'Authorization':f'Bearer {self._key}'}; url='https://api.openai.com/v1/chat/completions'
        elif self.provider in {'xai','groq'}:
            raise LLMError(f'{self.provider} requests use the OpenAI SDK transport.')
        elif self.provider=='anthropic':
            content=[{'type':'text','text':prompt}]
            for path in images:
                mime='image/png' if path.suffix.lower()=='.png' else 'image/jpeg'
                content.append({'type':'image','source':{'type':'base64','media_type':mime,'data':base64.b64encode(path.read_bytes()).decode()}})
            body={'model':model,'temperature':0,'max_tokens':2048,'system':system+' Return a JSON object matching this schema: '+json.dumps(schema),'messages':[{'role':'user','content':content}]}
            headers={'x-api-key':self._key,'anthropic-version':'2023-06-01'}; url='https://api.anthropic.com/v1/messages'
        else:
            parts=[{'text':system+'\nReturn a JSON object matching this schema: '+json.dumps(schema)+'\n'+prompt}]
            for path in images:
                mime='image/png' if path.suffix.lower()=='.png' else 'image/jpeg'
                parts.append({'inline_data':{'mime_type':mime,'data':base64.b64encode(path.read_bytes()).decode()}})
            body={'contents':[{'parts':parts}],'generationConfig':{'temperature':0,'responseMimeType':'application/json'}}
            headers={}; url=f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self._key}'
        data=json.dumps(body).encode('utf-8')
        return urllib.request.Request(url,data=data,headers={'Content-Type':'application/json',**headers},method='POST')

    def _parse_response(self, body: dict[str, Any]) -> tuple[str, dict[str,int]]:
        if self.provider=='openai':
            text=body['choices'][0]['message']['content']; usage=body.get('usage',{}); inp=usage.get('prompt_tokens',0); out=usage.get('completion_tokens',0)
        elif self.provider=='anthropic':
            text=''.join(x.get('text','') for x in body.get('content',[]) if x.get('type')=='text'); usage=body.get('usage',{}); inp=usage.get('input_tokens',0); out=usage.get('output_tokens',0)
        elif self.provider=='gemini':
            text=body['candidates'][0]['content']['parts'][0]['text']; usage=body.get('usageMetadata',{}); inp=usage.get('promptTokenCount',0); out=usage.get('candidatesTokenCount',0)
        return text,{'input_tokens':int(inp),'output_tokens':int(out)}

    def _record(self, stage: str, model: str, digest: str, usage: dict[str,int]) -> None:
        ir=self._model_rate(model,'input'); orate=self._model_rate(model,'output')
        cost=usage['input_tokens']*ir/1_000_000+usage['output_tokens']*orate/1_000_000 if ir is not None and orate is not None else None
        with self._lock:
            total=sum(x['estimated_cost_usd'] for x in self._usage['calls'][self._start_call_count:] if x['estimated_cost_usd'] is not None)
            if self.budget is not None and total+cost>self.budget: raise LLMError(f'LLM budget limit would be exceeded at stage {stage}.')
            row={'stage':stage,'provider':self.provider,'model':model,'input_hash':digest,
                 'input_tokens':usage['input_tokens'],'output_tokens':usage['output_tokens'],
                 'response_mode':usage.get('response_mode'),'estimated_cost_usd':cost}
            self._usage['calls'].append(row); self._save_usage()
