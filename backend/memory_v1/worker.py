"""Opt-in persistent worker: process memory and compress closed UTC periods."""
import argparse
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .agent import ChatCompletions, MemoryAgent
from .store import Store, now, packed
from .rollup import Rollups
from .daily import report


def tick(store, owner, complete):
    if os.getenv('MEMORY_GOTIFY_URL') and os.getenv('MEMORY_GOTIFY_TOKEN'):
        from .gotify_puller import GotifyPuller
        try:GotifyPuller(store,owner,os.environ['MEMORY_GOTIFY_URL'],os.environ['MEMORY_GOTIFY_TOKEN']).tick()
        except Exception as exc:print(json.dumps({'pull':'failed','type':type(exc).__name__}),flush=True)
    if complete is None:return {'state':'collecting_only'}
    result = store.process_one(owner, MemoryAgent(complete), auto_apply=os.getenv('MEMORY_AUTO_APPLY','false').lower()=='true')
    rollups=Rollups(store)
    today=datetime.now(timezone.utc).date()
    periods=[('day',(today-timedelta(days=1)).isoformat()),
             ('week',(today-timedelta(days=today.weekday()+1)).strftime('%G-W%V')),
             ('month',(today.replace(day=1)-timedelta(days=1)).strftime('%Y-%m'))]
    # Each period is content-hashed; unchanged sources cause zero model calls.
    for level,period in periods:
        rollups.summarize(owner,level,period,complete)
    with store.db() as con:
        con.execute('CREATE TABLE IF NOT EXISTS memory_reports(owner_id TEXT NOT NULL,day TEXT NOT NULL,blocks TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(owner_id,day))')
        existing=con.execute('SELECT 1 FROM memory_reports WHERE owner_id=? AND day=?',(owner,today.isoformat())).fetchone()
    if not existing:
        blocks=report(store,owner,complete)
        with store.db() as con:
            con.execute('INSERT OR IGNORE INTO memory_reports VALUES(?,?,?,?)',(owner,today.isoformat(),packed(blocks),now()))
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
    store=Store(os.getenv('MEMORY_DB_PATH',str(Path(__file__).with_name('memory.db'))))
    complete=ChatCompletions.from_env() if os.getenv('MEMORY_LLM_BASE_URL') and os.getenv('MEMORY_LLM_MODEL') else None
    while True:
        try:
            result=tick(store,os.getenv('MEMORY_CONNECTOR_OWNER','admin'),complete)
            print(json.dumps({'tick':'ok','job':result}),flush=True)
        except Exception as exc:
            print(json.dumps({'tick':'failed','type':type(exc).__name__}),flush=True)
        if args.once:break
        time.sleep(60)

if __name__=='__main__':main()
