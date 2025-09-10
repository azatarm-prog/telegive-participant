# Telegive Participant Service - Deployment Guide

This guide provides step-by-step instructions for deploying the Participant Management Service to Railway with proactive issue prevention.

## 🚀 Pre-Deployment Checklist

Before deploying, run these validation scripts to prevent common deployment issues:

### 1. Pre-Deployment Validation
```bash
# Run comprehensive pre-deployment validation
./scripts/pre-deploy-validate.sh
```

### 2. Requirements Validation
```bash
# Validate all Python requirements
python scripts/validate_requirements.py
```

### 3. Railway Variables Validation
```bash
# Validate Railway environment variable syntax
./scripts/validate-railway-vars.sh
```

## 🛠️ Railway Deployment Steps

### Step 1: Create Railway Project

1. **Go to Railway Dashboard**: https://railway.app/dashboard
2. **Create New Project**: Click "New Project"
3. **Deploy from GitHub**: Select "Deploy from GitHub repo"
4. **Choose Repository**: Select `telegive-participant`
5. **Auto-Detection**: Railway will detect Python and start building

### Step 2: Add Database Services

#### Add PostgreSQL Database
1. **In Railway Project**: Click "New" → "Database" → "Add PostgreSQL"
2. **Railway Creates**: `${{Postgres.DATABASE_PUBLIC_URL}}` variable
3. **Note**: Use `DATABASE_PUBLIC_URL` not `DATABASE_PRIVATE_URL` for external connections

#### Add Redis (Optional)
1. **In Railway Project**: Click "New" → "Database" → "Add Redis"
2. **Railway Creates**: `${{Redis.REDIS_URL}}` variable
3. **Used For**: Rate limiting and caching

### Step 3: Configure Environment Variables

Go to your service → **Settings** → **Variables** tab and add these variables:

```bash
# Service Configuration
SERVICE_NAME=telegive-participant
SERVICE_PORT=8004
SECRET_KEY=participant-secret-key-change-in-production-2024
FLASK_DEBUG=False

# Database - Use Railway PostgreSQL
DATABASE_URL=${{Postgres.DATABASE_PUBLIC_URL}}

# External Services - Update with actual Railway URLs
TELEGIVE_AUTH_URL=https://telegive-auth-production.up.railway.app
TELEGIVE_CHANNEL_URL=https://telegive-channel-production.up.railway.app
TELEGIVE_BOT_URL=https://telegive-bot-production.up.railway.app
TELEGIVE_MEDIA_URL=https://telegive-media-production.up.railway.app
TELEGIVE_GIVEAWAY_URL=https://telegive-giveaway-production.up.railway.app

# External APIs
TELEGRAM_API_BASE=https://api.telegram.org

# Captcha configuration
CAPTCHA_TIMEOUT_MINUTES=10
CAPTCHA_MAX_ATTEMPTS=3
CAPTCHA_MIN_NUMBER=1
CAPTCHA_MAX_NUMBER=10

# Winner selection
SELECTION_METHOD=cryptographic_random
SELECTION_AUDIT_ENABLED=true

# Redis (optional) - Use Railway Redis
REDIS_URL=${{Redis.REDIS_URL}}

# CORS settings
CORS_ORIGINS=*

# Rate limiting
RATELIMIT_DEFAULT=100 per hour

# Logging
LOG_LEVEL=INFO

# Environment
ENVIRONMENT=production
```

### Step 4: Deploy and Get Service URL

1. **Deploy**: Railway will automatically deploy after setting variables
2. **Get URL**: Go to service → **Settings** → **Domains**
3. **Generate Domain**: Click "Generate Domain"
4. **Copy URL**: Copy the generated URL (e.g., `https://telegive-participant-production.up.railway.app`)

### Step 5: Initialize Database

After successful deployment:

```bash
# Initialize database tables
curl -X POST https://your-service-url.railway.app/admin/init-db

# Expected response:
{
  "success": true,
  "message": "Database tables created successfully",
  "service": "participant-service"
}
```

### Step 6: Verify Deployment

```bash
# Check service health
curl https://your-service-url.railway.app/health

# Check database status
curl https://your-service-url.railway.app/admin/db-status

# Check readiness
curl https://your-service-url.railway.app/health/ready
```

