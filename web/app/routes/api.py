import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, create_access_token
from .. import db
from ..models import Message, Settings, Task
from ..services.gotify import GotifyClient
from ..services.ai import AiManager
from ..services.rss import RssService
from ..utils.forward import Forwarder
from ..config import Config

bp = Blueprint('api', __name__)
ai_manager = AiManager()

@bp.route('/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    # 从 Settings 读取密码，默认 admin
    saved_password = Settings.get('admin_password', 'admin')
    
    if username == 'admin' and password == saved_password:
        access_token = create_access_token(identity=username)
        return jsonify({'access_token': access_token})
    return jsonify({'error': '认证失败'}), 401

@bp.route('/auth/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """修改密码"""
    from flask_jwt_extended import get_jwt_identity
    current_user = get_jwt_identity()
    
    if current_user != 'admin':
        return jsonify({'error': '无权操作'}), 403
    
    data = request.get_json()
    new_password = data.get('new_password', '')
    
    if len(new_password) < 6:
        return jsonify({'error': '密码至少 6 位'}), 400
    
    Settings.set('admin_password', new_password)
    return jsonify({'success': True})

@bp.route('/messages', methods=['GET'])
@jwt_required()
def get_messages():
    """获取消息列表"""
    limit = request.args.get('limit', 50, type=int)
    source = request.args.get('source')
    
    query = Message.query
    if source:
        query = query.filter(Message.source == source)
    
    messages = query.order_by(Message.created_at.desc()).limit(limit).all()
    return jsonify([m.to_dict() for m in messages])

@bp.route('/messages/<int:id>/read', methods=['POST'])
@jwt_required()
def mark_read(id):
    """标记已读"""
    msg = Message.query.get_or_404(id)
    msg.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    """获取任务列表"""
    tasks = Task.query.all()
    return jsonify([t.to_dict() for t in tasks])

@bp.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    """创建任务"""
    data = request.get_json()
    task = Task.from_dict(data)
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201

@bp.route('/tasks/<id>', methods=['PUT'])
@jwt_required()
def update_task(id):
    """更新任务"""
    task = Task.query.get_or_404(id)
    data = request.get_json()
    
    task.name = data.get('name', task.name)
    task.prompt = data.get('prompt', task.prompt)
    task.mode = data.get('mode', task.mode)
    task.value = data.get('value', task.value)
    task.enabled = data.get('enabled', task.enabled)
    
    # domains 需要转为 JSON 字符串
    domains = data.get('domains')
    if domains:
        task.domains = json.dumps(domains)
    
    task.limit_gotify = data.get('limit_gotify', task.limit_gotify)
    task.limit_rss = data.get('limit_rss', task.limit_rss)
    task.limit_imap = data.get('limit_imap', task.limit_imap)
    task.limit_web3 = data.get('limit_web3', task.limit_web3)
    
    db.session.commit()
    return jsonify(task.to_dict())

@bp.route('/tasks/<id>', methods=['DELETE'])
@jwt_required()
def delete_task(id):
    """删除任务"""
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/tasks/<id>/run', methods=['POST'])
@jwt_required()
def run_task(id):
    """手动执行任务"""
    import requests
    from .. import db
    from ..services.gotify import GotifyClient
    from ..models import Message, Settings
    
    task = Task.query.get_or_404(id)
    task_dict = task.to_dict()
    
    try:
        # 获取上下文数据
        context_texts = []
        domains = task_dict.get('domains', [])
        
        if 'gotify' in domains:
            msgs = Message.query.filter(Message.source == 'gotify').order_by(Message.created_at.desc()).limit(task_dict.get('limit_gotify', 20)).all()
            if msgs:
                context_texts.append("=== 通知 ===\n" + "\n".join([f"[{m.title}] {m.message}" for m in msgs]))
        
        if not context_texts:
            return jsonify({'status': 'no_data', 'message': '暂无数据可处理'}), 200
        
        # 调用 AI
        from ..config import Config
        context_text = '\n\n'.join(context_texts)
        payload = {
            "model": Config.AI_MODEL,
            "messages": [{"role": "user", "content": f"任务：{task_dict['prompt']}\n\n数据：\n{context_text}"}],
            "temperature": 0.5
        }
        
        headers = {"Authorization": f"Bearer {Config.AI_API_KEY}"}
        resp = requests.post(f"{Config.AI_BASE_URL}/chat/completions", json=payload, headers=headers, timeout=120)
        
        if resp.status_code == 200:
            ans = resp.json()["choices"][0]["message"]["content"]
            
            # 更新任务运行计数
            task.run_count = (task.run_count or 0) + 1
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': '任务执行成功',
                'result': ans,
                'run_count': task.run_count
            })
        else:
            error_msg = f'AI 请求失败：{resp.status_code}'
            if resp.status_code == 401:
                error_msg = 'AI API Key 无效，请在 AI 助手页面配置正确的 API Key'
            return jsonify({'status': 'error', 'message': error_msg}), 500
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/ai/chat', methods=['POST'])
@jwt_required()
def ai_chat():
    """AI 对话"""
    data = request.get_json()
    user_msg = data.get('message')
    domains = data.get('domains', ['gotify'])
    context_limit = data.get('limit', {'gotify': 20, 'rss': 10})
    model_config = data.get('model_config')
    
    # 如果提供了自定义模型配置，临时使用
    if model_config:
        from ..services.ai import AiManager
        temp_ai = AiManager(
            base_url=model_config.get('baseUrl', ''),
            api_key=model_config.get('apiKey', ''),
            model=model_config.get('model', '')
        )
        response = temp_ai.chat(user_msg, domains, context_limit)
    else:
        response = ai_manager.chat(user_msg, domains, context_limit)
    
    return jsonify({'response': response})

