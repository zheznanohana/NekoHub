

# NekoHub 🐱

NekoHub is a modern, lightweight, and highly intelligent desktop notification hub for [Gotify](https://gotify.net/), built with Python, PySide6, and Fluent Design.

In version 1.1.0, it has evolved beyond a simple push client. It now features an **AI Automation Center**, **Smart Black/Whitelist Filtering**, and a **Multi-Platform Forwarding Engine** (DingTalk, Telegram, SMTP), making it the ultimate command center for all your server and app notifications.

<img width="1432" height="933" alt="image" src="https://github.com/user-attachments/assets/25c3b940-cd50-4002-9e4a-cd1fc0211e61" />

## ✨ Key Features (v1.1.0)

* **Modern Fluent UI & Markdown:** Beautiful native Windows 11 Fluent Design scrollbars and full Markdown rendering for notifications. Seamless switching between English and Simplified Chinese.
* **🛡️ Smart Filtering (Black/Whitelist):** Reject notification spam. Mute alerts automatically based on custom keywords before they even trigger a sound or AI analysis.
* **🤖 AI Automation Center:** Connects to OpenAI-compatible APIs (DeepSeek, Gemini, etc.). Set up tasks to auto-summarize notifications based on:
* **Count:** E.g., trigger an AI summary every 20 messages.
* **Time:** E.g., generate a daily brief at 08:00 and 20:00.
* **Interval:** E.g., review system logs every 60 minutes.


* **📤 Multi-Platform Forwarding:** Forward raw notifications or clean AI summaries to **DingTalk** (Secret signature supported), **Telegram Bots**, or **Email (SMTP)**.
* **Fully Portable:** The SQLite database (`neko_messages.db`) and configuration (`settings.json`) are stored locally next to the executable. No registry clutter.

## 📖 Quick Configuration Guide (Babysitter Level)

After launching the app, configure the following tabs to unleash NekoHub's full potential. **Always remember to click "Save" after modifying!**

### 1. Settings (Gotify & Filters)

* **Server URL:** Your Gotify server address (e.g., `https://push.yourdomain.com`).
* **Receive Token:** Generated in Gotify's `Clients` tab (starts with `C`).
* **Send Token:** Generated in Gotify's `Apps` tab (starts with `A`). Used for AI summary pushbacks.
* **Notification Filter:** Choose Blacklist (mute if matched) or Whitelist (mute unless matched). Enter keywords separated by commas (e.g., `ads,promo,test`).

### 2. AI Assistant (The Brain)

* **API Base URL:** Standard OpenAI format API URL (e.g., `https://api.deepseek.com` or `https://generativelanguage.googleapis.com/v1beta/openai`).
* **API Key:** Your private model key.
* **Model Name:** The model you wish to use (e.g., `deepseek-chat`).

### 3. Forwarding Center (Push to Mobile)

* **Filter Mode:** Highly recommend selecting **"AI Only"** so your phone only receives clean, summarized reports instead of raw spam.
* **DingTalk:** Enter your Webhook URL. If you enabled signature validation, enter the `SEC...` secret key.
* **Telegram:** Enter your Bot Token and Chat ID. *(Note: You must send `/start` to your bot first!)*

## 🛠️ Build from Source

**1. Clone the repository and setup the environment:**

```bash
git clone https://github.com/zheznanohana/NekoHub.git
cd NekoHub
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

```

**2. Run the app:**

```bash
python ui_app.py

```

**3. Build the executable (PyInstaller):**
*(Note: NekoHub v1.1.0 includes pathing fixes for PyInstaller, ensuring tray icons are never lost.)*

```bash
# Build as a single standalone executable (Extremely clean)
pyinstaller -y -w -F -n "NekoHub" -i "icon.ico" --add-data "icon.ico;." ui_app.py

# Build as a portable directory (Fast startup)
pyinstaller -y -w -n "NekoHub_Folder" -i "icon.ico" --add-data "icon.ico;." ui_app.py

```

## 📄 License

This project is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.gnu.org/licenses/agpl-3.0). Any modified versions or network-based services running this software must also be open-sourced under the same license.

---

<span id="简体中文"></span>

# NekoHub 🐱 (简体中文)

