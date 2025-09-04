# System Builder Hub - Local Development Guide

## 🚀 Quick Start

Your System Builder Hub is now running locally!

### Server Status
- **URL**: http://localhost:5001
- **Status**: ✅ Running
- **Environment**: Development mode with debug enabled

### Key Endpoints
- **Dashboard**: http://localhost:5001/
- **Health Check**: http://localhost:5001/healthz
- **API Documentation**: http://localhost:5001/openapi.json
- **Metrics**: http://localhost:5001/metrics

## 🛠️ Development Commands

### Start/Stop Server
```bash
# Start server (if not running)
python src/cli.py run --port 5001 --debug

# Stop server
Ctrl+C (in terminal where server is running)
```

### Database Operations
```bash
# Check migration status
cd src/db_migrations && alembic current

# Apply migrations
cd src/db_migrations && alembic upgrade head
```

### API Testing
```bash
# Health check
curl http://localhost:5001/healthz

# List all routes
python src/cli.py dump-routes

# Test protected endpoint
curl http://localhost:5001/api/builder/projects
```

## 📁 Project Structure
```
backend/
├── src/                    # Main application code
│   ├── app.py             # Flask application
│   ├── cli.py             # Command line interface
│   ├── config.py          # Configuration
│   └── [P1-P65 modules]   # Feature implementations
├── tests/                 # Test files
├── migrations/            # Database migrations
└── requirements.txt       # Python dependencies
```

## 🔧 Configuration

### Environment Variables
The app uses these key environment variables:
- `FLASK_ENV`: Set to 'development' for debug mode
- `DATABASE_URL`: SQLite database path
- `ENABLE_FEATURE_FLAGS`: Feature flag system
- `ENABLE_IDEMPOTENCY`: Idempotency protection

### Database
- **Type**: SQLite (development)
- **File**: `system_builder_hub.db`
- **Migrations**: Alembic managed

## 🧪 Testing

### Run Tests
```bash
# Install pytest (if needed)
pip install pytest

# Run tests
python -m pytest tests/
```

### Manual Testing
1. Open http://localhost:5001/ in browser
2. Check API docs at http://localhost:5001/openapi.json
3. Test endpoints with curl or Postman

## 🐛 Debugging

### Logs
Server logs are displayed in the terminal where you started the server.

### Common Issues
1. **Port already in use**: Change port with `--port 5002`
2. **Import errors**: Ensure you're in the backend directory
3. **Database issues**: Run `alembic upgrade head`

## 📚 API Documentation

The API is fully documented with OpenAPI/Swagger:
- **Interactive Docs**: http://localhost:5001/openapi.json
- **Total Endpoints**: 219 routes across all P1-P65 features
- **Authentication**: JWT-based with RBAC
- **Security**: CSRF protection, rate limiting

## 🎯 Next Steps

1. **Explore the Dashboard**: Visit http://localhost:5001/
2. **Review API Docs**: Check http://localhost:5001/openapi.json
3. **Test Features**: Try different endpoints
4. **Development**: Start building new features!

---

**Happy Coding! 🚀**