@bp.route('/settings', methods=['GET'])
@jwt_required()
def get_settings():
    """获取设置"""
    return jsonify(Settings.get_all())

@bp.route('/settings', methods=['POST'])
@jwt_required()
def update_settings():
    """更新设置"""
    data = request.get_json()
    for key, value in data.items():
        Settings.set(key, str(value))
    return jsonify({'success': True})

@bp.route('/gotify/test', methods=['POST'])
@jwt_required()
def test_gotify():
    """测试 Gotify 连接"""
    data = request.get_json()
    client = GotifyClient(
        data.get('url', ''),
        data.get('recv_token', ''),
        data.get('send_token', '')
    )
    ok, msg = client.test_connection()
    return jsonify({'success': ok, 'message': msg})

@bp.route('/forward/test', methods=['POST'])
@jwt_required()
def test_forward():
    """测试转发"""
    data = request.get_json()
    results = Forwarder.forward_all(
        data,
        "NekoHub 转发测试",
        "如果你看到这条消息，说明转发配置正确！",
        mode=0
    )
    return jsonify(results)

@bp.route('/rss', methods=['GET'])
@jwt_required()
def get_rss():
    """获取 RSS 订阅列表"""
    try:
        import json
        rss_service = RssService()
        feeds_str = Settings.get('rss_feeds', '[]')
        feeds = json.loads(feeds_str) if feeds_str else []
        for feed in feeds:
            rss_service.add_feed(feed['name'], feed['url'])
        items = rss_service.fetch_data(limit=50)
        return jsonify(items)
    except Exception as e:
        print(f"RSS API 错误：{e}")
        return jsonify([])

@bp.route('/rss/refresh', methods=['POST'])
@jwt_required()
def refresh_rss():
    """刷新 RSS"""
    data = request.get_json() or {}
    rss_service = RssService()
    import json
    feeds = Settings.get('rss_feeds', '[]')
    for feed in json.loads(feeds):
        rss_service.add_feed(feed['name'], feed['url'])
    items = rss_service.fetch_data(limit=50)
    return jsonify(items)
