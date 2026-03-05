from flask import Blueprint, request
from .. import socketio, db
from ..models import Message, Settings
from ..services.gotify import GotifyClient
from ..services.ai import AiManager
from ..utils.forward import Forwarder
import threading

bp = Blueprint('ws', __name__)
ai_manager = AiManager()
task_counters = {}

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('subscribe')
def handle_subscribe(data):
    """订阅消息"""
    print(f'Client {request.sid} subscribed')

def poll_gotify():
    """轮询 Gotify 新消息（后台线程）"""
    import time
    from .. import create_app
    last_id = 0
    
    app = create_app()
    
    while True:
        try:
            with app.app_context():
                s = Settings.get_all()
                if not s.get('gotify_url') or not s.get('gotify_recv_token'):
                    time.sleep(10)
                    continue
                
                # 创建带超时的客户端
                client = GotifyClient(s['gotify_url'], s['gotify_recv_token'], '')
                msgs = client.fetch_messages(limit=50)
                
                if msgs:
                    for msg in reversed(msgs):
                        msg_id = msg.get('id', 0)
                        if msg_id > last_id:
                            last_id = msg_id
                            m = Message.from_gotify(msg)
                            db.session.add(m)
                            db.session.commit()
                            socketio.emit('message', m.to_dict())
                
                time.sleep(5)
        except Exception as e:
            print(f"Poll error: {e}")
            time.sleep(10)

# 启动轮询线程
threading.Thread(target=poll_gotify, daemon=True).start()
