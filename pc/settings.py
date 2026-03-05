# settings.py
import json
import os
from dataclasses import dataclass, field, asdict

SETTINGS_FILE = "config.json"

@dataclass
class Settings:
    # 基础与常规
    language: str = "简体中文"
    
    # Gotify 通信配置
    gotify_url: str = ""
    gotify_recv_token: str = ""
    gotify_send_token: str = ""
    
    # 消息转发渠道
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
    
    # 过滤与通知
    filter_mode: int = 0
    filter_keywords: str = ""
    toast_duration: int = 5000
    poll_seconds: int = 2
    sound_enabled: bool = True
    
    # AI 任务与对话配置
    ai_tasks: list = field(default_factory=list)
    ai_base_url: str = "https://api.deepseek.com/v1"
    ai_api_key: str = ""
    ai_model: str = "deepseek-chat"
    ai_system_prompt: str = "你是一个智能助理。"
    ai_chat_context_limit: int = 50
    ai_profiles: list = field(default_factory=list)
    ai_active_profile_idx: int = 0
    
    # --- 三大外挂模块数据保存 ---
    plugin_rss_urls: list = field(default_factory=list)
    plugin_imap_accs: list = field(default_factory=list)
    plugin_web3_addrs: list = field(default_factory=list)
    
    # --- 外挂模块转发 Gotify 开关 ---
    forward_rss: bool = False
    forward_imap: bool = False
    forward_web3: bool = False

    # --- 外挂模块拉取频率 (单位: 分钟) ---
    plugin_rss_poll_mins: int = 10
    plugin_imap_poll_mins: int = 5
    plugin_web3_poll_mins: int = 3
    
    # --- [新增] 邮件收取数量保存字段 ---
    plugin_imap_fetch_limit: int = 15

def load_settings() -> Settings:
    if not os.path.exists(SETTINGS_FILE):
        return Settings()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        valid_keys = {f.name for f in Settings.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return Settings(**filtered_data)
    except Exception as e:
        print(f"Load settings error: {e}")
        return Settings()

def save_settings(s: Settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(s), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Save settings error: {e}")