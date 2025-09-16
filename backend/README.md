# System Builder Hub

A powerful, AI-driven system building platform with Co-Builder for automated code generation and application.

## Quickstart (CLI)

### Install

```bash
# From the backend directory
pip install -r requirements.txt
```

### Run CLI

```bash
# Apply a code change directly
python -m src.cobuilder.cli apply \
  --message "Create src/venture_os/__init__.py with __version__ = \"0.0.1\"" \
  --tenant demo --json

# Dry-run to see planned changes
python -m src.cobuilder.cli apply \
  --message "Add README.md with project overview" \
  --tenant demo --dry-run --json

# Use convenience script
./scripts/cob_apply.sh
```

### CLI Options

- `--message`: Change description (required)
- `--tenant`: Tenant ID (default: demo)
- `--project-root`: Project root path (default: auto-detect)
- `--path`: Explicit target file path (optional)
- `--dry-run`: Show planned change without applying
- `--json`: Output machine-readable JSON
- `--verbose`: Verbose output

## Server

### Start Server

```bash
# From the project root
python -m src.server
```

### Port Management

If port 5001 is in use, run:
```bash
./scripts/kill_5001.sh
```

### Verify Server

```bash
# Health check
curl http://127.0.0.1:5001/api/health

# Run smoke tests
./scripts/smoke_server.sh
```

## Venture OS Build Protocol

### Step-1: Scaffold Initialization ✅

**Status**: COMPLETED

**Command Executed**:
```bash
python -m src.cobuilder.cli apply \
  --message "Venture OS — Entity Management v1.0.1 (Step-1): create project root and seed a minimal scaffolding marker. Create file venture_os/README.md with a single line: \"Venture OS — Entity Management v1.0.1 (scaffold initialized)\" Additive single-file change. Multi-tenant + RBAC remains a future step. Keep this step tiny." \
  --tenant demo --json
```

**Result**:
- File: `src/venture_os/README.md`
- Content: "Venture OS — Entity Management v1.0.1 (scaffold initialized)"
- Bytes written: 63
- SHA256: `53733386b04f904852426698c557bf14ce52ddb73d8a90956aff85577ee44ee8`

**Next Steps**:
- Multi-tenant architecture design
- RBAC implementation
- Entity management core

### Build Workflow

1. **Propose** → Use `--dry-run` to see planned changes
2. **Implement** → Apply changes with CLI or server
3. **Smoke** → Run tests to verify functionality
4. **Summarize** → Document changes and next steps
5. **Track TODO** → Maintain build progress

## File Locations

- **Working Directory**: Repository root (where you run `python -m src.server`)
- **Generated Files**: Written under `src/` directory
- **Finder Path**: Check `src/venture_os/` for Venture OS files

## Features

### Co-Builder Apply Engine

- **Robust Content Generation**: Handles any LLM response format
- **Safe File Operations**: Path validation, SHA256 verification
- **Fallback Mechanisms**: JSON mode, fenced-JSON extraction, diff reconstruction
- **CLI Interface**: Direct access without server complexity

### Server Endpoints

- `/api/health` - Health check
- `/api/cobuilder/ask` - Generate and optionally apply changes
- `/api/cobuilder/files/inspect` - Inspect generated files

## Development

### Testing

```bash
# CLI tests
./scripts/cob_apply.sh

# Server tests
./scripts/smoke_server.sh

# Port cleanup
./scripts/kill_5001.sh
```

### Environment Variables

- `COBUILDER_USE_JSON_MODE`: Enable/disable strict JSON mode (default: 1)
- `PORT`: Server port (default: 5001)
- `FLASK_ENV`: Development mode (default: development)

## Architecture

- **Generator**: Robust LLM integration with fallback mechanisms
- **Applier**: Safe file operations with validation
- **CLI**: Direct command-line interface
- **Server**: HTTP API with Flask
- **Blueprints**: Modular endpoint organization

## Troubleshooting

### Common Issues

1. **Port 5001 in use**: Run `./scripts/kill_5001.sh`
2. **Import errors**: Ensure you're running from the correct directory
3. **Content empty**: Check `COBUILDER_USE_JSON_MODE` environment variable

### Debug Mode

```bash
# Enable verbose CLI output
python -m src.cobuilder.cli apply --message "test" --verbose

# Check server logs
tail -f /tmp/cobuilder.log
```

## Full Build: CLI (Start → Kickoff → Watch)

Prereqs: jq, curl, macOS textutil for .docx (or use .md/.txt).

Commands:

```bash
# 1) Start server (persist builds; no reloader)
scripts/start_server.sh

# 2) Kickoff a full build from a docx/markdown/text prompt
scripts/kickoff_full_build.sh ~/Downloads/AI\ Website\ Builder\ System.docx demo

# 3) Watch progress (option A: pass id from kickoff output)
scripts/watch_build.sh build_demo_1234567890 demo

# 3) Watch progress (option B: watch newest)
scripts/watch_build.sh --latest demo
```

Notes:

- Uses X-Tenant-ID header; default is demo.
- If you see "Build not found", ensure the server was started with persistence/no-reload (the script already does that).
- Scripts use mktemp + cleanup via trap; no files left in /tmp.