**NekoHub** 是一款基于 Python、PySide6 和 Fluent Design 构建的桌面级智能通知处理中枢。它完美接入了 [Gotify](https://gotify.net/) 消息推送系统。

在全新的 **v1.1.0** 版本中，它彻底超越了基础接收器的范畴。通过深度整合 **AI 自动化任务中心**、**智能黑白名单过滤** 与 **多端分发引擎**（钉钉、Telegram、SMTP），NekoHub 现已成为您掌控所有服务器与应用通知的终极大脑。

## ✨ 核心特性 (v1.1.0)

* **现代 Fluent UI 与 Markdown 支持：** 全面接入原生 Windows 11 Fluent 风格的精美滚动条，收件箱与 AI 对话完美支持 Markdown 富文本渲染（加粗、列表、代码块）。支持中英双语无缝切换。
* **🛡️ 智能过滤 (黑白名单)：** 告别垃圾推送轰炸。通过自定义关键字，在消息触发弹窗或 AI 分析前进行静默拦截。
* **🤖 AI 自动化任务中心：** 完美兼容 OpenAI 接口格式（DeepSeek, Gemini 等）。您可以利用 AI 自动总结通知，支持三种触发模式：
* **按累计计数：** 例如，每攒够 20 条新通知，触发一次 AI 简报。
* **按定时触发：** 例如，每天 08:00 和 20:00 准时生成日报/晚报。
* **按固定频率：** 例如，每隔 60 分钟巡查一次系统异常。


* **📤 多平台通知转发：** 将原始通知或 AI 提炼后的精华简报，一键自动下发至 **钉钉群组**（支持加签秘钥）、**Telegram Bot** 或 **电子邮件 (SMTP)**。
* **完美便携绿色版：** 数据库（`neko_messages.db`）和配置文件（`settings.json`）均安全储存在程序同级目录，随拷随用，不写注册表。

## 📖 保姆级配置教程

初次打开软件后，请依次进入左侧导航栏进行基础配置。**每次修改后，请务必点击卡片底部的「保存」按钮！**

### 1. 系统设置 (接入服务器与配置免打扰)

* **Gotify Server URL：** 填入您部署的 Gotify 服务端完整地址（如 `https://push.yourdomain.com`）。
* **接收 Token (Client)：** 在 Gotify 网页端的 `Clients` 页面生成，通常以 `C` 开头。
* **发送 Token (App)：** 在 Gotify 网页端的 `Apps` 页面生成，通常以 `A` 开头，用于 AI 将总结报告推回至系统。
* **过滤模式与关键字：** 可选“黑名单”或“白名单”。填入需过滤的词汇，**多个词必须用英文半角逗号 `,` 隔开**（例如：`广告,测试,error`）。

### 2. AI 助手 (为系统装上大脑)

* **接口配置：** 填入兼容格式的 API 地址（例如 DeepSeek 的 `https://api.deepseek.com`）。
* **API Key：** 您的模型私钥。
* **模型名称：** 您需要调用的具体模型（例如 `deepseek-chat`）。

### 3. 通知转发 (将消息推送到手机)

* **转发内容筛选：** 强烈建议选择 **“仅转发 AI 分析结果”**，这样您的手机只会收到精简后的高价值报告，拒绝垃圾通知打扰。
* **钉钉 (DingTalk)：** 填入 Webhook 链接。如果机器人的安全设置开启了“加签”，请务必将 `SEC` 开头的字符串填入“加签秘钥”框中。
* **Telegram Bot：** 填入 Token 与 Chat ID。*(注意：必须先在 TG 中向您的 Bot 发送一次 `/start`，它才能主动向您推送消息！)*

## 🛠️ 从源码开发与编译打包

**1. 拉取代码并配置虚拟环境：**

```bash
git clone https://github.com/zheznanohana/NekoHub.git
cd NekoHub
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

```

**2. 运行程序：**

```bash
python ui_app.py

```

**3. 使用 PyInstaller 打包独立程序：**
*(注：v1.1.0 源码已打入路径寻址补丁，彻底修复了单文件打包后托盘图标丢失的问题)*

```bash
# 打包为极致整洁的单文件版 (.exe)
pyinstaller -y -w -F -n "NekoHub" -i "icon.ico" --add-data "icon.ico;." ui_app.py

# 打包为启动更快的文件夹版
pyinstaller -y -w -n "NekoHub_Folder" -i "icon.ico" --add-data "icon.ico;." ui_app.py

```

## 📜 更新日志 (Changelog)

### v1.1.0

* **✨ UI 全面重构**：接入 Windows 11 Fluent 风格原生滚动条，全局支持中英双语切换，完美支持 Markdown 渲染。
* **🤖 新增 AI 自动化任务**：支持 Count / Time / Interval 三大触发模式。
* **📤 新增外转分发引擎**：支持 DingTalk (含加签)、Telegram、SMTP。
* **🛡️ 新增拦截器**：加入前置正则级黑白名单免打扰过滤。
* **🔧 核心修复**：修复打包 `.exe` 后托盘图标丢失问题；修复 WebSocket 底层参数传递导致的闪退 Bug。

### v1.0.0

* 🚀 基础核心架构发布，接入 Gotify。
* ✅ 新增 AI 聊天与上下文记忆。

## 📄 许可证

本项目基于 [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.gnu.org/licenses/agpl-3.0) 开源。



