# NekoHub Web API 文档

## 📡 API 概览

所有 API 端点前缀：`/api`

### 认证

使用 JWT Token 认证，在请求头中添加：

```
Authorization: Bearer <token>
```

---

## 🔐 认证接口

### POST /auth/login

用户登录

**请求体：**

```json
{
  "username": "admin",
  "password": "your-secret-key"
}
```

**响应：**

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## 📨 消息接口

### GET /messages

获取消息列表

**参数：**

- `limit` (可选): 返回数量，默认 50
- `source` (可选): 过滤来源 (gotify/rss/imap/web3)

**响应：**

```json
[
  {
    "id": 1,
    "gotify_id": 123,
    "title": "通知标题",
    "message": "通知内容",
    "priority": 5,
    "source": "gotify",
    "created_at": "2026-03-03T10:00:00",
    "is_read": false
  }
]
```

### POST /messages/{id}/read

标记消息为已读

**响应：**

```json
{
  "success": true
}
```

---

## 🤖 AI 接口

### POST /ai/chat

AI 对话

**请求体：**

```json
{
  "message": "请总结今天的通知",
  "domains": ["gotify", "rss"],
  "limit": {
    "gotify": 20,
    "rss": 10
  }
}
```

**响应：**

```json
{
  "response": "今天共收到 30 条通知，主要内容如下..."
}
```

---

## 📋 任务接口

### GET /tasks

获取所有自动化任务

**响应：**

```json
[
  {
    "id": "uuid",
    "name": "每日摘要",
    "prompt": "请总结以下信息",
    "mode": "time",
    "value": "08:00,20:00",
    "enabled": true,
    "domains": ["gotify", "rss"],
    "run_count": 5
  }
]
```

### POST /tasks

创建新任务

**请求体：**

```json
{
  "name": "新任务",
  "prompt": "请总结",
  "mode": "count",
  "value": "10",
  "domains": ["gotify"]
}
```

### DELETE /tasks/{id}

删除任务

### POST /tasks/{id}/run

手动执行任务

---

## ⚙️ 设置接口

### GET /settings

获取所有设置

**响应：**

```json
{
  "gotify_url": "https://notify.diu.ac.cn",
  "gotify_recv_token": "Cxxx",
  "gotify_send_token": "Axxx",
  "ai_base_url": "https://api.deepseek.com/v1",
  "ai_api_key": "sk-xxx",
  "ai_model": "deepseek-chat",
  "forward_enabled": "true",
  "forward_mode": "2",
  "dingtalk_webhook": "https://...",
  "filter_mode": "0",
  "filter_keywords": ""
}
```

### POST /settings

更新设置

**请求体：**

```json
{
  "gotify_url": "https://...",
  "gotify_recv_token": "Cxxx"
}
```

---

## 🧪 测试接口

### POST /gotify/test

测试 Gotify 连接

**请求体：**

```json
{
  "url": "https://notify.diu.ac.cn",
  "recv_token": "Cxxx",
  "send_token": "Axxx"
}
```

**响应：**

```json
{
  "success": true,
  "message": "连接成功"
}
```

### POST /forward/test

测试转发配置

**请求体：**

```json
{
  "dingtalk_webhook": "https://...",
  "dingtalk_secret": "SEC...",
  "tg_bot_token": "xxx",
  "tg_chat_id": "xxx",
  "email_smtp": "smtp.gmail.com",
  "email_user": "xxx@gmail.com",
  "email_pass": "xxx",
  "email_to": "xxx@example.com"
}
```

**响应：**

```json
{
  "dingtalk": true,
  "telegram": true,
  "email": false
}
```

---

## 🔌 OpenClaw 专用接口

### POST /openclaw/message

OpenClaw 推送消息到 NekoHub

**请求体：**

```json
{
  "title": "通知标题",
  "message": "通知内容",
  "priority": 5,
  "tags": ["gotify"]
}
```

**响应：**

```json
{
  "success": true,
  "message_id": 123
}
```

### POST /openclaw/task/{id}/run

OpenClaw 触发 AI 任务

**请求体：**

```json
{
  "domains": ["gotify", "rss"],
  "extra_context": "额外数据"
}
```

### GET /openclaw/status

查询 NekoHub 状态

**响应：**

```json
{
  "status": "online",
  "messages_count": 1234,
  "tasks_count": 5,
  "tasks_enabled": 3
}
```

---

## 🔌 WebSocket 接口

### 连接

```javascript
const socket = io('http://localhost:5000');
```

### 事件

**connect** - 连接成功

```javascript
socket.on('connect', () => {
  console.log('WebSocket 已连接');
});
```

**message** - 收到新消息

```javascript
socket.on('message', (msg) => {
  console.log('新消息:', msg);
});
```

**task_status** - 任务执行状态

```javascript
socket.on('task_status', (data) => {
  console.log('任务状态:', data.task_name, data.message);
});
```

---

## 📝 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

**文档版本：** 1.0  
**最后更新：** 2026-03-03
