#!/usr/bin/env python3
# scripts/validate_requirements.py
import subprocess
import sys
import pkg_resources
from packaging import version
import requests
import time

def validate_requirements():
    """Validate all requirements in requirements.txt"""
    
    print("🔍 Validating requirements.txt...")
    
    with open('requirements.txt', 'r') as f:
        requirements = f.read().strip().split('\n')
    
    invalid_packages = []
    outdated_packages = []
    security_warnings = []
    
    for req in requirements:
        if not req.strip() or req.startswith('#'):
            continue
            
        # Parse package name and version
        if '==' in req:
            package_name, package_version = req.split('==')
        else:
            package_name = req
            package_version = None
        
        # Check if package exists on PyPI
        try:
            response = requests.get(f'https://pypi.org/pypi/{package_name}/json', timeout=10)
            if response.status_code != 200:
                invalid_packages.append(package_name)
                continue
                
            package_info = response.json()
            latest_version = package_info['info']['version']
            
            if package_version:
                # Check if specified version exists
                available_versions = list(package_info['releases'].keys())
                if package_version not in available_versions:
                    invalid_packages.append(f"{package_name}=={package_version}")
                    continue
                
                # Check if version is outdated
                if version.parse(package_version) < version.parse(latest_version):
                    outdated_packages.append(f"{package_name}: {package_version} -> {latest_version}")
                
                # Check for security vulnerabilities (basic check)
                if package_name.lower() in ['flask', 'requests', 'sqlalchemy', 'psycopg2-binary']:
                    try:
                        current_version = version.parse(package_version)
                        latest_version_parsed = version.parse(latest_version)
                        
                        # If more than 2 major versions behind, flag as potential security risk
                        if latest_version_parsed.major - current_version.major >= 2:
                            security_warnings.append(f"{package_name}: {package_version} (consider updating for security)")
                    except:
                        pass
            
            # Add small delay to avoid rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"⚠️  Could not validate {package_name}: {e}")
    
    # Report results
    if invalid_packages:
        print("❌ Invalid packages found:")
        for pkg in invalid_packages:
            print(f"   - {pkg}")
        return False
    
    if outdated_packages:
        print("⚠️  Outdated packages found:")
        for pkg in outdated_packages:
            print(f"   - {pkg}")
    
    if security_warnings:
        print("🔒 Security warnings:")
        for warning in security_warnings:
            print(f"   - {warning}")
    
    print("✅ All requirements are valid!")
    return True

def check_requirements_security():
    """Check for known security vulnerabilities"""
    print("🔒 Checking for security vulnerabilities...")
    
    # Known vulnerable versions (simplified check)
    vulnerable_packages = {
        'flask': ['0.12.4', '1.0.4', '1.1.4'],  # Examples of versions with known issues
        'requests': ['2.19.1', '2.20.0'],
        'sqlalchemy': ['1.3.0', '1.4.0']
    }
    
    with open('requirements.txt', 'r') as f:
        requirements = f.read().strip().split('\n')
    
    vulnerabilities_found = []
    
    for req in requirements:
        if not req.strip() or req.startswith('#') or '==' not in req:
            continue
            
        package_name, package_version = req.split('==')
        
        if package_name in vulnerable_packages:
            if package_version in vulnerable_packages[package_name]:
                vulnerabilities_found.append(f"{package_name}=={package_version}")
    
    if vulnerabilities_found:
        print("🚨 Known vulnerable packages found:")
        for vuln in vulnerabilities_found:
            print(f"   - {vuln}")
        return False
    
    print("✅ No known vulnerabilities found")
    return True

def validate_flask_specific_requirements():
    """Validate Flask-specific requirements"""
    print("🌐 Validating Flask-specific requirements...")
    
    required_flask_packages = [
        'Flask',
        'Flask-SQLAlchemy',
        'Flask-CORS',
        'psycopg2-binary',
        'gunicorn'
    ]
    
    with open('requirements.txt', 'r') as f:
        requirements_content = f.read()
    
    missing_packages = []
    
    for package in required_flask_packages:
        if package not in requirements_content:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required Flask packages:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        return False
    
    print("✅ All required Flask packages are present")
    return True

def test_requirements_installation():
    """Test that requirements can be installed"""
    print("📦 Testing requirements installation...")
    
    try:
        # Create a temporary virtual environment
        subprocess.run(['python3', '-m', 'venv', 'temp_test_venv'], check=True, capture_output=True)
        
        # Install requirements
        result = subprocess.run([
            'temp_test_venv/bin/pip', 'install', '-r', 'requirements.txt'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("❌ Requirements installation failed:")
            print(result.stderr)
            return False
        
        print("✅ Requirements can be installed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Installation test failed: {e}")
        return False
    
    finally:
        # Clean up
        subprocess.run(['rm', '-rf', 'temp_test_venv'], capture_output=True)

if __name__ == "__main__":
    success = True
    
    # Run all validation checks
    if not validate_requirements():
        success = False
    
    if not check_requirements_security():
        success = False
    
    if not validate_flask_specific_requirements():
        success = False
    
    if not test_requirements_installation():
        success = False
    
    if success:
        print("\n🎉 All requirements validation checks passed!")
        sys.exit(0)
    else:
        print("\n❌ Requirements validation failed!")
        sys.exit(1)

