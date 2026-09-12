import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import patch
import httpx
from pc.memory_sources import snapshots
from backend.memory_v1.store import Store
from backend.memory_v1.presentation import table
from backend.memory_v1.blocks import VALIDATOR
from backend.memory_v1.chat import envelope
from integrations.social.bridge import Bridge, render


class IntegrationTests(unittest.TestCase):
    def test_mail_allowlist_roundtrip(self):
        docs=snapshots('imap',{'work':[{'subject':'日报','from':'sender','body':'正文','uid':3,
            'raw_acc':{'in_pass':'NEVER_IMPORT_SECRET'},'token':'NEVER_IMPORT_SECRET'}]})
        self.assertNotIn('NEVER_IMPORT_SECRET',json.dumps(docs))
        self.assertIn('正文',docs[0]['content']['text'])
        with tempfile.TemporaryDirectory() as d:
            store=Store(d+'/db');ack=store.ingest('admin',docs[0])
            self.assertTrue(store.ingest('admin',snapshots('imap',{'work':[{'subject':'日报','from':'sender','body':'正文','uid':3} ]})[0])['duplicate'])
            block=table(store,'admin');VALIDATOR.validate(envelope('test',[block]))
            self.assertEqual(block['rows'][0]['fields']['subject'],'日报')
            self.assertEqual(store.event('admin',ack['event_id'])['content']['fields']['uid'],'3')

    def test_rss_and_transaction_fields(self):
        for kind,cache in [('rss',{'feed':[{'id':'a','title':'Title','link':'https://example.org','summary':'Body'}]}),
                           ('web3',{'wallet':[{'hash':'abc','time':123,'val_sym':'1 ETH'}]})]:
            docs=snapshots(kind,cache)
            with tempfile.TemporaryDirectory() as d:Store(d+'/db').ingest('admin',docs[0])
            self.assertEqual(len(docs),1)

    def test_bridge_allowlist_and_fixed_endpoint(self):
        calls=[]
        def transport(request):
            calls.append(request)
            return httpx.Response(200,json=envelope('test',[{'type':'text','text':'找到记录'}]))
        identity={'adapter':'Telegram','bot_id':'1','user_id':'2','session_id':'3'}
        with patch.dict(os.environ,{'MEMORY_SERVICE_TOKEN':'test'*8,'MEMORY_SERVICE_URL':'http://127.0.0.1:18081'}):
            bridge=Bridge({'allowed_sessions':[identity]},transport=httpx.MockTransport(transport))
            self.assertIsNone(asyncio.run(bridge.handle('Telegram','1','99','3','/neko secret')))
            self.assertIsNone(asyncio.run(bridge.handle('Telegram','1','2','3','ordinary text')))
            self.assertEqual(asyncio.run(bridge.handle('Telegram','1','2','3','/neko /memory.search {"text":""}')),'找到记录')
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0].url.path,'/api/memory/v1/chat')

    def test_social_action_never_exposes_confirmation_token(self):
        output=render(envelope('test',[{'type':'memory.action','action_id':'secret-confirm-token',
            'command':{'command':'memory.delete','event_id':'id'},'expires_in':600}]))
        self.assertNotIn('secret-confirm-token',output)
        self.assertIn('本地',output)


if __name__=='__main__':unittest.main()
