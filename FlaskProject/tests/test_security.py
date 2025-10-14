# tests/test_security.py - Security Utilities Tests

import pytest
from utils.security import (
    validate_pin,
    validate_player_name,
    sanitize_answer,
    is_safe_filename
)


class TestPinValidation:
    """Test PIN validation functionality."""
    
    def test_valid_pins(self):
        """Test validation of valid PINs."""
        valid_pins = ['123456', '000000', '999999', '101010']
        
        for pin in valid_pins:
            assert validate_pin(pin) is True
    
    def test_invalid_pins(self):
        """Test validation of invalid PINs."""
        invalid_pins = [
            '',           # Empty
            '12345',      # Too short
            '1234567',    # Too long
            '12345a',     # Contains letters
            '12345!',     # Contains special chars
            '12 345',     # Contains space
            None,         # None value
            123456,       # Integer instead of string
        ]
        
        for pin in invalid_pins:
            assert validate_pin(pin) is False


class TestPlayerNameValidation:
    """Test player name validation and sanitization."""
    
    def test_valid_names(self):
        """Test validation of valid player names."""
        valid_names = [
            'John',
            'Alice_123',
            'Player One',
            'José',
            'François',
            'München-Fan',
            'Test.User'
        ]
        
        for name in valid_names:
            result = validate_player_name(name)
            assert result is not None
            assert len(result) >= 2
    
    def test_invalid_names(self):
        """Test validation of invalid player names."""
        invalid_names = [
            '',                    # Empty
            'A',                  # Too short
            'A' * 25,            # Too long
            '<script>alert(1)</script>',  # HTML injection
            'javascript:alert(1)',        # JavaScript protocol
            'data:text/html,<h1>Test</h1>',  # Data protocol
            'onclick=alert(1)',           # Event handler
            None,                 # None value
            123,                  # Not a string
            '###!!!',            # Only special characters
            'Test<>User',        # Invalid characters
        ]
        
        for name in invalid_names:
            result = validate_player_name(name)
            assert result is None
    
    def test_name_sanitization(self):
        """Test that names are properly sanitized."""
        # Test HTML escaping
        result = validate_player_name('Test&User')
        assert result == 'Test&amp;User'
        
        # Test whitespace normalization
        result = validate_player_name('  Test   User  ')
        assert result == 'Test User'
        
        # Test multiple spaces
        result = validate_player_name('Test     User')
        assert result == 'Test User'
    
    def test_unicode_names(self):
        """Test handling of unicode characters."""
        unicode_names = [
            'José',
            'François',
            'München',
            'Zürich',
            'Niño'
        ]
        
        for name in unicode_names:
            result = validate_player_name(name)
            assert result is not None
            assert result == name


class TestAnswerSanitization:
    """Test answer input sanitization."""
    
    def test_valid_answers(self):
        """Test sanitization of valid answers."""
        valid_answers = [
            'Paris',
            '42',
            'The quick brown fox',
            'A & B',
            'C++ Programming'
        ]
        
        for answer in valid_answers:
            result = sanitize_answer(answer)
            assert result is not None
            assert len(result) > 0
    
    def test_answer_html_escaping(self):
        """Test HTML escaping in answers."""
        test_cases = [
            ('Test & User', 'Test &amp; User'),
            ('<script>alert(1)</script>', '&lt;script&gt;alert(1)&lt;/script&gt;'),
            ('A < B > C', 'A &lt; B &gt; C'),
            ('Say "Hello"', 'Say &quot;Hello&quot;')
        ]
        
        for input_answer, expected in test_cases:
            result = sanitize_answer(input_answer)
            assert result == expected
    
    def test_answer_length_limit(self):
        """Test answer length limitation."""
        long_answer = 'A' * 1000  # Very long answer
        result = sanitize_answer(long_answer)
        assert len(result) <= 500
    
    def test_empty_answers(self):
        """Test handling of empty or None answers."""
        empty_answers = [None, '', '   ']
        
        for answer in empty_answers:
            result = sanitize_answer(answer)
            assert result == ''
    
    def test_non_string_answers(self):
        """Test handling of non-string answers."""
        non_string_answers = [123, [], {}, True]
        
        for answer in non_string_answers:
            result = sanitize_answer(answer)
            assert result == ''


class TestFilenameValidation:
    """Test filename safety validation."""
    
    def test_safe_filenames(self):
        """Test validation of safe filenames."""
        safe_filenames = [
            'test.txt',
            'document_1.pdf',
            'my-file.json',
            'data123.csv',
            'image.png'
        ]
        
        for filename in safe_filenames:
            assert is_safe_filename(filename) is True
    
    def test_unsafe_filenames(self):
        """Test validation of unsafe filenames."""
        unsafe_filenames = [
            '',                    # Empty
            '../config.txt',       # Directory traversal
            '/etc/passwd',         # Absolute path
            'file\\path.txt',      # Backslash
            'con.txt',             # Windows reserved name (depends on OS)
            'file*.txt',           # Wildcard
            'file?.txt',           # Question mark
            'file"name.txt',       # Quote
            'file<name>.txt',      # Angle brackets
            'file|name.txt',       # Pipe
            'A' * 300 + '.txt',    # Too long
            None,                  # None value
            123,                   # Not a string
        ]
        
        for filename in unsafe_filenames:
            assert is_safe_filename(filename) is False
    
    def test_filename_length_limit(self):
        """Test filename length limitations."""
        # Test exactly at limit
        long_name = 'A' * 251 + '.txt'  # 255 chars total
        assert is_safe_filename(long_name) is True
        
        # Test over limit
        too_long_name = 'A' * 252 + '.txt'  # 256 chars total
        assert is_safe_filename(too_long_name) is False


class TestSecurityEdgeCases:
    """Test edge cases and attack vectors."""
    
    def test_xss_prevention_in_names(self):
        """Test XSS prevention in player names."""
        xss_payloads = [
            '<script>alert("XSS")</script>',
            'javascript:alert(1)',
            'onload=alert(1)',
            '<img src=x onerror=alert(1)>',
            '"><script>alert(1)</script>',
            "'; DROP TABLE users; --",
        ]
        
        for payload in xss_payloads:
            result = validate_player_name(payload)
            assert result is None  # Should be rejected
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in inputs."""
        sql_payloads = [
            "'; DROP TABLE games; --",
            "1' OR '1'='1",
            "admin'/*",
            "' UNION SELECT * FROM users --",
        ]
        
        # These should be safely handled (escaped or rejected)
        for payload in sql_payloads:
            name_result = validate_player_name(payload)
            answer_result = sanitize_answer(payload)
            
            # Name should be rejected (too dangerous)
            assert name_result is None
            
            # Answer should be escaped
            assert '<' not in answer_result or '&lt;' in answer_result
    
    def test_path_traversal_prevention(self):
        """Test path traversal prevention in filenames."""
        path_traversal_payloads = [
            '../../../etc/passwd',
            '..\\..\\windows\\system32\\config\\sam',
            '....//....//etc/passwd',
            '%2e%2e%2f%2e%2e%2f',
        ]
        
        for payload in path_traversal_payloads:
            assert is_safe_filename(payload) is False