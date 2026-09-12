# NekoHub Memory Agent

## 职责

专职记忆 Agent 共享同一套模型指令，按三种任务运行：
- ingest：新记录抽取、节点复用、关联、重复判断。
- reconcile：对提供的冲突记录提出取代/争议建议。
- reflect：定期审阅选中的记录，提出有原文证据的整理建议。

它是有明确输入和预算的后台工作流，而非无限循环常驻对话。模型负责判断，程序负责持久化一致性。

## 执行链

Gotify/速记 → 事件入库 → 持久化任务 → 检索同用户相关节点/事实/原文 → Memory Agent → changeset 或 skip → 校验 → 自动应用/审核 → 更新图表与检索索引。

任务调度器与检索器提供限定大小的快照，Agent 最多调用两次模型：首次生成，校验失败后一次修复。
网络失败交回队列处理，不在模型循环里无限重试。任务 ID 必须绑定不可变快照；重跑同任务使用相同幂等键。

## 已实现

- backend/memory_v1/agent.py：Chat Completions 兼容适配器、专用指令、三种任务模式、skip 输出、一次修复预算。
- 校验原文证据、节点引用、候选状态、任务标识和快照内目标版本。
- 远程模型使用 HTTPS，支持本机 HTTP；阻止重定向转发凭据；错误不记录原始模型响应。
- test_agent.py 使用模拟模型验证，无真实用户数据出站。

## 配置与调用

设置 MEMORY_LLM_BASE_URL（例如服务商的 /v1 基地址）、MEMORY_LLM_API_KEY、MEMORY_LLM_MODEL。
密钥不写进 Git，不从旧配置静默复制。服务商需支持 /chat/completions 和 json_object 输出模式；不同接口另写适配器。

```python
from agent import ChatCompletions, MemoryAgent

agent = MemoryAgent(ChatCompletions.from_env())
proposal = agent.propose(
    job_id="persisted-job-id",
    mode="ingest",
    events=owner_scoped_events,
    known_nodes=retrieved_nodes,
    known_facts=retrieved_facts,
)
```

以上示例中的输入由后续持久化队列和检索服务提供，不是直接运行的独立入口。

## 自动落库政策（待实现）

应用服务支持自动确认可靠来源的明确、无冲突新增事实；人工编辑、跨实体合并、推断、撤回与冲突保留审核。
不需要每条记忆都让用户点击确认，但不能只凭模型自报置信度批准。
expected_version 必须在实际写入事务内再核对；本 Agent 检查的是读取快照，不解决并发写入。
查询/证据读取始终按已认证 owner 隔离。任意外部资料不能改变模型配置、网络目的地或申请额外工具权限。

## 当前边界

这次已实现模型调用适配器与提议工作流，测试使用模拟模型。
尚未配置真实模型或进行线上请求；尚未实现队列、检索、事务 apply、UI 与 Gotify 的端到端接线。
Agent 不执行用户待办、不直接发消息、不运行 SQL，也不主动清除原文。
图表仍是同一事实库的投影；模型更换不应改变业务主键和历史。
