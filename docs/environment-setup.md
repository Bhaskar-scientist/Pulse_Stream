# Environment Setup Guide

This guide explains how to set up environment configuration for PulseStream across different deployment scenarios.

## Quick Setup

### 1. Development Environment

```bash
# Run the setup script
poetry run python scripts/setup_env.py setup --environment development

# Or manually copy and edit
cp env-example .env
# Edit .env with your values
```

### 2. Production Environment

```bash
# Use production template
poetry run python scripts/setup_env.py setup --environment production

# Or manually
cp .env.production .env
# Edit with production values
```

### 3. Test Environment

```bash
# Use test template
poetry run python scripts/setup_env.py setup --environment test

# Or manually
cp .env.test .env
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `development` |
| `SECRET_KEY` | JWT signing key | `your-secret-key` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | Celery message broker | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery result storage | `redis://localhost:6379/2` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `SMTP_HOST` | Email server host | - |
| `SMTP_USERNAME` | Email username | - |
| `SMTP_PASSWORD` | Email password | - |
| `SLACK_WEBHOOK_URL` | Slack webhook for alerts | - |
| `OPENAI_API_KEY` | OpenAI API key (Phase 2) | - |

## Environment-Specific Configurations

### Development
- Uses local PostgreSQL and Redis
- Debug logging enabled
- CORS allows localhost origins
- File-based logging

### Production
- Uses external database services
- INFO level logging
- Restricted CORS origins
- Structured JSON logging
- Rate limiting enabled

### Test
- Uses test databases (separate Redis DBs)
- Debug logging
- External services disabled
- Mock configurations

## Validation

Check your environment configuration:

```bash
# Validate current .env file
poetry run python scripts/setup_env.py validate

# Show current configuration (secrets hidden)
poetry run python scripts/setup_env.py show
```

## Security Notes

### Secret Key
- Must be at least 32 characters
- Use `secrets.token_urlsafe(32)` to generate
- Different for each environment
- Never commit to version control

### Database Credentials
- Use environment variables
- Different users for dev/prod
- Restrict database permissions

### API Keys
- Store in environment variables
- Use different keys for dev/prod
- Rotate regularly

## Docker Environment

When using Docker Compose, environment variables are set in the compose file:

```yaml
environment:
  - ENVIRONMENT=development
  - SECRET_KEY=dev-secret-key
  - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/pulsestream_dev
```

## Common Issues

### 1. Missing .env file
```bash
Error: Settings validation error for ENVIRONMENT
```
**Solution:** Run `poetry run python scripts/setup_env.py setup`

### 2. Weak secret key
```bash
⚠️ Weak configuration: SECRET_KEY
```
**Solution:** Generate a stronger key using the setup script

### 3. Database connection issues
```bash
Error: could not connect to server
```
**Solution:** Check DATABASE_URL format and ensure PostgreSQL is running

### 4. Redis connection issues
```bash
Error: Connection refused (redis)
```
**Solution:** Check REDIS_URL and ensure Redis is running

## Environment Templates

### Local Development
```env
ENVIRONMENT=development
SECRET_KEY=dev-generated-secret-key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/pulsestream_dev
REDIS_URL=redis://localhost:6379/0
DEBUG=true
LOG_LEVEL=DEBUG
```

### Docker Development
```env
ENVIRONMENT=development
SECRET_KEY=dev-generated-secret-key
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/pulsestream_dev
REDIS_URL=redis://redis:6379/0
DEBUG=true
LOG_LEVEL=DEBUG
```

### Production
```env
ENVIRONMENT=production
SECRET_KEY=production-secret-key-very-long-and-secure
DATABASE_URL=postgresql://user:pass@prod-db.amazonaws.com:5432/pulsestream
REDIS_URL=redis://prod-redis.cache.amazonaws.com:6379/0
DEBUG=false
LOG_LEVEL=INFO
SMTP_HOST=smtp.sendgrid.net
SMTP_USERNAME=apikey
SMTP_PASSWORD=sendgrid-api-key
EMAIL_FROM=alerts@yourcompany.com
```
