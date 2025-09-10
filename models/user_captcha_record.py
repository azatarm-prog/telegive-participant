from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class UserCaptchaRecord(db.Model):
    __tablename__ = 'user_captcha_records'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, nullable=False, unique=True)
    captcha_completed = db.Column(db.Boolean, default=False)
    captcha_completed_at = db.Column(db.DateTime(timezone=True), default=None)
    first_participation_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    total_participations = db.Column(db.Integer, default=0)
    total_wins = db.Column(db.Integer, default=0)
    last_participation_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Index for fast user lookups
    __table_args__ = (
        db.Index('idx_user_captcha_records_user_id', 'user_id'),
    )
    
    def to_dict(self):
        """Convert user captcha record to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'captcha_completed': self.captcha_completed,
            'captcha_completed_at': self.captcha_completed_at.isoformat() if self.captcha_completed_at else None,
            'first_participation_at': self.first_participation_at.isoformat() if self.first_participation_at else None,
            'total_participations': self.total_participations,
            'total_wins': self.total_wins,
            'last_participation_at': self.last_participation_at.isoformat() if self.last_participation_at else None
        }
    
    def __repr__(self):
        return f'<UserCaptchaRecord {self.id}: User {self.user_id}, Captcha: {self.captcha_completed}>'

