import json
import threading
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional
from flask_socketio import emit

class AiManager:
    """AI 管理器 - 处理对话和自动化任务"""
    
    def __init__(self, app=None, base_url=None, api_key=None, model=None):
        self.app = app
        self.task_counters = {}
        self.running_tasks = set()
        self.last_run_times = {}
        # 支持自定义配置
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
    
    def init_app(self, app):
        self.app = app
    
    def chat(self, user_msg: str, domains: List[str], context_limit: Dict) -> str:
        """AI 对话"""
        try:
            from ..models import Message
            from .. import db
            
            # 获取上下文数据
            context_texts = []
            
            # Gotify 通知
            if 'gotify' in domains:
                msgs = Message.query.filter(
                    Message.source == 'gotify'
                ).order_by(Message.created_at.desc()).limit(context_limit.get('gotify', 20)).all()
                if msgs:
                    context_texts.append("【原生通知】\n" + "\n".join([f"[{m.title}] {m.message}" for m in msgs]))
            
            # RSS
            if 'rss' in domains:
                from .rss import RssService
                rss = RssService()
                data = rss.fetch_data()[:context_limit.get('rss', 10)]
                if data:
                    context_texts.append("【RSS 资讯】\n" + "\n".join([f"[{d['title']}] {d['summary']}" for d in data]))
            
            # 构建请求
            from ..config import Config
            from ..models import Settings
            context_text = '\n\n'.join(context_texts)
            
            # 优先从数据库读取配置，其次使用环境变量
            settings = Settings.get_all()
            base_url = self.base_url or settings.get('ai_base_url') or Config.AI_BASE_URL
            api_key = self.api_key or settings.get('ai_api_key') or Config.AI_API_KEY
            model = self.model or settings.get('ai_model') or Config.AI_MODEL
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是专业的信息处理助手。"},
                    {"role": "user", "content": f"背景：\n{context_text}\n\n问题：{user_msg}"}
                ],
                "temperature": 0.7
            }
            
            headers = {"Authorization": f"Bearer {api_key}"}
            
            resp = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=60)
            
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            return f"API 错误：{resp.status_code}"
        except Exception as e:
            return f"请求异常：{str(e)}"
    
    def run_task(self, task: Dict, socketio=None) -> bool:
        """执行自动化任务"""
        tid = task.get('id')
        if tid in self.running_tasks:
            return False
        
        self.running_tasks.add(tid)
        try:
            from ..models import Message, Task, Settings
            from .. import db
            from .gotify import GotifyClient
            
            # 获取上下文
            context_texts = []
            domains = json.loads(task.get('domains', '[]'))
            
            if 'gotify' in domains:
                msgs = Message.query.filter(Message.source == 'gotify').order_by(Message.created_at.desc()).limit(task.get('limit_gotify', 20)).all()
                if msgs:
                    context_texts.append("=== 通知 ===\n" + "\n".join([f"[{m.title}] {m.message}" for m in msgs]))
            
            if not context_texts:
                if socketio:
                    socketio.emit('task_status', {'task_name': task['name'], 'message': '无数据可处理', 'error': False})
                return False
            
            # 调用 AI
            from ..config import Config
            context_text = '\n\n'.join(context_texts)
            payload = {
                "model": Config.AI_MODEL,
                "messages": [{"role": "user", "content": f"任务：{task['prompt']}\n\n数据：\n{context_text}"}],
                "temperature": 0.5
            }
            
            headers = {"Authorization": f"Bearer {Config.AI_API_KEY}"}
            resp = requests.post(f"{Config.AI_BASE_URL}/chat/completions", json=payload, headers=headers, timeout=120)
            
            if resp.status_code == 200:
                ans = resp.json()["choices"][0]["message"]["content"]
                
                # 发送结果到 Gotify
                s = Settings.get_all()
                gotify = GotifyClient(
                    s.get('gotify_url', ''),
                    s.get('gotify_recv_token', ''),
                    s.get('gotify_send_token', '')
                )
                gotify.send_message(f"[AI 任务完成] {task['name']}", ans, priority=5)
                
                # 更新任务状态
                task_obj = Task.query.get(tid)
                if task_obj:
                    task_obj.last_run = datetime.utcnow()
                    task_obj.run_count += 1
                    db.session.commit()
                
                if socketio:
                    socketio.emit('task_status', {'task_name': task['name'], 'message': '执行成功', 'error': False})
                return True
            else:
                if socketio:
                    socketio.emit('task_status', {'task_name': task['name'], 'message': f'API 失败：{resp.status_code}', 'error': True})
                return False
        except Exception as e:
            if socketio:
                socketio.emit('task_status', {'task_name': task['name'], 'message': f'崩溃：{str(e)}', 'error': True})
            return False
        finally:
            self.running_tasks.discard(tid)
    
    def check_scheduled_tasks(self, socketio=None):
        """检查定时任务（每分钟调用）"""
        from ..models import Task
        now = datetime.utcnow()
        hm = now.strftime("%H:%M")
        
        for task in Task.query.filter_by(enabled=True).all():
            tid = task.id
            mode = task.mode
            val = str(task.value or '').strip()
            
            # 定时执行
            if mode == 'time' and hm in [x.strip() for x in val.split(',')]:
                if self.last_run_times.get(tid) != hm:
                    self.last_run_times[tid] = hm
                    threading.Thread(target=self.run_task, args=(task.to_dict(), socketio), daemon=True).start()
            
            # 间隔执行
            elif mode == 'interval':
                try:
                    mins = int(val)
                    if mins > 0:
                        last_ts = self.last_run_times.get(tid, 0)
                        if time.time() - last_ts >= mins * 60:
                            self.last_run_times[tid] = time.time()
                            threading.Thread(target=self.run_task, args=(task.to_dict(), socketio), daemon=True).start()
                except:
                    pass
            
            # 计数触发
            elif mode == 'count':
                count = self.task_counters.get(tid, 0)
                try:
                    limit = int(val)
                    if count >= limit:
                        self.task_counters[tid] = 0
                        threading.Thread(target=self.run_task, args=(task.to_dict(), socketio), daemon=True).start()
                except:
                    pass
    
    def increment_counter(self, tid: str):
        """增加任务计数器"""
        self.task_counters[tid] = self.task_counters.get(tid, 0) + 1
