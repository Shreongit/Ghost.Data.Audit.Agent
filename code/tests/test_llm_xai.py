import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import LLMClient


class XaiProviderTests(unittest.TestCase):
    def test_schema_rejection_falls_back_to_json_mode(self):
        calls=[]
        class BadRequestError(Exception):
            pass
        class Completions:
            def create(self, **kwargs):
                calls.append(kwargs)
                if kwargs['response_format']['type']=='json_schema':
                    raise BadRequestError('unsupported schema format')
                usage=types.SimpleNamespace(prompt_tokens=13,completion_tokens=5)
                msg=types.SimpleNamespace(content='{"ok":true}')
                return types.SimpleNamespace(usage=usage,choices=[types.SimpleNamespace(message=msg)])
        class OpenAI:
            def __init__(self, **kwargs):
                self.kwargs=kwargs
                self.chat=types.SimpleNamespace(completions=Completions())
        fake=types.ModuleType('openai');fake.OpenAI=OpenAI;fake.BadRequestError=BadRequestError;fake.RateLimitError=type('RateLimitError',(Exception,),{})
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2],ignore_cleanup_errors=True) as tmp, patch.dict(os.environ,{
            'LLM_PROVIDER':'xai','XAI_API_KEY':'test-key','LLM_MODEL_FAST':'test-model','LLM_MODEL_STRONG':'test-model'
        }), patch.dict(sys.modules,{'openai':fake}):
            client=LLMClient(Path(tmp))
            text,usage=client._request('test-model','system','prompt',{'type':'object','properties':{'ok':{'type':'boolean'}}},[])
        self.assertEqual(text,'{"ok":true}')
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[0]['response_format']['type'],'json_schema')
        self.assertEqual(calls[1]['response_format']['type'],'json_object')
        self.assertEqual(usage['response_mode'],'json_object_fallback')
        self.assertEqual(usage['input_tokens'],13)

    def test_groq_rate_limit_retries_with_bounded_backoff(self):
        calls=[]
        class RateLimitError(Exception): pass
        class FakeClient:
            def __init__(self):
                self.chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=self.create))
            def create(self,**kwargs):
                calls.append(kwargs)
                if len(calls)==1: raise RateLimitError()
                return 'ok'
        fake=types.ModuleType('openai');fake.RateLimitError=RateLimitError
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2],ignore_cleanup_errors=True) as tmp, patch.dict(os.environ,{
            'LLM_PROVIDER':'groq','GROQ_API_KEY':'test-key','LLM_MODEL_FAST':'listed-model','LLM_MODEL_STRONG':'listed-model'
        }), patch.dict(sys.modules,{'openai':fake}), patch('llm.time.sleep') as sleep:
            client=LLMClient(Path(tmp))
            self.assertEqual(client._sdk_completion(FakeClient(),marker='request'),'ok')
        self.assertEqual(len(calls),2)
        self.assertEqual(client.rate_limit_retries,1)
        sleep.assert_called_once()


if __name__=='__main__':
    unittest.main()
