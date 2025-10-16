# FlaskProject/app.py - Main Application File

import logging
import os
from datetime import timedelta

from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

# Import configuration
from config import get_config
# Import extensions
from extensions import db, migrate, socketio
# Import blueprints
from views.api_routes import api_bp
from views.host_routes import host_bp
from views.player_routes import player_bp

# Import SocketIO event handlers (initialize handlers)
import socketio_events

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def create_app(config_name=None):
    """Create and configure a Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # Setup CORS
    cors_origins = config.CORS_ORIGINS
    if cors_origins == '*':
        CORS(app, origins="*")
    else:
        CORS(app, origins=cors_origins.split(',') if cors_origins else ["http://localhost:5000"])
    
    # Setup rate limiting
    if config.RATELIMIT_ENABLED:
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[config.RATELIMIT_DEFAULT],
            storage_uri=config.RATELIMIT_STORAGE_URL
        )
        limiter.init_app(app)
    
    # Setup security headers
    if not app.debug:
        Talisman(app, 
                force_https=False,  # Set to True in production with HTTPS
                strict_transport_security=False  # Enable with HTTPS
        )
    
    # Register blueprints
    app.register_blueprint(player_bp)
    app.register_blueprint(host_bp)
    app.register_blueprint(api_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Configure session
    app.permanent_session_lifetime = timedelta(seconds=config.PERMANENT_SESSION_LIFETIME)
    
    return app

def create_socketio_app(app):
    """Create SocketIO application."""
    return socketio

def display_startup_info(config, network_manager=None):
    """Display network information and startup details."""
    from utils.network import get_network_info, get_network_urls
    import platform
    
    print("\n" + "="*60)
    print("🧠 QUIZ APP - NETWORK READY (Dynamic IP Enabled)")
    print("="*60)
    
    # Network information - use dynamic manager if available
    if network_manager and config.DYNAMIC_IP_ENABLED:
        network_info = network_manager.get_network_info()
        local_ip = network_manager.get_current_ip()
    else:
        network_info = get_network_info(prefer_method=getattr(config, 'DYNAMIC_IP_PREFERRED_METHOD', 'auto'))
        local_ip = network_info.get('local_ip')
    
    if network_info.get('status') == 'success' and local_ip:
        print(f"🌐 Network Configuration:")
        print(f"   • Local IP: {local_ip}")
        if 'method' in network_info:
            print(f"   • Detection method: {network_info['method']}")
        print(f"   • Hostname: {platform.node()}")
        print(f"   • Platform: {platform.system()}")
        print(f"   • Binding to: {config.FLASK_HOST}:{config.FLASK_PORT}")
        
        # Dynamic IP info
        if config.DYNAMIC_IP_ENABLED:
            print(f"   • Dynamic IP monitoring: Enabled (check every {config.DYNAMIC_IP_CHECK_INTERVAL}s)")
            print(f"   • IP change notifications: {'Enabled' if config.DYNAMIC_IP_NOTIFY_CLIENTS else 'Disabled'}")
        else:
            print(f"   • Dynamic IP monitoring: Disabled")
        
        # URLs for different purposes
        if network_manager:
            urls = network_manager.get_network_urls(port=config.FLASK_PORT)
        else:
            urls = get_network_urls(host=local_ip, port=config.FLASK_PORT)
            
        print(f"\n👥 For classmates/other devices:")
        print(f"   • Main page: {urls['local_url']}")
        print(f"   • Join game: {urls['join_url']}")
        print(f"   • Host dashboard: {urls['host_url']}")
        print(f"   • Statistics: {urls['stats_url']}")
        
        print(f"\n📱 Tips:")
        print(f"   • All devices must be on the same network")
        print(f"   • QR codes available in host dashboard")
        print(f"   • Firewall may need to allow port {config.FLASK_PORT}")
        if config.DYNAMIC_IP_ENABLED:
            print(f"   • App will automatically adjust if IP changes")
    else:
        print(f"⚠️  Network detection failed, using localhost only")
        print(f"   • Local access: http://127.0.0.1:{config.FLASK_PORT}")
        if 'error' in network_info:
            print(f"   • Error: {network_info['error']}")
    
    print(f"\n🔒 Security: Minimal (development mode)")
    print(f"🌐 CORS: Allowing all origins for easy access")
    print("="*60 + "\n")


if __name__ == '__main__':
    app = create_app()
    config = get_config()
    
    # Initialize dynamic IP monitoring if enabled
    network_manager = None
    if config.DYNAMIC_IP_ENABLED:
        from services.network_monitor import network_manager as nm
        network_manager = nm
        network_manager.init_app(app)
        
        # Configure monitoring settings from config
        network_manager.monitor.check_interval = config.DYNAMIC_IP_CHECK_INTERVAL
        
        # Start monitoring
        print("🔍 Initializing dynamic IP monitoring...")
        initial_check = network_manager.start_monitoring()
        
        if initial_check.get('new_ip'):
            print(f"✅ Dynamic IP detected: {initial_check['new_ip']}")
        else:
            print(f"⚠️ Dynamic IP detection had issues, falling back to static detection")
    
    # Display startup information
    display_startup_info(config, network_manager)
    
    # Setup graceful shutdown for network monitoring
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print("\n🚫 Shutting down...")
        if network_manager:
            print("🗜️ Stopping network monitoring...")
            network_manager.stop_monitoring()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run development server
    try:
        if config.SSL_ENABLED and os.path.exists(config.SSL_CERT_PATH) and os.path.exists(config.SSL_KEY_PATH):
            context = (config.SSL_CERT_PATH, config.SSL_KEY_PATH)
            print("🔒 Starting with SSL/HTTPS...")
            socketio.run(app, 
                        host=config.FLASK_HOST, 
                        port=config.FLASK_PORT, 
                        debug=config.FLASK_DEBUG,
                        ssl_context=context)
        else:
            print("🚀 Starting HTTP server...")
            socketio.run(app, 
                        host=config.FLASK_HOST, 
                        port=config.FLASK_PORT, 
                        debug=config.FLASK_DEBUG)
    except KeyboardInterrupt:
        print("\n🚫 Server interrupted by user")
    finally:
        if network_manager:
            print("🗜️ Cleaning up network monitoring...")
            network_manager.stop_monitoring()
