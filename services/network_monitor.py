# FlaskProject/services/network_monitor.py - Dynamic IP Monitoring Service

import threading
import time
import logging
from typing import Dict, Optional, Callable
from utils.network import get_network_info

logger = logging.getLogger(__name__)

class NetworkMonitor:
    """Monitor network changes and detect IP address changes."""
    
    def __init__(self, check_interval: int = 30, callback: Optional[Callable] = None):
        """Initialize network monitor.
        
        Args:
            check_interval: Seconds between network checks
            callback: Function to call when IP changes (receives old_ip, new_ip)
        """
        self.check_interval = check_interval
        self.callback = callback
        self.current_ip = None
        self.network_info = {}
        self.monitoring = False
        self.monitor_thread = None
        self._lock = threading.Lock()
        
    def start_monitoring(self):
        """Start monitoring network changes in background thread."""
        if self.monitoring:
            logger.warning("Network monitoring already started")
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"Network monitoring started (check interval: {self.check_interval}s)")
        
    def stop_monitoring(self):
        """Stop network monitoring."""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        logger.info("Network monitoring stopped")
        
    def get_current_network_info(self) -> Dict:
        """Get current network information thread-safely."""
        with self._lock:
            return self.network_info.copy()
            
    def get_current_ip(self) -> Optional[str]:
        """Get current IP address thread-safely."""
        with self._lock:
            return self.current_ip
            
    def force_check(self) -> Dict:
        """Force an immediate network check and return results."""
        return self._check_network_change()
        
    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)."""
        # Initial check
        self._check_network_change()
        
        while self.monitoring:
            try:
                time.sleep(self.check_interval)
                if self.monitoring:  # Check again in case stop was called during sleep
                    self._check_network_change()
            except Exception as e:
                logger.error(f"Error in network monitoring loop: {e}")
                
    def _check_network_change(self) -> Dict:
        """Check for network changes and update state."""
        try:
            new_network_info = get_network_info()
            new_ip = new_network_info.get('local_ip')
            
            with self._lock:
                old_ip = self.current_ip
                
                # Update stored information
                self.network_info = new_network_info
                self.current_ip = new_ip
                
                # Check if IP changed
                if old_ip != new_ip:
                    logger.info(f"IP address changed: {old_ip} -> {new_ip}")
                    
                    # Call callback if provided
                    if self.callback:
                        try:
                            self.callback(old_ip, new_ip, new_network_info)
                        except Exception as e:
                            logger.error(f"Error in network change callback: {e}")
                            
                return {
                    'changed': old_ip != new_ip,
                    'old_ip': old_ip,
                    'new_ip': new_ip,
                    'network_info': new_network_info
                }
                
        except Exception as e:
            logger.error(f"Error checking network change: {e}")
            return {
                'changed': False,
                'error': str(e)
            }

class DynamicIPManager:
    """Manager for dynamic IP detection and Flask app integration."""
    
    def __init__(self, app=None, check_interval: int = 30):
        """Initialize dynamic IP manager.
        
        Args:
            app: Flask app instance (optional, can be set later)
            check_interval: Seconds between IP checks
        """
        self.app = app
        self.monitor = NetworkMonitor(
            check_interval=check_interval,
            callback=self._on_ip_change
        )
        self.startup_ip = None
        self.urls_cache = {}
        
    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app
        
    def start_monitoring(self):
        """Start IP monitoring."""
        # Get initial IP
        initial_check = self.monitor.force_check()
        self.startup_ip = initial_check.get('new_ip')
        
        # Start background monitoring
        self.monitor.start_monitoring()
        
        return initial_check
        
    def stop_monitoring(self):
        """Stop IP monitoring."""
        self.monitor.stop_monitoring()
        
    def get_current_ip(self) -> Optional[str]:
        """Get current detected IP address."""
        return self.monitor.get_current_ip()
        
    def get_network_info(self) -> Dict:
        """Get current network information."""
        return self.monitor.get_current_network_info()
        
    def get_network_urls(self, port: int = 5000) -> Dict[str, str]:
        """Get network URLs using current IP."""
        current_ip = self.get_current_ip()
        if not current_ip:
            current_ip = '127.0.0.1'
            
        # Import here to avoid circular imports
        from utils.network import get_network_urls
        return get_network_urls(host=current_ip, port=port)
        
    def _on_ip_change(self, old_ip: str, new_ip: str, network_info: Dict):
        """Handle IP address changes."""
        logger.info(f"🔄 Network IP changed from {old_ip} to {new_ip}")
        
        # Print to console for immediate visibility
        print(f"\n🔄 NETWORK CHANGE DETECTED:")
        print(f"   📡 Old IP: {old_ip or 'None'}")
        print(f"   🆕 New IP: {new_ip}")
        print(f"   📋 Method: {network_info.get('method', 'unknown')}")
        
        # Clear URL cache
        self.urls_cache.clear()
        
        # If we have an app context, we could emit events or update cached URLs
        if self.app:
            with self.app.app_context():
                port = self.app.config.get('FLASK_PORT', 5000)
                urls = self.get_network_urls(port)
                
                logger.info(f"Updated network configuration: {network_info}")
                
                # Print updated URLs
                print(f"   🔗 Updated URLs:")
                print(f"      • Main: {urls.get('local_url', 'N/A')}")
                print(f"      • Join: {urls.get('join_url', 'N/A')}")
                print(f"      • Host: {urls.get('host_url', 'N/A')}")
                
                # Notify connected clients if enabled
                if self.app.config.get('DYNAMIC_IP_NOTIFY_CLIENTS', True):
                    try:
                        from extensions import socketio
                        socketio.emit('network_change', {
                            'old_ip': old_ip,
                            'new_ip': new_ip,
                            'urls': urls,
                            'timestamp': time.time(),
                            'message': f'Network IP updated to {new_ip}'
                        }, broadcast=True)
                        logger.info("✅ Notified connected clients of IP change")
                        print(f"   ✅ Notified connected clients")
                    except Exception as e:
                        logger.warning(f"Could not emit network change event: {e}")
                        print(f"   ⚠️ Could not notify clients: {e}")
                else:
                    print(f"   ℹ️ Client notifications disabled")
                    
        print("   ✅ Network change handling completed\n")

# Global instance for easy access
network_manager = DynamicIPManager()

def get_dynamic_ip() -> Optional[str]:
    """Get current dynamic IP address."""
    return network_manager.get_current_ip()

def get_dynamic_network_info() -> Dict:
    """Get current dynamic network information."""
    return network_manager.get_network_info()

def get_dynamic_urls(port: int = 5000) -> Dict[str, str]:
    """Get URLs with current dynamic IP."""
    return network_manager.get_network_urls(port)