from flask import Blueprint, jsonify, request, current_app
from models import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/update-schema', methods=['POST'])
def update_database_schema():
    """Update database schema for Bot Service integration"""
    try:
        from datetime import datetime
        
        # Schema updates for Bot Service integration
        schema_updates = [
            # Create user_captcha_records table
            """CREATE TABLE IF NOT EXISTS user_captcha_records (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE,
                captcha_completed BOOLEAN DEFAULT FALSE,
                captcha_completed_at TIMESTAMP,
                first_participation_at TIMESTAMP,
                total_participations INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Create captcha_sessions table
            """CREATE TABLE IF NOT EXISTS captcha_sessions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                giveaway_id INTEGER NOT NULL,
                session_id VARCHAR(32) NOT NULL UNIQUE,
                question TEXT NOT NULL,
                correct_answer INTEGER NOT NULL,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Create winner_selection_logs table
            """CREATE TABLE IF NOT EXISTS winner_selection_logs (
                id SERIAL PRIMARY KEY,
                giveaway_id INTEGER NOT NULL,
                total_participants INTEGER NOT NULL,
                winner_count_requested INTEGER NOT NULL,
                winner_count_selected INTEGER NOT NULL,
                selection_method VARCHAR(50) NOT NULL,
                winner_user_ids BIGINT[] NOT NULL,
                selection_timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            
            # Add indexes for performance
            """CREATE INDEX IF NOT EXISTS idx_user_captcha_records_user_id ON user_captcha_records(user_id)""",
            """CREATE INDEX IF NOT EXISTS idx_captcha_sessions_user_id ON captcha_sessions(user_id)""",
            """CREATE INDEX IF NOT EXISTS idx_captcha_sessions_session_id ON captcha_sessions(session_id)""",
            """CREATE INDEX IF NOT EXISTS idx_captcha_sessions_expires_at ON captcha_sessions(expires_at)""",
            """CREATE INDEX IF NOT EXISTS idx_winner_selection_logs_giveaway_id ON winner_selection_logs(giveaway_id)"""
        ]
        
        for update in schema_updates:
            db.session.execute(text(update))
        
        db.session.commit()
        
        logger.info("Database schema updated successfully for Bot Service integration")
        
        return jsonify({
            'success': True,
            'message': 'Database schema updated successfully for Bot Service integration',
            'tables_created': ['user_captcha_records', 'captcha_sessions', 'winner_selection_logs'],
            'indexes_created': ['user_id', 'session_id', 'expires_at', 'giveaway_id'],
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Schema update failed: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Schema update failed: {str(e)}',
            'error_code': 'SCHEMA_UPDATE_FAILED'
        }), 500

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

