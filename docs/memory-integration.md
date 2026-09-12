# 记忆工作台：集成与运行记录

## 当前已接入的代码

- PC：新增原生“记忆工作台”页，调用本机记忆服务。原有聊天和通知页保留。
- Web：新增 /memory 页面与侧栏入口，Flask 注册 /api/memory/v1 蓝图。
- 同一后台支持结构化聊天命令、确认卡、持久化任务、模型抽取、人工审核、关系图和表格。
- Gotify 分页读取、GitHub Issue 只读导入经过模拟接口测试。GitHub 的仓库由环境配置固定，Token 不进入聊天。
- Gotify 已在本机实际部署（官方 v3.1.0 发行版二进制，127.0.0.1:18080），Client Token 由 worker 拉取，真实通知已完整落到原文表。详见 `integrations/gotify/README.md`。
- 聊天引擎为 Pi Agent（`@earendil-works/pi-agent-core`），通过 `integrations/pi/runner.mjs` 子进程运行，工具由 Python 宿主执行。原有 Chatbox 与模型配置界面不变。
- GitHub 有官方现成 MCP Server（https://github.com/github/github-mcp-server）；本轮没有引入整套 MCP 客户端，而是实现较小的官方 REST 只读适配器。没有社交平台发帖或 GitHub 写操作。

## 固定输入和输出

输入 /chat：`{"schema_version":"1.0","message":"..."}`。
输出：chat.blocks，严格 JSON Schema 见 backend/memory_v1/chat-blocks.schema.json。
支持 text、memory.cards、memory.network、memory.graph、memory.summaries、memory.table、memory.action、memory.receipt。
`/chat` 可附带 `view_context`（selected_ids / visible_ids / levels / query）；服务端只保留确实存在于当前图中的 ID，前端伪造的 ID 会被丢弃。
模型不输出 HTML；Vue 与 PC 按类型渲染并转义文本。表格可以打开、查看、下载 JSON，支持横向字段与纵向记录模式。
表格含原始记录、已确认事实、日/周/月摘要；source 字段用于区分实际导入的数据源，不为尚未接入的来源伪造数据。

固定表字段：id / level / source / subject / relation / content / period / status / parent_ids / child_ids / evidence_ids。
当前导出是有范围的工作视图（最近 100 条原文、最多 200 条事实与摘要），不是全库备份。

## Agent 的读写工具

```
/memory.create {"text":"今天开始整理项目"}
/memory.search {"text":"项目"}
/memory.update {"event_id":"从查询结果取得","text":"更正后的记录"}
/memory.delete {"event_id":"从查询结果取得"}
/memory.graph {}
/memory.export {}
/memory.table.read {"source":"manual","level":"raw","text":"项目"}
/memory.recall {"text":"项目"}
/memory.expand {"summary_id":"从回忆结果取得"}
/memory.compress {"level":"day","period":"2026-09-12"}
/memory.daily {}
```

自然语言聊天有最多 4 步的读取循环，可先摘要后原文，再回答并附来源。精确字段筛选由程序执行；当前文本检索为 SQLite 子串匹配，不是 embedding 语义搜索。
Agent 可以读取结构化表，不需要截图或 SQL 权限。写命令只生成待确认操作；模型没有 confirm 工具。
用户点击确认是独立 HTTP 操作，绑定用户、一次性 ID、10 分钟有效期及原文版本哈希。

## 分层图与删除边界

详细事实与原文不被摘要覆盖；日摘要为细层，周摘要为阶段层，月摘要为宏观层。
上层保存 child_ids，下层可反查 parent_ids；所有层保留 event_ids 原文引用。
跨月的一周不强塞入单个月摘要，使用落在该月的日摘要或原文补齐。
回忆先读摘要，精确问题可以展开原文。新记录、修改或删除使旧摘要失效，等待重建。
时间分组原型使用 UTC，未实现用户自定义时区分组。
目前图形视图是二维分层网络：raw / day / week / month / entity 按层排环，实线为压缩汇总、虚线为实体关联、点线为原文证据。
PC 与 Web 都可点选节点、沿 parents/children 展开、打开原文并导出 JSON；并非三维交互引擎。

