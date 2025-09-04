# Docker Setup Guide

This guide explains how to run the CRM Flagship application using Docker.

## Prerequisites

- Docker
- Docker Compose

## Quick Start

### One-Command Demo Setup
```bash
# Start everything with one command
docker-compose up -d

# Access the application
# Frontend: http://localhost:5174
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Health Check: http://localhost:8000/health

# Demo users (pre-seeded)
# Owner: owner@sbh.dev / Owner!123
# Admin: admin@sbh.dev / Admin!123
# Sales: sales@sbh.dev / Sales!123
# ReadOnly: readonly@sbh.dev / ReadOnly!123

# Run smoke test to verify everything works
make smoke
```

### Production Setup
1. **Clone or download the template**

2. **Set up environment variables**
   ```bash
   # Create .env file
   cp .env.example .env
   
   # Edit .env with your configuration
   AUTH_SECRET=your-super-secret-jwt-key-here
   DATABASE_URL=sqlite:///data/app.db
   SENDGRID_API_KEY=SG.your-sendgrid-api-key  # Optional
   TWILIO_ACCOUNT_SID=ACyour-twilio-account-sid  # Optional
   TWILIO_AUTH_TOKEN=your-twilio-auth-token  # Optional
   ENVIRONMENT=production
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - **Frontend**: http://localhost:5174
   - **Backend API**: http://localhost:8000
   - **API Docs**: http://localhost:8000/docs
   - **Health Check**: http://localhost:8000/health

## Services

### Backend (FastAPI)
- **Port**: 8000
- **Health Check**: `/health`
- **API Documentation**: `/docs`
- **Database**: SQLite (persisted in `./backend/data`)

### Frontend (React + Vite)
- **Port**: 5174
- **Development Server**: Hot reload enabled
- **API Proxy**: Routes API calls to backend

### Reverse Proxy (Nginx)
- **Port**: 3000
- **Routes**: 
  - `/api/*` → Backend
  - `/docs` → Backend
  - `/health` → Backend
  - `/*` → Frontend

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_SECRET` | Yes | - | JWT signing secret |
| `DATABASE_URL` | No | `sqlite:///data/app.db` | Database connection string |
| `SENDGRID_API_KEY` | No | - | SendGrid API key for email |
| `TWILIO_ACCOUNT_SID` | No | - | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | No | - | Twilio auth token |
| `VITE_API_URL` | No | `http://localhost:8000` | Backend API URL |

## Development

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f proxy
```

### Stop services
```bash
docker-compose down
```

### Rebuild services
```bash
docker-compose build
docker-compose up -d
```

### Reset everything
```bash
docker-compose down -v
docker-compose up -d
```

## Troubleshooting

### Port conflicts
If ports 3000, 5174, or 8000 are already in use:
```bash
# Edit docker-compose.yml to use different ports
ports:
  - "3001:80"  # Change 3000 to 3001
```

### Database issues
```bash
# Remove database volume and restart
docker-compose down -v
docker-compose up -d
```

### Build issues
```bash
# Clean build
docker-compose build --no-cache
docker-compose up -d
```

## Production Considerations

For production deployment:

1. **Use production images**
   - Build optimized frontend with `npm run build`
   - Use production-grade web server (nginx, Apache)

2. **Environment variables**
   - Use strong `AUTH_SECRET`
   - Configure real provider credentials
   - Use production database (PostgreSQL, MySQL)

3. **Security**
   - Enable HTTPS
   - Configure CORS properly
   - Use secrets management

4. **Monitoring**
   - Add logging
   - Configure health checks
   - Set up monitoring/alerting

## Health Checks

The application includes health checks:
- **Backend**: `curl http://localhost:8000/health`
- **Docker**: `docker-compose ps`

All services should show "healthy" status when running properly.
