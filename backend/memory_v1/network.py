"""Deterministic, evidence-linked multiscale network; never invent edges."""
from .curate import current_tiers
from .rollup import Rollups


def network(store, owner):
    nodes=[];edges=[]
    summaries=Rollups(store).search(owner)
    records=store.search(owner,'',limit=100)
    for row in records:
        doc=store.event(owner,row['id'])
        nodes.append({'id':row['id'],'kind':row['source_type'],'level':'raw',
            'label':doc['content']['title'] or row['text'][:36], 'text':row['text'],
            'period':row['occurred_at'] or '', 'evidence_ids':[row['id']]})
    for summary in summaries:
        nodes.append({'id':summary['id'],'kind':'summary','level':summary['level'],
            'label':summary['period'],'text':summary['summary'],'period':summary['period'],
            'evidence_ids':summary['event_ids']})
    graph=store.graph(owner,100)
    tiers=current_tiers(store,owner)
    for node in graph['nodes']:
        nodes.append({'id':node['id'],'kind':node['kind'],'level':'entity','label':node['label'],
            'tier':tiers.get(node['id'],{}).get('tier','') ,
            'text':node['label'],'period':'','evidence_ids':list(dict.fromkeys(e['event_id'] for f in graph['facts'] if f['subject_id']==node['id'] for e in f['evidence']))})
    ids={n['id'] for n in nodes}
    for summary in summaries:
        # child_ids encode immediate compression inputs. Day summaries link raw evidence.
        children=summary['child_ids'] or summary['event_ids']
        for child in children:
            if child in ids:
                edges.append({'source':child,'target':summary['id'],'kind':'compresses','label':'压缩汇总'})
    for fact in graph['facts']:
        target=fact['object'].get('node_id')
        if target and target in ids:
            edges.append({'source':fact['subject_id'],'target':target,'kind':'association','label':fact['predicate']})
        for evidence in fact['evidence']:
            if evidence['event_id'] in ids:
                edges.append({'source':evidence['event_id'],'target':fact['subject_id'],'kind':'evidence','label':fact['predicate']})
    # Similarity links are computed, not asserted: they say two records read
    # alike, never that a fact connects them. The kind keeps that distinction
    # visible to the agent, which is told not to treat them as evidence.
    try:
        for source,target,score in store.index().neighbours(owner,[n['id'] for n in nodes]):
            edges.append({'source':source,'target':target,'kind':'similar',
                'label':'语义相似 '+str(round(score*100))+'%'})
    except Exception:
        pass
    edges=list({(e['source'],e['target'],e['kind'],e['label']):e for e in edges}.values())
    return {'type':'memory.network','nodes':nodes,'edges':edges,
        'scope':'最近 100 条原文、当前有效摘要和最多 100 条已确认事实；视图之外的证据可点选查看。compresses 向上汇总，association 是已确认实体关系，evidence 指向原文，similar 只是向量相似度（不是断言的事实关系）。'}
