from flask import Blueprint, jsonify
from models import db
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)

@health_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """Ultra-fast liveness check - no external calls"""
    return jsonify({
        'status': 'alive',
        'service': 'participant-service'
    }), 200

@health_bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """Fast readiness check - only essential database test"""
    try:
        # Quick database ping only
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        
        return jsonify({
            'status': 'ready',
            'service': 'participant-service',
            'database': 'connected'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'service': 'participant-service',
            'error': str(e),
            'database': 'disconnected'
        }), 503

@health_bp.route('/health', methods=['GET'])
def health_check_fast():
    """Fast health check - minimal external calls"""
    try:
        health_status = {
            'service': 'participant-service',
            'status': 'healthy',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Quick database test only
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            health_status['database'] = 'connected'
        except Exception as e:
            health_status['database'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Quick system checks (no external calls)
        try:
            from utils.captcha_generator import captcha_generator
            question, answer = captcha_generator.generate_question()
            if question and isinstance(answer, int):
                health_status['captcha_system'] = 'operational'
            else:
                health_status['captcha_system'] = 'error'
                health_status['status'] = 'unhealthy'
        except Exception as e:
            health_status['captcha_system'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        try:
            from utils.winner_selection import select_winners_cryptographic
            test_participants = [1, 2, 3, 4, 5]
            winners = select_winners_cryptographic(test_participants, 2)
            if len(winners) == 2:
                health_status['winner_selection'] = 'operational'
            else:
                health_status['winner_selection'] = 'error'
                health_status['status'] = 'unhealthy'
        except Exception as e:
            health_status['winner_selection'] = f'error: {str(e)}'
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
    """Detailed health check with external services - USE SPARINGLY"""
    try:
        import requests
        from services import auth_service, channel_service, telegive_service
        
        health_info = {
            'service': 'participant-service',
            'status': 'healthy',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'database': {
                'status': 'unknown'
            },
            'external_services': {},
            'system_checks': {
                'captcha_generator': 'unknown',
                'winner_selection': 'unknown',
                'input_validation': 'unknown'
            }
        }
        
        # Database checks
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            health_info['database']['status'] = 'connected'
        except Exception as e:
            health_info['database']['status'] = f'error: {str(e)}'
            health_info['status'] = 'unhealthy'
        
        # External service checks with reduced timeout
        external_services = {
            'auth_service': auth_service.base_url,
            'channel_service': channel_service.base_url,
            'telegive_service': telegive_service.base_url
        }
        
        for service_name, service_url in external_services.items():
            try:
                # Reduced timeout from 5s to 2s
                response = requests.get(f'{service_url}/health', timeout=2)
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

