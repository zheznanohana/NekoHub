from datetime import datetime
from .. import db

class Message(db.Model):
    """消息模型 - 存储所有通知"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    gotify_id = db.Column(db.Integer, unique=True, index=True)  # Gotify 原始 ID
    title = db.Column(db.String(500))
    message = db.Column(db.Text)
    priority = db.Column(db.Integer, default=5)
    tags = db.Column(db.String(200))  # 逗号分隔的标签
    source = db.Column(db.String(50), default='gotify')  # gotify/rss/imap/web3
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    is_forwarded = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'gotify_id': self.gotify_id,
            'title': self.title,
            'message': self.message,
            'priority': self.priority,
            'tags': self.tags,
            'source': self.source,
            'created_at': self.created_at.isoformat(),
            'is_read': self.is_read,
            'is_forwarded': self.is_forwarded
        }
    
    @staticmethod
    def from_gotify(gotify_msg):
        """从 Gotify 消息创建"""
        return Message(
            gotify_id=gotify_msg.get('id'),
            title=gotify_msg.get('title', ''),
            message=gotify_msg.get('message', ''),
            priority=gotify_msg.get('priority', 5),
            tags=','.join(gotify_msg.get('tags', [])),
            source='gotify'
        )
