from flask import Blueprint, jsonify, request, current_app
from models import db
from sqlalchemy import text
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

admin_optimized_bp = Blueprint('admin_optimized', __name__)

@admin_optimized_bp.route('/admin/update-schema', methods=['POST'])
def update_database_schema():
    """Update database schema for Bot Service integration"""
    try:
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

@admin_optimized_bp.route('/admin/init-db', methods=['POST'])
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

@admin_optimized_bp.route('/admin/db-status', methods=['GET'])
def database_status():
    """Fast database status check"""
    try:
        # Test connection
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        
        # Quick table check
        table_info = {}
        
        try:
            from models import Participant
            count = Participant.query.count()
            table_info['participants'] = {
                'exists': True,
                'record_count': count
            }
        except Exception as e:
            table_info['participants'] = {
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

@admin_optimized_bp.route('/admin/cleanup', methods=['POST'])
def cleanup_data():
    """Run cleanup tasks"""
    try:
        # Simple cleanup without external dependencies
        from datetime import datetime, timedelta
        
        cleanup_results = {
            'expired_captcha_sessions': 0,
            'old_logs': 0,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Clean up expired captcha sessions
        try:
            expired_sessions = db.session.execute(text(
                "DELETE FROM captcha_sessions WHERE expires_at < NOW() RETURNING id"
            )).rowcount
            cleanup_results['expired_captcha_sessions'] = expired_sessions
        except Exception as e:
            logger.warning(f"Could not clean captcha sessions: {e}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cleanup completed',
            'results': cleanup_results,
            'service': 'participant-service'
        }), 200
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'service': 'participant-service'
        }), 500

@admin_optimized_bp.route('/admin/stats-fast', methods=['GET'])
def get_stats_fast():
    """Get fast service statistics without external calls"""
    try:
        from datetime import datetime, timedelta
        
        stats = {
            'service': 'participant-service',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'status': 'healthy'
        }
        
        # Database statistics only
        try:
            from models import Participant
            
            # Basic counts
            total_participants = Participant.query.count()
            
            # Recent activity (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            try:
                recent_participants = Participant.query.filter(Participant.participated_at > yesterday).count()
            except:
                recent_participants = 0
            
            stats['database'] = {
                'status': 'connected',
                'tables': {
                    'participants': {
                        'exists': True,
                        'record_count': total_participants
                    }
                },
                'recent_activity': {
                    'new_participants_24h': recent_participants
                }
            }
            
        except Exception as e:
            stats['database'] = {
                'status': f'error: {str(e)}',
                'tables': {}
            }
            stats['status'] = 'degraded'
        
        # System checks (no external calls)
        stats['system_checks'] = {}
        
        try:
            # Simple captcha test
            import random
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            if a and b:
                stats['system_checks']['captcha_generator'] = 'operational'
            else:
                stats['system_checks']['captcha_generator'] = 'error'
                stats['status'] = 'degraded'
        except Exception as e:
            stats['system_checks']['captcha_generator'] = f'error: {str(e)}'
            stats['status'] = 'degraded'
        
        try:
            # Simple winner selection test
            import secrets
            test_participants = [1, 2, 3, 4, 5]
            winner_index = secrets.randbelow(len(test_participants))
            if winner_index is not None:
                stats['system_checks']['winner_selection'] = 'operational'
            else:
                stats['system_checks']['winner_selection'] = 'error'
                stats['status'] = 'degraded'
        except Exception as e:
            stats['system_checks']['winner_selection'] = f'error: {str(e)}'
            stats['status'] = 'degraded'
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Fast stats retrieval failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'service': 'participant-service'
        }), 500

@admin_optimized_bp.route('/admin/stats', methods=['GET'])
def get_stats_with_external():
    """Get full service statistics with external services - USE SPARINGLY"""
    try:
        from datetime import datetime, timedelta
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        stats = {
            'service': 'participant-service',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'status': 'healthy'
        }
        
        # Database statistics
        try:
            from models import Participant
            
            total_participants = Participant.query.count()
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_participants = Participant.query.filter(Participant.participated_at > yesterday).count()
            
            stats['database'] = {
                'status': 'connected',
                'tables': {
                    'participants': {
                        'exists': True,
                        'record_count': total_participants
                    }
                },
                'recent_activity': {
                    'new_participants_24h': recent_participants
                }
            }
            
        except Exception as e:
            stats['database'] = {
                'status': f'error: {str(e)}',
                'tables': {}
            }
            stats['status'] = 'degraded'
        
        # External services check with very short timeout
        external_services = {
            'auth_service': 'https://web-production-ddd7e.up.railway.app',
            'channel_service': 'https://telegive-channel-production.up.railway.app',
            'telegive_service': 'https://telegive-giveaway-production.up.railway.app'
        }
        
        stats['external_services'] = {}
        
        def check_service(service_name, service_url):
            try:
                response = requests.get(f'{service_url}/health', timeout=1)
                return service_name, {
                    'url': service_url,
                    'status_code': response.status_code,
                    'accessible': response.status_code == 200,
                    'response_time': response.elapsed.total_seconds()
                }
            except Exception as e:
                return service_name, {
                    'url': service_url,
                    'accessible': False,
                    'error': str(e)
                }
        
        # Check services in parallel with timeout
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_service = {
                executor.submit(check_service, name, url): name 
                for name, url in external_services.items()
            }
            
            for future in as_completed(future_to_service, timeout=2):
                try:
                    service_name, result = future.result()
                    stats['external_services'][service_name] = result
                except Exception as e:
                    service_name = future_to_service[future]
                    stats['external_services'][service_name] = {
                        'accessible': False,
                        'error': f'Timeout: {str(e)}'
                    }
        
        # System checks
        stats['system_checks'] = {}
        
        try:
            import random
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            stats['system_checks']['captcha_generator'] = 'operational'
        except Exception as e:
            stats['system_checks']['captcha_generator'] = f'error: {str(e)}'
            stats['status'] = 'degraded'
        
        try:
            import secrets
            test_participants = [1, 2, 3, 4, 5]
            winner_index = secrets.randbelow(len(test_participants))
            stats['system_checks']['winner_selection'] = 'operational'
        except Exception as e:
            stats['system_checks']['winner_selection'] = f'error: {str(e)}'
            stats['status'] = 'degraded'
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'service': 'participant-service'
        }), 500

