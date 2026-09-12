"""Pi's application tools. No shell, arbitrary SQL, confirmation or file tools."""
import hashlib
import http.client
import ipaddress
import json
import socket
import ssl
import uuid
from html.parser import HTMLParser
from urllib.parse import urlsplit,quote
from .chat import COMMAND_SCHEMA,render_command


EXTRA=[
 {'command':'web.fetch','fields':{'url':{'type':'string','maxLength':2000}}},
 {'command':'web.search','fields':{'query':{'type':'string','minLength':1,'maxLength':300}}},
 {'command':'agent.improve.propose','fields':{'problem':{'type':'string','minLength':1,'maxLength':4000},'proposal':{'type':'string','minLength':1,'maxLength':8000},'test_plan':{'type':'string','minLength':1,'maxLength':4000}}},
 {'command':'agent.improve.list','fields':{}},
]

def specs():
    output=[]
    for spec in COMMAND_SCHEMA['oneOf']:
        name=spec['properties']['command']['const']
        if name in ('memory.reply','memory.daily','memory.compress','memory.clarify'):continue
        fields={k:v for k,v in spec['properties'].items() if k!='command'}
        output.append({'name':name.replace('.','_'),'command':name,'description':name+'; write operations only propose user-confirmed changes',
            'parameters':{'type':'object','additionalProperties':False,'properties':fields,'required':list(fields)}})
    for item in EXTRA:
        output.append({'name':item['command'].replace('.','_'),'command':item['command'],'description':item['command'],
            'parameters':{'type':'object','additionalProperties':False,'properties':item['fields'],'required':list(item['fields'])}})
    return output

class TextParser(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
        if tag=='a':
            href=dict(attrs).get('href','')
            if href.startswith('https://'):self.parts.append(' '+href+' ')
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

def fetch(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,443):raise ValueError('public HTTPS URL required')
    addresses={i[4][0] for i in socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):raise ValueError('public network destinations only')
    address=sorted(addresses)[0]
    class PinnedHTTPS(http.client.HTTPSConnection):
        def connect(self):
            sock=socket.create_connection((address,443),timeout=15)
            self.sock=ssl.create_default_context().wrap_socket(sock,server_hostname=parsed.hostname)
    con=PinnedHTTPS(parsed.hostname,timeout=15)
    try:
        con.request('GET',(parsed.path or '/')+('?' + parsed.query if parsed.query else ''),headers={'User-Agent':'NekoHubMemory/1.0','Accept':'text/html, text/plain, application/json'})
        res=con.getresponse()
        if res.status!=200:raise ValueError('web HTTP '+str(res.status))
        content_type=res.getheader('Content-Type','')
        if not any(t in content_type for t in ('text/','application/json')):raise ValueError('text pages only')
        raw=res.read(1_000_001)
        if len(raw)>1_000_000:raise ValueError('page budget exceeded')
        text=raw.decode('utf-8',errors='replace')
        if 'html' in content_type:
            parser=TextParser();parser.feed(text);text=' '.join(parser.parts)
        return {'url':url,'text':text[:24000],'truncated':len(text)>24000,'trust':'external_untrusted'}
    finally:con.close()

def execute(store,owner,name,args):
    from jsonschema import Draft202012Validator
    spec=next((s for s in specs() if s['name']==name),None)
    if not spec:raise ValueError('unknown tool')
    Draft202012Validator(spec['parameters']).validate(args)
    command=spec['command']
    if command=='web.fetch':return fetch(args['url'])
    if command=='web.search':
        return fetch('https://html.duckduckgo.com/html/?q='+quote(args['query']))
    if command.startswith('agent.improve.'):
        with store.db() as con:
            con.execute('CREATE TABLE IF NOT EXISTS agent_improvements(id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,proposal TEXT NOT NULL,state TEXT NOT NULL)')
            if command.endswith('propose'):
                proposal_id=uuid.uuid4().hex
                con.execute('INSERT INTO agent_improvements VALUES(?,?,?,?)',(proposal_id,owner,json.dumps(args,ensure_ascii=False),'proposed'))
                return {'state':'proposed','id':proposal_id,'requires':'human review and regression tests; no code or policy changed'}
            return [dict(r) for r in con.execute('SELECT id,proposal,state FROM agent_improvements WHERE owner_id=?',(owner,))]
    return render_command(store,owner,{'command':command,**args})
