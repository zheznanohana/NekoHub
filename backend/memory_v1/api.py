"""Reusable authenticated Flask blueprint for NekoHub web and local service."""
import os
import uuid
from flask import Blueprint, jsonify, request
from jsonschema import ValidationError
from .agent import AgentError, ChatCompletions, MemoryAgent
from .chat import envelope, render_command, route, run_chat
from .connectors import github_sync, gotify_sync
from .rollup import Rollups
from .store import Conflict


def make_blueprint(store, authenticate, identity, complete=None):
    bp = Blueprint("memory_v1", __name__)

    def model(messages):
        return complete(messages) if complete else ChatCompletions.from_env()(messages)

    def body(allowed, required=()):
        data = request.get_json()
        if not isinstance(data, dict) or set(data) - set(allowed) or not set(required) <= set(data):
            raise ValueError("invalid request fields")
        return data

    def response(blocks):
        from .blocks import VALIDATOR
        value = envelope(uuid.uuid4().hex, blocks)
        VALIDATOR.validate(value)
        return jsonify(value)

    @bp.errorhandler(Exception)
    def error(exc):
        from werkzeug.exceptions import HTTPException
        if isinstance(exc, HTTPException):
            status, message = exc.code, exc.name
        elif isinstance(exc, Conflict):
            status, message = 409, str(exc)
        elif isinstance(exc, KeyError):
            status, message = 404, "Record or configuration not available"
        elif isinstance(exc, (ValueError, ValidationError)):
            status, message = 400, "Invalid command, format, evidence or context size"
        elif isinstance(exc, AgentError):
            status, message = 502, "Memory model request failed; data remains stored"
        else:
            status, message = 502, "Memory operation failed; inspect local diagnostics"
        return jsonify({"schema_version": "1.0", "kind": "memory.error", "request_id": uuid.uuid4().hex,
                        "code": "VERSION_CONFLICT" if status == 409 else "NOT_FOUND" if status == 404 else "VALIDATION_ERROR" if status == 400 else "INTERNAL_ERROR",
                        "message": message, "retryable": status >= 500}), status

    @bp.route("/status")
    @authenticate
    def status():
        return jsonify({"llm_configured": bool(complete or (os.getenv("MEMORY_LLM_BASE_URL") and os.getenv("MEMORY_LLM_MODEL"))), "gotify_configured": bool(os.getenv("MEMORY_GOTIFY_URL") and os.getenv("MEMORY_GOTIFY_TOKEN")), "github_configured": bool(os.getenv("MEMORY_GITHUB_REPO")), "jobs": store.jobs(identity())})

    @bp.route("/daily/latest")
    @authenticate
    def latest_daily():
        import json
        with store.db() as con:
            exists=con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='memory_reports'").fetchone()
            row=con.execute("SELECT blocks FROM memory_reports WHERE owner_id=? ORDER BY day DESC LIMIT 1",(identity(),)).fetchone() if exists else None
        if not row:
            return response([{"type":"text","text":"暂无后台日报，可点击整理日报即时生成。"}])
        blocks=json.loads(row[0])
        for block in blocks:
            if block['type']=='memory.action':
                try:block['action_id']=store.prepare_action(identity(),block['command'])
                except KeyError:
                    block.clear();block.update(type='text',text='该删除建议对应记录已处理。')
        return response(blocks)

    @bp.route("/chat", methods=["POST"])
    @authenticate
    def chat():
        data = body(("schema_version", "message", "view_context"), ("schema_version", "message"))
        if data["schema_version"] != "1.0" or not isinstance(data["message"], str) or not 0 < len(data["message"]) <= 10000:
            raise ValueError("invalid chat input")
        if data["message"].startswith("/"):
            command = route(data["message"], model)
        else:
            if os.getenv('MEMORY_AGENT_RUNTIME')=='pi' and complete is None:
                from .pi_runtime import run_pi
                return response(run_pi(data['message'],store,identity(),data.get('view_context')))
            output = run_chat(data["message"], store, identity(), model, view_context=data.get('view_context'))
            if isinstance(output, list):
                return response(output)
            command = output
        if command["command"] == "memory.reply":
            raise ValueError("memory.reply is reserved for the agent tool loop")
        if command["command"] == "memory.daily":
            from .daily import report
            return response(report(store, identity(), model))
        if command["command"] == "memory.compress":
            return response([{"type": "memory.receipt", "data": Rollups(store).summarize(identity(), command["level"], command["period"], model)}])
        return response(render_command(store, identity(), command))

    @bp.route("/actions/<action_id>/confirm", methods=["POST"])
    @authenticate
    def confirm(action_id):
        body(())
        return response([{"type": "text", "text": "操作已执行"}, {"type": "memory.receipt", "data": store.confirm_action(identity(), action_id)}])

    @bp.route("/events", methods=["POST"])
    @authenticate
    def ingest():
        document = request.get_json()
        if not isinstance(document, dict) or not isinstance(document.get("source"), dict):
            raise ValueError("source object required")
        source_type=document["source"].get("type")
        if source_type not in ('manual','gotify','rss','imap','web3','github','import'):
            raise ValueError("unsupported source")
        document["source"]["instance_id"] = "manual-api" if source_type=='manual' else 'client:'+source_type
        document["provenance"] = "user_authored" if source_type=='manual' else 'external'
        return jsonify(store.ingest(identity(), document)), 202

    @bp.route("/events/<event_id>")
    @authenticate
    def event(event_id):
        return jsonify(store.event(identity(), event_id))

    @bp.route("/graph")
    @authenticate
    def graph():
        return response([{"type": "memory.graph", "data": store.graph(identity())}])

    @bp.route("/process", methods=["POST"])
    @authenticate
    def process():
        body(())
        result = store.process_one(identity(), MemoryAgent(model), auto_apply=os.getenv("MEMORY_AUTO_APPLY", "false").lower() == "true")
        return response([{"type": "memory.receipt", "data": result or {"state": "idle"}}])

    @bp.route("/jobs/<job_id>")
    @authenticate
    def proposal(job_id):
        return jsonify(store.proposal(identity(), job_id))

    @bp.route("/jobs/<job_id>/review", methods=["POST"])
    @authenticate
    def review(job_id):
        data = body(("approve",), ("approve",))
        if type(data["approve"]) is not bool:
            raise ValueError("approve must be boolean")
        return response([{"type": "memory.receipt", "data": store.review(identity(), job_id, approve=data["approve"])}])

    @bp.route("/compress", methods=["POST"])
    @authenticate
    def compress():
        data = body(("level", "period"), ("level", "period"))
        return response([{"type": "memory.receipt", "data": Rollups(store).summarize(identity(), data["level"], data["period"], model)}])

    @bp.route("/sync/<source>", methods=["POST"])
    @authenticate
    def sync(source):
        # Global connector credentials belong only to the configured single owner.
        if identity() != os.getenv("MEMORY_CONNECTOR_OWNER", "admin"):
            raise KeyError("connector")
        data = body(("page", "since"))
        if source == "gotify":
            since = data.get("since", 0)
            if type(since) is not int or since < 0:
                raise ValueError("invalid since")
            result = gotify_sync(store, identity(), os.environ["MEMORY_GOTIFY_URL"], os.environ["MEMORY_GOTIFY_TOKEN"], start_since=since)
        elif source == "github":
            page = data.get("page", 1)
            if type(page) is not int or not 1 <= page <= 10000:
                raise ValueError("invalid page")
            result = github_sync(store, identity(), os.environ["MEMORY_GITHUB_REPO"], os.getenv("MEMORY_GITHUB_TOKEN", ""), page=page)
        else:
            raise ValueError("unknown connector")
        return response([{"type": "memory.receipt", "data": result}])

    return bp
