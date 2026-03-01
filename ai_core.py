# ai_core.py
import threading, requests, time, hmac, hashlib, base64, urllib.parse, smtplib
from email.mime.text import MIMEText
from datetime import datetime
from PySide6.QtCore import QObject, QTimer, Signal
from storage import latest_messages
from gotify_client import send_message

class AiManager(QObject):
    chat_response_ready = Signal(str)
    task_status_signal = Signal(str, str, bool)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.task_counters, self.last_run_minute, self.last_run_timestamp = {}, {}, {}
        self.timer = QTimer(self); self.timer.timeout.connect(self._check_periodic_tasks); self.timer.start(60000) 

    def update_settings(self, new_settings): self.settings = new_settings

    def _do_forward(self, title, content):
        """核心转发引擎"""
        s = self.settings
        if not s.forward_enabled: return
        msg_text = f"【NekoHub】\n📌 标题：{title}\n📝 内容：\n{content}"

        # --- 1. 钉钉转发 (支持加签模式) ---
        if s.dingtalk_webhook:
            def send_ding():
                url = s.dingtalk_webhook
                if s.dingtalk_secret:
                    timestamp = str(round(time.time() * 1000))
                    secret_enc = s.dingtalk_secret.encode('utf-8')
                    string_to_sign = f'{timestamp}\n{s.dingtalk_secret}'
                    hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
                    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                    url = f"{url}&timestamp={timestamp}&sign={sign}"
                try: 
                    res = requests.post(url, json={"msgtype": "text", "text": {"content": msg_text}}, timeout=10)
                    print(f"DingTalk Response: {res.text}") # 调试用
                except Exception as e: print(f"DingTalk Error: {e}")
            threading.Thread(target=send_ding, daemon=True).start()

        # --- 2. Telegram 转发 (标准 API) ---
        if s.tg_bot_token and s.tg_chat_id:
            def send_tg():
                url = f"https://api.telegram.org/bot{s.tg_bot_token}/sendMessage"
                # 注意：TG 转发需要确保 chat_id 正确，个人通常是数字，群组是负数
                payload = {"chat_id": s.tg_chat_id, "text": msg_text}
                try: 
                    res = requests.post(url, json=payload, timeout=10)
                    print(f"Telegram Response: {res.text}") 
                except Exception as e: print(f"Telegram Error: {e}")
            threading.Thread(target=send_tg, daemon=True).start()

        # --- 3. 邮件转发 ---
        if s.email_smtp and s.email_to:
            def send_mail():
                try:
                    msg = MIMEText(msg_text, 'plain', 'utf-8')
                    msg['Subject'], msg['From'], msg['To'] = f"NekoHub: {title}", s.email_user, s.email_to
                    with smtplib.SMTP_SSL(s.email_smtp, s.email_port) as svr:
                        svr.login(s.email_user, s.email_pass); svr.sendmail(s.email_user, [s.email_to], msg.as_string())
                except Exception as e: print(f"Email Error: {e}")
            threading.Thread(target=send_mail, daemon=True).start()

    def on_new_message(self, msg: dict):
        if self.settings.forward_mode in [0, 1]:
            self._do_forward(msg.get("title", "新通知"), msg.get("message", ""))
        for t in self.settings.ai_tasks:
            if not t.get("enabled", True) or t.get("mode") != "count": continue
            tid = t.get("id"); self.task_counters[tid] = self.task_counters.get(tid, 0) + 1
            if self.task_counters[tid] >= int(t.get("value", "10")):
                self.task_counters[tid] = 0; self.run_task_async(t, "【累计触发】")

    def _check_periodic_tasks(self):
        now_str, now_ts = datetime.now().strftime("%H:%M"), time.time()
        for t in self.settings.ai_tasks:
            if not t.get("enabled", True): continue
            tid, mode, val = t.get("id"), t.get("mode"), str(t.get("value", ""))
            if mode == "time" and now_str in [x.strip() for x in val.split(",")] and self.last_run_minute.get(tid) != now_str:
                self.last_run_minute[tid] = now_str; self.run_task_async(t, f"【定时 {now_str}】")
            elif mode == "interval" and now_ts - self.last_run_timestamp.get(tid, 0) >= int(val or 60) * 60:
                self.last_run_timestamp[tid] = now_ts; self.run_task_async(t, "【频率触发】")

    def run_task_async(self, task, prefix=""):
        threading.Thread(target=self._execute_llm_task, args=(task, prefix), daemon=True).start()

    def _execute_llm_task(self, task, prefix):
        name, limit = task.get('name', '任务'), int(task.get("context_limit", 50))
        rows = latest_messages(limit)
        if not rows: return
        self.task_status_signal.emit(name, f"AI 分析中({len(rows)}条)...", False)
        prompt = f"{self.settings.ai_system_prompt}\n指令：{task.get('prompt')}\n内容：\n" + "\n".join([f"[{r[5]}] {r[2]}: {r[3]}" for r in rows])
        reply, err = self._call_llm(prompt)
        if reply:
            if self.settings.forward_mode in [0, 2]: self._do_forward(f"AI任务: {name}", reply)
            if self.settings.gotify_url: send_message(self.settings.gotify_url, self.settings.gotify_send_token, f"🤖 {name}", f"{prefix}\n{reply}")
            self.task_status_signal.emit(name, "已完成并分发", False)

    def send_chat_async(self, text): threading.Thread(target=self._process_chat, args=(text,), daemon=True).start()
    def _process_chat(self, text):
        limit = getattr(self.settings, "ai_chat_context_limit", 50); rows = latest_messages(limit)
        prompt = f"问：{text}\n背景：\n" + "\n".join([f"[{r[5]}] {r[2]}: {r[3]}" for r in rows])
        reply, err = self._call_llm(prompt); self.chat_response_ready.emit(reply if not err else f"错误：{err}")

    def _call_llm(self, content):
        base = self.settings.ai_base_url.strip().rstrip('/')
        url = f"{base}/chat/completions" if "/v1" in base or "localhost" in base else f"{base}/v1/chat/completions"
        try:
            r = requests.post(url, headers={"Authorization": f"Bearer {self.settings.ai_api_key}"}, json={"model": self.settings.ai_model, "messages": [{"role": "user", "content": content}]}, timeout=35)
            return r.json()["choices"][0]["message"]["content"], None
        except Exception as e: return None, str(e)