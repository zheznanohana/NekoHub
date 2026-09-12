# NekoHub：从通知中心到日常记录与记忆管理

## 0. 本次边界

已获取 NekoHub main 与 Gotify 上游源码，添加 Gotify Compose 部署底座。
本文是结合现有代码的实施设计，尚未实现记忆服务、向量检索、自动抽取或生产调度。
尚未连接用户 Gotify 实例，没有导出真实消息。源码下载与消息 dump 是两件事。

## 1. 现有实现与直接影响

- PC 实际使用 Python / PySide6，根 README 中 PyQt5 描述与代码不一致。
- `pc/storage.py` 的 SQLite messages 仅有 id/appid/title/message/priority/date；id 为主键，未区分实例和用户，extras 未保存。
- `pc/ui_app.py` 的消息入口已调用 upsert_messages，适合接增量事件；历史刷新目前只取最近 50 条。
- `pc/gotify_client.py` 只取最新一页；断线期间超过页长的消息有遗漏风险。轮询还在回调前推进游标，持久化失败可能漏处理。
- `pc/ai_core.py` 从最近 200 条筛选有限消息并拼接上下文，不是按问题检索，也缺少原文证据引用。
- `pc/gotify_ws.py` 状态消息包含带 Token 的 URL，接入时应脱敏，凭据放系统凭据库或服务端密钥配置。
- `web/app` 已有 Flask、SQLAlchemy、调度器及 Gotify 服务，优先复用共享后端，避免 PC/Web/Android 各维护一套记忆。

## 2. 三种方案与选择

| 方案 | 结构 | 适用情况 | 代价 |
|---|---|---|---|
| A 纯本机 | Gotify 本地进程/容器 + Python worker + SQLite + 可替换向量索引 | 单台电脑、先跑通 MVP | PC 关机停收；跨端同步需后补 |
| B 共享后端（推荐） | Gotify 独立服务 + 现有 Flask 扩展 + worker + PostgreSQL/pgvector | PC/手机统一记录，持续处理 | 需要常驻主机、备份与监控 |
| C 深度修改 Gotify | 在 Go 服务内增加记录、抽取和记忆 API | 明确要长期维护 Go 后端 | 上游升级耦合最重，现有 Python 逻辑需迁移 |

建议按 B 的数据模型设计，先交付 A 规模的 MVP。集成是同一套启动/设置体验，不必把 Python 与 Go 强塞进同一进程。
Gotify 保留通知入口与推送职责；NekoHub 持有规范记录和记忆。独立数据库，通过 API 对接，避免直接写 Gotify 的内部表。

## 3. 主链路

Gotify / 手写速记 / IMAP / RSS → 原始事件库 → 分类与去重 → 结构化候选 → 校验与审核 → 正式记录与记忆 → 全文/向量索引 → 检索问答。

重要：RSS、促销、系统心跳默认只归档或短期缓存，不自动变成“我的经历”。例如“文章提到跑步”不等于“我今天跑了步”。
用户手写、个人应用通知、外部资讯、AI 生成结果分开标识；AI 摘要排除出下一轮事实抽取，避免自我强化和通知循环。

## 4. Gotify 历史 dump 与持续同步

1. 新建专用 Client Token，仅用于当前用户可见消息的读取；发送使用另一个 Application Token。
2. 固定 source_instance_id 和 owner_id；实例 ID 使用内部 UUID，不把 Token 当标识。
3. 请求 GET /message?limit=200，随后用 since=本页最小 ID 继续向旧消息翻页。
4. **since 是 ID 小于该值，不是新于该值**。此语义已从当前下载的 Gotify api/message.go 核对。
5. 每页原文、extras、原始时间、获取时间和 SHA-256 入库，同一事务写同步进度；唯一键为 owner_id + source_instance_id + message_id。
6. dump 同时输出 JSONL 与 manifest（实例 ID、起止时间、最大 ID、条数、文件哈希），输出中排除凭据。
7. WebSocket 提供低延迟；重连后从最新页向旧翻到已持久化水位，事务提交后才推进水位。首次 dump 后也执行一次追平，覆盖导出期间的新消息。
8. 翻页失败指数退避；重放幂等；检测游标停滞。全量导出并非数据库级瞬时快照，期间发生的删除需记录这一限制。
9. 老 PC 数据库单独迁移；多实例来源不明确的旧记录进入 legacy source，避免按 message_id 错合并。
10. Gotify 已经删除的历史消息不在 API 导出范围。必要时从已有备份恢复到隔离实例再读，不修改运行中的数据库。

## 5. 自动落表：固定 schema + 可扩展字段

不是让模型随手 CREATE TABLE 或执行生成的 SQL。模型只输出符合 JSON Schema 的候选，服务端控制事务和写入。

