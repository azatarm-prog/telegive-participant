from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Participant(db.Model):
    __tablename__ = 'participants'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    giveaway_id = db.Column(db.BigInteger, nullable=False)
    user_id = db.Column(db.BigInteger, nullable=False)
    username = db.Column(db.String(100), default=None)
    first_name = db.Column(db.String(100), default=None)
    last_name = db.Column(db.String(100), default=None)
    
    # Participation details
    participated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    captcha_completed = db.Column(db.Boolean, default=False)
    subscription_verified = db.Column(db.Boolean, default=False)
    subscription_verified_at = db.Column(db.DateTime(timezone=True), default=None)
    
    # Winner status
    is_winner = db.Column(db.Boolean, default=False)
    winner_selected_at = db.Column(db.DateTime(timezone=True), default=None)
    
    # Message delivery tracking
    message_delivered = db.Column(db.Boolean, default=False)
    delivery_timestamp = db.Column(db.DateTime(timezone=True), default=None)
    delivery_attempts = db.Column(db.Integer, default=0)
    
    # Unique constraint: one participation per user per giveaway
    __table_args__ = (
        db.UniqueConstraint('giveaway_id', 'user_id', name='uq_giveaway_user'),
        db.Index('idx_participants_giveaway_id', 'giveaway_id'),
        db.Index('idx_participants_user_id', 'user_id'),
        db.Index('idx_participants_is_winner', 'is_winner'),
    )
    
    def to_dict(self):
        """Convert participant to dictionary for API responses"""
        return {
            'id': self.id,
            'giveaway_id': self.giveaway_id,
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'participated_at': self.participated_at.isoformat() if self.participated_at else None,
            'captcha_completed': self.captcha_completed,
            'subscription_verified': self.subscription_verified,
            'subscription_verified_at': self.subscription_verified_at.isoformat() if self.subscription_verified_at else None,
            'is_winner': self.is_winner,
            'winner_selected_at': self.winner_selected_at.isoformat() if self.winner_selected_at else None,
            'message_delivered': self.message_delivered,
            'delivery_timestamp': self.delivery_timestamp.isoformat() if self.delivery_timestamp else None,
            'delivery_attempts': self.delivery_attempts
        }
    
    def __repr__(self):
        return f'<Participant {self.id}: User {self.user_id} in Giveaway {self.giveaway_id}>'

