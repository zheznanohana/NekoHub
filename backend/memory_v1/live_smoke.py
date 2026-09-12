"""Opt-in live LLM check using synthetic data only; never logs credentials."""
import json
import tempfile
from pathlib import Path
from .server import create_app
from .blocks import VALIDATOR
from .rollup import Rollups
from .agent import ChatCompletions
from .chat import run_chat


def main():
    token="synthetic-smoke-test-token"
    with tempfile.TemporaryDirectory() as folder:
        app=create_app(path=str(Path(folder)/'test.db'),token=token)
        client=app.test_client();headers={'Authorization':'Bearer '+token}
        doc={'schema_version':'1.0','kind':'memory.ingest','request_id':'smoke',
             'source':{'type':'manual','instance_id':'smoke','external_id':'smoke'},
             'occurred_at':'2026-09-12T06:00:00Z','timezone':'Asia/Tokyo',
             'content':{'title':'Synthetic test','text':'I plan to review NekoHub.'},'provenance':'user_authored'}
        r=client.post('/api/memory/v1/events',json=doc,headers=headers)
        assert r.status_code==202,r.json
        job_id=r.json['job_id']
        r=client.post('/api/memory/v1/process',json={},headers=headers)
        assert r.status_code==200,r.json
        job=app.extensions['memory_store'].proposal('admin',job_id)
        assert job['state']=='review',job['state']
        # Explicit synthetic test approval, never real user data.
        r=client.post('/api/memory/v1/jobs/'+job_id+'/review',json={'approve':True},headers=headers)
        assert r.status_code==200,r.json
        r=client.post('/api/memory/v1/chat',json={'schema_version':'1.0','message':'/memory.export {}'},headers=headers)
        assert r.status_code==200,r.json;VALIDATOR.validate(r.json)
        rollup=Rollups(app.extensions['memory_store']).summarize('admin','day','2026-09-12',ChatCompletions.from_env())
        # Direct call also exposes validation failures while using synthetic data only.
        blocks=run_chat('查一下 NekoHub 的计划，读取证据后回答。',app.extensions['memory_store'],'admin',ChatCompletions.from_env())
        r=client.post('/api/memory/v1/chat',json={'schema_version':'1.0','message':'/memory.export {}'},headers=headers)
        assert r.status_code==200,r.json;VALIDATOR.validate(r.json)
        assert isinstance(blocks,list)
        print(json.dumps({'live_llm':'passed','pipeline':'ingest -> LLM -> review -> graph/table','rollup':rollup['state'],'chat_blocks':[b['type'] for b in blocks]},ensure_ascii=False))

if __name__=='__main__':main()
