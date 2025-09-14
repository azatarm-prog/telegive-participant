from flask import request, jsonify, current_app
from functools import wraps
import os
import logging

logger = logging.getLogger(__name__)

def require_service_token(f):
    """
    Decorator to require service-to-service authentication token
    Used for endpoints that should only be called by other services
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get the expected service token
        expected_token = os.getenv('SERVICE_TO_SERVICE_SECRET')
        
        if not expected_token:
            logger.error("SERVICE_TO_SERVICE_SECRET not configured")
            return jsonify({
                'success': False,
                'error': 'Service authentication not configured',
                'error_code': 'AUTH_NOT_CONFIGURED'
            }), 500
        
        # Check for token in headers
        auth_header = request.headers.get('X-Service-Token')
        if not auth_header:
            logger.warning(f"Missing service token for {request.endpoint}")
            return jsonify({
                'success': False,
                'error': 'Service authentication required',
                'error_code': 'AUTH_REQUIRED'
            }), 401
        
        # Validate token
        if auth_header != expected_token:
            logger.warning(f"Invalid service token for {request.endpoint}")
            return jsonify({
                'success': False,
                'error': 'Invalid service token',
                'error_code': 'AUTH_INVALID'
            }), 401
        
        # Log successful authentication
        service_name = request.headers.get('X-Service-Name', 'unknown')
        logger.info(f"Authenticated service request from {service_name} to {request.endpoint}")
        
        return f(*args, **kwargs)
    
    return decorated_function

def log_request_info():
    """
    Log incoming request information for debugging
    """
    user_agent = request.headers.get('User-Agent', 'unknown')
    service_name = request.headers.get('X-Service-Name', 'unknown')
    service_token = request.headers.get('X-Service-Token', 'none')
    
    logger.info(f"Request: {request.method} {request.path} | "
                f"User-Agent: {user_agent} | "
                f"Service: {service_name} | "
                f"Token: {'present' if service_token else 'missing'}")

def is_bot_service_request():
    """
    Check if request is coming from Bot Service
    """
    user_agent = request.headers.get('User-Agent', '')
    service_name = request.headers.get('X-Service-Name', '')
    
    return ('TelegiveBotService' in user_agent or 
            'bot-service' in service_name.lower())

def validate_bot_service_request():
    """
    Validate that request is properly formatted from Bot Service
    Returns tuple (is_valid, error_response)
    """
    # Check User-Agent
    user_agent = request.headers.get('User-Agent', '')
    if 'TelegiveBotService' not in user_agent:
        return False, jsonify({
            'success': False,
            'error': 'Invalid User-Agent for Bot Service',
            'error_code': 'INVALID_USER_AGENT'
        })
    
    # Check Content-Type for POST/PUT requests
    if request.method in ['POST', 'PUT']:
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            return False, jsonify({
                'success': False,
                'error': 'Content-Type must be application/json',
                'error_code': 'INVALID_CONTENT_TYPE'
            })
    
    return True, None

