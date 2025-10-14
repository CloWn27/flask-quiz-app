# FlaskProject/utils/security.py - Security Utilities

import re
import html
from typing import Optional

def validate_pin(pin: str) -> bool:
    """Validate that PIN is exactly 6 digits."""
    if not pin:
        return False
    return re.match(r'^\d{6}$', pin) is not None

def validate_player_name(name: str) -> Optional[str]:
    """Validate and sanitize player name.
    
    Args:
        name: Raw player name input
        
    Returns:
        Sanitized name if valid, None otherwise
    """
    if not name or not isinstance(name, str):
        return None
    
    # Remove leading/trailing whitespace
    name = name.strip()
    
    # Check length
    if len(name) < 2 or len(name) > 20:
        return None
    
    # Allow letters, numbers, spaces, and basic punctuation
    if not re.match(r'^[a-zA-Z0-9\s\.\-_àáâäèéêëìíîïòóôöùúûüñç]+$', name):
        return None
    
    # Prevent HTML injection
    name = html.escape(name)
    
    # Remove excessive whitespace
    name = re.sub(r'\s+', ' ', name)
    
    # Additional checks for malicious patterns
    suspicious_patterns = [
        r'<[^>]*>',  # HTML tags
        r'javascript:',  # JavaScript protocol
        r'data:',  # Data protocol
        r'vbscript:',  # VBScript protocol
        r'on\w+\s*=',  # Event handlers
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return None
    
    return name

def sanitize_answer(answer: str) -> str:
    """Sanitize answer input to prevent injection attacks."""
    if not answer or not isinstance(answer, str):
        return ""
    
    # Strip whitespace and limit length
    answer = answer.strip()[:500]  # Max 500 chars
    
    # Escape HTML
    answer = html.escape(answer)
    
    return answer

def is_safe_filename(filename: str) -> bool:
    """Check if filename is safe for file operations."""
    if not filename or not isinstance(filename, str):
        return False
    
    # Check for directory traversal attempts
    dangerous_patterns = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
    
    for pattern in dangerous_patterns:
        if pattern in filename:
            return False
    
    # Check length
    if len(filename) > 255:
        return False
    
    # Must contain only safe characters
    if not re.match(r'^[a-zA-Z0-9\.\-_]+$', filename):
        return False
    
    return True

def rate_limit_key(request) -> str:
    """Generate rate limiting key based on IP and user agent."""
    ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
    user_agent = request.environ.get('HTTP_USER_AGENT', '')
    return f"{ip}:{hash(user_agent)}"