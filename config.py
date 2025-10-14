# FlaskProject/config.py - Configuration Management

import os
import secrets
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

def load_env_file():
    """Load environment variables from .env file if it exists."""
    env_file = BASE_DIR / '.env'
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value

# Load .env file if it exists
load_env_file()

class Config:
    """Base configuration class."""
    
    # Core Flask settings
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32)
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or secrets.token_hex(32)
    
    # Database
    if os.environ.get('DATABASE_URL'):
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    else:
        # Default to SQLite in instance directory
        db_path = BASE_DIR / 'instance' / 'quiz_app.db'
        db_path.parent.mkdir(exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security settings
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Strict')
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('PERMANENT_SESSION_LIFETIME', 3600))
    
    # Rate limiting
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'True').lower() == 'true'
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per hour')
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    
    # CORS - Allow all origins for easy device access (minimal security)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    
    # File upload limits
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16777216))  # 16MB
    MAX_FORM_MEMORY_SIZE = int(os.environ.get('MAX_FORM_MEMORY_SIZE', 2097152))  # 2MB
    
    # Application limits
    MAX_PLAYERS_PER_GAME = int(os.environ.get('MAX_PLAYERS_PER_GAME', 50))
    MAX_QUESTIONS_PER_QUIZ = int(os.environ.get('MAX_QUESTIONS_PER_QUIZ', 100))
    PIN_EXPIRY_MINUTES = int(os.environ.get('PIN_EXPIRY_MINUTES', 60))
    
    # Server settings - Default to network accessible
    FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')  # Allow external connections
    FLASK_PORT = int(os.environ.get('FLASK_PORT', 5000))
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # SSL settings
    SSL_ENABLED = os.environ.get('SSL_ENABLED', 'False').lower() == 'true'
    SSL_CERT_PATH = os.environ.get('SSL_CERT_PATH', 'certs/cert.pem')
    SSL_KEY_PATH = os.environ.get('SSL_KEY_PATH', 'certs/key.pem')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/quiz_app.log')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_DEBUG = True
    
class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    # Enhanced security for production
    RATELIMIT_DEFAULT = '50 per hour'
    
    # Use Redis for rate limiting in production if available
    if os.environ.get('REDIS_URL'):
        RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL')

# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration based on environment or provided name."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config_map.get(config_name, DevelopmentConfig)