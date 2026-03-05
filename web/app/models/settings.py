from .. import db

class Settings(db.Model):
    """系统设置模型"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())
    
    @staticmethod
    def get(key, default=None):
        """获取设置值"""
        s = Settings.query.filter_by(key=key).first()
        return s.value if s else default
    
    @staticmethod
    def set(key, value):
        """设置值"""
        s = Settings.query.filter_by(key=key).first()
        if s:
            s.value = value
        else:
            s = Settings(key=key, value=value)
            db.session.add(s)
        db.session.commit()
        return value
    
    @staticmethod
    def get_all():
        """获取所有设置"""
        return {s.key: s.value for s in Settings.query.all()}
