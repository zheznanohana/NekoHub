# i18n.py
from __future__ import annotations

_LANG = "zh"  # 默认中文

def set_lang(lang_code: str):
    global _LANG
    _LANG = lang_code if lang_code in ("zh", "en") else "zh"

_STRINGS = {
    # 侧边栏 & 标题
    "inbox": {"zh": "收件箱", "en": "Inbox"},
    "ai_chat": {"zh": "AI 助手", "en": "AI Chat"},
    "settings": {"zh": "设置", "en": "Settings"},
    
    # 收件箱页面
    "mark_read": {"zh": "标为已读", "en": "Mark read"},
    "ws_idle": {"zh": "WS: 空闲", "en": "WS: idle"},
    "ws_conn": {"zh": "WS: 连接中…", "en": "WS: connecting…"},
    "ws_err": {"zh": "WS: websocket-client 库缺失", "en": "WS: websocket-client missing"},
    "ws_hint": {"zh": "请在设置中配置 Gotify URL 与 Receive Token。", "en": "Please set Gotify URL + Receive Token in Settings."},
    "waiting": {"zh": "等待消息中...", "en": "Waiting for messages…"},
    "no_msg": {"zh": "暂无消息。", "en": "No messages yet."},
    "showing_msg": {"zh": "显示 {} 条消息。", "en": "Showing {} messages."},
    
    # 设置页面 - 基础
    "gotify_cfg": {"zh": "Gotify 配置", "en": "Gotify Configuration"},
    "recv_token": {"zh": "接收 Token (Client token, 用于监听)", "en": "Receive Token (Client token, listen/get)"},
    "send_token": {"zh": "发送 Token (App token, 用于推送)", "en": "Send Token (App token, post/push)"},
    "notification": {"zh": "通知设置", "en": "Notification"},
    "enable_sound": {"zh": "启用提示音 (Windows 默认)", "en": "Enable sound (Windows default)"},
    "poll_sec": {"zh": "轮询拉取间隔 (秒)", "en": "Poll seconds (history fetch)"},
    "lang_setting": {"zh": "界面语言 / Language", "en": "Language / 界面语言"},
    
    # 设置页面 - 按钮 & 弹窗
    "save": {"zh": "保存", "en": "Save"},
    "send_test": {"zh": "发送测试", "en": "Send Test"},
    "reconn_ws": {"zh": "重连 WS", "en": "Reconnect WS"},
    "saved_title": {"zh": "已保存", "en": "Saved"},
    "saved_desc": {"zh": "设置已保存。\n(若切换了语言，请重启软件以完全生效)", "en": "Settings saved.\n(Restart app if language changed)"},
    "ok": {"zh": "成功", "en": "OK"},
    "test_ok": {"zh": "测试消息已发送。", "en": "Test message sent."},
    "fail": {"zh": "失败", "en": "Fail"},
    "reconn_trig": {"zh": "WebSocket 重连已触发。", "en": "WebSocket reconnect triggered."},
    
    # AI 页面
    "ai_config": {"zh": "AI 助手与摘要配置", "en": "AI Assistant & Summary"},
    "api_cfg": {"zh": "API 接口配置", "en": "API Configuration"},
    "auto_rule": {"zh": "自动摘要规则", "en": "Auto Summary Rules"},
    "enable_auto": {"zh": "启用后台自动摘要", "en": "Enable Auto Summary"},
    "trig_mode": {"zh": "触发模式:", "en": "Trigger Mode:"},
    "mode_count": {"zh": "按条数触发", "en": "By Count"},
    "mode_time": {"zh": "按时间触发", "en": "By Time"},
    "threshold": {"zh": "条数阈值:", "en": "Count Threshold:"},
    "trig_time": {"zh": "触发时间(逗号分隔):", "en": "Trigger Times (comma separated):"},
    "save_ai": {"zh": "保存 AI 配置", "en": "Save AI Config"},
    "manual_btn": {"zh": "手动生成并发送摘要", "en": "Manual Gen & Send Summary"},
    "discuss": {"zh": "与 AI 讨论通知记录", "en": "Discuss with AI"},
    "chat_ph": {"zh": "在此输入你想问 AI 的问题...", "en": "Ask AI about notifications..."},
    "send": {"zh": "发送", "en": "Send"},
    
    # AI 内部提示
    "sys_ai_saved": {"zh": "<i>[系统] AI 配置已保存。</i><br>", "en": "<i>[System] AI config saved.</i><br>"},
    "sys_manual": {"zh": "<i>[系统] 已触发手动摘要，正在后台生成并发送...</i><br>", "en": "<i>[System] Manual summary triggered, generating in background...</i><br>"},
    "ai_thinking": {"zh": "<i>AI 正在思考中...</i>", "en": "<i>AI is thinking...</i>"},
    "ai_count_prefix": {"zh": "达到设定条数，自动摘要：", "en": "Count reached, auto summary:"},
    "ai_time_prefix": {"zh": "定时 ({}) 自动摘要：", "en": "Scheduled ({}) auto summary:"},
    "ai_fail": {"zh": "AI 请求失败，请检查配置或网络。", "en": "AI Request failed, check config/network."},
}

def tr(key: str, *args) -> str:
    """翻译函数，获取对应语言的字符串"""
    text = _STRINGS.get(key, {}).get(_LANG, key)
    if args:
        try:
            text = text.format(*args)
        except Exception:
            pass
    return text
