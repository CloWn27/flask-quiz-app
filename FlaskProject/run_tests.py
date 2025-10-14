#!/usr/bin/env python3
"""
Flask Quiz App - Test Runner
This script runs various tests and checks to ensure the app is working correctly.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from app import create_app
        print("✅ Main app imports OK")
    except ImportError as e:
        print(f"❌ Failed to import app: {e}")
        return False
    
    try:
        from utils.network import get_network_info, generate_qr_code
        print("✅ Network utilities import OK")
    except ImportError as e:
        print(f"❌ Failed to import network utils: {e}")
        return False
    
    try:
        from utils.security import validate_pin, validate_player_name
        print("✅ Security utilities import OK")
    except ImportError as e:
        print(f"❌ Failed to import security utils: {e}")
        return False
    
    try:
        from database import Game, Player, PlayerStats
        print("✅ Database models import OK")
    except ImportError as e:
        print(f"❌ Failed to import database models: {e}")
        return False
    
    try:
        from game_logic import load_questions, generate_pin
        print("✅ Game logic imports OK")
    except ImportError as e:
        print(f"❌ Failed to import game logic: {e}")
        return False
    
    return True

def test_question_files():
    """Test that question files exist and are valid JSON."""
    print("📚 Testing question files...")
    
    question_files = ['questions_de.json', 'questions_en.json']
    
    for filename in question_files:
        filepath = Path(filename)
        if not filepath.exists():
            print(f"❌ Missing question file: {filename}")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check structure
            required_keys = ['easy', 'medium', 'hard', 'heavy']
            if not all(key in data for key in required_keys):
                print(f"❌ Invalid structure in {filename}")
                return False
            
            # Check that each difficulty has questions
            total_questions = sum(len(data[key]) for key in required_keys)
            if total_questions == 0:
                print(f"❌ No questions found in {filename}")
                return False
            
            print(f"✅ {filename}: {total_questions} questions")
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {filename}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")
            return False
    
    return True

def test_app_creation():
    """Test that the Flask app can be created."""
    print("🔧 Testing app creation...")
    
    try:
        from app import create_app
        app = create_app()
        
        if not app:
            print("❌ App creation returned None")
            return False
        
        print("✅ Flask app created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create Flask app: {e}")
        return False

def test_network_functions():
    """Test network utility functions."""
    print("🌐 Testing network functions...")
    
    try:
        from utils.network import get_network_info, is_valid_ip, get_port_status
        
        # Test network info
        network_info = get_network_info()
        if 'local_ip' not in network_info:
            print("❌ Network info missing local_ip")
            return False
        
        print(f"✅ Network detection: {network_info['local_ip']}")
        
        # Test IP validation
        if not is_valid_ip('192.168.1.1'):
            print("❌ IP validation failed for valid IP")
            return False
        
        if is_valid_ip('invalid.ip'):
            print("❌ IP validation passed for invalid IP")
            return False
        
        print("✅ IP validation working")
        
        # Test QR code generation
        try:
            from utils.network import generate_qr_code
            qr_result = generate_qr_code("http://example.com")
            if qr_result and qr_result.startswith("data:image/png;base64,"):
                print("✅ QR code generation working")
            else:
                print("⚠️  QR code generation might not be working (libraries missing?)")
        except:
            print("⚠️  QR code generation not available")
        
        return True
        
    except Exception as e:
        print(f"❌ Network function test failed: {e}")
        return False

def test_security_functions():
    """Test security utility functions."""
    print("🔒 Testing security functions...")
    
    try:
        from utils.security import validate_pin, validate_player_name, sanitize_answer
        
        # Test PIN validation
        if not validate_pin('123456'):
            print("❌ PIN validation failed for valid PIN")
            return False
        
        if validate_pin('12345'):  # Too short
            print("❌ PIN validation passed for invalid PIN")
            return False
        
        print("✅ PIN validation working")
        
        # Test player name validation
        valid_name = validate_player_name('TestPlayer123')
        if not valid_name:
            print("❌ Player name validation failed for valid name")
            return False
        
        invalid_name = validate_player_name('<script>alert("hack")</script>')
        if invalid_name:
            print("❌ Player name validation passed for malicious input")
            return False
        
        print("✅ Player name validation working")
        
        # Test answer sanitization
        clean_answer = sanitize_answer('Test Answer <script>')
        if '<script>' in clean_answer:
            print("❌ Answer sanitization failed")
            return False
        
        print("✅ Answer sanitization working")
        
        return True
        
    except Exception as e:
        print(f"❌ Security function test failed: {e}")
        return False

def test_game_logic():
    """Test core game logic functions."""
    print("🎮 Testing game logic...")
    
    try:
        from game_logic import load_questions
        from app import create_app
        
        # Test question loading
        questions_de = load_questions('de')
        if not questions_de:
            print("❌ Failed to load German questions")
            return False
        
        questions_en = load_questions('en')
        if not questions_en:
            print("❌ Failed to load English questions")
            return False
        
        print(f"✅ Loaded {len(questions_de)} German, {len(questions_en)} English questions")
        
        # Test PIN generation with app context
        app = create_app()
        with app.app_context():
            from game_logic import generate_pin
            pin = generate_pin()
            if not pin or len(pin) != 6 or not pin.isdigit():
                print("❌ PIN generation failed")
                return False
        
        print("✅ PIN generation working")
        
        return True
        
    except Exception as e:
        print(f"❌ Game logic test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧠 Flask Quiz App - Test Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_question_files,
        test_app_creation,
        test_network_functions,
        test_security_functions,
        test_game_logic
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            print()  # Empty line for readability
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            print()
    
    print("=" * 50)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! App is ready to run.")
        print("\n🚀 To start the app:")
        print("   python app.py")
        return True
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)