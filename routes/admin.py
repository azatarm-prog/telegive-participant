from flask import Blueprint, jsonify, request
from models import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/init-db', methods=['POST'])
def init_database():
    """Initialize database tables"""
    try:
        # Create all tables
        db.create_all()
        db.session.commit()
        
        logger.info("Database tables created successfully")
        
        return jsonify({
            'success': True,
            'message': 'Database tables created successfully',
            'service': 'participant-service'
        }), 200
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'service': 'participant-service'
        }), 500

@admin_bp.route('/admin/db-status', methods=['GET'])
def database_status():
    """Check database status and table information"""
    try:
        # Test connection
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        
        # Check tables
        from models import Participant, UserCaptchaRecord, CaptchaSession, WinnerSelectionLog
        
        table_info = {}
        tables = {
            'participants': Participant,
            'user_captcha_records': UserCaptchaRecord,
            'captcha_sessions': CaptchaSession,
            'winner_selection_log': WinnerSelectionLog
        }
        
        for table_name, model in tables.items():
            try:
                count = model.query.count()
                table_info[table_name] = {
                    'exists': True,
                    'record_count': count
                }
            except Exception as e:
                table_info[table_name] = {
                    'exists': False,
                    'error': str(e)
                }
        
        return jsonify({
            'database_connected': True,
            'message': 'Database is accessible',
            'tables': table_info,
            'service': 'participant-service'
        }), 200
        
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return jsonify({
            'database_connected': False,
            'error': str(e),
            'service': 'participant-service'
        }), 500

@admin_bp.route('/admin/cleanup', methods=['POST'])
def cleanup_data():
    """Run cleanup tasks"""
    try:
        from tasks.cleanup_tasks import run_cleanup
        
        results = run_cleanup()
        
        return jsonify({
            'success': True,
            'message': 'Cleanup completed',
            'results': results,
            'service': 'participant-service'
        }), 200
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'service': 'participant-service'
        }), 500

@admin_bp.route('/admin/stats', methods=['GET'])
def get_stats():
    """Get service statistics"""
    try:
        from models import Participant, UserCaptchaRecord, CaptchaSession, WinnerSelectionLog
        from datetime import datetime, timedelta
        
        # Basic counts
        total_participants = Participant.query.count()
        total_users_with_captcha = UserCaptchaRecord.query.filter_by(captcha_completed=True).count()
        active_captcha_sessions = CaptchaSession.query.filter_by(completed=False).filter(
            CaptchaSession.expires_at > datetime.utcnow()
        ).count()
        total_winner_selections = WinnerSelectionLog.query.count()
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_participants = Participant.query.filter(Participant.created_at > yesterday).count()
        recent_captcha_completions = UserCaptchaRecord.query.filter(
            UserCaptchaRecord.captcha_completed_at > yesterday
        ).count()
        
        stats = {
            'total_participants': total_participants,
            'total_users_with_captcha': total_users_with_captcha,
            'active_captcha_sessions': active_captcha_sessions,
            'total_winner_selections': total_winner_selections,
            'recent_activity': {
                'new_participants_24h': recent_participants,
                'captcha_completions_24h': recent_captcha_completions
            },
            'service': 'participant-service',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'service': 'participant-service'
        }), 500

