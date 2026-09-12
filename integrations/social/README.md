# NekoHub 社交连接层

采用 NoneBot2 官方适配器，不重新实现平台协议。运行根目录 `Start-NekoHub.ps1` 启动本机记忆服务、工作进程、社交桥和 PC 界面。适配器空配置可运行，**不等于已登录社交账号**。

配置在 `%LOCALAPPDATA%/NekoHubMemory/social.json`，不要提交 Token 到 Git。

- `telegram_bots`: `[{"token":"BotFather token"}]`，使用长轮询。
- `discord_bots`: `[{"token":"bot token","intent":{"message_content":true}}]`，平台后台也需启用对应 intent。
- OneBot v11：启用 `onebot_enabled`、设置至少 24 字符 `onebot_v11_access_token`，配置 `onebot_v11_ws_urls` 对接已有网关。QQ 等还需运行兼容网关并登录；不声称提供微信原生适配器。
- `allowed_sessions` 每项为 `{"adapter":"Telegram","bot_id":"...","user_id":"...","session_id":"..."}`，四项精确匹配 NoneBot 事件；空列表不接收任何用户请求。不要把公共群聊加入私人记忆的会话白名单。
- 消息前缀 `/neko `，例如 `/neko /memory.search {"text":"项目"}`，也可 `/neko 回忆上周的计划`。

桥仅调用 `/api/memory/v1/chat`，校验 `chat.blocks` JSON 后生成平台文本投影。桌面和 Web 保持原始卡片/表/图协议。写入只给出提议，确认 token 不发到社交平台；用户在本地重新提交并确认。不是全量聊天历史采集器。

资料：[NoneBot 适配器](https://nonebot.dev/docs/advanced/adapter)。
