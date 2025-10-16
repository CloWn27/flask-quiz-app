#!/usr/bin/env python3
# FlaskProject/functionality_test.py - Comprehensive Functionality Test

import json
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure basic logging for testing
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_question_files():
    """Test that question files exist and are valid."""
    print("📚 Testing question files...")
    
    for lang in ['de', 'en']:
        file_path = project_root / f'questions_{lang}.json'
        if not file_path.exists():
            print(f"❌ Questions file not found: {file_path}")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                print(f"❌ Invalid format in {file_path}")
                return False
            
            total_questions = sum(len(questions) for questions in data.values())
            print(f"✅ {lang.upper()}: {total_questions} questions in {len(data)} difficulty levels")
        
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
            return False
    
    return True

def test_app_imports():
    """Test that all critical modules can be imported."""
    print("\n🔍 Testing imports...")
    
    try:
        from app import create_app
        print("✅ Main app module")
        
        from game_logic import load_questions, create_new_game, generate_pin
        print("✅ Game logic module")
        
        from config import get_config
        print("✅ Configuration module")
        
        from database import db, Game, Player
        print("✅ Database models")
        
        from utils.network import get_network_info
        print("✅ Network utilities")
        
        from utils.security import validate_pin, validate_player_name
        print("✅ Security utilities")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_game_logic():
    """Test core game logic functions."""
    print("\n🎮 Testing game logic...")
    
    try:
        from game_logic import load_questions
        from app import create_app
        
        # Test question loading
        de_questions = load_questions('de')
        if not de_questions:
            print("❌ Failed to load German questions")
            return False
        print(f"✅ Loaded {len(de_questions)} German questions")
        
        en_questions = load_questions('en')
        if not en_questions:
            print("❌ Failed to load English questions")
            return False
        print(f"✅ Loaded {len(en_questions)} English questions")
        
        # Test PIN generation with app context
        app = create_app('testing')
        with app.app_context():
            from game_logic import generate_pin
            pin = generate_pin()
            if not pin or len(pin) != 6 or not pin.isdigit():
                print(f"❌ Invalid PIN generated: {pin}")
                return False
            print(f"✅ Generated valid PIN: {pin}")
        
        return True
    except Exception as e:
        print(f"❌ Game logic error: {e}")
        return False

def test_app_creation():
    """Test Flask app creation."""
    print("\n🌐 Testing app creation...")
    
    try:
        from app import create_app
        app = create_app('testing')
        
        if not app:
            print("❌ Failed to create Flask app")
            return False
        
        print("✅ Flask app created successfully")
        
        # Test basic routes exist
        with app.test_request_context():
            from flask import url_for
            
            # Test if key routes are registered
            routes = ['player.index', 'player.join_game', 'host.host_dashboard']
            for route in routes:
                try:
                    url = url_for(route)
                    print(f"✅ Route {route}: {url}")
                except Exception as e:
                    print(f"❌ Route {route} not found: {e}")
                    return False
        
        return True
    except Exception as e:
        print(f"❌ App creation error: {e}")
        return False

def test_network_functions():
    """Test network utility functions."""
    print("\n🌐 Testing network functions...")
    
    try:
        from utils.network import get_network_info, get_network_urls
        
        # Test network info
        network_info = get_network_info()
        if network_info['status'] == 'success':
            print(f"✅ Network detected: {network_info['local_ip']}")
        else:
            print("⚠️ Network detection failed (might be expected in some environments)")
        
        # Test URL generation
        urls = get_network_urls(host='127.0.0.1', port=5000)
        if not urls or 'local_url' not in urls:
            print("❌ Failed to generate network URLs")
            return False
        
        print(f"✅ Generated URLs: {urls['local_url']}")
        return True
    except Exception as e:
        print(f"❌ Network function error: {e}")
        return False

def test_security_functions():
    """Test security utility functions."""
    print("\n🔒 Testing security functions...")
    
    try:
        from utils.security import validate_pin, validate_player_name, sanitize_answer
        
        # Test PIN validation
        valid_pin = "123456"
        invalid_pin = "12345"
        
        if not validate_pin(valid_pin):
            print(f"❌ Valid PIN rejected: {valid_pin}")
            return False
        
        if validate_pin(invalid_pin):
            print(f"❌ Invalid PIN accepted: {invalid_pin}")
            return False
        
        print("✅ PIN validation working")
        
        # Test player name validation
        valid_name = "Player123"
        invalid_name = "<script>alert('hack')</script>"
        
        clean_name = validate_player_name(valid_name)
        if not clean_name:
            print(f"❌ Valid name rejected: {valid_name}")
            return False
        
        malicious_name = validate_player_name(invalid_name)
        if malicious_name == invalid_name:
            print(f"❌ Malicious name not sanitized: {invalid_name}")
            return False
        
        print("✅ Player name validation working")
        
        # Test answer sanitization
        raw_answer = "<b>Test Answer</b>"
        clean_answer = sanitize_answer(raw_answer)
        if "<b>" in clean_answer or "</b>" in clean_answer:
            print(f"❌ Answer not properly sanitized: {clean_answer}")
            return False
        
        print("✅ Answer sanitization working")
        return True
    except Exception as e:
        print(f"❌ Security function error: {e}")
        return False

def main():
    """Run all functionality tests."""
    print("🧪 Flask Quiz App - Comprehensive Functionality Test")
    print("=" * 60)
    
    tests = [
        ("Question Files", test_question_files),
        ("App Imports", test_app_imports),
        ("Game Logic", test_game_logic),
        ("App Creation", test_app_creation),
        ("Network Functions", test_network_functions),
        ("Security Functions", test_security_functions),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All functionality tests passed! The app is ready to use.")
        print("\n🚀 Available game modes:")
        print("   • Solo Mode: Individual quiz with difficulty selection")
        print("   • Multiplayer Mode: Host creates game, players join with PIN")
        print("   • Language Support: German (DE) and English (EN)")
        print("   • Difficulty Levels: Easy, Medium, Hard, Very Hard")
        print("   • Custom Questions: Host can create custom question sets")
    else:
        print(f"⚠️ {total - passed} test(s) failed. Check the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())