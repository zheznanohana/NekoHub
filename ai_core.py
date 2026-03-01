# ai_core.py
from __future__ import annotations
import threading
import requests
from datetime import datetime
from PySide6.QtCore import QObject, QTimer, Signal
from storage import latest_messages
from gotify_client import send_message

class AiManager(QObject):
    chat_response_ready = Signal(str)
    
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.current_msg_count = 0
        self.last_summary_date = ""
        
        self.time_check_timer = QTimer(self)
        self.time_check_timer.timeout.connect(self._check_time_trigger)
        self.time_check_timer.start(60000) 

    def update_settings(self, new_settings):
        self.settings = new_settings

    def on_new_message(self, msg: dict):
        # --- 如果总开关关了，直接跳过 ---
        if not getattr(self.settings, 'ai_summary_enabled', False):
            return
            
        if getattr(self.settings, 'ai_summary_mode', 'count') == "count":
            self.current_msg_count += 1
            if self.current_msg_count >= getattr(self.settings, 'ai_summary_count', 10):
                self.current_msg_count = 0
                self.trigger_summary_async("达到设定条数，自动摘要：")

    def _check_time_trigger(self):
        # --- 如果总开关关了，直接跳过 ---
        if not getattr(self.settings, 'ai_summary_enabled', False):
            return
            
        if getattr(self.settings, 'ai_summary_mode', 'count') != "time":
            return
        
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        current_date_str = now.strftime("%Y-%m-%d %H:%M")
        
        times_str = getattr(self.settings, 'ai_summary_times', '08:00,18:00')
        times = [t.strip() for t in times_str.split(",") if t.strip()]
        if current_time_str in times and self.last_summary_date != current_date_str:
            self.last_summary_date = current_date_str
            self.trigger_summary_async(f"定时 ({current_time_str}) 自动摘要：")

    def trigger_summary_async(self, prefix=""):
        threading.Thread(target=self._generate_and_send_summary, args=(prefix,), daemon=True).start()

    def _generate_and_send_summary(self, prefix):
        api_key = getattr(self.settings, 'ai_api_key', '')
        if not api_key:
            return
            
        rows = latest_messages(20) 
        if not rows:
            return
            
        content = "\n".join([f"[{r[5]}] {r[2]}: {r[3]}" for r in rows])
        sys_prompt = getattr(self.settings, 'ai_system_prompt', '你是一个通知摘要助手。请简明扼要地总结以下收到的通知。')
        prompt = f"{sys_prompt}\n\n以下是最近的通知：\n{content}"
        
        summary = self._call_llm(prompt)
        
        g_url = getattr(self.settings, 'gotify_url', '')
        g_token = getattr(self.settings, 'gotify_send_token', '')
        if summary and g_url and g_token:
            try:
                send_message(
                    base_url=g_url,
                    app_token=g_token,
                    title="🤖 AI 通知摘要",
                    message=f"{prefix}\n{summary}",
                    priority=5
                )
            except Exception as e:
                print(f"发送摘要回 Gotify 失败: {e}")

    def send_chat_async(self, user_text: str):
        threading.Thread(target=self._process_chat, args=(user_text,), daemon=True).start()

    def _process_chat(self, user_text: str):
        rows = latest_messages(50) 
        context = "\n".join([f"[{r[5]}] {r[2]}: {r[3]}" for r in rows])
        prompt = f"你是一个贴心的智能助手，用户正在询问关于通知的问题。\n最近的通知记录如下：\n{context}\n\n用户的问题：{user_text}"
        
        reply = self._call_llm(prompt)
        self.chat_response_ready.emit(reply if reply else "AI 请求失败，请检查配置或网络。")

    def _call_llm(self, user_content: str) -> str:
        base_url = getattr(self.settings, 'ai_base_url', 'https://api.openai.com/v1')
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {getattr(self.settings, 'ai_api_key', '')}",
            "Content-Type": "application/json"
        }
        data = {
            "model": getattr(self.settings, 'ai_model', 'gpt-3.5-turbo'),
            "messages": [{"role": "user", "content": user_content}],
            "temperature": 0.7
        }
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"LLM API Error: {e}")
            return f"Error: {str(e)}"

