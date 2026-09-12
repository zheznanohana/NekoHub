import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from backend.memory_v1.store import Store
from backend.memory_v1.pi_runtime import run_pi
from backend.memory_v1.agent_tools import execute,fetch
from backend.memory_v1.view_context import resolve


class PiRuntimeTests(unittest.TestCase):
    def test_real_pi_runtime_calls_tool_and_returns_blocks(self):
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));requests.append(data)
                if len(requests)==1:
                    delta={'role':'assistant','tool_calls':[{'index':0,'id':'test-call','type':'function','function':{'name':'memory_search','arguments':'{"text":""}'}}]};finish='tool_calls'
                else:delta={'role':'assistant','content':'已读取记忆。'};finish='stop'
                chunks=[{'id':'test','object':'chat.completion.chunk','created':1,'model':'test','choices':[{'index':0,'delta':delta,'finish_reason':None}]},
                        {'id':'test','object':'chat.completion.chunk','created':1,'model':'test','choices':[{'index':0,'delta':{},'finish_reason':finish}]}]
                body=''.join('data: '+json.dumps(c)+'\n\n' for c in chunks)+'data: [DONE]\n\n'
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Content-Length',str(len(body.encode())));self.end_headers();self.wfile.write(body.encode())
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as d:
                result=run_pi('查询记忆',Store(d+'/db'),'admin',provider={'base_url':f'http://127.0.0.1:{server.server_port}/v1','api_key':'synthetic','model':'test'})
                self.assertEqual(result[0]['type'],'memory.cards');self.assertEqual(result[-1]['text'],'已读取记忆。')
                self.assertEqual(len(requests),2)
                self.assertTrue(any(m['role']=='tool' for m in requests[1]['messages']))
        finally:server.shutdown();server.server_close()

    def test_no_confirm_tool_and_private_url(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):execute(Store(d+'/db'),'admin','memory_confirm',{})
        with self.assertRaises(ValueError):fetch('https://127.0.0.1/secret')

    def test_view_forgery_and_improvement_proposal(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(d+'/db')
            context=resolve(store,'admin',{'selected_ids':['foreign'],'visible_ids':['foreign'],'levels':[],'query':''})
            self.assertEqual(context['selected_ids'],[])
            result=execute(store,'admin','agent_improve_propose',{'problem':'检索重复','proposal':'减少重复调用','test_plan':'验证调用次数'})
            self.assertEqual(result['state'],'proposed')
            self.assertEqual(len(execute(store,'admin','agent_improve_list',{})),1)


if __name__=='__main__':unittest.main()
