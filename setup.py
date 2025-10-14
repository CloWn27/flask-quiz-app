#!/usr/bin/env python3
"""
Flask Quiz App - Setup Script
This script sets up the Flask Quiz App with all dependencies and configurations.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(cmd, shell=True):
    """Run a system command and return the result."""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_python_version():
    """Check if Python version is adequate."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required. Current: {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
    return True

def create_virtual_environment():
    """Create and activate virtual environment."""
    print("🌐 Setting up virtual environment...")
    
    # Check if .venv already exists
    if Path(".venv").exists():
        print("✅ Virtual environment already exists")
        return True
    
    # Create virtual environment
    success, stdout, stderr = run_command("python -m venv .venv")
    if not success:
        print(f"❌ Failed to create virtual environment: {stderr}")
        return False
    
    print("✅ Virtual environment created")
    return True

def install_dependencies():
    """Install Python dependencies."""
    print("📦 Installing dependencies...")
    
    # Determine pip command based on platform
    system = platform.system()
    if system == "Windows":
        pip_cmd = ".venv\\Scripts\\pip"
    else:
        pip_cmd = ".venv/bin/pip"
    
    # Upgrade pip first
    success, _, stderr = run_command(f"{pip_cmd} install --upgrade pip")
    if not success:
        print(f"⚠️  Warning: Could not upgrade pip: {stderr}")
    
    # Install requirements
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found")
        return False
    
    success, stdout, stderr = run_command(f"{pip_cmd} install -r requirements.txt")
    if not success:
        print(f"❌ Failed to install dependencies: {stderr}")
        return False
    
    print("✅ Dependencies installed successfully")
    return True

def setup_environment():
    """Set up environment configuration."""
    print("⚙️  Setting up environment...")
    
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    # Copy from example
    example_file = Path(".env.example")
    if not example_file.exists():
        print("❌ .env.example not found")
        return False
    
    try:
        import secrets
        
        # Read example file
        with open(example_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Generate secure keys
        secret_key = secrets.token_hex(32)
        csrf_key = secrets.token_hex(32)
        
        # Replace placeholder values
        content = content.replace(
            'your-super-secure-64-character-secret-key-generate-with-flask-command',
            secret_key
        )
        content = content.replace(
            'your-csrf-protection-secret-key-also-64-characters-long',
            csrf_key
        )
        
        # Set for network access
        content = content.replace(
            'FLASK_HOST=127.0.0.1',
            'FLASK_HOST=0.0.0.0'
        )
        
        # Write .env file
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Environment file created with secure keys")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def initialize_database():
    """Initialize the database."""
    print("🗄️  Initializing database...")
    
    system = platform.system()
    if system == "Windows":
        python_cmd = ".venv\\Scripts\\python"
    else:
        python_cmd = ".venv/bin/python"
    
    # Create instance directory
    instance_dir = Path("instance")
    instance_dir.mkdir(exist_ok=True)
    
    # Initialize Flask-Migrate if needed
    if not Path("migrations").exists():
        success, _, stderr = run_command(f"{python_cmd} -c \"from app import create_app; from extensions import db; app=create_app(); app.app_context().push(); db.create_all(); print('Database initialized')\"")
        if not success:
            print(f"⚠️  Database initialization had issues: {stderr}")
        else:
            print("✅ Database initialized")
    else:
        print("✅ Database migrations already exist")
    
    return True

def setup_firewall_windows():
    """Set up Windows firewall rule for Flask."""
    print("🔥 Setting up Windows Firewall...")
    
    # Check if running as admin
    try:
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("⚠️  Admin rights needed for firewall setup")
            print("   Run setup again as administrator, or manually allow port 5000")
            return True
    except:
        pass
    
    # Try to add firewall rule
    firewall_cmd = 'netsh advfirewall firewall add rule name="Flask Quiz App" dir=in action=allow protocol=TCP localport=5000'
    success, stdout, stderr = run_command(firewall_cmd)
    
    if success:
        print("✅ Firewall rule added for port 5000")
    else:
        print("⚠️  Could not add firewall rule automatically")
        print("   Please manually allow port 5000 in Windows Firewall")
    
    return True

def main():
    """Main setup function."""
    print("🧠 Flask Quiz App Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        sys.exit(1)
    
    # Setup firewall on Windows
    if platform.system() == "Windows":
        setup_firewall_windows()
    
    print("\n🎉 Setup Complete!")
    print("=" * 50)
    print("Next steps:")
    print("1. Activate virtual environment:")
    
    if platform.system() == "Windows":
        print("   .venv\\Scripts\\Activate.ps1")
        print("2. Run the app:")
        print("   python app.py")
    else:
        print("   source .venv/bin/activate")
        print("2. Run the app:")
        print("   python app.py")
    
    print("\n📱 The app will be accessible on your network!")
    print("   Check the console output for URLs and QR codes")

if __name__ == "__main__":
    main()