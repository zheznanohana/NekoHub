# NekoHub Web - 快速启动指南

## 🚀 开发环境启动

### 1. 安装依赖

```bash
# Python 后端
cd /root/.openclaw/workspace/projects/nekohub-web
pip install -r requirements.txt

# Node.js 前端
cd frontend
npm install
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# Gotify 配置
GOTIFY_URL=https://notify.diu.ac.cn
GOTIFY_RECV_TOKEN=CBy3EA.goihUB8q
GOTIFY_SEND_TOKEN=ARBeXlBd1PUVw7B

# AI 配置
AI_BASE_URL=https://api.deepseek.com/v1
AI_API_KEY=sk-d6e6afe91c3c470e8d64998973a04534
AI_MODEL=deepseek-chat

# OpenClaw 接口
OPENCLAW_ENABLED=true
OPENCLAW_SESSION_KEY=default
```

### 3. 启动服务

**终端 1 - 启动后端：**

```bash
cd /root/.openclaw/workspace/projects/nekohub-web
python run.py
```

后端将在 `http://localhost:5000` 启动

**终端 2 - 启动前端：**

```bash
cd /root/.openclaw/workspace/projects/nekohub-web/frontend
npm run dev
```

前端将在 `http://localhost:5173` 启动

### 4. 访问应用

打开浏览器访问：`http://localhost:5173`

---

## 📦 生产环境部署

### 1. 构建前端

```bash
cd frontend
npm run build
```

构建产物在 `frontend/dist/` 目录

### 2. 使用 Gunicorn 启动

```bash
pip install gunicorn eventlet
gunicorn -w 4 -b 0.0.0.0:5000 "run:app"
```

### 3. 配置 Nginx（可选）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## 🔌 OpenClaw 集成

### 推送消息到 NekoHub

```bash
curl -X POST http://localhost:5000/api/openclaw/message \
  -H "Content-Type: application/json" \
  -d '{
    "title": "通知标题",
    "message": "通知内容",
    "priority": 5,
    "tags": ["gotify"]
  }'
```

### 触发 AI 任务

```bash
curl -X POST http://localhost:5000/api/openclaw/task/{task_id}/run \
  -H "Content-Type: application/json" \
  -d '{
    "domains": ["gotify", "rss"],
    "extra_context": "额外背景数据"
  }'
```

---

## 📊 默认登录凭据

- **用户名：** `admin`
- **密码：** 在 `app/config.py` 中的 `SECRET_KEY`

---

## 🛠️ 故障排查

### 后端启动失败

```bash
# 检查 Python 依赖
pip install -r requirements.txt --upgrade

# 查看详细错误
python run.py 2>&1 | tee debug.log
```

### 前端无法连接后端

1. 确认后端在 `http://localhost:5000` 运行
2. 检查 `frontend/vite.config.js` 中的代理配置
3. 查看浏览器控制台错误信息

### WebSocket 连接失败

1. 确认 Gotify URL 和 Token 正确
2. 检查防火墙是否允许 WebSocket 连接
3. 查看后端日志中的 WebSocket 状态

---

## 📝 下一步

1. 登录系统（首次使用需配置 Gotify）
2. 在"系统设置"中配置 Gotify 服务器
3. 在"AI 助手"中配置 AI 模型
4. 在"自动化任务"中创建 AI 总结任务
5. 在"通知转发"中配置手机推送

---

**祝你使用愉快！** 🐱
