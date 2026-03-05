from datetime import datetime
import uuid
from .. import db

class Task(db.Model):
    """AI 自动化任务模型"""
    __tablename__ = 'tasks'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    mode = db.Column(db.String(20), default='count')  # count/time/interval
    value = db.Column(db.String(50))  # 触发值 (条数/时间点/分钟数)
    enabled = db.Column(db.Boolean, default=True)
    domains = db.Column(db.String(200))  # JSON 数组：["gotify","rss","imap","web3"]
    limit_gotify = db.Column(db.Integer, default=20)
    limit_rss = db.Column(db.Integer, default=10)
    limit_imap = db.Column(db.Integer, default=10)
    limit_web3 = db.Column(db.Integer, default=20)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    run_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'name': self.name,
            'prompt': self.prompt,
            'mode': self.mode,
            'value': self.value,
            'enabled': self.enabled,
            'domains': json.loads(self.domains or '[]'),
            'limit_gotify': self.limit_gotify,
            'limit_rss': self.limit_rss,
            'limit_imap': self.limit_imap,
            'limit_web3': self.limit_web3,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'run_count': self.run_count,
            'created_at': self.created_at.isoformat()
        }
    
    @staticmethod
    def from_dict(data):
        import json
        return Task(
            id=data.get('id') or str(uuid.uuid4()),
            name=data.get('name', 'New Task'),
            prompt=data.get('prompt', ''),
            mode=data.get('mode', 'count'),
            value=data.get('value', '10'),
            enabled=data.get('enabled', True),
            domains=json.dumps(data.get('domains', ['gotify'])),
            limit_gotify=data.get('limit_gotify', 20),
            limit_rss=data.get('limit_rss', 10),
            limit_imap=data.get('limit_imap', 10),
            limit_web3=data.get('limit_web3', 20)
        )