| 表 | 职责与关键字段 |
|---|---|
| sources | owner_id、instance_id、source_type、信任等级、保留策略 |
| raw_events | source_id、external_id、payload、content_hash、occurred_at、ingested_at、deleted_at；来源内幂等 |
| records | owner_id、type、title、body、occurred_at、timezone、structured_data、status、version |
| record_evidence | record_id、raw_event_id、原文定位/摘录、抽取版本；每条事实可追溯 |
| entities / entity_aliases | 人、项目、地点及别名；模糊合并进入审核 |
| tasks | record_id、due_at、status、completed_at；更新时要求版本匹配 |
| expenses | record_id、amount_decimal、currency、merchant、category、transaction_ref；通知不是到账证明 |
| habits | record_id、habit_type、value、unit；只有真实记录才计完成 |
| memories | subject、predicate、object、valid_from/to、status、supersedes_id、confidence、review_at |
| memory_evidence | memory_id、record_id；汇总记忆可以关联多份证据 |
| chunks | record_id、content_hash、chunk_index、embedding_model/version、index_status |
| review_queue | candidate_json、reason、evidence、decision、reviewer、decided_at |
| jobs / outbox | dedupe_key、stage、attempts、next_retry_at、lease_until、error；事务性排队与失败重试 |
| audit_log | actor、object、before/after、reason、request_id、时间；支持撤销与变更追踪 |

候选例：用户速记“今天午饭 38 元，明天下午三点交周报”。
- 消费候选：amount=38，currency 未由上下文确定时留空并审核，不猜币种。
- 待办候选：交周报，due_at 按消息发生日期和来源时区解析；时间上下文不足时保留原文和待确认状态。
- 一个事件允许多条 record，共享证据；重复转发依靠交易号/来源事件 ID 辅助去重，不仅比较句子相似度。

## 6. 自动维护的边界和规则

三档控制：自动归档 → 自动生成候选 → 满足校验后自动确认。
- 明确格式的个人日志可以自动落表；LLM 推断、健康/财务敏感字段、人员别名合并默认进审核。
- 初始实验阈值可设高置信候选 ≥0.90 自动确认、0.65–0.90 审核、其余仅归档，但必须按标注样本校准；模型自报分数不单独作为批准依据。
- 通过来源信任、必填字段、证据一致性、类型约束、重复检测共同决定是否写入正式表。
- 偏好变更采用新版本：例如“现在不喝咖啡”关闭旧偏好的有效期，历史保留；互相冲突且时间不明的记忆待审核。
- 手动编辑优先，自动任务采用乐观锁，禁止后台抽取覆盖用户修正。
- 删除采用 tombstone，立刻从检索过滤，再清理向量、派生摘要和缓存；备份遵循单独保留周期，恢复时重放 tombstone。
- 原文默认不因“记忆衰减”被删除。衰减只影响排序/归档；永久固定、短期、到期复核分别管理。

建议调度（尚未启用）：
- 事件到达：幂等入库，事务 outbox 排抽取/索引任务；不要在 UI 线程跑模型。
- 每 5 分钟：租约过期任务重领、补漏同步、索引失败重试。
- 每晚：生成可重建的日记草稿、遗漏记录提示；按原始记录关联，不以昨日摘要为唯一证据。
- 每周：冲突记忆、实体合并候选、过期待办、长期偏好复核列表。
- 定期：备份并做恢复演练；检查队列积压、同步延迟、死信、引用正确率。自动通知只发有行动价值的变化。

## 7. RAG：结构化查询优先，语义检索补充

1. 识别日期范围、记录类型、实体、用户和来源过滤条件，所有召回路径都应用相同访问控制。
2. “本月花多少钱/还有几个待办”走服务端允许的结构化聚合，不让向量相似度代替精确统计；不同币种分别求和。
3. “上次为什么放弃某方案”走原文全文 + 向量混合召回，重排后取证据片段。中文需专门验证分词/多语言 embedding 效果。
4. 短通知整条索引；长邮件/日记按段分块，保留标题、来源、时间及段落定位。
5. 答案带 record_id 和原文跳转；区分原文事实、推断与待确认候选，无证据时明确缺少记录。
6. 原文是数据，不作为系统指令；检索结果中的工具调用、外发请求或 SQL 文本不执行。
7. 向量是可重建索引，不是唯一存档。记录 embedding 模型和维度，换模型新建索引，验证后切换。
8. 默认先本地保存；外部模型出站内容按来源开关、脱敏策略和用户配置控制。

## 8. 实施顺序与验收

M1 收件箱变成记录库：Gotify 部署、全量 dump、增量同步、来源命名空间、速记 API、时间线与原文详情。
验收：500+ 消息跨页全量一致；重复同步零重复；断网后超过一页仍补齐；事务失败不丢游标。

M2 自动落表：先做待办、消费、日记三类，JSON Schema、审核页面、编辑/撤销和 outbox。
验收：错误日期/币种不猜；同一通知重放不重复记账；人工编辑不被重算覆盖；模型离线仍正常收件。

