from flask import Blueprint, jsonify
from models import db
import requests
import logging
from services import auth_service, channel_service, telegive_service

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check"""
    try:
        health_status = {
            'service': 'participant-service',
            'status': 'healthy',
            'version': '1.0.0',
            'database': 'unknown',
            'external_services': {
                'auth_service': 'unknown',
                'channel_service': 'unknown',
                'telegive_service': 'unknown'
            },
            'captcha_system': 'operational',
            'winner_selection': 'operational'
        }
        
        # Test database connection
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            database_status = "connected"
        except Exception as e:
            database_status = f"error: {str(e)}"
            health_status['status'] = 'unhealthy'
        
        health_status['database'] = database_status
        
        # Check external services
        external_services = {
            'auth_service': auth_service.base_url,
            'channel_service': channel_service.base_url,
            'telegive_service': telegive_service.base_url
        }
        
        for service_name, service_url in external_services.items():
            try:
                response = requests.get(f'{service_url}/health', timeout=5)
                if response.status_code == 200:
                    health_status['external_services'][service_name] = 'accessible'
                else:
                    health_status['external_services'][service_name] = f'error: HTTP {response.status_code}'
            except Exception as e:
                health_status['external_services'][service_name] = f'error: {str(e)}'
        
        # Test captcha system
        try:
            from utils.captcha_generator import captcha_generator
            question, answer = captcha_generator.generate_question()
            if not question or not isinstance(answer, int):
                health_status['captcha_system'] = 'error'
                health_status['status'] = 'unhealthy'
        except Exception as e:
            health_status['captcha_system'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Test winner selection
        try:
            from utils.winner_selection import select_winners_cryptographic
            test_participants = [1, 2, 3, 4, 5]
            winners = select_winners_cryptographic(test_participants, 2)
            if len(winners) != 2:
                health_status['winner_selection'] = 'error'
                health_status['status'] = 'unhealthy'
        except Exception as e:
            health_status['winner_selection'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Determine overall status
        if health_status['database'].startswith('error'):
            health_status['status'] = 'unhealthy'
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'service': 'participant-service',
            'status': 'unhealthy',
            'version': '1.0.0',
            'error': f'Health check failed: {str(e)}'
        }), 503

@health_bp.route('/health/detailed', methods=['GET'])
def detailed_health_check():
    """Detailed health check with more information"""
    try:
        health_info = {
            'service': 'participant-service',
            'status': 'healthy',
            'version': '1.0.0',
            'timestamp': None,
            'database': {
                'status': 'unknown',
                'tables': {}
            },
            'external_services': {},
            'system_checks': {
                'captcha_generator': 'unknown',
                'winner_selection': 'unknown',
                'input_validation': 'unknown'
            }
        }
        
        from datetime import datetime
        health_info['timestamp'] = datetime.utcnow().isoformat()
        
        # Database checks
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            health_info['database']['status'] = 'connected'
            
            # Check tables
            from models import Participant, UserCaptchaRecord, CaptchaSession, WinnerSelectionLog
            tables = {
                'participants': Participant,
                'user_captcha_records': UserCaptchaRecord,
                'captcha_sessions': CaptchaSession,
                'winner_selection_log': WinnerSelectionLog
            }
            
            for table_name, model in tables.items():
                try:
                    count = model.query.count()
                    health_info['database']['tables'][table_name] = {
                        'exists': True,
                        'record_count': count
                    }
                except Exception as e:
                    health_info['database']['tables'][table_name] = {
                        'exists': False,
                        'error': str(e)
                    }
                    
        except Exception as e:
            health_info['database']['status'] = f'error: {str(e)}'
            health_info['status'] = 'unhealthy'
        
        # External service checks
        external_services = {
            'auth_service': auth_service.base_url,
            'channel_service': channel_service.base_url,
            'telegive_service': telegive_service.base_url
        }
        
        for service_name, service_url in external_services.items():
            try:
                response = requests.get(f'{service_url}/health', timeout=5)
                health_info['external_services'][service_name] = {
                    'url': service_url,
                    'status_code': response.status_code,
                    'accessible': response.status_code == 200,
                    'response_time': response.elapsed.total_seconds()
                }
            except Exception as e:
                health_info['external_services'][service_name] = {
                    'url': service_url,
                    'accessible': False,
                    'error': str(e)
                }
        
        # System component checks
        try:
            from utils.captcha_generator import captcha_generator
            question, answer = captcha_generator.generate_question()
            if question and isinstance(answer, int):
                health_info['system_checks']['captcha_generator'] = 'operational'
            else:
                health_info['system_checks']['captcha_generator'] = 'error'
                health_info['status'] = 'unhealthy'
        except Exception as e:
            health_info['system_checks']['captcha_generator'] = f'error: {str(e)}'
            health_info['status'] = 'unhealthy'
        
        try:
            from utils.winner_selection import select_winners_cryptographic
            test_participants = [1, 2, 3, 4, 5]
            winners = select_winners_cryptographic(test_participants, 2)
            if len(winners) == 2:
                health_info['system_checks']['winner_selection'] = 'operational'
            else:
                health_info['system_checks']['winner_selection'] = 'error'
                health_info['status'] = 'unhealthy'
        except Exception as e:
            health_info['system_checks']['winner_selection'] = f'error: {str(e)}'
            health_info['status'] = 'unhealthy'
        
        try:
            from utils.validation import input_validator
            test_data = {'giveaway_id': 123, 'user_id': 456789012, 'username': 'testuser'}
            result = input_validator.validate_participation_request(test_data)
            if result['valid']:
                health_info['system_checks']['input_validation'] = 'operational'
            else:
                health_info['system_checks']['input_validation'] = 'error'
                health_info['status'] = 'unhealthy'
        except Exception as e:
            health_info['system_checks']['input_validation'] = f'error: {str(e)}'
            health_info['status'] = 'unhealthy'
        
        status_code = 200 if health_info['status'] == 'healthy' else 503
        return jsonify(health_info), status_code
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return jsonify({
            'service': 'participant-service',
            'status': 'unhealthy',
            'version': '1.0.0',
            'error': f'Detailed health check failed: {str(e)}'
        }), 503

@health_bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """Readiness check for Kubernetes/deployment"""
    try:
        # Check database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        
        # Check if tables exist
        from models import Participant
        Participant.query.limit(1).all()
        
        return jsonify({
            'status': 'ready',
            'service': 'participant-service',
            'database': 'connected',
            'tables': 'initialized'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'service': 'participant-service',
            'error': str(e),
            'database': 'disconnected'
        }), 503

@health_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """Liveness check for Kubernetes/deployment"""
    return jsonify({
        'status': 'alive',
        'service': 'participant-service'
    }), 200

