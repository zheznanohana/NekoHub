"""Restart-safe polling: independent incremental and historical cursors."""
from .connectors import get_json
from .agent import ChatCompletions
from .store import packed
import urllib.parse


class GotifyPuller:
    def __init__(self, store, owner, url, token, get=get_json):
        ChatCompletions(url,token,'url-validation')
        if not token:raise ValueError('Gotify client token required')
        self.store,self.owner,self.url,self.token,self.get=store,owner,url.rstrip('/'),token,get
        with store.db() as con:
            con.execute('''CREATE TABLE IF NOT EXISTS gotify_pull_state(
                owner_id TEXT NOT NULL,url TEXT NOT NULL,watermark INTEGER NOT NULL DEFAULT 0,
                history_cursor INTEGER NOT NULL DEFAULT 0,history_done INTEGER NOT NULL DEFAULT 0,
                catchup_cursor INTEGER NOT NULL DEFAULT 0,catchup_target INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(owner_id,url))''')
            con.execute('INSERT OR IGNORE INTO gotify_pull_state(owner_id,url) VALUES(?,?)',(owner,self.url))

    def state(self):
        with self.store.db() as con:
            return dict(con.execute('SELECT * FROM gotify_pull_state WHERE owner_id=? AND url=?',(self.owner,self.url)).fetchone())

    def _save(self, state):
        with self.store.db() as con:
            con.execute('UPDATE gotify_pull_state SET watermark=?,history_cursor=?,history_done=?,catchup_cursor=?,catchup_target=? WHERE owner_id=? AND url=?',
                        tuple(state[k] for k in ('watermark','history_cursor','history_done','catchup_cursor','catchup_target'))+(self.owner,self.url))

    def _page(self,since):
        data=self.get(self.url+'/message?'+urllib.parse.urlencode({'limit':200,'since':since}),{'X-Gotify-Key':self.token})
        rows=data['messages']
        if rows and since and min(int(m['id']) for m in rows)>=since:raise ValueError('Gotify cursor stalled')
        for m in rows:
            self.store.ingest(self.owner,{'schema_version':'1.0','kind':'memory.ingest','request_id':'gotify-'+str(m['id']),
                'source':{'type':'gotify','instance_id':'gotify:'+self.url,'external_id':str(m['id'])},
                'occurred_at':m.get('date'),'timezone':'UTC','content':{'title':m.get('title') or '', 'text':m.get('message') or '(empty notification)'},'provenance':'external'})
        return rows,bool(data.get('paging',{}).get('next'))

    def tick(self):
        # Run only one puller for an owner/source. Durable cursors change after all page writes.
        s=self.state()
        rows,more=self._page(s['catchup_cursor'])
        if rows:
            newest=max(int(m['id']) for m in rows);oldest=min(int(m['id']) for m in rows)
            if not s['watermark']:
                s.update(watermark=newest,history_cursor=oldest,history_done=int(not more))
            else:
                target=s['catchup_target'] or newest
                if oldest<=s['watermark'] or not more:
                    s.update(watermark=max(s['watermark'],target),catchup_cursor=0,catchup_target=0)
                else:s.update(catchup_cursor=oldest,catchup_target=target)
            self._save(s)
        elif s['catchup_cursor']:
            s.update(watermark=max(s['watermark'],s['catchup_target']),catchup_cursor=0,catchup_target=0);self._save(s)
        if s['history_cursor'] and not s['history_done']:
            history,more=self._page(s['history_cursor'])
            if history:s['history_cursor']=min(int(m['id']) for m in history)
            s['history_done']=int(not more or not history)
            self._save(s)
        return {k:s[k] for k in ('watermark','history_cursor','history_done','catchup_cursor')}
