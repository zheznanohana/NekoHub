"""Client viewport is a selection hint, not trusted memory or instructions."""
from jsonschema import Draft202012Validator
from .network import network

SCHEMA={'type':'object','additionalProperties':False,'properties':{
    'selected_ids':{'type':'array','maxItems':20,'uniqueItems':True,'items':{'type':'string','maxLength':160}},
    'visible_ids':{'type':'array','maxItems':500,'uniqueItems':True,'items':{'type':'string','maxLength':160}},
    'levels':{'type':'array','uniqueItems':True,'items':{'enum':['raw','day','week','month','entity']}},
    'query':{'type':'string','maxLength':1000}},'required':['selected_ids','visible_ids','levels','query']}

def resolve(store,owner,context=None):
    context=context or {'selected_ids':[],'visible_ids':[],'levels':[],'query':''}
    Draft202012Validator(SCHEMA).validate(context)
    ids={n['id'] for n in network(store,owner)['nodes']}
    return {**context,'selected_ids':[i for i in context['selected_ids'] if i in ids],
            'visible_ids':[i for i in context['visible_ids'] if i in ids]}

def read_node(store,owner,node_id,direction=None):
    graph=network(store,owner);nodes={n['id']:n for n in graph['nodes']}
    if node_id not in nodes:
        raw=store.event(owner,node_id)
        return [{'type':'memory.cards','items':[{'id':node_id,'text':raw['content']['text']}]}]
    selected={node_id}
    for e in graph['edges']:
        if direction in ('parents','both') and e['source']==node_id:selected.add(e['target'])
        if direction in ('children','both') and e['target']==node_id:selected.add(e['source'])
    graph['nodes']=[n for n in graph['nodes'] if n['id'] in selected]
    graph['edges']=[e for e in graph['edges'] if e['source'] in selected and e['target'] in selected]
    return [graph]
