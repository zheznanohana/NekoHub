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
支持 text、memory.cards、memory.network、memory.graph、memory.summaries、memory.table、memory.diary、memory.action、memory.receipt。
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
/memory.diary.read {"from":"2026-03-01","to":"2026-03-05","text":""}
/memory.diary.write {"day":"2026-03-01","text":"这一天的记录"}
```

自然语言聊天有最多 4 步的读取循环，可先摘要后原文，再回答并附来源。精确字段筛选由程序执行。

## 检索（RAG）

`backend/memory_v1/retrieval.py`。两层，第二层可选。

**第一层：BM25，无外部依赖，默认开启。** SQLite FTS5，但两种现成分词器都不能用：
`trigram` 永远匹配不到两字中文查询，`unicode61` 把整段汉字当作一个 token，
查「群组」命中不了「在群组」。所以索引和查询两侧都把 CJK 切成一字一 token，
查询时拼成短语匹配（`"群 组"`），既恢复子串语义又保留 BM25 排序；
拉丁词整体保留并转小写，按前缀匹配。索引增量维护，跟随内容哈希与软删除。

**第二层：向量，需要配置才开启。** 设置 `MEMORY_EMBED_BASE_URL` / `MEMORY_EMBED_MODEL`
（任意 OpenAI 兼容 `/embeddings` 端点）后，向量与 BM25 结果用 RRF 融合。
向量按 batch 增量生成，存在 `memory_vectors`，内容变了自动失效。
**DeepSeek 目前没有 embeddings 接口（实测 404），所以语义层需要另配一个提供方。**
未配置时只跑 BM25；提供方报错时自动降级为 BM25，不会让查询失败。
`GET /status` 的 `retrieval` 字段（`lexical` / `hybrid`）告诉前端当前实际跑的是哪一层。

实测对比（1059 条真实数据）：
`群组` 从 0 → 9 条且相关项排第一；`下载` 0 → 24 条；`福利群` 0 → 4 条。
仍然查不到的：`电报`→Telegram、`安装包`→apk。这类同义/跨语言改写只有向量层能解决，
在配好 embeddings 之前它就是查不到——这一点不要当成已经做完。
Agent 可以读取结构化表，不需要截图或 SQL 权限。写命令只生成待确认操作；模型没有 confirm 工具。
用户点击确认是独立 HTTP 操作，绑定用户、一次性 ID、10 分钟有效期及原文版本哈希。

## 日记表

每天一行：你亲笔写的日记、当天记录条数与来源、该日自动摘要。只列出确实有记录或有日记的日期，不补空白天。
读用 `GET /diary`（可带 from/to/text），写用 `POST /diary {"day","text"}`。PC 和 Web 都是左表右编辑器。

- **你直接写是直接生效**（你就是作者）；**Agent 的 `memory.diary.write` 只生成待确认卡片**，确认后才写入。
- 每次编辑保留上一版到 `memory_diary_history`，并把新版本作为一条 manual 记录发布，
  所以日记内容可以被当作证据引用，改写也不会抹掉原来写过的话。
- 日记优先于自动摘要：提示词里明确「用户亲笔，优先级高于自动摘要」。

## 旧版数据导入

旧版桌面端的 `nekohub.db`（扁平 `messages` 表）用 `backend/memory_v1/import_legacy.py` 导入：

```
python -m backend.memory_v1.import_legacy <旧 nekohub.db 路径>
```

设置 `MEMORY_LEGACY_DB` 后，PC 的「导入旧版数据」按钮与 Web 同名按钮直接调用 `POST /import/legacy`。
路径由服务端环境变量提供，客户端不能指定路径，避免任意文件读取。

导入规则：逐行原样复制为 `source.type=import`，不改写、不摘要、不丢弃；
`external_id` 用旧自增 ID，所以重复导入幂等。安卓转发器放在正文首行的包名会提取到
`content.fields.app_package`，`legacy_id / appid / priority` 一并进入 fields，正文只留标题与内容。

一次性导入上千条会留下同样多的待处理任务，每条一次模型调用。
`MEMORY_WORKER_BATCH`（默认 1）控制 worker 每 60 秒处理几条；导入后临时调高，之后调回。

## 分层图与删除边界

详细事实与原文不被摘要覆盖；日摘要为细层，周摘要为阶段层，月摘要为宏观层。
上层保存 child_ids，下层可反查 parent_ids；所有层保留 event_ids 原文引用。
跨月的一周不强塞入单个月摘要，使用落在该月的日摘要或原文补齐。
回忆先读摘要，精确问题可以展开原文。新记录、修改或删除使旧摘要失效，等待重建。
时间分组原型使用 UTC，未实现用户自定义时区分组。
目前图形视图是二维分层网络：raw / day / week / month / entity 按层排环，实线为压缩汇总、虚线为实体关联、点线为原文证据。
PC 与 Web 都可点选节点、沿 parents/children 展开、打开原文并导出 JSON；并非三维交互引擎。

**确认边界：只有删除需要你点确认。**
新增、修改、写日记由 Agent 直接生效，全部进 `memory_audit`，修改是软删除旧版 + 新建，可回溯。
删除仍然只产生待确认卡片：一次性 action ID、10 分钟有效、绑定原文内容哈希。
**Agent 没有删除权限**，日报只能建议删除并给出理由和受影响事实数。
压缩不自动删除原文。软删除使记录不再参与检索；数据库/审计/备份中的物理清除尚未实现。

## 每日自我整理

`backend/memory_v1/curate.py`，由 worker 每天跑一次，和日报一起出现。

- **分层（tier）**：Agent 给每个实体节点评 `core / active / background / dormant`，
  依据是连接数、证据条数和最近活动，不是年代。这是元数据，不覆盖任何事实，
  旧评级进 `memory_node_tier_history`，所以 Agent 自己就能应用。
- **合并建议**：两个节点疑似同一实体时只能**提议**，因为合并会改写事实指向谁。
  建议出现在日报里等你确认，Agent 无权执行。
- tier 会随 `memory.network` 一起下发，前端据此显示重要性。
- 整理失败不影响日报：当天分层保持不变，并在日报里如实说明。

## 连接器

`backend/memory_v1/sources.py` + 前端「连接器」面板（PC 与 Web 都有）。
目前支持 Gotify、GitHub Issue、RSS/Atom，由 `KINDS` 声明字段，前端按声明渲染表单，
服务端拒绝声明之外的字段。

**凭据是单向的**：写进去之后，任何读取路径只返回 `has_secret`，不返回值。
所以就算页面被注入、或模型拿到读取工具，也拿不到它从未见过的 token。
移除连接器不删除已导入的记录。启用的连接器由 worker 按自己的节奏拉取，
单个连接器失败只记录在它自己的 `last_result` 上，不影响其他来源。

旧的 `MEMORY_GOTIFY_*` / `MEMORY_GITHUB_*` 环境变量和 `/sync/<source>` 仍然有效，
适合无界面部署；界面上新增的来源走连接器表。

## 记忆网络视图

力导向图（`backend/memory_v1/layout.py`，PC 与 Web 各自渲染同一份数据）：
连接紧密的记忆聚在一起，孤立的被推开；圆点大小 = 连接数；颜色 = 层级。
可拖节点、滚轮缩放、拖空白平移，点选高亮直接连接并淡化其余。

**位置不是语义。** 布局只决定画法，含义只在 `memory.network` 的 `edges[].kind` 里
（`compresses` 压缩汇总 / `association` 实体关联 / `evidence` 原文证据）。
提示词明确要求 Agent 不得根据坐标或距离推断关系。

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
