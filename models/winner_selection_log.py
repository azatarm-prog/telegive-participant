from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY

db = SQLAlchemy()

class WinnerSelectionLog(db.Model):
    __tablename__ = 'winner_selection_log'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    giveaway_id = db.Column(db.BigInteger, nullable=False)
    total_participants = db.Column(db.Integer, nullable=False)
    winner_count_requested = db.Column(db.Integer, nullable=False)
    winner_count_selected = db.Column(db.Integer, nullable=False)
    selection_method = db.Column(db.String(50), default='cryptographic_random')
    selection_seed = db.Column(db.String(255), default=None)
    selected_user_ids = db.Column(ARRAY(db.BigInteger), nullable=False)
    selection_timestamp = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Index for giveaway lookups
    __table_args__ = (
        db.Index('idx_winner_selection_log_giveaway_id', 'giveaway_id'),
    )
    
    @classmethod
    def create_log(cls, giveaway_id, total_participants, winner_count_requested, 
                   selected_user_ids, selection_method='cryptographic_random', selection_seed=None):
        """Create a new winner selection log entry"""
        return cls(
            giveaway_id=giveaway_id,
            total_participants=total_participants,
            winner_count_requested=winner_count_requested,
            winner_count_selected=len(selected_user_ids),
            selection_method=selection_method,
            selection_seed=selection_seed,
            selected_user_ids=selected_user_ids
        )
    
    def to_dict(self):
        """Convert winner selection log to dictionary for API responses"""
        return {
            'id': self.id,
            'giveaway_id': self.giveaway_id,
            'total_participants': self.total_participants,
            'winner_count_requested': self.winner_count_requested,
            'winner_count_selected': self.winner_count_selected,
            'selection_method': self.selection_method,
            'selection_seed': self.selection_seed,
            'selected_user_ids': self.selected_user_ids,
            'selection_timestamp': self.selection_timestamp.isoformat() if self.selection_timestamp else None
        }
    
    def __repr__(self):
        return f'<WinnerSelectionLog {self.id}: Giveaway {self.giveaway_id}, {self.winner_count_selected} winners>'

