import os
import logging
from flask import Flask
from flask_cors import CORS
from config import config
from models import db
from routes import participants_bp, captcha_bp
from routes.health_optimized import health_optimized_bp
from routes.admin_optimized import admin_optimized_bp
from routes.participants_enhanced import participants_bp as participants_enhanced_bp
from routes.participants_bot_service import bot_service_bp
from routes.bot_service_final import bot_service_final_bp

def create_app(config_name=None):
    """Application factory pattern"""
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, app.config.get('LOG_LEVEL', 'INFO')),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize extensions
    db.init_app(app)
    
    # Setup CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', '*'))
    
    # Register blueprints
    app.register_blueprint(participants_bp)
    app.register_blueprint(participants_enhanced_bp)  # Enhanced Bot Service endpoints
    app.register_blueprint(bot_service_bp)  # Working Bot Service endpoints
    app.register_blueprint(bot_service_final_bp)  # Final working Bot Service endpoints (v2)
    app.register_blueprint(captcha_bp)
    app.register_blueprint(health_optimized_bp)  # Optimized health endpoints
    app.register_blueprint(admin_optimized_bp)  # Optimized admin endpoints
    
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database tables created successfully")
        except Exception as e:
            app.logger.error(f"Error creating database tables: {e}")
    
    # Add error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {
            'success': False,
            'error': 'Endpoint not found',
            'error_code': 'NOT_FOUND'
        }, 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return {
            'success': False,
            'error': 'Method not allowed',
            'error_code': 'METHOD_NOT_ALLOWED'
        }, 405
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }, 500
    
    # Add root endpoint
    @app.route('/')
    def root():
        return {
            'service': 'telegive-participant',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'health': '/health',
                'participants': '/api/participants/*',
                'captcha': '/api/participants/validate-captcha'
            }
        }
    
    # Add service info endpoint
    @app.route('/info')
    def service_info():
        return {
            'service': app.config.get('SERVICE_NAME', 'participant-service'),
            'version': '1.0.0',
            'description': 'Participant Management Service for Telegive',
            'capabilities': [
                'User participation tracking',
                'Math captcha system',
                'Cryptographic winner selection',
                'Subscription verification',
                'Participation history'
            ],
            'database': 'PostgreSQL',
            'framework': 'Flask'
        }
    
    app.logger.info(f"Participant service started in {config_name} mode")
    
    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', app.config.get('SERVICE_PORT', 8004)))
    host = '0.0.0.0'  # Listen on all interfaces for deployment
    
    app.logger.info(f"Starting Participant Management Service on {host}:{port}")
    
    app.run(
        host=host,
        port=port,
        debug=app.config.get('DEBUG', False)
    )

