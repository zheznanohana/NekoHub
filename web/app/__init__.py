from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from .config import config

# 初始化扩展
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')

def create_app(config_name=None):
    """应用工厂函数"""
    if config_name is None:
        config_name = 'default'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # 确保上传目录存在
    import os
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins=app.config['SOCKETIO_CORS_CORS_ORIGIN'])
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # 注册路由蓝图
    from .routes import api, ws, openclaw
    app.register_blueprint(api.bp, url_prefix='/api')
    app.register_blueprint(ws.bp, url_prefix='/ws')
    app.register_blueprint(openclaw.bp, url_prefix='/api/openclaw')
    
    # 注册模型
    with app.app_context():
        from .models import message, settings, task
        db.create_all()
    
    # 注册后台任务
    from .services import scheduler
    scheduler.init_app(app)
    
    return app
