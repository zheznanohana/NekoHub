from flask import Blueprint, request, jsonify
from ..models import Message, Task, Settings
from ..services.ai import AiManager
from .. import db, socketio
import threading

bp = Blueprint('openclaw', __name__)
ai_manager = AiManager()

@bp.route('/message', methods=['POST'])
def receive_message():
    """
    OpenClaw 推送消息到 NekoHub
    POST /api/openclaw/message
    {
      "title": "通知标题",
      "message": "通知内容",
      "priority": 5,
      "tags": ["gotify", "rss"]
    }
    """
    data = request.get_json()
    
    if not data or not data.get('message'):
        return jsonify({'error': '缺少 message 字段'}), 400
    
    # 创建消息
    msg = Message(
        title=data.get('title', 'OpenClaw'),
        message=data.get('message', ''),
        priority=data.get('priority', 5),
        tags=','.join(data.get('tags', [])),
        source='openclaw'
    )
    db.session.add(msg)
    db.session.commit()
    
    # 广播给所有 WebSocket 客户端
    socketio.emit('message', msg.to_dict())
    
    # 检查是否需要转发
    s = Settings.get_all()
    if s.get('forward_enabled') == 'true':
        from ..utils.forward import Forwarder
        mode = int(s.get('forward_mode', 0))
        if mode in (0, 1):  # 0:全部，1:仅原始
            threading.Thread(
                target=Forwarder.forward_all,
                args=(s, msg.title, msg.message, mode),
                daemon=True
            ).start()
    
    return jsonify({'success': True, 'message_id': msg.id})

@bp.route('/task/<task_id>/run', methods=['POST'])
def run_task(task_id):
    """
    OpenClaw 触发 AI 任务
    POST /api/openclaw/task/{task_id}/run
    {
      "domains": ["gotify", "rss"],
      "extra_context": "额外背景数据"
    }
    """
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    data = request.get_json() or {}
    
    # 更新任务 domains
    if data.get('domains'):
        import json
        task.domains = json.dumps(data['domains'])
        db.session.commit()
    
    # 异步执行任务
    threading.Thread(
        target=ai_manager.run_task,
        args=(task.to_dict(), socketio),
        daemon=True
    ).start()
    
    return jsonify({'status': 'running', 'task_id': task_id})

@bp.route('/task/counter/<task_id>', methods=['POST'])
def increment_counter(task_id):
    """
    OpenClaw 增加任务计数器
    POST /api/openclaw/task/counter/{task_id}
    """
    ai_manager.increment_counter(task_id)
    return jsonify({'success': True})

@bp.route('/status', methods=['GET'])
def get_status():
    """
    OpenClaw 查询 NekoHub 状态
    GET /api/openclaw/status
    """
    return jsonify({
        'status': 'online',
        'messages_count': Message.query.count(),
        'tasks_count': Task.query.count(),
        'tasks_enabled': Task.query.filter_by(enabled=True).count()
    })
