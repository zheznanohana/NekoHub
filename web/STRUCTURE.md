# NekoHub Web - 项目结构

```
nekohub-web/
│
├── 📄 README.md                    # 项目介绍
├── 📄 QUICKSTART.md                # 快速启动指南
├── 📄 COMPLETION.md                # 完成总结
├── 📄 requirements.txt             # Python 依赖
├── 📄 run.py                       # 启动脚本
│
├── 📁 docs/
│   └── 📄 api.md                   # API 文档
│
├── 📁 app/                         # Flask 后端
│   ├── 📄 __init__.py              # 应用工厂
│   ├── 📄 config.py                # 配置文件
│   │
│   ├── 📁 models/                  # 数据模型
│   │   ├── 📄 __init__.py
│   │   ├── 📄 message.py           # 消息模型
│   │   ├── 📄 settings.py          # 设置模型
│   │   └── 📄 task.py              # 任务模型
│   │
│   ├── 📁 routes/                  # API 路由
│   │   ├── 📄 __init__.py
│   │   ├── 📄 api.py               # REST API
│   │   ├── 📄 ws.py                # WebSocket
│   │   └── 📄 openclaw.py          # OpenClaw 接口
│   │
│   ├── 📁 services/                # 业务服务
│   │   ├── 📄 __init__.py
│   │   ├── 📄 gotify.py            # Gotify 客户端
│   │   ├── 📄 ai.py                # AI 管理器
│   │   ├── 📄 rss.py               # RSS 服务
│   │   ├── 📄 imap.py              # 邮件服务
│   │   ├── 📄 web3.py              # Web3 服务
│   │   └── 📄 scheduler.py         # 定时任务
│   │
│   └── 📁 utils/                   # 工具类
│       ├── 📄 __init__.py
│       └── 📄 forward.py           # 转发器
│
└── 📁 frontend/                    # Vue 3 前端
    ├── 📄 package.json             # Node 依赖
    ├── 📄 vite.config.js           # Vite 配置
    ├── 📄 index.html               # 入口 HTML
    │
    └── 📁 src/
        ├── 📄 main.js              # Vue 入口
        ├── 📄 App.vue              # 主布局
        │
        ├── 📁 components/          # 页面组件
        │   ├── 📄 Inbox.vue        # 收件箱
        │   ├── 📄 AIChat.vue       # AI 助手
        │   ├── 📄 Tasks.vue        # 自动化任务
        │   ├── 📄 Forward.vue      # 通知转发
        │   ├── 📄 RSS.vue          # RSS 订阅
        │   └── 📄 Settings.vue     # 系统设置
        │
        ├── 📁 stores/              # Pinia 状态管理
        │   ├── 📄 message.js
        │   ├── 📄 settings.js
        │   └── 📄 task.js
        │
        ├── 📁 router/              # 路由
        │   └── 📄 index.js
        │
        └── 📁 api/                 # API 客户端
            └── 📄 index.js
```

---

## 📊 文件统计

| 类型 | 文件数 |
|------|--------|
| Python 后端 | 14 |
| Vue 前端 | 12 |
| 文档 | 4 |
| 配置 | 3 |
| **总计** | **33** |

---

## 🎯 核心文件

### 后端核心
- `app/__init__.py` - Flask 应用工厂
- `app/routes/openclaw.py` - **OpenClaw 集成接口**
- `app/services/ai.py` - AI 任务管理器
- `app/utils/forward.py` - 多平台转发器

### 前端核心
- `frontend/src/App.vue` - 主布局（侧边栏导航）
- `frontend/src/components/Inbox.vue` - 收件箱（WebSocket 实时）
- `frontend/src/components/AIChat.vue` - AI 对话
- `frontend/src/stores/message.js` - 消息状态管理

### 文档
- `QUICKSTART.md` - **快速启动指南**
- `docs/api.md` - 完整 API 文档
- `COMPLETION.md` - 项目总结

---

**所有文件已创建完成！** ✅
