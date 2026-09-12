# Memory v1

Graph memory: contract, store, agents and the HTTP service shared by the PC app and Web.

- `validate.py` / `build_schema.py` / `contract.schema.json` — the ingest and changeset contract.
- `blocks.py` / `chat-blocks.schema.json` — the `chat.blocks` presentation contract both UIs render.
- `store.py` — SQLite queue, transactional graph writes, one-shot confirm tokens.
- `agent.py` — bounded LLM curator: proposes changesets, never writes facts.
- `chat.py` / `agent_tools.py` / `pi_runtime.py` — the chat command protocol and its two runtimes.
- `rollup.py` / `network.py` / `presentation.py` — day/week/month compression and the two projections.
- `connectors.py` / `gotify_puller.py` — read-only Gotify and GitHub import with durable cursors.

## Run

From the **repository root**, with the project virtual environment:

```powershell
python -m unittest discover -s backend/memory_v1 -t .
python -m backend.memory_v1.build_schema   # regenerate contract.schema.json
python -m backend.memory_v1.blocks         # regenerate chat-blocks.schema.json
python -m backend.memory_v1.server         # 127.0.0.1:18081
python -m backend.memory_v1.worker         # optional background pass, every 60s
python -m backend.memory_v1.live_smoke     # opt-in real-model check, synthetic data only
```

Modules use package-relative imports, so `-t .` (or `PYTHONPATH=.`) is required.
Generated schema files are committed alongside the generator that produced them.
`Start-NekoHub.ps1` at the repository root starts Gotify, the service, the worker,
the social bridge and the desktop app with the local DPAPI-protected configuration.

## Trust boundary

- Owner comes from the authenticated session, never from input JSON. No client `owner_id`.
- `evidence_texts` and `existing_node_ids` come only from an owner-scoped repository.
- Validation proves quote equality and structural integrity, not truth or semantic entailment.
- Review promotes a candidate to active in one transaction, checking ownership, `expected_version`,
  immutable evidence, idempotency hash and audit writes. The model has no path around it.
- **The agent has no delete capability.** Deletion is a proposal with a one-shot, 10-minute,
  content-hash-bound action ID; only an explicit user confirm applies it, and it is a soft delete.
- Records, summaries, tool results, web pages and view context are data, never instructions.
- SQLite foreign keys must be enabled per connection. Direct SQL writers bypass API constraints;
  SQLite is not itself a row-level authorization system.

See `docs/graph-memory-v1.md` and `docs/memory-integration.md` at repository root.
