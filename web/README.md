# NekoHub Web - Linux Web 端信息统合与 AI 分析转发系统

_从 PySide6 桌面端移植到 Flask + Vue3 Web 端_

## 🏗️ 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Flask + SQLAlchemy + WebSocket |
| **前端** | Vue 3 + Vite + Element Plus |
| **数据库** | SQLite (可切换 PostgreSQL) |
| **实时通信** | Flask-SocketIO |
| **API 接口** | RESTful + WebSocket |

## 📁 项目结构

```
nekohub-web/
├── app/
│   ├── __init__.py          # Flask 应用工厂
│   ├── config.py            # 配置文件
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api.py           # REST API 路由
│   │   ├── ws.py            # WebSocket 路由
│   │   └── openclaw.py      # OpenClaw 接口
│   ├── models/
│   │   ├── __init__.py
│   │   ├── message.py       # 消息模型
│   │   ├── settings.py      # 设置模型
│   │   └── task.py          # AI 任务模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gotify.py        # Gotify 客户端
│   │   ├── ai.py            # AI 管理器
│   │   ├── rss.py           # RSS 订阅
│   │   ├── imap.py          # 邮件中心
│   │   └── web3.py          # Web3 雷达
│   └── utils/
│       ├── __init__.py
│       ├── filter.py        # 通知过滤器
│       └── forward.py       # 转发器 (钉钉/TG/邮件)
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   ├── components/
│   │   │   ├── Inbox.vue    # 收件箱
│   │   │   ├── AIChat.vue   # AI 助手
│   │   │   ├── Tasks.vue    # 自动化任务
│   │   │   ├── Forward.vue  # 转发中心
│   │   │   ├── Settings.vue # 系统设置
│   │   │   ├── RSS.vue      # RSS 订阅
│   │   │   ├── Imap.vue     # 邮件中心
│   │   │   └── Web3.vue     # Web3 雷达
│   │   └── api/
│   │       └── index.js     # API 客户端
│   ├── package.json
│   └── vite.config.js
├── requirements.txt
├── run.py
└── README.md
```

## 🚀 快速启动

### 1. 安装依赖

```bash
# Python 后端
cd nekohub-web
pip install -r requirements.txt

# Node.js 前端
cd frontend
npm install
```

### 2. 配置环境变量

```bash
# .env 文件
GOTIFY_URL=https://notify.diu.ac.cn
GOTIFY_RECV_TOKEN=CBy3EA.goihUB8q
GOTIFY_SEND_TOKEN=AB3Kv9AbdIarjtd

# AI 配置
AI_BASE_URL=https://api.deepseek.com/v1
AI_API_KEY=sk-xxx
AI_MODEL=deepseek-chat

# OpenClaw 接口 (可选)
OPENCLAW_ENABLED=true
OPENCLAW_SESSION_KEY=default
```

### 3. 启动服务

```bash
# 启动后端 (默认 5000 端口)
python run.py

# 启动前端 (开发模式，默认 5173 端口)
cd frontend
npm run dev
```

## 🔌 OpenClaw 接口

### 消息推送接口

```python
# OpenClaw 可以调用此接口推送消息到 NekoHub
POST /api/openclaw/message
{
  "title": "通知标题",
  "message": "通知内容",
  "priority": 5,
  "tags": ["gotify", "rss"]
}
```

### AI 任务调用接口

```python
# OpenClaw 可以触发 AI 自动化任务
POST /api/openclaw/task/{task_id}/run
{
  "domains": ["gotify", "rss", "imap"],
  "extra_context": "额外背景数据"
}
```

### WebSocket 订阅

```javascript
// OpenClaw 可以通过 WebSocket 订阅实时通知
const socket = io('http://localhost:5000', {
  auth: { token: 'openclaw_token' }
});

socket.on('message', (data) => {
  console.log('收到新消息:', data);
});
```

## 📊 功能对照表

| 桌面端功能 | Web 端状态 | 说明 |
|-----------|-----------|------|
| 收件箱 | ✅ 已实现 | WebSocket 实时推送 |
| AI 助手对话 | ✅ 已实现 | 支持多数据源上下文 |
| 自动化任务 | ✅ 已实现 | 计数/定时/间隔触发 |
| 通知转发 | ✅ 已实现 | 钉钉/TG/邮件 |
| RSS 订阅 | ✅ 已实现 | 定时轮询 |
| 邮件中心 | ✅ 已实现 | IMAP 协议 |
| Web3 雷达 | ✅ 已实现 | 链上监控 |
| 系统托盘 | ❌ 不适用 | Web 端无需托盘 |
| Toast 通知 | ✅ 已实现 | 浏览器通知 API |

## 🔐 安全配置

### 1. 启用 HTTPS

```bash
# 生成自签名证书
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365

# Flask 配置
app.config['SSL_CERT'] = 'cert.pem'
app.config['SSL_KEY'] = 'key.pem'
```

### 2. API 认证

```python
# 使用 JWT Token 认证
from flask_jwt_extended import JWTManager

app.config['JWT_SECRET_KEY'] = 'your-secret-key'
jwt = JWTManager(app)
```

### 3. CORS 配置

```python
from flask_cors import CORS

CORS(app, resources={
  r"/api/*": {
    "origins": ["http://localhost:5173", "https://yourdomain.com"],
    "methods": ["GET", "POST", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "Authorization"]
  }
})
```

## 📝 API 文档

详见 `/docs/api.md`

## 🛠️ 开发指南

### 添加新插件

1. 在 `app/services/` 创建新服务类
2. 在 `frontend/src/components/` 创建前端组件
3. 在 `app/routes/api.py` 添加 API 路由
4. 更新导航菜单

### 自定义 AI Prompt

在 `app/services/ai.py` 中修改 `system_prompt` 变量

### 修改转发逻辑

在 `app/utils/forward.py` 中添加新的转发渠道

## 📄 许可证

MIT License
