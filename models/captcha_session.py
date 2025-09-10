from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

class CaptchaSession(db.Model):
    __tablename__ = 'captcha_sessions'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, nullable=False)
    giveaway_id = db.Column(db.BigInteger, nullable=False)
    question = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Integer, nullable=False)
    attempts = db.Column(db.Integer, default=0)
    max_attempts = db.Column(db.Integer, default=3)
    completed = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Indexes for efficient queries
    __table_args__ = (
        db.Index('idx_captcha_sessions_user_giveaway', 'user_id', 'giveaway_id'),
        db.Index('idx_captcha_sessions_expires_at', 'expires_at'),
    )
    
    @classmethod
    def create_session(cls, user_id, giveaway_id, question, correct_answer, timeout_minutes=10):
        """Create a new captcha session with expiration"""
        expires_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)
        return cls(
            user_id=user_id,
            giveaway_id=giveaway_id,
            question=question,
            correct_answer=correct_answer,
            expires_at=expires_at
        )
    
    def is_expired(self):
        """Check if the captcha session has expired"""
        return datetime.utcnow() > self.expires_at
    
    def can_attempt(self):
        """Check if user can still attempt to answer"""
        return not self.completed and self.attempts < self.max_attempts and not self.is_expired()
    
    def increment_attempts(self):
        """Increment the number of attempts"""
        self.attempts += 1
    
    def mark_completed(self):
        """Mark the captcha session as completed"""
        self.completed = True
    
    def to_dict(self):
        """Convert captcha session to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'giveaway_id': self.giveaway_id,
            'question': self.question,
            'attempts': self.attempts,
            'max_attempts': self.max_attempts,
            'completed': self.completed,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_expired': self.is_expired(),
            'can_attempt': self.can_attempt(),
            'attempts_remaining': max(0, self.max_attempts - self.attempts)
        }
    
    def __repr__(self):
        return f'<CaptchaSession {self.id}: User {self.user_id}, Giveaway {self.giveaway_id}>'