**Agent 没有删除权限。** 日报只能建议删除，给理由及受影响事实数；用户确认后才软删除。
压缩不自动删除原文。软删除使记录与相关记忆不再参与检索；数据库/审计/备份中的物理清除尚未实现。

## 运行

在项目根目录使用 Python 3.12，安装 backend/memory_v1/requirements.txt。
参考 .env.example 设置环境变量（程序不自动读取 .env，需由启动器注入）。不要把密钥写入仓库。
MEMORY_SERVICE_TOKEN 至少 16 字符。PC 和本机服务使用同一个 Token。
MEMORY_DB_PATH 必须为有效绝对路径；服务、Web、worker 必须指向同一数据库。

```
python -m backend.memory_v1.server
python -m backend.memory_v1.worker
```

第一条启动本机 127.0.0.1:18081；第二条是可选后台 worker，每分钟处理一条记忆，按内容哈希压缩已关闭的日/周/月，并保存每日整理报告。
worker 不是常驻无限模型对话；未变内容跳过模型调用。当前不自动启动、不自动同步第三方来源，也不自动重试失败任务。
Web 继续使用原有 JWT 登录；新页面 /memory。既有服务含默认开发认证配置，公网部署前需单独加固旧路由、密钥和 CORS。

## 验证命令

```
python -m unittest discover -s backend/memory_v1 -v
python -m backend.memory_v1.blocks
python -m backend.memory_v1.live_smoke
```

live_smoke 需要模型环境变量，只使用模拟记录，在临时数据库里测试真实模型调用；不导入用户历史、不打印密钥。

## 尚待完善

旧插件历史回填、向量索引、全量导出分页、失败任务重试 UI、细粒度谓词校验仍待补齐。
社交桥可启动并监听 127.0.0.1:18082，但未登录任何平台账号：Telegram/Discord/OneBot 仍需各自 Token 与 `allowed_sessions` 白名单。
`agent.improve.propose` 只把问题、改进和测试计划写入 `agent_improvements` 表，不自行改代码、提示词或权限。
PC 在配置 MEMORY_SERVICE_TOKEN 后将新收到的 RSS/IMAP/Web3 通知送入记忆队列；未配置时保留原行为。尚未处理每个插件独立开关、发送失败重试和历史回填。
Gotify 统一由后台 worker 的 GotifyPuller 拉取，PC 不再次导入 Gotify 数据。增量和历史回填分别保存 SQLite 游标，每页写入成功后才推进；每轮最多增量一页、历史一页。重启续拉、重复页幂等。当前同一用户/来源只运行一个 puller。

## 本轮测试结果

- 42 项自动化测试通过：鉴权、幂等、CRUD 确认、日报不自动删除、摘要失效与展开、模拟 Gotify/GitHub、Agent 表格读取、Pi 工具回路、桌面渲染器覆盖全部 block 类型。
- 真实 DeepSeek（`deepseek-flash`）联调通过 `live_smoke`：原文入库 → 模型提议 → 审核写图 → 结构化表格 → 日摘要。
- Pi Agent 真机联调通过：经本机服务 `/chat` 提问，Agent 依次调用 graph/table/search/recall 工具并引用真实记录作答。
- Gotify 真机联调通过：发送测试通知 → worker 拉取 → 原文入库 → 出现在结构化表；第二次 tick 幂等不重复。
- 四个本机服务同时在位：Gotify 18080、记忆服务 18081、社交桥 18082、后台 worker。PC 桌面端已启动。
- Web 生产构建通过；现有前端包有大 chunk 警告，安装依赖时审计提示既有依赖风险，未做破坏性自动升级。
- 模型密钥、Gotify 管理员密码与两种 Token 由 DPAPI 保存在 `%LOCALAPPDATA%\NekoHubMemory\environment.xml`，不进入仓库。
