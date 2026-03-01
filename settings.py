# settings.py
from __future__ import annotations
import json
import os
import sys
from dataclasses import dataclass, fields, field
from pathlib import Path

def _base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent.resolve()
    else:
        return Path(os.path.dirname(__file__)).resolve()

SETTINGS_PATH = str(_base_dir() / "settings.json")

@dataclass
class Settings:
    language: str = "简体中文"
    gotify_url: str = ""
    gotify_recv_token: str = ""  
    gotify_send_token: str = ""  
    poll_seconds: int = 2
    sound_enabled: bool = True
    toast_duration: int = 5000

    # AI 配置
    ai_api_key: str = ""
    ai_base_url: str = "https://api.deepseek.com/v1"
    ai_model: str = "deepseek-chat"
    ai_system_prompt: str = "你是一个通知处理助手。请务必使用 Markdown 格式输出。"
    ai_chat_context_limit: int = 50
    ai_tasks: list = field(default_factory=list)

    # 转发配置
    forward_enabled: bool = False
    forward_mode: int = 0 
    dingtalk_webhook: str = ""
    dingtalk_secret: str = ""
    tg_bot_token: str = ""
    tg_chat_id: str = ""
    email_smtp: str = ""
    email_port: int = 465
    email_user: str = ""
    email_pass: str = ""
    email_to: str = ""

    # --- 新增：黑白名单过滤配置 ---
    filter_mode: int = 0  # 0: 不过滤, 1: 黑名单, 2: 白名单
    filter_keywords: str = ""  # 关键字，用逗号分隔

def load_settings() -> Settings:
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        valid_keys = {f.name for f in fields(Settings)}
        filtered_d = {k: v for k, v in d.items() if k in valid_keys}
        return Settings(**filtered_d)
    except Exception:
        return Settings()

def save_settings(s: Settings):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(s.__dict__, f, ensure_ascii=False, indent=2)