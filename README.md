# NekoHub - 全平台通知管理中心

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Web%20%7C%20Android-blue)](https://github.com/zheznanohana/NekoHub)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

🐱 **NekoHub** 是一个全平台的通知管理中心，支持 Gotify 通知、RSS 订阅、AI 智能分析、任务自动化等功能。

---

## 📱 平台支持

| 平台 | 技术栈 | 状态 | 路径 |
|------|--------|------|------|
| **PC (Windows)** | Python + PyQt5 | ✅ 稳定 | `/pc` |
| **Web** | Vue 3 + Flask | ✅ 稳定 | `/web` |
| **Android** | Kotlin + Jetpack Compose | ✅ 稳定 | `/android` |

---

## 🚀 快速开始

### PC 端 (Windows)

```bash
cd pc

# 安装依赖
pip install -r requirements.txt

# 运行
python ui_app.py

# 或打包为 exe
pyinstaller NekoHub.spec
```

**功能:**
- ✅ Gotify 通知管理
- ✅ RSS 订阅
- ✅ AI 智能分析
- ✅ 通知转发 (钉钉/Telegram/SMTP)
- ✅ 任务自动化
- ✅ Web3 雷达
- ✅ IMAP 邮件

---

### Web 端

```bash
cd web

# 安装后端依赖
pip install -r requirements.txt

# 启动后端
python run.py

# 安装前端依赖
cd frontend
npm install
npm run dev
```

**访问:** http://localhost:5173

**功能:**
- ✅ 响应式 Web 界面
- ✅ 跨平台访问
- ✅ 与 PC 端功能一致

---

### Android 端

```bash
cd android

# 使用 Gradle 构建
./gradlew assembleDebug

# APK 输出位置
# app/build/outputs/apk/debug/app-debug.apk
```

**功能:**
- ✅ 原生 Android 应用
- ✅ Material Design 3
- ✅ 离线支持
- ✅ 通知推送

---

## 📋 核心功能

### 1. 📬 通知收件箱
- 连接 Gotify 服务器
- 实时通知同步
- 已读/未读管理
- 关键词过滤

### 2. 🤖 AI 智能分析
- 支持自定义 AI 模型
- 通知内容智能摘要
- 数据源配置 (Gotify/RSS)
- 可配置分析限制

### 3. 📰 RSS 订阅
- 支持 RSS 2.0 / Atom 1.0
- 多源管理
- 文章列表/详情浏览

### 4. ⚡ 任务自动化
- 计数触发
- 定时触发
- 间隔触发

### 5. 🔗 通知转发
- 钉钉机器人
- Telegram Bot
- SMTP 邮件

---

## 📁 项目结构

```
NekoHub/
├── pc/                 # PC 端 (Python + PyQt5)
│   ├── ui_*.py        # UI 界面
│   ├── plugin_*.py    # 插件系统
│   ├── gotify_*.py    # Gotify 客户端
│   └── requirements.txt
├── web/               # Web 端 (Vue 3 + Flask)
│   ├── frontend/      # Vue 前端
│   ├── app/           # Flask 后端
│   └── requirements.txt
├── android/           # Android 端 (Kotlin + Compose)
│   ├── app/           # 应用源码
│   ├── build.gradle.kts
│   └── README.md
├── docs/              # 文档
└── README.md          # 本文件
```

---

## ⚙️ 配置说明

### Gotify 配置
- **服务器地址:** 你的 Gotify 服务器 URL
- **Client Token:** 用于读取消息
- **App Token:** 用于发送消息

### AI 配置
- **API Base URL:** AI 服务提供商地址
- **API Key:** 你的 API 密钥
- **模型名称:** 自定义模型标识

### RSS 配置
- **订阅 URL:** RSS/Atom feed 地址
- **更新间隔:** 自动刷新频率

---

## 🔒 安全提示

⚠️ **以下文件包含敏感信息，请勿上传到公开仓库:**

- `settings.json` - 用户配置
- `neko_messages.db` - 本地数据库
- `.env` - 环境变量
- `*.jks` - Android 签名密钥
- `local.properties` - 本地配置

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 👤 作者

**@zheznanohana**

- GitHub: https://github.com/zheznanohana
- Telegram: @tadokoro114810

---

## 🎯 开发计划

- [ ] iOS 端 (SwiftUI)
- [ ] 浏览器扩展
- [ ] 更多通知源支持
- [ ] 云端同步

---

**🐾 Made with ❤️ by NekoHub Team**
