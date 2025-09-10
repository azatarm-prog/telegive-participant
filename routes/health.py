from flask import Blueprint, jsonify
import os
import requests
from models import db
from services.auth_service import auth_service
from services.channel_service import channel_service
from services.telegive_service import telegive_service

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        health_status = {
            'status': 'healthy',
            'service': 'participant-service',
            'version': '1.0.0',
            'database': 'disconnected',
            'external_services': {
                'auth_service': 'unknown',
                'channel_service': 'unknown',
                'telegive_service': 'unknown'
            },
            'captcha_system': 'operational',
            'winner_selection': 'operational'
        }
        
        # Check database connection
        try:
            db.session.execute('SELECT 1')
            health_status['database'] = 'connected'
        except Exception as e:
            health_status['database'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
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
            except requests.RequestException as e:
                health_status['external_services'][service_name] = f'error: {str(e)}'
        
        # Check captcha system
        try:
            from utils.captcha_generator import captcha_generator
            question, answer = captcha_generator.generate_question()
            if question and isinstance(answer, int):
                health_status['captcha_system'] = 'operational'
            else:
                health_status['captcha_system'] = 'error: invalid generation'
                health_status['status'] = 'degraded'
        except Exception as e:
            health_status['captcha_system'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Check winner selection
        try:
            from utils.winner_selection import winner_selector
            test_participants = [1, 2, 3, 4, 5]
            test_winners = winner_selector.select_winners_cryptographic(test_participants, 2)
            if len(test_winners) == 2 and all(w in test_participants for w in test_winners):
                health_status['winner_selection'] = 'operational'
            else:
                health_status['winner_selection'] = 'error: invalid selection'
                health_status['status'] = 'degraded'
        except Exception as e:
            health_status['winner_selection'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Determine overall status
        if health_status['database'] != 'connected':
            health_status['status'] = 'unhealthy'
        elif any('error:' in status for status in health_status['external_services'].values()):
            if health_status['status'] == 'healthy':
                health_status['status'] = 'degraded'
        
        # Return appropriate HTTP status code
        if health_status['status'] == 'healthy':
            return jsonify(health_status), 200
        elif health_status['status'] == 'degraded':
            return jsonify(health_status), 200  # Still operational but with issues
        else:
            return jsonify(health_status), 503  # Service unavailable
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'service': 'participant-service',
            'version': '1.0.0',
            'error': f'Health check failed: {str(e)}'
        }), 503

@health_bp.route('/health/detailed', methods=['GET'])
def detailed_health_check():
    """Detailed health check with more information"""
    try:
        from models import Participant, UserCaptchaRecord, CaptchaSession, WinnerSelectionLog
        
        detailed_status = {
            'status': 'healthy',
            'service': 'participant-service',
            'version': '1.0.0',
            'timestamp': None,
            'database': {
                'status': 'disconnected',
                'tables': {}
            },
            'statistics': {
                'total_participants': 0,
                'total_users_with_captcha': 0,
                'active_captcha_sessions': 0,
                'total_winner_selections': 0
            },
            'configuration': {
                'captcha_timeout_minutes': os.getenv('CAPTCHA_TIMEOUT_MINUTES', 10),
                'captcha_max_attempts': os.getenv('CAPTCHA_MAX_ATTEMPTS', 3),
                'selection_method': os.getenv('SELECTION_METHOD', 'cryptographic_random'),
                'audit_enabled': os.getenv('SELECTION_AUDIT_ENABLED', 'true')
            }
        }
        
        from datetime import datetime
        detailed_status['timestamp'] = datetime.utcnow().isoformat()
        
        # Check database and get statistics
        try:
            db.session.execute('SELECT 1')
            detailed_status['database']['status'] = 'connected'
            
            # Check each table
            tables = {
                'participants': Participant,
                'user_captcha_records': UserCaptchaRecord,
                'captcha_sessions': CaptchaSession,
                'winner_selection_log': WinnerSelectionLog
            }
            
            for table_name, model in tables.items():
                try:
                    count = model.query.count()
                    detailed_status['database']['tables'][table_name] = {
                        'status': 'accessible',
                        'record_count': count
                    }
                except Exception as e:
                    detailed_status['database']['tables'][table_name] = {
                        'status': f'error: {str(e)}',
                        'record_count': 0
                    }
                    detailed_status['status'] = 'degraded'
            
            # Get statistics
            detailed_status['statistics']['total_participants'] = Participant.query.count()
            detailed_status['statistics']['total_users_with_captcha'] = UserCaptchaRecord.query.filter_by(captcha_completed=True).count()
            detailed_status['statistics']['active_captcha_sessions'] = CaptchaSession.query.filter_by(completed=False).filter(
                CaptchaSession.expires_at > datetime.utcnow()
            ).count()
            detailed_status['statistics']['total_winner_selections'] = WinnerSelectionLog.query.count()
            
        except Exception as e:
            detailed_status['database']['status'] = f'error: {str(e)}'
            detailed_status['status'] = 'unhealthy'
        
        # Return appropriate HTTP status code
        if detailed_status['status'] == 'healthy':
            return jsonify(detailed_status), 200
        elif detailed_status['status'] == 'degraded':
            return jsonify(detailed_status), 200
        else:
            return jsonify(detailed_status), 503
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'service': 'participant-service',
            'version': '1.0.0',
            'error': f'Detailed health check failed: {str(e)}'
        }), 503

@health_bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """Readiness check for Kubernetes/deployment"""
    try:
        # Check if service is ready to accept requests
        db.session.execute('SELECT 1')
        
        return jsonify({
            'status': 'ready',
            'service': 'participant-service'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'service': 'participant-service',
            'error': str(e)
        }), 503

@health_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """Liveness check for Kubernetes/deployment"""
    try:
        # Basic liveness check - service is running
        return jsonify({
            'status': 'alive',
            'service': 'participant-service'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'dead',
            'service': 'participant-service',
            'error': str(e)
        }), 503

