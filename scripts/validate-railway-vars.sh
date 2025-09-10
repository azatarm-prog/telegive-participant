#!/bin/bash
# scripts/validate-railway-vars.sh

echo "🔍 Validating Railway environment variables..."

# Check for common Railway variable syntax errors
check_var_syntax() {
    local var_name=$1
    local var_value=$2
    
    # Check for quotes around Railway variables
    if [[ $var_value == *'${{Postgres'* ]] && [[ $var_value == '"'* ]]; then
        echo "❌ ERROR: $var_name has quotes around Railway variable"
        echo "   Current: $var_value"
        echo "   Should be: ${var_value//\"/}"
        return 1
    fi
    
    # Check for PRIVATE_URL usage
    if [[ $var_value == *'DATABASE_PRIVATE_URL'* ]]; then
        echo "⚠️  WARNING: $var_name uses PRIVATE_URL"
        echo "   Consider using DATABASE_PUBLIC_URL for external connections"
    fi
    
    # Check for localhost URLs in production
    if [[ $var_value == *'localhost'* ]]; then
        echo "⚠️  WARNING: $var_name contains localhost URL"
        echo "   This should be updated for production deployment"
    fi
    
    return 0
}

# Validate common variables
vars_to_check=(
    "DATABASE_URL"
    "REDIS_URL"
    "TELEGIVE_AUTH_URL"
    "TELEGIVE_CHANNEL_URL"
    "TELEGIVE_BOT_URL"
    "TELEGIVE_PARTICIPANT_URL"
    "TELEGIVE_MEDIA_URL"
    "TELEGIVE_GIVEAWAY_URL"
)

error_count=0

# Check .env.example file
if [ -f ".env.example" ]; then
    echo "📋 Checking .env.example file..."
    
    while IFS='=' read -r var_name var_value; do
        # Skip comments and empty lines
        if [[ $var_name =~ ^#.*$ ]] || [[ -z $var_name ]]; then
            continue
        fi
        
        # Check if this is one of our target variables
        for target_var in "${vars_to_check[@]}"; do
            if [[ $var_name == $target_var ]]; then
                if ! check_var_syntax "$var_name" "$var_value"; then
                    ((error_count++))
                fi
                break
            fi
        done
    done < .env.example
else
    echo "⚠️  .env.example file not found"
    ((error_count++))
fi

# Check for required Railway variables in .env.example
echo "🔧 Checking for required Railway variables..."

required_railway_vars=(
    "DATABASE_URL=\${{Postgres.DATABASE_PUBLIC_URL}}"
    "REDIS_URL=\${{Redis.REDIS_URL}}"
)

for required_var in "${required_railway_vars[@]}"; do
    if ! grep -q "$required_var" .env.example 2>/dev/null; then
        echo "❌ Missing required Railway variable: $required_var"
        ((error_count++))
    fi
done

# Check for proper service URLs format
echo "🌐 Checking service URL formats..."

service_url_pattern="https://telegive-.*-production\.up\.railway\.app"

for var in "${vars_to_check[@]}"; do
    if [[ $var == TELEGIVE_*_URL ]]; then
        if grep -q "^$var=" .env.example; then
            url_value=$(grep "^$var=" .env.example | cut -d'=' -f2)
            if [[ ! $url_value =~ $service_url_pattern ]] && [[ $url_value != *"localhost"* ]]; then
                echo "⚠️  $var format may be incorrect: $url_value"
                echo "   Expected format: https://telegive-service-production.up.railway.app"
            fi
        fi
    fi
done

# Check for unique secret keys
echo "🔐 Checking for unique secret keys..."

if grep -q "SECRET_KEY=.*participant.*" .env.example; then
    echo "✅ Service-specific secret key found"
else
    echo "⚠️  Consider using a service-specific secret key"
fi

# Summary
if [ $error_count -eq 0 ]; then
    echo "✅ All Railway variables are properly formatted"
    echo ""
    echo "📋 Railway Deployment Checklist:"
    echo "   - [ ] Create Railway project"
    echo "   - [ ] Add PostgreSQL database"
    echo "   - [ ] Add Redis (optional)"
    echo "   - [ ] Set environment variables (copy from .env.example)"
    echo "   - [ ] Deploy service"
    echo "   - [ ] Get service URL"
    echo "   - [ ] Update other services with new URL"
    echo "   - [ ] Run: curl https://your-service.railway.app/admin/init-db"
    echo "   - [ ] Verify: curl https://your-service.railway.app/health"
else
    echo "❌ Found $error_count Railway variable issues"
    echo ""
    echo "🔧 Fix these issues before deploying to Railway"
    exit 1
fi

