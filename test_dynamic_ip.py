#!/usr/bin/env python3
"""
Test script for Dynamic IP Detection functionality
Run this to verify that the dynamic IP detection is working properly.
"""

import time
import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.network import get_network_info, _detect_ip_via_system_commands, _is_private_ip
from services.network_monitor import NetworkMonitor, DynamicIPManager

def test_static_ip_detection():
    """Test the static IP detection methods."""
    print("🔍 Testing Static IP Detection Methods")
    print("=" * 50)
    
    methods = ['auto', 'remote', 'hostname', 'system']
    
    for method in methods:
        print(f"\n📡 Testing method: {method}")
        try:
            result = get_network_info(prefer_method=method)
            print(f"   ✅ Result: {result}")
            
            ip = result.get('local_ip')
            if ip:
                is_private = _is_private_ip(ip)
                print(f"   🏠 Is private IP: {is_private}")
                print(f"   🎯 Status: {result.get('status')}")
                print(f"   🛠️  Method used: {result.get('method')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)

def test_system_commands():
    """Test system-specific IP detection commands."""
    print("\n🖥️  Testing System Command Detection")
    print("=" * 50)
    
    try:
        result = _detect_ip_via_system_commands()
        if result:
            print(f"✅ System command result: {result}")
        else:
            print("❌ System commands failed to detect IP")
    except Exception as e:
        print(f"❌ System command error: {e}")
    
    print("=" * 50)

def test_dynamic_monitoring():
    """Test the dynamic IP monitoring functionality."""
    print("\n🔄 Testing Dynamic IP Monitoring")
    print("=" * 50)
    
    def ip_change_callback(old_ip, new_ip, network_info):
        print(f"\n🚨 IP CHANGE DETECTED IN CALLBACK:")
        print(f"   📤 Old IP: {old_ip}")
        print(f"   📥 New IP: {new_ip}")
        print(f"   📊 Network info: {network_info}")
    
    # Create monitor with short check interval for testing
    monitor = NetworkMonitor(check_interval=5, callback=ip_change_callback)
    
    print("🚀 Starting network monitoring (will run for 20 seconds)...")
    monitor.start_monitoring()
    
    # Show current state for a few cycles
    for i in range(4):
        time.sleep(5)
        current_ip = monitor.get_current_ip()
        network_info = monitor.get_current_network_info()
        
        print(f"\n📊 Check #{i+1}:")
        print(f"   🌐 Current IP: {current_ip}")
        print(f"   📈 Status: {network_info.get('status', 'unknown')}")
        print(f"   🔧 Method: {network_info.get('method', 'unknown')}")
        
        # Force a check to see if anything changes
        check_result = monitor.force_check()
        if check_result.get('changed'):
            print(f"   🔄 Change detected during force check!")
    
    print("\n🛑 Stopping monitor...")
    monitor.stop_monitoring()
    print("=" * 50)

def test_dynamic_manager():
    """Test the DynamicIPManager functionality."""
    print("\n🎯 Testing Dynamic IP Manager")
    print("=" * 50)
    
    manager = DynamicIPManager(check_interval=10)
    
    print("🚀 Starting manager...")
    initial_check = manager.start_monitoring()
    
    print(f"📊 Initial check result: {initial_check}")
    
    # Test URL generation
    time.sleep(2)  # Give it a moment to establish
    
    current_ip = manager.get_current_ip()
    network_info = manager.get_network_info()
    urls = manager.get_network_urls(port=5000)
    
    print(f"\n🌐 Manager State:")
    print(f"   📍 Current IP: {current_ip}")
    print(f"   📊 Network info: {network_info}")
    print(f"   🔗 URLs:")
    for key, url in urls.items():
        if not key.endswith('_qr'):  # Skip QR code data
            print(f"      {key}: {url}")
    
    print("\n🛑 Stopping manager...")
    manager.stop_monitoring()
    print("=" * 50)

def main():
    """Run all tests."""
    print("🧪 Dynamic IP Detection Test Suite")
    print("=" * 60)
    print("This script will test various aspects of the dynamic IP detection system.")
    print("=" * 60)
    
    try:
        # Test static detection first
        test_static_ip_detection()
        
        # Test system commands
        test_system_commands()
        
        # Test dynamic monitoring
        test_dynamic_monitoring()
        
        # Test manager
        test_dynamic_manager()
        
        print("\n✅ All tests completed!")
        print("\n💡 Tips for using dynamic IP detection:")
        print("   • Enable in config: DYNAMIC_IP_ENABLED=True")
        print("   • Adjust check interval: DYNAMIC_IP_CHECK_INTERVAL=30")
        print("   • Choose detection method: DYNAMIC_IP_PREFERRED_METHOD=auto")
        print("   • Enable client notifications: DYNAMIC_IP_NOTIFY_CLIENTS=True")
        
    except KeyboardInterrupt:
        print("\n\n🚫 Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()