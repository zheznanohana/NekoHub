
# NekoHub 🐱

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/PySide6-Fluent--Widgets-orange)](https://qfluentwidgets.com/)

*English | [简体中文](#简体中文)*

NekoHub is a modern, lightweight, and smart desktop client for [Gotify](https://gotify.net/), built with Python, PySide6, and Fluent Design. It goes beyond simple push notifications by integrating a powerful AI assistant that can auto-summarize your alerts and chat with you about your notification history.


## ✨ Key Features

* **Modern Fluent Design:** Beautiful, smooth UI powered by `PySide6` and `PyQt-Fluent-Widgets`.
* **Real-time Notifications:** Uses WebSocket for instant message delivery with custom, multi-monitor friendly Toast popups and native Windows sounds.
* **System Tray Integration:** Minimizes to the system tray to run quietly in the background without cluttering your taskbar.
* **🤖 AI Assistant & Auto-Summary:** * Connects to any OpenAI-compatible API (e.g., DeepSeek, Gemini, ChatGPT).
    * **Auto-Summary:** Automatically summarizes notifications based on a set count (e.g., every 10 messages) or at specific times of the day (e.g., 08:00 and 18:00).
    * **Chat with Context:** Ask the AI questions about your recent notifications directly within the app.
* **Fully Portable:** The SQLite database and settings file are safely stored right next to the executable, making it a perfect, portable "green" software.
* **Multi-language Support:** Built-in English and Simplified Chinese UI.

## 🚀 Quick Start (Releases)

If you just want to use the app, head over to the [Releases](https://github.com/zheznanohana/NekoHub/releases) page and download the latest `.zip` file.
1. Extract the folder.
2. Run `NekoHub.exe`.
3. Go to **Settings** and fill in your Gotify URL, **Receive Token** (Client Token), and **Send Token** (App Token).

## 🛠️ Build from Source

**1. Clone the repository and setup virtual environment:**
```bash
git clone [https://github.com/zheznanohana/NekoHub.git](https://github.com/zheznanohana/NekoHub.git)
cd NekoHub
python -m venv venv
venv\Scripts\activate

```

**2. Install dependencies:**

```bash
pip install -r requirements.txt

```

**3. Run the app:**

```bash
python ui_app.py

```

**4. Build the executable (PyInstaller):**

```bash
# Build as a portable directory (Recommended)
pyinstaller --noconsole --onedir --icon=icon.ico --name=NekoHub --distpath=dist2 ui_app.py

# Build as a single standalone executable
pyinstaller --noconsole --onefile --icon=icon.ico --name=NekoHub ui_app.py

```

## ⚙️ AI Configuration Guide

To enable the AI features, go to the **AI Chat** tab and configure:

* **Base URL:** e.g., `https://api.deepseek.com` (for DeepSeek) or `https://generativelanguage.googleapis.com/v1beta/openai` (for Gemini).
* **API Key:** Your private key.
* **Model:** e.g., `deepseek-chat` or `gemini-2.0-flash`.

## 📄 License

This project is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.google.com/search?q=LICENSE). Any modified versions or network-based services running this software must also be open-sourced under the same license.

---

<span id="简体中文"></span>

# NekoHub 🐱 (简体中文)

NekoHub 是一款基于 Python、PySide6 和 Fluent Design 构建的现代化、轻量级且智能的 [Gotify](https://gotify.net/) 桌面客户端。除了基础的实时推送功能外，它还深度集成了强大的 AI 助手，能够对你的通知进行自动摘要，并支持针对历史通知进行对话询问。

## ✨ 核心特性

* **现代 Fluent UI：** 基于 `PySide6` 和 `PyQt-Fluent-Widgets`，提供丝滑、美观的现代 Windows 设计规范界面。
* **实时桌面通知：** 通过 WebSocket 建立长连接，支持自定义的优雅 Toast 弹窗（完美适配多显示器）和 Windows 原生提示音。
* **系统托盘常驻：** 支持最小化到系统托盘，后台静默运行，不占用任务栏空间。
* **🤖 AI 助手与自动摘要：**
* 完全兼容 OpenAI 接口格式，完美接入 DeepSeek、Gemini、ChatGPT 等大模型。
* **自动摘要：** 支持“按积攒条数”（如每 10 条）或“按特定时间点”（如每天早晚 8 点）自动生成通知摘要，并推回给 Gotify。
* **上下文对话：** 可以在内置的聊天界面直接向 AI 询问关于近期通知的任何问题。


* **完美便携绿色版：** 所有的配置（`settings.json`）和历史通知数据库（`nekohub.db`）均会安全地生成在 `.exe` 同级目录下，随拷随用，不会污染系统临时文件夹。
* **多语言支持：** 内置简体中文与英文界面。

## 🚀 快速使用

如果你只想直接使用软件，请前往 [Releases](https://www.google.com/url?sa=E&source=gmail&q=https://github.com/zheznanohana/NekoHub/releases) 页面下载最新的 `.zip` 压缩包。

1. 解压文件夹。
2. 双击运行 `NekoHub.exe`。
3. 进入 **Settings (设置)** 页面，填入你的 Gotify URL、**接收 Token** (Client Token) 和 **发送 Token** (App Token)。

## 🛠️ 从源码开发与编译

**1. 拉取代码并配置虚拟环境：**

```bash
git clone [https://github.com/zheznanohana/NekoHub.git](https://github.com/zheznanohana/NekoHub.git)
cd NekoHub
python -m venv venv
venv\Scripts\activate

```

**2. 安装依赖：**

```bash
pip install -r requirements.txt

```

**3. 运行程序：**

```bash
python ui_app.py

```

**4. 使用 PyInstaller 打包为可执行文件：**

```bash
# 打包为文件夹版（推荐，启动快，方便维护）
pyinstaller --noconsole --onedir --icon=icon.ico --name=NekoHub --distpath=dist2 ui_app.py

# 打包为单文件版（极致整洁）
pyinstaller --noconsole --onefile --icon=icon.ico --name=NekoHub ui_app.py

```

## ⚙️ AI 配置指南

如需启用 AI 功能，请在 **AI 助手** 界面中填入以下信息：

* **Base URL (接口地址)：** 例如 `https://api.deepseek.com` (DeepSeek 官方接口) 或 `https://generativelanguage.googleapis.com/v1beta/openai` (Gemini 官方兼容接口)。
* **API Key：** 你的私钥。
* **模型名称：** 例如 `deepseek-chat` 或 `gemini-2.0-flash`。
* 开启**“启用后台自动摘要”**开关即可让 AI 在后台默默为你工作。

## 📄 许可证

本项目基于 [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.google.com/search?q=LICENSE) 开源。


