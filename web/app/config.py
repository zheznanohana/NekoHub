import os
from datetime import timedelta

class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'nekohub-secret-key-change-in-production')
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///nekohub.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT 配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # SocketIO 配置
    SOCKETIO_ASYNC_MODE = 'eventlet'
    SOCKETIO_CORS_CORS_ORIGIN = os.environ.get('SOCKETIO_CORS_ORIGIN', '*')
    
    # Gotify 配置
    GOTIFY_URL = os.environ.get('GOTIFY_URL', 'https://notify.diu.ac.cn')
    GOTIFY_RECV_TOKEN = os.environ.get('GOTIFY_RECV_TOKEN', '')
    GOTIFY_SEND_TOKEN = os.environ.get('GOTIFY_SEND_TOKEN', '')
    
    # AI 配置
    AI_BASE_URL = os.environ.get('AI_BASE_URL', 'https://api.deepseek.com/v1')
    AI_API_KEY = os.environ.get('AI_API_KEY', '')
    AI_MODEL = os.environ.get('AI_MODEL', 'deepseek-chat')
    
    # OpenClaw 接口配置
    OPENCLAW_ENABLED = os.environ.get('OPENCLAW_ENABLED', 'false').lower() == 'true'
    OPENCLAW_SESSION_KEY = os.environ.get('OPENCLAW_SESSION_KEY', 'default')
    OPENCLAW_API_URL = os.environ.get('OPENCLAW_API_URL', 'http://localhost:8080')
    
    # 邮件 SMTP 配置
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASS = os.environ.get('SMTP_PASS', '')
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SQLALCHEMY_ECHO = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
