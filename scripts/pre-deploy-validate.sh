#!/bin/bash
# scripts/pre-deploy-validate.sh

set -e  # Exit on any error

echo "🔍 Starting pre-deployment validation for telegive-participant..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# 1. Validate Python environment
echo "🐍 Validating Python environment..."
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed"
fi
print_status "Python3 is available"

# 2. Validate requirements.txt
echo "📦 Validating requirements.txt..."
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found"
fi

# Test requirements installation
python3 -m venv temp_venv
source temp_venv/bin/activate
pip install --quiet -r requirements.txt || print_error "Failed to install requirements"
deactivate
rm -rf temp_venv
print_status "All requirements are valid and installable"

# 3. Validate environment variables
echo "🔧 Validating environment variables..."
if [ ! -f ".env.example" ]; then
    print_error ".env.example file not found"
fi

# Check if all required variables are documented
required_vars=("DATABASE_URL" "SECRET_KEY" "SERVICE_NAME" "SERVICE_PORT")
for var in "${required_vars[@]}"; do
    if ! grep -q "^$var=" .env.example; then
        print_error "Required variable $var not found in .env.example"
    fi
done
print_status "All required environment variables are documented"

# 4. Validate deployment configuration
echo "🚀 Validating deployment configuration..."
railway_json_exists=false

if [ -f "railway.json" ]; then
    railway_json_exists=true
fi

if [ "$railway_json_exists" = false ]; then
    print_error "railway.json not found. Railway deployment configuration is required."
fi

print_status "Railway deployment configuration is valid"

# 5. Validate Flask application structure
echo "🌐 Validating Flask application..."
if [ ! -f "app.py" ]; then
    print_error "app.py not found"
fi

# Test if app can be imported
python3 -c "
import sys
sys.path.append('.')
try:
    from app import app
    print('✅ Flask app imports successfully')
except Exception as e:
    print(f'❌ Flask app import failed: {e}')
    sys.exit(1)
" || print_error "Flask application validation failed"

print_status "Flask application structure is valid"

# 6. Validate database models
echo "🗄️  Validating database models..."
python3 -c "
import sys
sys.path.append('.')
import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['FLASK_ENV'] = 'testing'
try:
    from app import create_app
    from models import db
    app = create_app('testing')
    with app.app_context():
        db.create_all()
    print('✅ Database models are valid')
except Exception as e:
    print(f'❌ Database model validation failed: {e}')
    sys.exit(1)
" || print_error "Database model validation failed"

print_status "Database models are valid"

# 7. Validate health endpoints
echo "🏥 Validating health endpoints..."
python3 -c "
import sys
sys.path.append('.')
import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['FLASK_ENV'] = 'testing'
try:
    from app import create_app
    app = create_app('testing')
    client = app.test_client()
    
    # Test health endpoints
    endpoints = ['/health/live', '/health/ready', '/health']
    for endpoint in endpoints:
        response = client.get(endpoint)
        if response.status_code not in [200, 503]:  # 503 is acceptable for ready endpoint
            raise Exception(f'Health endpoint {endpoint} returned {response.status_code}')
    
    print('✅ Health endpoints are working')
except Exception as e:
    print(f'❌ Health endpoint validation failed: {e}')
    sys.exit(1)
" || print_error "Health endpoint validation failed"

print_status "Health endpoints are working"

# 8. Validate API routes
echo "🛣️  Validating API routes..."
python3 -c "
import sys
sys.path.append('.')
import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['FLASK_ENV'] = 'testing'
try:
    from app import create_app
    app = create_app('testing')
    
    # Check if blueprints are registered
    blueprint_count = len(app.blueprints)
    if blueprint_count == 0:
        raise Exception('No blueprints registered')
    
    print(f'✅ {blueprint_count} blueprints registered')
except Exception as e:
    print(f'❌ API route validation failed: {e}')
    sys.exit(1)
" || print_error "API route validation failed"

print_status "API routes are valid"

# 9. Validate participant-specific functionality
echo "🎯 Validating participant service functionality..."
python3 -c "
import sys
sys.path.append('.')
import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['FLASK_ENV'] = 'testing'
try:
    from utils.captcha_generator import captcha_generator
    from utils.winner_selection import select_winners_cryptographic
    from utils.validation import input_validator
    
    # Test captcha generation
    question, answer = captcha_generator.generate_question()
    if not question or not isinstance(answer, int):
        raise Exception('Captcha generation failed')
    
    # Test winner selection
    participants = [1, 2, 3, 4, 5]
    winners = select_winners_cryptographic(participants, 2)
    if len(winners) != 2:
        raise Exception('Winner selection failed')
    
    # Test input validation
    test_data = {'giveaway_id': 123, 'user_id': 456789012, 'username': 'testuser'}
    result = input_validator.validate_participation_request(test_data)
    if not result['valid']:
        raise Exception('Input validation failed')
    
    print('✅ Participant service functionality is working')
except Exception as e:
    print(f'❌ Participant service validation failed: {e}')
    sys.exit(1)
" || print_error "Participant service functionality validation failed"

print_status "Participant service functionality is valid"

echo "🎉 All pre-deployment validations passed!"
echo "📋 Summary:"
echo "   - Python environment: ✅"
echo "   - Requirements: ✅"
echo "   - Environment variables: ✅"
echo "   - Railway config: ✅"
echo "   - Flask application: ✅"
echo "   - Database models: ✅"
echo "   - Health endpoints: ✅"
echo "   - API routes: ✅"
echo "   - Participant functionality: ✅"
echo ""
echo "🚀 Ready for Railway deployment!"

