from flask import Blueprint, jsonify, request, current_app
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
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        
        # Check tables using current app context
        table_info = {}
        
        # Import models within app context
        from models import Participant, UserCaptchaRecord, CaptchaSession, WinnerSelectionLog
        
        tables = {
            'participants': Participant,
            'user_captcha_records': UserCaptchaRecord,
            'captcha_sessions': CaptchaSession,
            'winner_selection_log': WinnerSelectionLog
        }
        
        for table_name, model in tables.items():
            try:
                with current_app.app_context():
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
        from datetime import datetime, timedelta
        import requests
        from services import auth_service, channel_service, telegive_service
        
        # Import models within app context
        from models import Participant, UserCaptchaRecord, CaptchaSession, WinnerSelectionLog
        
        stats = {
            'service': 'participant-service',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'status': 'healthy'
        }
        
        # Database statistics
        try:
            with current_app.app_context():
                # Basic counts
                total_participants = Participant.query.count()
                
                # Try to get other counts, but don't fail if models aren't registered
                try:
                    total_users_with_captcha = UserCaptchaRecord.query.filter_by(captcha_completed=True).count()
                except:
                    total_users_with_captcha = 0
                
                try:
                    active_captcha_sessions = CaptchaSession.query.filter_by(completed=False).filter(
                        CaptchaSession.expires_at > datetime.utcnow()
                    ).count()
                except:
                    active_captcha_sessions = 0
                
                try:
                    total_winner_selections = WinnerSelectionLog.query.count()
                except:
                    total_winner_selections = 0
                
                # Recent activity (last 24 hours)
                yesterday = datetime.utcnow() - timedelta(days=1)
                try:
                    recent_participants = Participant.query.filter(Participant.created_at > yesterday).count()
                except:
                    recent_participants = 0
                
                try:
                    recent_captcha_completions = UserCaptchaRecord.query.filter(
                        UserCaptchaRecord.captcha_completed_at > yesterday
                    ).count()
                except:
                    recent_captcha_completions = 0
                
                stats['database'] = {
                    'status': 'connected',
                    'tables': {
                        'participants': {
                            'exists': True,
                            'record_count': total_participants
                        },
                        'user_captcha_records': {
                            'exists': True,
                            'record_count': total_users_with_captcha
                        },
                        'captcha_sessions': {
                            'exists': True,
                            'record_count': active_captcha_sessions
                        },
                        'winner_selection_log': {
                            'exists': True,
                            'record_count': total_winner_selections
                        }
                    },
                    'recent_activity': {
                        'new_participants_24h': recent_participants,
                        'captcha_completions_24h': recent_captcha_completions
                    }
                }
                
        except Exception as e:
            stats['database'] = {
                'status': f'error: {str(e)}',
                'tables': {}
            }
            stats['status'] = 'degraded'
        
        # External services check
        external_services = {
            'auth_service': auth_service.base_url,
            'channel_service': channel_service.base_url,
            'telegive_service': telegive_service.base_url
        }
        
        stats['external_services'] = {}
        
        for service_name, service_url in external_services.items():
            try:
                response = requests.get(f'{service_url}/health', timeout=5)
                stats['external_services'][service_name] = {
                    'url': service_url,
                    'status_code': response.status_code,
                    'accessible': response.status_code == 200,
                    'response_time': response.elapsed.total_seconds()
                }
            except Exception as e:
                stats['external_services'][service_name] = {
                    'url': service_url,
                    'accessible': False,
                    'error': str(e)
                }
        
        # System checks
        stats['system_checks'] = {}
        
        try:
            from utils.captcha_generator import captcha_generator
            question, answer = captcha_generator.generate_question()
            if question and isinstance(answer, int):
                stats['system_checks']['captcha_generator'] = 'operational'
            else:
                stats['system_checks']['captcha_generator'] = 'error'
                stats['status'] = 'degraded'
        except Exception as e:
            stats['system_checks']['captcha_generator'] = f'error: {str(e)}'
            stats['status'] = 'degraded'
        
        try:
            from utils.winner_selection import select_winners_cryptographic
            test_participants = [1, 2, 3, 4, 5]
            winners = select_winners_cryptographic(test_participants, 2)
            if len(winners) == 2:
                stats['system_checks']['winner_selection'] = 'operational'
            else:
                stats['system_checks']['winner_selection'] = 'error'
                stats['status'] = 'degraded'
        except Exception as e:
            stats['system_checks']['winner_selection'] = f'error: {str(e)}'
            stats['status'] = 'degraded'
        
        try:
            from utils.validation import input_validator
            test_data = {'giveaway_id': 123, 'user_id': 456789012, 'username': 'testuser'}
            result = input_validator.validate_participation_request(test_data)
            if result['valid']:
                stats['system_checks']['input_validation'] = 'operational'
            else:
                stats['system_checks']['input_validation'] = 'error'
                stats['status'] = 'degraded'
        except Exception as e:
            stats['system_checks']['input_validation'] = f'error: {str(e)}'
            stats['status'] = 'degraded'
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'service': 'participant-service'
        }), 500