## 🔄 Update Other Services

After deploying the Participant Service, update other Telegive services with the new URL:

### Services to Update
- `telegive-auth`
- `telegive-channel`
- `telegive-bot`
- `telegive-media`
- `telegive-giveaway`

### Variable to Update
```bash
TELEGIVE_PARTICIPANT_URL=https://telegive-participant-production.up.railway.app
```

### Update Process
1. Go to each service in Railway
2. Navigate to **Settings** → **Variables**
3. Find `TELEGIVE_PARTICIPANT_URL`
4. Update with the new URL
5. Save changes (service will redeploy automatically)

## 🚨 Common Deployment Issues & Solutions

### Issue 1: Database Connection Failed
**Symptoms**: Health checks fail, 503 errors
**Solution**:
```bash
# Check if DATABASE_URL is set correctly
# Should be: ${{Postgres.DATABASE_PUBLIC_URL}}
# NOT: "${{Postgres.DATABASE_PUBLIC_URL}}" (no quotes)
```

### Issue 2: Tables Not Found
**Symptoms**: Ready check fails, database errors
**Solution**:
```bash
# Initialize database after deployment
curl -X POST https://your-service-url.railway.app/admin/init-db
```

### Issue 3: Service URLs Not Working
**Symptoms**: External service calls fail
**Solution**:
```bash
# Verify all TELEGIVE_*_URL variables are set
# Format: https://telegive-service-production.up.railway.app
# NOT: http://localhost:8001
```

### Issue 4: Import Errors
**Symptoms**: Application fails to start
**Solution**:
```bash
# Run pre-deployment validation locally
./scripts/pre-deploy-validate.sh

# Check requirements
python scripts/validate_requirements.py
```

## 🔍 Health Check Endpoints

The service provides multiple health check endpoints:

### Liveness Check
```bash
curl https://your-service-url.railway.app/health/live
# Returns: {"alive": true, "status": "alive"}
```

### Readiness Check
```bash
curl https://your-service-url.railway.app/health/ready
# Returns: {"status": "ready", "database": "connected", "tables": "initialized"}
```

### Detailed Health Check
```bash
curl https://your-service-url.railway.app/health
# Returns: Comprehensive health status with external service checks
```

## 📊 Monitoring & Maintenance

### Get Service Statistics
```bash
curl https://your-service-url.railway.app/admin/stats
```

### Run Cleanup Tasks
```bash
curl -X POST https://your-service-url.railway.app/admin/cleanup
```

### Check Database Status
```bash
curl https://your-service-url.railway.app/admin/db-status
```

## 🔧 Troubleshooting Commands

### Check Logs in Railway
1. Go to your service in Railway dashboard
2. Click on **Deployments** tab
3. Click on the latest deployment
4. View logs for errors

### Test Locally Before Deployment
```bash
# Set up local environment
cp .env.example .env
# Edit .env with your local database

# Run validation
./scripts/pre-deploy-validate.sh

# Start service
python app.py

# Test endpoints
curl http://localhost:8004/health/live
```

### Validate Configuration
```bash
# Check Railway variables
./scripts/validate-railway-vars.sh

# Check requirements
python scripts/validate_requirements.py
```

## 📋 Post-Deployment Checklist

- [ ] Service deploys successfully
- [ ] Database initializes: `curl -X POST .../admin/init-db`
- [ ] Health checks pass: `curl .../health`
- [ ] All external service URLs updated
- [ ] Other services can reach this service
- [ ] Logs show no errors
- [ ] Statistics endpoint works: `curl .../admin/stats`

## 🆘 Emergency Rollback

If deployment fails:

1. **Check Railway Logs**: Identify the error
2. **Revert Changes**: Use Railway's deployment history
3. **Fix Issues**: Address the root cause
4. **Re-validate**: Run all validation scripts
5. **Re-deploy**: Deploy again after fixes

## 📞 Support

If you encounter issues not covered in this guide:

1. **Check Logs**: Railway dashboard → Service → Deployments → Logs
2. **Run Validations**: All scripts in `/scripts/` directory
3. **Verify Configuration**: Compare with `.env.example`
4. **Test Locally**: Ensure it works locally first

---

**Remember**: Always run the validation scripts before deploying to prevent common issues!

