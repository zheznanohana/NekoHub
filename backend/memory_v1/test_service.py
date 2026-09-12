import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from backend.memory_v1.agent import MemoryAgent
from backend.memory_v1.server import create_app
from backend.memory_v1.store import Store, Conflict
from backend.memory_v1.rollup import Rollups
from backend.memory_v1.connectors import gotify_sync, github_sync
from backend.memory_v1.daily import report
from backend.memory_v1.blocks import VALIDATOR
from backend.memory_v1.examples import INGEST, CHANGESET


def model(messages):
    job=json.loads(messages[1]["content"])
    result=deepcopy(CHANGESET)
    result.update({k:job[k] for k in ("request_id","idempotency_key","extractor_version")})
    result["operations"][0]["fact"]["evidence"][0]["event_id"]=job["events"][0]["event_id"]
    return json.dumps(result)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=str(Path(self.temp.name)/"memory.db")
        self.app=create_app(path=self.path,token="test-token-123456789",complete=model)
        self.client=self.app.test_client();self.store=self.app.extensions["memory_store"]
        self.headers={"Authorization":"Bearer test-token-123456789"}

    def tearDown(self):self.temp.cleanup()
    def post(self,path,data):return self.client.post('/api/memory/v1'+path,json=data,headers=self.headers)
    def ingest(self):return self.store.ingest("admin",deepcopy(INGEST))

    def test_auth(self):self.assertEqual(self.client.get('/api/memory/v1/status').status_code,401)

    def test_pipeline_and_owner(self):
        ack=self.ingest()
        self.assertTrue(self.ingest()["duplicate"])
        result=self.post('/process',{});self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(self.store.jobs("admin")[0]["state"],"review")
        self.assertEqual(self.store.graph("admin")["facts"],[])
        self.assertEqual(self.post('/jobs/'+ack["job_id"]+'/review',{"approve":True}).status_code,200)
        self.assertEqual(len(self.store.graph("admin")["facts"]),1)
        self.assertEqual(self.store.graph("other")["facts"],[])
        with self.assertRaises(KeyError):self.store.event("other",ack["event_id"])
        response=self.post('/chat',{"schema_version":"1.0","message":"/memory.export {}"})
        self.assertEqual(response.status_code,200,response.json);VALIDATOR.validate(response.json)

    def test_writes_apply_at_once_and_only_deletion_waits(self):
        """Policy: deletion is the single command that needs a click."""
        def chat(cmd):return self.post('/chat',{"schema_version":"1.0","message":cmd})
        response=chat('/memory.create {"text":"hello"}')
        self.assertEqual([b['type'] for b in response.json['blocks']],['text','memory.receipt'])
        self.assertEqual(len(self.store.search('admin','hello')),1)
        event=self.store.search('admin','hello')[0]
        response=chat('/memory.update '+json.dumps({'event_id':event['id'],'text':'changed'}))
        self.assertNotIn('memory.action',[b['type'] for b in response.json['blocks']])
        self.assertEqual(self.store.search('admin','hello'),[])
        self.assertEqual(len(self.store.search('admin','changed')),1)
        event=self.store.search('admin','changed')[0]
        response=chat('/memory.delete '+json.dumps({'event_id':event['id']}))
        block=response.json['blocks'][0]
        self.assertEqual(block['type'],'memory.action')
        self.assertEqual(len(self.store.search('admin','changed')),1)   # still there until confirmed
        self.assertEqual(self.post('/actions/'+block['action_id']+'/confirm',{}).status_code,200)
        self.assertEqual(self.store.search('admin','changed'),[])
        self.assertEqual(self.post('/actions/'+block['action_id']+'/confirm',{}).status_code,409)

    def test_source_conflict(self):
        self.ingest(); doc=deepcopy(INGEST);doc['content']['text']='changed'
        with self.assertRaises(Conflict):self.store.ingest('admin',doc)

    def test_daily_has_no_delete_authority(self):
        ack=self.ingest()
        blocks=report(self.store,'admin',lambda _:json.dumps({'summary':'整理建议','delete_suggestions':[{'event_id':ack['event_id'],'reason':'仅为测试建议'}]}))
        self.assertEqual(blocks[1]['type'],'memory.action')
        self.assertEqual(len(self.store.search('admin','')),1)
        with self.assertRaises(KeyError):self.store.confirm_action('other',blocks[1]['action_id'])

    def test_rollups_expand_invalidate(self):
        ack=self.ingest();rollups=Rollups(self.store)
        def summarize(messages):
            sources=json.loads(messages[1]['content'])['sources']
            return json.dumps({'summary':'项目计划','source_ids':[s['id'] for s in sources]})
        day=rollups.summarize('admin','day','2026-09-12',summarize)
        week=rollups.summarize('admin','week','2026-W37',summarize)
        month=rollups.summarize('admin','month','2026-09',summarize)
        self.assertEqual(len(rollups.expand('admin',month['id'])),1)
        monthly=next(s for s in rollups.search('admin') if s['level']=='month')
        self.assertIn(week['id'],monthly['child_ids'])
        action=self.store.prepare_action('admin',{'command':'memory.delete','event_id':ack['event_id']})
        self.store.confirm_action('admin',action)
        self.assertEqual(rollups.search('admin'),[])
        with self.assertRaises(KeyError):rollups.expand('admin',month['id'])

    def test_gotify_paging(self):
        calls=[]
        def get(url,headers):
            calls.append(url);mid=2 if len(calls)==1 else 1
            return {'messages':[{'id':mid,'title':'t','message':'m','date':'2026-09-12T00:00:00Z'}],'paging':{'next':'next' if mid==2 else ''}}
        result=gotify_sync(self.store,'admin','http://127.0.0.1:18080','token',get=get)
        self.assertEqual(result['imported'],2);self.assertIn('since=2',calls[1])

    def test_github_readonly_mapping(self):
        data=[{'id':1,'number':1,'title':'Test','state':'open','body':'Body','html_url':'https://github.com/a/b/issues/1','updated_at':'2026-09-12T00:00:00Z'}]
        result=github_sync(self.store,'admin','a/b',get=lambda *_:data)
        self.assertEqual(result['imported'],1)
        self.assertEqual(github_sync(self.store,'admin','a/b',get=lambda *_:data)['imported'],0)

    def test_no_arbitrary_command(self):
        result=self.post('/chat',{'schema_version':'1.0','message':'/shell {"text":"whoami"}'})
        self.assertEqual(result.status_code,400)

    def test_chat_agent_reads_table_then_answers(self):
        from backend.memory_v1.chat import run_chat
        ack=self.ingest()
        responses=iter([json.dumps({'command':'memory.table.read','source':'manual','level':'raw','text':'NekoHub'}),
                        json.dumps({'command':'memory.reply','text':'存在项目计划。','evidence_ids':[ack['event_id']]})])
        blocks=run_chat('读取表格',self.store,'admin',lambda _:next(responses))
        self.assertEqual(blocks[1]['items'][0]['id'],ack['event_id'])
        self.assertEqual(len(self.store.search('admin','')),1)

    def test_output_schema_rejects_html_block(self):
        from jsonschema import ValidationError
        with self.assertRaises(ValidationError):
            VALIDATOR.validate({'schema_version':'1.0','kind':'chat.blocks','request_id':'test','blocks':[{'type':'html','html':'<script />'}]})

    def test_puller_restart_and_large_catchup(self):
        from backend.memory_v1.gotify_puller import GotifyPuller
        from urllib.parse import urlsplit,parse_qs
        top=[450]
        def get(url,headers):
            since=int(parse_qs(urlsplit(url).query)['since'][0]);highest=min(top[0],since-1) if since else top[0]
            ids=list(range(highest,max(0,highest-200),-1))
            return {'messages':[{'id':i,'message':str(i),'date':'2026-09-12T00:00:00Z'} for i in ids], 'paging':{'next':'next' if ids and min(ids)>1 else ''}}
        def puller():return GotifyPuller(self.store,'admin','http://127.0.0.1:18080','token',get)
        puller().tick();puller().tick()
        self.assertEqual(puller().state()['history_done'],1)
        with self.store.db() as con:self.assertEqual(con.execute('SELECT count(*) FROM memory_events').fetchone()[0],450)
        top[0]=900
        for _ in range(3):puller().tick()
        self.assertEqual(puller().state()['watermark'],900)
        with self.store.db() as con:self.assertEqual(con.execute('SELECT count(*) FROM memory_events').fetchone()[0],900)


if __name__=='__main__':unittest.main()
