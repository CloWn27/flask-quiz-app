# FlaskProject/utils/network.py - Network Utilities

import socket
import logging
import io
import base64
from typing import Dict

try:
    import qrcode
    from PIL import Image
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

logger = logging.getLogger(__name__)

def get_network_info() -> Dict[str, str]:
    """Get network information including local IP address.
    
    Returns:
        Dictionary containing network information
    """
    try:
        # Method 1: Connect to a remote server to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(1)
            # Connect to Google's DNS server
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            
        return {
            'local_ip': local_ip,
            'status': 'success',
            'method': 'remote_connect'
        }
        
    except Exception as e:
        logger.warning(f"Primary network detection failed: {e}")
        
        # Method 2: Get hostname and resolve IP
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            # Filter out localhost
            if local_ip != '127.0.0.1':
                return {
                    'local_ip': local_ip,
                    'status': 'success',
                    'method': 'hostname_resolve',
                    'hostname': hostname
                }
                
        except Exception as e2:
            logger.warning(f"Secondary network detection failed: {e2}")
        
        # Method 3: Try to get all network interfaces
        try:
            # This is a simplified approach - in production you might want to use
            # more sophisticated network interface detection
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                # Windows: use ipconfig
                result = subprocess.run(['ipconfig'], capture_output=True, text=True)
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'IPv4 Address' in line and '192.168.' in line:
                        ip = line.split(':')[1].strip()
                        return {
                            'local_ip': ip,
                            'status': 'success',
                            'method': 'system_command',
                            'note': 'Detected via ipconfig'
                        }
                        
            else:
                # Linux/Mac: use ip or ifconfig
                try:
                    result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                    if result.returncode == 0:
                        ips = result.stdout.strip().split()
                        for ip in ips:
                            if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                                return {
                                    'local_ip': ip,
                                    'status': 'success',
                                    'method': 'hostname_command'
                                }
                except:
                    pass
                    
        except Exception as e3:
            logger.warning(f"System command network detection failed: {e3}")
        
        # Fallback to localhost
        logger.error("All network detection methods failed, falling back to localhost")
        return {
            'local_ip': '127.0.0.1',
            'status': 'fallback',
            'error': 'Could not detect network IP',
            'note': 'Using localhost - external access may not work'
        }

def is_valid_ip(ip: str) -> bool:
    """Check if the given string is a valid IP address.
    
    Args:
        ip: IP address string to validate
        
    Returns:
        True if valid IP, False otherwise
    """
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def get_port_status(host: str, port: int, timeout: float = 3.0) -> bool:
    """Check if a port is open on the given host.
    
    Args:
        host: Host to check
        port: Port number to check  
        timeout: Connection timeout in seconds
        
    Returns:
        True if port is open, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


def generate_qr_code(url: str, size: int = 10) -> str:
    """Generate a QR code for the given URL.
    
    Args:
        url: URL to encode in QR code
        size: Size of the QR code (1-40)
        
    Returns:
        Base64 encoded PNG image data or empty string if QR generation fails
    """
    if not QR_AVAILABLE:
        logger.warning("QR code libraries not available")
        return ""
        
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
        
    except Exception as e:
        logger.error(f"Failed to generate QR code: {e}")
        return ""


def get_network_urls(host: str = None, port: int = 5000) -> Dict[str, str]:
    """Get all relevant URLs for network access.
    
    Args:
        host: Host IP (auto-detected if None)
        port: Port number
        
    Returns:
        Dictionary with various URLs and QR codes
    """
    if host is None:
        network_info = get_network_info()
        host = network_info.get('local_ip', '127.0.0.1')
    
    urls = {
        'local_url': f'http://{host}:{port}',
        'join_url': f'http://{host}:{port}/join',
        'host_url': f'http://{host}:{port}/host',
        'stats_url': f'http://{host}:{port}/stats'
    }
    
    # Generate QR codes if available
    if QR_AVAILABLE:
        urls.update({
            'local_qr': generate_qr_code(urls['local_url']),
            'join_qr': generate_qr_code(urls['join_url']),
            'host_qr': generate_qr_code(urls['host_url'])
        })
    
    return urls
