# ai_core.py
import json
import threading
import time
import requests
from datetime import datetime
from PySide6.QtCore import QObject, Signal, QTimer

class AiManager(QObject):
    chat_response_ready = Signal(str)
    task_status_signal = Signal(str, str, bool)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.rss_plugin = None
        self.imap_plugin = None
        self.web3_plugin = None
        
        # --- 任务调度状态存储 ---
        self.task_counters = {}   # 累计计数触发用
        self.running_tasks = set() # 防止任务重复并发
        self.last_run_times = {}  # 定时点/间隔执行记录
        
        # 每分钟心跳定时器，处理定时任务
        self.timer_1m = QTimer()
        self.timer_1m.timeout.connect(self._on_1m_tick)
        self.timer_1m.start(60000)

    def mount_plugins(self, rss, imap, web3):
        self.rss_plugin = rss
        self.imap_plugin = imap
        self.web3_plugin = web3

    def update_settings(self, new_settings):
        self.settings = new_settings

    # ---------------------------------------------------------
    # 核心逻辑一：任务触发器 (累计计数触发)
    # ---------------------------------------------------------
    def on_new_message(self, gotify_msg: dict):
        """当收到新的 Gotify 消息时，检查是否有 '累计计数' 触发的任务"""
        for task in self.settings.ai_tasks:
            if not task.get("enabled", False): 
                continue
                
            if task.get("mode") == "count":
                tid = task["id"]
                self.task_counters[tid] = self.task_counters.get(tid, 0) + 1
                
                try:
                    limit = int(task.get("value", "10"))
                except:
                    limit = 10
                    
                if self.task_counters[tid] >= limit:
                    self.task_counters[tid] = 0 # 重置计数
                    self.run_task_async(task)

    # ---------------------------------------------------------
    # 核心逻辑二：定时触发器 (心跳检测)
    # ---------------------------------------------------------
    def _on_1m_tick(self):
        """每分钟检测一次定时或间隔任务"""
        now = datetime.now()
        hm = now.strftime("%H:%M")
        
        for task in self.settings.ai_tasks:
            if not task.get("enabled", False): 
                continue
                
            tid = task["id"]
            mode = task.get("mode")
            val = str(task.get("value", "")).strip()
            
            # 1. 定时执行 (如 08:00, 20:00)
            if mode == "time":
                times = [x.strip() for x in val.split(",") if x.strip()]
                if hm in times:
                    # 确保这一分钟只跑一次
                    if self.last_run_times.get(tid) != hm:
                        self.last_run_times[tid] = hm
                        self.run_task_async(task)
            
            # 2. 固定间隔执行 (如 每隔 60 分钟)
            elif mode == "interval":
                try:
                    mins = int(val)
                except:
                    continue
                if mins <= 0: continue
                
                last_ts = self.last_run_times.get(tid, 0)
                if time.time() - last_ts >= mins * 60:
                    self.last_run_times[tid] = time.time()
                    self.run_task_async(task)

    # ---------------------------------------------------------
    # 核心逻辑三：AI 对话逻辑 (带精准过滤)
    # ---------------------------------------------------------
    def send_chat_async(self, user_msg: str, domains: list):
        threading.Thread(target=self._process_chat, args=(user_msg, domains), daemon=True).start()

    def _process_chat(self, user_msg: str, domains: list):
        try:
            s = self.settings
            limit_gotify = getattr(s, "ai_limit_gotify", 20)
            limit_rss = getattr(s, "ai_limit_rss", 10)
            limit_imap = getattr(s, "ai_limit_imap", 10)
            limit_web3 = getattr(s, "ai_limit_web3", 20)

            context_texts = []
            
            # 1. 严格过滤后的 Gotify 原生通知
            if "gotify" in domains:
                try:
                    from storage import latest_messages
                    # 深度拉取，防止过滤掉标签后条数不足
                    raw_msgs = latest_messages(200) 
                    gotify_pure = []
                    for m in raw_msgs:
                        title = str(m[2] or "").upper()
                        # 【核心改动：防侧漏】如果标题带了插件标签或AI前缀，不作为“通知”来源
                        if any(tag in title for tag in ["[RSS]", "[WEB3]", "[IMAP]", "[AI任务完成]"]):
                            continue
                        gotify_pure.append(f"通知: {m[2]}\n内容: {m[3]}")
                        if len(gotify_pure) >= limit_gotify:
                            break
                    if gotify_pure:
                        context_texts.append("【原生通知流】\n" + "\n".join(gotify_pure))
                except: pass

            # 2. 独立 RSS (只有勾选了才进上下文)
            if "rss" in domains and self.rss_plugin:
                data = self.rss_plugin.fetch_data(is_bg=True)[:limit_rss]
                if data:
                    context_texts.append("【RSS 订阅资讯】\n" + "\n".join([f"标题: {d['title']}\n摘要: {d['summary']}" for d in data]))

            # 3. 独立 邮件
            if "imap" in domains and self.imap_plugin:
                data = self.imap_plugin.fetch_data(is_bg=True)[:limit_imap]
                if data:
                    context_texts.append("【邮件动态】\n" + "\n".join([f"发件人: {d['source']}\n内容: {d['title']}" for d in data]))

            # 4. 独立 Web3
            if "web3" in domains and self.web3_plugin:
                data = self.web3_plugin.fetch_data(is_bg=True)[:limit_web3]
                if data:
                    context_texts.append("【链上资金预警】\n" + "\n".join([f"账户: {d['source']}\n标题: {d['title']}\n详情: {d['summary']}" for d in data]))

            full_context = "\n\n".join(context_texts)
            system_prompt = "你是一个专业的信息处理助手。请根据提供的背景上下文回答用户。背景数据中不存在的内容请直说。"
            
            # 组织请求
            payload = {
                "model": s.ai_model,
                "messages": [
                    {"role": "system", "content": f"{system_prompt}\n\n背景数据：\n{full_context if full_context else '暂无勾选的数据源或数据为空。'}"},
                    {"role": "user", "content": user_msg}
                ],
                "temperature": 0.7
            }
            
            headers = {"Authorization": f"Bearer {s.ai_api_key}", "Content-Type": "application/json"}
            resp = requests.post(s.ai_base_url + "/chat/completions", json=payload, headers=headers, timeout=60)
            
            if resp.status_code == 200:
                self.chat_response_ready.emit(resp.json()["choices"][0]["message"]["content"])
            else:
                self.chat_response_ready.emit(f"⚠️ API 错误: {resp.status_code}")
        except Exception as e:
            self.chat_response_ready.emit(f"⚠️ 请求异常: {str(e)}")

    # ---------------------------------------------------------
    # 核心逻辑四：自动化任务执行 (带隔离逻辑)
    # ---------------------------------------------------------
    def run_task_async(self, task: dict):
        tid = task.get("id")
        if tid in self.running_tasks: return
        self.running_tasks.add(tid)
        threading.Thread(target=self._run_task, args=(task,), daemon=True).start()

    def _run_task(self, task: dict):
        try:
            name = task.get("name", "Unnamed")
            prompt = task.get("prompt", "")
            domains = task.get("domains", [])
            s = self.settings

            if not s.ai_base_url or not s.ai_api_key:
                self.task_status_signal.emit(name, "缺少 AI 配置", True)
                return

            # 获取该任务特定的条数限制
            limit_gotify = int(task.get("limit_gotify", 20))
            limit_rss = int(task.get("limit_rss", 10))
            limit_imap = int(task.get("limit_imap", 10))
            limit_web3 = int(task.get("limit_web3", 20))

            context_texts = []
            
            # 处理选中的数据源，执行同样的“净水过滤”逻辑
            if "gotify" in domains:
                try:
                    from storage import latest_messages
                    raw_msgs = latest_messages(200)
                    gotify_pure = []
                    for m in raw_msgs:
                        title = str(m[2] or "").upper()
                        if any(tag in title for tag in ["[RSS]", "[WEB3]", "[IMAP]", "[AI任务完成]"]):
                            continue
                        gotify_pure.append(f"[{m[2]}] {m[3]}")
                        if len(gotify_pure) >= limit_gotify: break
                    if gotify_pure: context_texts.append("=== 通知数据 ===\n" + "\n".join(gotify_pure))
                except: pass

            if "rss" in domains and self.rss_plugin:
                data = self.rss_plugin.fetch_data(is_bg=True)[:limit_rss]
                if data: context_texts.append("=== RSS 订阅 ===\n" + "\n".join([d['title'] for d in data]))

            if "imap" in domains and self.imap_plugin:
                data = self.imap_plugin.fetch_data(is_bg=True)[:limit_imap]
                if data: context_texts.append("=== 邮件动态 ===\n" + "\n".join([d['title'] for d in data]))

            if "web3" in domains and self.web3_plugin:
                data = self.web3_plugin.fetch_data(is_bg=True)[:limit_web3]
                if data: context_texts.append("=== 链上异动 ===\n" + "\n".join([d['title'] for d in data]))

            full_context = "\n\n".join(context_texts)
            if not full_context.strip():
                self.task_status_signal.emit(name, "当前无相关内容可处理", False)
                return

            self.task_status_signal.emit(name, "正在智能分析中...", False)
            
            payload = {
                "model": s.ai_model,
                "messages": [{"role": "user", "content": f"任务指令: {prompt}\n\n数据背景: {full_context}"}],
                "temperature": 0.5
            }
            headers = {"Authorization": f"Bearer {s.ai_api_key}", "Content-Type": "application/json"}
            resp = requests.post(s.ai_base_url + "/chat/completions", json=payload, headers=headers, timeout=120)
            
            if resp.status_code == 200:
                ans = resp.json()["choices"][0]["message"]["content"]
                from gotify_client import send_message
                # 任务完成后把结果发回 Gotify 弹窗和记录
                send_message(s.gotify_url, s.gotify_send_token, f"[AI任务完成] {name}", ans, priority=5)
                self.task_status_signal.emit(name, "执行成功", False)
            else:
                self.task_status_signal.emit(name, f"API 响应失败: {resp.status_code}", True)

        except Exception as e:
            self.task_status_signal.emit(name, f"崩溃: {str(e)}", True)
        finally:
            self.running_tasks.discard(task.get("id"))