M3 RAG：记录搜索、时间/类型筛选、混合召回、引用跳转、聚合查询。
验收：准备至少 30 个真实匿名化问答对，测试召回率、引用支持率、无证据回答、中文姓名检索和删除后零召回。

M4 长期记忆：偏好版本、项目进展、日/周草稿、复核与备份恢复。
验收：相互冲突记忆不静默覆盖；摘要可重建；恢复后仍保留删除/人工修正语义。

PC 增加“速记 / 时间线 / 待办 / 账本 / 记忆 / 审核”导航，保留现有通知与插件功能；第一阶段不要整体重写 UI。

## 9. 参考

- https://github.com/zheznanohana/NekoHub/tree/main/pc
- https://github.com/gotify/server
- https://gotify.net/api-docs
- 本地 Gotify api/message.go：分页定义与 since 语义。

## 10. 当前记忆维护方案对比（2026-09-12 官方资料核查）

以下是代表性候选，不是按市场份额或下载量排序。优缺点为针对 NekoHub 的工程判断，尚未做同机性能测试。

| 候选 | 官方描述的机制 | 对本项目的优势 | 代价/边界 |
|---|---|---|---|
| Mem0 | 记忆抽取与检索；Platform 新算法为 ADD-only 并保留时间上下文，混合检索排序 | 易于做个人偏好与语义记忆服务 | Platform 与 OSS 分开核对；追加不等于自动压缩，正式业务表、审核、清理仍需自建 |
| Graphiti / Zep | 实体/关系、双时间模型、事实失效；前者开源自托管，后者托管系统 | 擅长人物/项目关系变化、过去和现在的区别 | 图存储与抽取流程更重；图中事实失效不等于整个应用的数据删除 |
| Letta | 当前文档使用 Git-backed MemFS；Dreaming 后台整理，可复核更新 | 人类可读、版本追溯；适合长期助手整理偏好和工作经验 | 是 Agent 体系而非单纯数据库插件；后台复核增加模型开销，不能代替业务事务校验 |
| LangMem | schema 化 profile/collection、记忆合并与后台处理 | Python 可组合，方便将抽取接入现有后端 | 是工具库而非完整产品；持久化任务、审核 UI、删除传播和运维需自己建设 |
| Supermemory | 原文与记忆分离，updates/extends/derives 关系、最新状态标记 | 一体化记忆关系处理，减少自建检索工作 | 需验证出站数据、可导出性和部署条件；推导记忆必须与原文事实分开 |
| memU | 当前主仓库侧重跨 Agent 记忆，prepare → agent → commit，将历史整理为 Markdown/skills | 可读可迁移，利于跨助手复用经验 | 当前 MemoryService 不负责 LLM 综合，需外部 Agent；不是现成的 Gotify 通知抽取器 |

版本提醒：Mem0 新平台算法并非旧教程中每次 ADD/UPDATE/DELETE 的逻辑；Letta 当前主文档也已转向 MemFS；memU 当前主仓库与旧版三层分类介绍有差异。实施前固定具体版本和 API，不混用旧教程。

### 推荐决策

NekoHub 的核心是可靠日常记录，不是让助手任意改写自己的印象。因此：
1. 自有关系库是事实账本，Gotify 原文先可靠入库；记忆引擎作为可替换派生层。
2. 第一版用 schema 抽取 + 持久化后台 worker + 全文/向量检索；LangMem 可作为抽取/合并候选库，不强制引入整个 Agent 系统。
3. 如果人物/项目关系与历史变化成为核心问法，再对 Graphiti 做小样本对比试验。
4. Letta 的夜间整理思路值得借用：输出带证据的变更集，由校验器应用，而非直接获得任意 SQL 权限。
5. 不同时安装所有记忆框架；使用同一组匿名化样本衡量错误覆盖率、重复率、引用支持率、删除完整性、人工修正保留率和每千条成本后再选。

### 维护状态机

received → extracted → validated → applied → indexed；任一步失败进入 retry/dead-letter。
每个候选保存 evidence_ids、operation、target_id、expected_version、reason、extractor_version。
维护操作分为新增、补充、取代、标记冲突、归档、撤回。前五种默认保留原始证据。
任务完成、金额修正、事件合并必须遵循各自业务规则，不依据文本相似度直接执行。

### 本节资料

- Mem0：https://docs.mem0.ai/migration/platform-v2-to-v3
- Graphiti / Zep：https://help.getzep.com/zep-vs-graphiti
- Letta：https://docs.letta.com/configuration/memory
- LangMem：https://langchain-ai.github.io/langmem/concepts/conceptual_guide/
- Supermemory：https://supermemory.ai/docs/concepts/how-it-works
- memU：https://github.com/NevaMind-AI/memU
