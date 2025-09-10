import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Database settings
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/telegive_participant')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
    
    # Service configuration
    SERVICE_NAME = os.getenv('SERVICE_NAME', 'participant-service')
    SERVICE_PORT = int(os.getenv('SERVICE_PORT', 8004))
    
    # Other services URLs
    TELEGIVE_AUTH_URL = os.getenv('TELEGIVE_AUTH_URL', 'https://telegive-auth.railway.app')
    TELEGIVE_CHANNEL_URL = os.getenv('TELEGIVE_CHANNEL_URL', 'https://telegive-channel.railway.app')
    TELEGIVE_GIVEAWAY_URL = os.getenv('TELEGIVE_GIVEAWAY_URL', 'https://telegive-service.railway.app')
    
    # External APIs
    TELEGRAM_API_BASE = os.getenv('TELEGRAM_API_BASE', 'https://api.telegram.org')
    
    # Captcha configuration
    CAPTCHA_TIMEOUT_MINUTES = int(os.getenv('CAPTCHA_TIMEOUT_MINUTES', 10))
    CAPTCHA_MAX_ATTEMPTS = int(os.getenv('CAPTCHA_MAX_ATTEMPTS', 3))
    CAPTCHA_MIN_NUMBER = int(os.getenv('CAPTCHA_MIN_NUMBER', 1))
    CAPTCHA_MAX_NUMBER = int(os.getenv('CAPTCHA_MAX_NUMBER', 10))
    
    # Winner selection
    SELECTION_METHOD = os.getenv('SELECTION_METHOD', 'cryptographic_random')
    SELECTION_AUDIT_ENABLED = os.getenv('SELECTION_AUDIT_ENABLED', 'true').lower() == 'true'
    
    # Redis (optional, for caching)
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # CORS settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:')
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True
    }
    WTF_CSRF_ENABLED = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

