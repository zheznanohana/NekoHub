# settings.py
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, fields
from pathlib import Path


def _base_dir() -> Path:
    # 核心魔法：判断是否被 PyInstaller 打包成了单文件 exe
    if getattr(sys, 'frozen', False):
        # 如果是 exe，就获取 exe 文件所在的真实物理路径
        return Path(sys.executable).parent.resolve()
    else:
        # 如果是 python 源码运行，就获取当前 py 文件所在路径
        return Path(os.path.dirname(__file__)).resolve()


SETTINGS_PATH = str(_base_dir() / "settings.json")


@dataclass
class Settings:
    # --- 基础配置 ---
    language: str = "Auto"  
    gotify_url: str = ""
    gotify_recv_token: str = ""  
    gotify_send_token: str = ""  
    poll_seconds: int = 2
    sound_enabled: bool = True

    # --- AI 配置 ---
    ai_summary_enabled: bool = False
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-3.5-turbo"
    ai_summary_mode: str = "count"  
    ai_summary_count: int = 10      
    ai_summary_times: str = "08:00,18:00"  
    ai_system_prompt: str = "你是一个通知摘要助手。请简明扼要地总结以下收到的通知。"


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
