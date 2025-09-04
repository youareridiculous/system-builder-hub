# Environment Variables

This document describes all environment variables used by System Builder Hub.

## Required Variables

### `LLM_SECRET_KEY`
- **Description**: 32-byte encryption key for LLM provider secrets (base64-encoded)
- **Format**: 44-character base64 string
- **Example**: `AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=`
- **Security**: Required in production, auto-generated in development

### `FLASK_ENV`
- **Description**: Flask environment mode
- **Values**: `development`, `production`, `staging`
- **Default**: `development`

## Database Configuration

### `DATABASE_URL`
- **Description**: Database connection string
- **Default**: `sqlite:///./db/sbh.db`
- **Examples**: 
  - SQLite: `sqlite:///./db/sbh.db`
  - PostgreSQL: `postgresql://user:pass@localhost/sbh`

## LLM Configuration

### `FEATURE_LLM_API`
- **Description**: Enable/disable LLM API endpoints
- **Values**: `true`, `false`
- **Default**: `true`
- **Note**: When disabled, LLM endpoints return 404 and readiness shows "disabled"

## Server Configuration

### `SBH_PORT`
- **Description**: Port for the Flask application
- **Default**: `5001`
- **Range**: 1024-65535

## CORS Configuration

### `CORS_ORIGINS`
- **Description**: Comma-separated list of allowed CORS origins
- **Default**: `http://localhost:5001`
- **Example**: `http://localhost:3000,https://app.example.com`

## Optional Configuration

### `SENTRY_DSN`
- **Description**: Sentry DSN for error tracking
- **Default**: Not set
- **Format**: `https://key@sentry.io/project`

### `LOG_LEVEL`
- **Description**: Logging level
- **Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **Default**: `INFO`

## Security Notes

- `LLM_SECRET_KEY` must be kept secure and rotated regularly
- In production, all secrets should be stored in a secure vault
- CORS origins should be restricted to trusted domains
- Database URLs should use encrypted connections in production
