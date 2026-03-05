from apscheduler.schedulers.background import BackgroundScheduler
from .. import socketio

scheduler = BackgroundScheduler()
_scheduler_initialized = False

def init_app(app):
    """初始化定时任务"""
    global _scheduler_initialized
    if _scheduler_initialized:
        return
    _scheduler_initialized = True
    
    from .ai import AiManager
    
    def scheduled_check():
        with app.app_context():
            ai_manager = AiManager()
            ai_manager.check_scheduled_tasks(socketio)
    
    # 每分钟检查定时任务
    scheduler.add_job(
        scheduled_check,
        'interval',
        minutes=1
    )
    scheduler.start()
