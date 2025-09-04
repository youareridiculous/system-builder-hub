# SBH Startup Instructions

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

3. **Set Python path:**
   ```bash
   export PYTHONPATH=.
   ```

4. **Start the server:**
   ```bash
   python cli.py run
   ```

## Development Mode

For development with auto-reload:
```bash
export PYTHONPATH=.
python cli.py run --debug
```

## Verification

After startup, verify these endpoints are live:

- **Health Check:** http://localhost:5001/healthz
- **Metrics:** http://localhost:5001/metrics  
- **OpenAPI Docs:** http://localhost:5001/openapi.json
- **Dashboard:** http://localhost:5001/dashboard
- **LLM Setup:** http://localhost:5001/ui/build

## Troubleshooting

### Import Errors
If you get import errors:
```bash
export PYTHONPATH=.
python cli.py run
```

### Port Already in Use
If port 5001 is busy:
```bash
python cli.py run --port 5002
```

### Database Issues
If database errors occur:
```bash
alembic upgrade head
```

## Environment Variables

Optional environment variables:
- `FLASK_ENV=development` - Enable debug mode
- `SBH_BOOT_MODE=safe` - Safe boot mode (default)
- `LLM_PROVIDER=openai` - Default LLM provider
- `LLM_API_KEY=your-key` - LLM API key

## CLI Commands

- `python cli.py run` - Start server
- `python cli.py doctor` - Run diagnostics
- `python cli.py smoke` - Run smoke tests
