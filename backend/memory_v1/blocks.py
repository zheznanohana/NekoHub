"""Strict, versioned presentation contract shared by the two renderers."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from .chat import COMMAND_SCHEMA
from .validate import SCHEMA as MEMORY_SCHEMA


def obj(properties, required=None):
    return {"type":"object", "additionalProperties":False, "properties":properties, "required":list(properties) if required is None else required}


S={"type":"string"}; N={"type":"integer"}; IDS={"type":"array","items":S}
def array(items): return {"type":"array","items":items}
def block(kind,fields,required=None):
    return obj({"type":{"const":kind},**fields}, None if required is None else ["type",*required])

CARD=obj({"id":S,"text":S,"occurred_at":{"type":["string","null"]},"source_type":S,"content_hash":S},["id","text"])
SUMMARY=obj({"id":S,"level":{"enum":["day","week","month"]},"period":S,"summary":S,"event_ids":IDS,"child_ids":IDS})
ROW=obj({"id":S,"level":{"enum":["raw","detail","day","week","month"]},"source":S,"subject":S,"relation":S,"content":S,"period":{"type":["string","null"]},"status":S,"parent_ids":IDS,"child_ids":IDS,"evidence_ids":IDS,"fields":{"type":"object","additionalProperties":{"type":["string","number","boolean","null"]}}})
DIARY_ROW=obj({"day":S,"text":S,"version":N,"updated_at":{"type":["string","null"]},"event_count":N,
                "event_ids":IDS,"sources":array(S),"summary":S,"summary_id":S})
TABLE=block("memory.table",{"columns":{"const":["id","level","source","subject","relation","content","period","status","parent_ids","child_ids","evidence_ids","fields"]},"rows":array(ROW),"scope":S})
BLOCKS=[block("text",{"text":S}), block("memory.cards",{"items":array(CARD)}),
        block("memory.network",{"nodes":array(obj({"id":S,"kind":S,"level":{"enum":["raw","day","week","month","entity"]},"label":S,"text":S,"period":S,"evidence_ids":IDS,"tier":S},["id","kind","level","label","text","period","evidence_ids"])),
              "edges":array(obj({"source":S,"target":S,"kind":{"enum":["compresses","association","evidence","similar"]},"label":S})),"scope":S}),
        block("memory.summaries",{"items":array(SUMMARY)}), TABLE,
        block("memory.diary",{"rows":array(DIARY_ROW),"scope":S}),
        block("memory.graph",{"data":obj({"nodes":array({"$ref":"#/$defs/node"}),"facts":array({"$ref":"#/$defs/fact"})})}),
        block("memory.action",{"action_id":S,"command":COMMAND_SCHEMA,"expires_in":N,"reason":S,"preview":S,"affected_facts":N},["action_id","command","expires_in"]),
        block("memory.receipt",{"data":obj({"state":S,"event_id":{"type":["string","null"]},"job_id":S,"id":S,"reason":S,"imported":N,"duplicate":N,"failed":N,"source":S,"day":S,"version":N,"indexed":N,"dropped":N,"pending":N,"embed_state":S,"embed_embedded":N,"embed_pending":N,"graded":N,"changed":N,"merge_suggestions":N,"entries":N,"feed":S,"kind":S,"name":S,"error":S,"history_complete":{"type":"boolean"},"next_since":{"type":["integer","null"]},"next_page":{"type":["integer","null"]}},[])})]
SCHEMA={"$schema":"https://json-schema.org/draft/2020-12/schema","$defs":MEMORY_SCHEMA["$defs"],
        **obj({"schema_version":{"const":"1.0"},"kind":{"const":"chat.blocks"},"request_id":S,"blocks":array({"oneOf":BLOCKS})})}
VALIDATOR=Draft202012Validator(SCHEMA)

if __name__=="__main__":
    Path(__file__).with_name("chat-blocks.schema.json").write_text(json.dumps(SCHEMA,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
