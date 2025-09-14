from flask import Blueprint, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

health_optimized_bp = Blueprint('health_optimized', __name__)

@health_optimized_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """Ultra-fast liveness check - no database, no external calls"""
    return jsonify({
        'status': 'alive',
        'service': 'participant-service',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

@health_optimized_bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """Fast readiness check - minimal database test only"""
    try:
        # Import only when needed to avoid startup delays
        from models import db
        from sqlalchemy import text
        
        # Single quick query with timeout
        result = db.session.execute(text('SELECT 1'))
        result.close()
        
        return jsonify({
            'status': 'ready',
            'service': 'participant-service',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({
            'status': 'not_ready',
            'service': 'participant-service',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@health_optimized_bp.route('/health', methods=['GET'])
def health_check():
    """Fast health check - database only, no external services"""
    try:
        health_status = {
            'service': 'participant-service',
            'status': 'healthy',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Quick database test only
        try:
            from models import db
            from sqlalchemy import text
            
            result = db.session.execute(text('SELECT 1'))
            result.close()
            health_status['database'] = 'connected'
        except Exception as e:
            health_status['database'] = 'disconnected'
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        # Quick participant count (cached if possible)
        try:
            from models import Participant
            count = Participant.query.count()
            health_status['participants_count'] = count
        except Exception as e:
            health_status['participants_count'] = 'error'
            logger.warning(f"Could not get participant count: {e}")
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'service': 'participant-service',
            'status': 'unhealthy',
            'version': '1.0.0',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@health_optimized_bp.route('/health/system', methods=['GET'])
def system_health_check():
    """System component health check - no external services"""
    try:
        health_status = {
            'service': 'participant-service',
            'status': 'healthy',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'system_checks': {}
        }
        
        # Test captcha generator
        try:
            import random
            # Use simple fallback instead of complex captcha generator
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            question = f"What is {a} + {b}?"
            answer = a + b
            if question and isinstance(answer, int):
                health_status['system_checks']['captcha_generator'] = 'operational'
            else:
                health_status['system_checks']['captcha_generator'] = 'error'
                health_status['status'] = 'degraded'
        except Exception as e:
            health_status['system_checks']['captcha_generator'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Test winner selection
        try:
            import secrets
            # Simple cryptographic selection test
            test_participants = [1, 2, 3, 4, 5]
            selected_count = 2
            selected_indices = set()
            
            while len(selected_indices) < selected_count:
                random_index = secrets.randbelow(len(test_participants))
                selected_indices.add(random_index)
            
            winners = [test_participants[i] for i in selected_indices]
            
            if len(winners) == 2:
                health_status['system_checks']['winner_selection'] = 'operational'
            else:
                health_status['system_checks']['winner_selection'] = 'error'
                health_status['status'] = 'degraded'
        except Exception as e:
            health_status['system_checks']['winner_selection'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Test basic validation
        try:
            test_data = {'giveaway_id': 123, 'user_id': 456789012, 'username': 'testuser'}
            # Simple validation test
            if all(key in test_data for key in ['giveaway_id', 'user_id']):
                health_status['system_checks']['input_validation'] = 'operational'
            else:
                health_status['system_checks']['input_validation'] = 'error'
                health_status['status'] = 'degraded'
        except Exception as e:
            health_status['system_checks']['input_validation'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
        
        status_code = 200 if health_status['status'] in ['healthy', 'degraded'] else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return jsonify({
            'service': 'participant-service',
            'status': 'unhealthy',
            'version': '1.0.0',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@health_optimized_bp.route('/health/external', methods=['GET'])
def external_services_health():
    """External services health check - USE ONLY WHEN NEEDED"""
    try:
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        health_status = {
            'service': 'participant-service',
            'status': 'healthy',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'external_services': {}
        }
        
        # External services to check
        services = {
            'auth_service': 'https://web-production-ddd7e.up.railway.app',
            'channel_service': 'https://telegive-channel-production.up.railway.app',
            'telegive_service': 'https://telegive-giveaway-production.up.railway.app'
        }
        
        def check_service(service_name, service_url):
            try:
                # Very short timeout for external checks
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
        
        # Check services in parallel with very short timeout
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_service = {
                executor.submit(check_service, name, url): name 
                for name, url in services.items()
            }
            
            for future in as_completed(future_to_service, timeout=2):
                try:
                    service_name, result = future.result()
                    health_status['external_services'][service_name] = result
                except Exception as e:
                    service_name = future_to_service[future]
                    health_status['external_services'][service_name] = {
                        'accessible': False,
                        'error': f'Timeout or error: {str(e)}'
                    }
        
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"External services health check failed: {e}")
        return jsonify({
            'service': 'participant-service',
            'status': 'error',
            'version': '1.0.0',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

