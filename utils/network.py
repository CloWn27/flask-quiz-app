# FlaskProject/utils/network.py - Network Utilities

import socket
import logging
import io
import base64
from typing import Dict, Optional

try:
    import qrcode
    from PIL import Image
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

logger = logging.getLogger(__name__)

def get_network_info(prefer_method: str = 'auto') -> Dict[str, str]:
    """Get network information including local IP address.
    
    Args:
        prefer_method: Preferred detection method ('auto', 'remote', 'hostname', 'system')
    
    Returns:
        Dictionary containing network information
    """
    methods = []
    
    if prefer_method == 'auto':
        methods = ['remote_connect', 'hostname_resolve', 'system_command']
    elif prefer_method == 'remote':
        methods = ['remote_connect', 'hostname_resolve', 'system_command']
    elif prefer_method == 'hostname':
        methods = ['hostname_resolve', 'remote_connect', 'system_command']
    elif prefer_method == 'system':
        methods = ['system_command', 'hostname_resolve', 'remote_connect']
    else:
        methods = ['remote_connect', 'hostname_resolve', 'system_command']
    
    for method in methods:
        try:
            if method == 'remote_connect':
                # Method 1: Connect to a remote server to determine local IP
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.settimeout(1)
                    # Try multiple DNS servers for reliability
                    dns_servers = [('8.8.8.8', 80), ('1.1.1.1', 80), ('208.67.222.222', 80)]
                    for dns_server in dns_servers:
                        try:
                            s.connect(dns_server)
                            local_ip = s.getsockname()[0]
                            if local_ip and local_ip != '127.0.0.1':
                                return {
                                    'local_ip': local_ip,
                                    'status': 'success',
                                    'method': 'remote_connect',
                                    'dns_server': dns_server[0]
                                }
                        except:
                            continue
                            
            elif method == 'hostname_resolve':
                # Method 2: Get hostname and resolve IP
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                
                # Filter out localhost
                if local_ip and local_ip != '127.0.0.1':
                    return {
                        'local_ip': local_ip,
                        'status': 'success',
                        'method': 'hostname_resolve',
                        'hostname': hostname
                    }
                    
            elif method == 'system_command':
                # Method 3: Use system commands
                result = _detect_ip_via_system_commands()
                if result:
                    return result
                    
        except Exception as e:
            logger.warning(f"Method {method} failed: {e}")
            continue
        
    
    # Fallback to localhost if all methods failed
    logger.error("All network detection methods failed, falling back to localhost")
    return {
        'local_ip': '127.0.0.1',
        'status': 'fallback',
        'error': 'Could not detect network IP',
        'note': 'Using localhost - external access may not work'
    }

def _detect_ip_via_system_commands() -> Optional[Dict[str, str]]:
    """Detect IP using system-specific commands.
    
    Returns:
        Dictionary with IP info or None if failed
    """
    import subprocess
    import platform
    import re
    
    try:
        system = platform.system()
        
        if system == "Windows":
            # Windows: use ipconfig and parse more thoroughly
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Look for IPv4 addresses in private ranges
                ipv4_pattern = r'IPv4 Address[^:]*:\s*([0-9.]+)'
                matches = re.findall(ipv4_pattern, result.stdout)
                
                for match in matches:
                    ip = match.strip()
                    if _is_private_ip(ip):
                        return {
                            'local_ip': ip,
                            'status': 'success',
                            'method': 'system_command_windows',
                            'note': 'Detected via ipconfig'
                        }
                        
            # Try using PowerShell as backup
            try:
                ps_cmd = ['powershell', '-Command', 
                         'Get-NetIPAddress -AddressFamily IPv4 -PrefixOrigin Dhcp,Manual | Where-Object {$_.IPAddress -like "192.168.*" -or $_.IPAddress -like "10.*" -or ($_.IPAddress -like "172.*" -and [int]($_.IPAddress.Split(".")[1]) -ge 16 -and [int]($_.IPAddress.Split(".")[1]) -le 31)} | Select-Object -First 1 -ExpandProperty IPAddress']
                result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    ip = result.stdout.strip()
                    if _is_private_ip(ip):
                        return {
                            'local_ip': ip,
                            'status': 'success',
                            'method': 'system_command_powershell',
                            'note': 'Detected via PowerShell'
                        }
            except:
                pass
                
        elif system in ["Linux", "Darwin"]:  # Linux or macOS
            # Try multiple Unix commands
            commands = [
                ['hostname', '-I'],
                ['ip', 'route', 'get', '1.1.1.1'],
                ['ifconfig']
            ]
            
            for cmd in commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        output = result.stdout
                        
                        if cmd[0] == 'hostname':
                            ips = output.strip().split()
                            for ip in ips:
                                if _is_private_ip(ip):
                                    return {
                                        'local_ip': ip,
                                        'status': 'success',
                                        'method': 'system_command_hostname'
                                    }
                                    
                        elif cmd[0] == 'ip':
                            # Parse ip route output
                            for line in output.split('\n'):
                                if 'src' in line:
                                    match = re.search(r'src ([0-9.]+)', line)
                                    if match:
                                        ip = match.group(1)
                                        if _is_private_ip(ip):
                                            return {
                                                'local_ip': ip,
                                                'status': 'success',
                                                'method': 'system_command_ip_route'
                                            }
                                            
                        elif cmd[0] == 'ifconfig':
                            # Parse ifconfig output
                            ip_pattern = r'inet ([0-9.]+)'
                            matches = re.findall(ip_pattern, output)
                            for ip in matches:
                                if _is_private_ip(ip):
                                    return {
                                        'local_ip': ip,
                                        'status': 'success',
                                        'method': 'system_command_ifconfig'
                                    }
                                    
                except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                    continue
                    
    except Exception as e:
        logger.warning(f"System command detection failed: {e}")
        
    return None

def _is_private_ip(ip: str) -> bool:
    """Check if IP is in private range.
    
    Args:
        ip: IP address string
        
    Returns:
        True if IP is private, False otherwise
    """
    if not is_valid_ip(ip):
        return False
        
    parts = ip.split('.')
    if len(parts) != 4:
        return False
        
    try:
        first = int(parts[0])
        second = int(parts[1])
        
        # Private IP ranges:
        # 10.0.0.0 - 10.255.255.255
        # 172.16.0.0 - 172.31.255.255  
        # 192.168.0.0 - 192.168.255.255
        
        if first == 10:
            return True
        elif first == 172 and 16 <= second <= 31:
            return True
        elif first == 192 and second == 168:
            return True
            
        return False
        
    except ValueError:
        return False

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
