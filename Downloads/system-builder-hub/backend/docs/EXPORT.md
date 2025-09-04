# Project Export Guide

This document explains SBH's project export system, including ZIP artifact generation, GitHub sync, and CI bootstrap capabilities.

## Overview

The SBH Export system provides:

1. **Project Bundling**: Complete standalone application export
2. **GitHub Sync**: Repository creation and branch management
3. **CI Bootstrap**: GitHub Actions workflow generation
4. **Infrastructure**: Docker, AWS, and Terraform configurations

## Export Bundle Structure

### Generated Files

```
.
├── app/                  # Flask application
│   ├── __init__.py      # Flask app factory
│   ├── routes.py        # API routes
│   ├── models.py        # Database models
│   ├── templates/       # HTML templates
│   └── static/          # Static files
├── requirements.txt     # Python dependencies
├── wsgi.py             # WSGI entry point
├── gunicorn.conf.py    # Gunicorn configuration
├── Dockerfile          # Docker container
├── .github/
│   └── workflows/
│       └── ci.yml      # CI/CD pipeline
├── README.md           # Project documentation
├── .env.sample         # Environment variables
└── export_manifest.json # Export metadata
```

### Infrastructure Files (Optional)

```
.
├── Dockerrun.aws.json  # AWS Elastic Beanstalk
├── .ebextensions/      # EB configuration
└── deploy/
    └── terraform/      # Terraform templates
```

## Export Service

### Materialize Build

```python
from src.exporter.service import ExportService

service = ExportService()
bundle = service.materialize_build(
    project_id='project-123',
    tenant_id='tenant-456',
    include_runtime=True
)
```

### Create ZIP Archive

```python
zip_buffer = service.zip_bundle(bundle)
# Returns BytesIO with ZIP content
```

### Generate Diff

```python
diff = service.diff_bundle(prev_manifest, new_manifest)
# Returns ExportDiff with added/removed/changed files
```

## GitHub Integration

### Repository Management

```python
from src.vcs.github_service import GitHubService

github = GitHubService()

# Ensure repository exists
repo = github.ensure_repo('owner', 'repo-name', private=True)

# Sync branch
result = github.sync_branch(
    owner='owner',
    repo='repo-name',
    branch='feature-branch',
    bundle=export_bundle,
    commit_message='Update from SBH'
)
```

### Authentication

#### Personal Access Token (PAT)
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

#### GitHub App
```bash
export GITHUB_APP_ID=12345
export GITHUB_INSTALLATION_ID=67890
```

#### Tenant-Specific Tokens
```bash
# Stored in SSM Parameter Store
/tenant/{tenant_id}/github_token
```

### Repository Structure

The GitHub sync creates:

1. **Repository**: Creates if doesn't exist
2. **Branch**: Creates or updates branch
3. **Files**: Uploads all bundle files
4. **Commit**: Creates commit with message
5. **Pull Request**: Opens PR if branch ≠ default

## API Endpoints

### Plan Export
```http
POST /api/export/plan
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "project_id": "project-123",
  "include_runtime": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "manifest": {
      "project_id": "project-123",
      "files": [...],
      "total_size": 1024,
      "checksum": "abc123..."
    },
    "files_count": 15,
    "total_size": 1024
  }
}
```

### Download Archive
```http
POST /api/export/archive
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "project_id": "project-123",
  "include_runtime": true
}
```

**Response:** ZIP file download

### GitHub Sync
```http
POST /api/export/github/sync
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "project_id": "project-123",
  "owner": "username",
  "repo": "repo-name",
  "branch": "sbh-sync-20240115-143022",
  "sync_mode": "replace_all",
  "include_runtime": true,
  "dry_run": false
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "repo_url": "https://github.com/username/repo-name",
    "branch": "sbh-sync-20240115-143022",
    "commit_sha": "abc123...",
    "pr_url": "https://github.com/username/repo-name/pull/123",
    "files_count": 15,
    "total_size": 1024
  }
}
```

## CI/CD Pipeline

### GitHub Actions Workflow

The generated `.github/workflows/ci.yml` includes:

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Lint with flake8
      run: |
        pip install flake8
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    - name: Test with pytest
      run: |
        pip install pytest
        pytest -q
    - name: Build Docker image
      if: env.CI_BUILD_IMAGE == 'true'
      run: |
        docker build -t your-app .
```

### Customization

Enable Docker builds:
```bash
export CI_BUILD_IMAGE=true
```

## Configuration

### Environment Variables

```bash
# Enable export features
FEATURE_EXPORT=true
FEATURE_EXPORT_GITHUB=true

# Export options
EXPORT_INCLUDE_INFRA=true
EXPORT_MAX_SIZE_MB=200

# GitHub configuration
GITHUB_APP_ID=
GITHUB_INSTALLATION_ID=
GITHUB_TOKEN=

# Tenant GitHub allowlist (optional)
TENANT_GH_ALLOW=["org1/*", "me/myrepo"]
```

### Feature Flags

- `FEATURE_EXPORT`: Enable/disable export functionality
- `FEATURE_EXPORT_GITHUB`: Enable/disable GitHub sync
- `EXPORT_INCLUDE_INFRA`: Include infrastructure files
- `EXPORT_MAX_SIZE_MB`: Maximum archive size limit

## Security & Hardening

### Token Security

- **Never log tokens**: Tokens are masked in logs (last 4 chars)
- **SSM Integration**: Tenant-specific tokens stored in SSM
- **Scope Limitation**: Use fine-grained GitHub permissions

### Repository Validation

```python
# Validate repository names
pattern = r'^[A-Za-z0-9._/-]{1,200}$'
```

### Size Limits

- **Archive Limit**: 200MB maximum (configurable)
- **File Limits**: 5MB per file (GitHub API limit)
- **Memory Limits**: Streaming ZIP generation

### Rate Limiting

- **GitHub API**: Automatic rate limit handling
- **Backoff Strategy**: Exponential backoff on failures
- **Queue Management**: Background job processing

## Usage Examples

### Export Project

```python
from src.exporter.service import ExportService

service = ExportService()

# Generate export bundle
bundle = service.materialize_build(
    project_id='my-project',
    tenant_id='my-tenant',
    include_runtime=True
)

# Create ZIP archive
zip_buffer = service.zip_bundle(bundle)

# Save to file
with open('export.zip', 'wb') as f:
    f.write(zip_buffer.getvalue())
```

### Sync to GitHub

```python
from src.vcs.github_service import GitHubService

github = GitHubService()

# Sync project to GitHub
result = github.sync_branch(
    owner='myusername',
    repo='my-app',
    branch='sbh-sync-20240115',
    bundle=export_bundle,
    commit_message='Deploy from SBH',
    sync_mode='replace_all'
)

print(f"Repository: {result['repo_url']}")
print(f"Branch: {result['branch']}")
if result['pr_url']:
    print(f"Pull Request: {result['pr_url']}")
```

### Web Interface

```javascript
// Plan export
const response = await fetch('/api/export/plan', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Tenant-Slug': tenant
    },
    body: JSON.stringify({
        project_id: 'my-project',
        include_runtime: true
    })
});

const data = await response.json();
console.log(`Files: ${data.data.files_count}`);
console.log(`Size: ${data.data.total_size} bytes`);

// Download ZIP
const zipResponse = await fetch('/api/export/archive', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Tenant-Slug': tenant
    },
    body: JSON.stringify({
        project_id: 'my-project',
        include_runtime: true
    })
});

const blob = await zipResponse.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'my-project-export.zip';
a.click();
```

## Troubleshooting

### Common Issues

#### GitHub Token Issues
```bash
# Check token permissions
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/user

# Verify repository access
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/owner/repo
```

#### Export Size Limits
```bash
# Check bundle size
ls -lh export.zip

# Reduce size by excluding files
include_runtime: false
include_infra: false
```

#### Rate Limiting
```bash
# Check rate limit status
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/rate_limit
```

### Debug Commands

```bash
# Test export service
python -c "
from src.exporter.service import ExportService
service = ExportService()
bundle = service.materialize_build('test-project', 'test-tenant')
print(f'Files: {len(bundle.files)}')
print(f'Size: {bundle.manifest.total_size}')
"

# Test GitHub service
python -c "
from src.vcs.github_service import GitHubService
github = GitHubService()
repo = github.get_repo_stats('username', 'repo')
print(f'Repo: {repo[\"full_name\"]}')
"
```

### Error Handling

#### Network Errors
- Automatic retry with exponential backoff
- Structured error responses
- No secret leakage in logs

#### Validation Errors
```json
{
  "error": "Invalid repository name",
  "details": {
    "field": "repo",
    "value": "invalid@repo",
    "pattern": "^[A-Za-z0-9._/-]{1,200}$"
  }
}
```

#### Size Limit Errors
```json
{
  "error": "Archive size exceeds limit",
  "details": {
    "size": 250000000,
    "limit": 209715200,
    "files_count": 150
  }
}
```

## Best Practices

### Export Optimization

1. **Selective Export**: Only include necessary files
2. **Size Management**: Monitor bundle sizes
3. **Incremental Sync**: Use incremental mode for updates
4. **Dry Runs**: Test with dry_run before actual sync

### GitHub Integration

1. **Repository Naming**: Use descriptive names
2. **Branch Strategy**: Use feature branches for changes
3. **Pull Requests**: Review changes before merging
4. **Token Security**: Use minimal required permissions

### CI/CD Pipeline

1. **Test Coverage**: Ensure comprehensive testing
2. **Security Scanning**: Add security checks to CI
3. **Deployment Gates**: Use deployment approvals
4. **Monitoring**: Add application monitoring

## Analytics & Monitoring

### Export Events

- `export.plan` - Export planning
- `export.archive` - ZIP download
- `export.github.sync` - GitHub sync

### Event Properties

```json
{
  "project_id": "project-123",
  "files_count": 15,
  "total_size": 1024,
  "include_runtime": true,
  "sync_mode": "replace_all",
  "dry_run": false
}
```

### Health Checks

```json
{
  "export": {
    "configured": true,
    "ok": true,
    "github_enabled": true,
    "last_export": "2024-01-15T14:30:22Z"
  }
}
```

## Future Enhancements

### Planned Features

1. **GitLab Integration**: Support for GitLab repositories
2. **Azure DevOps**: Azure DevOps pipeline integration
3. **Custom CI**: Configurable CI/CD templates
4. **Artifact Storage**: Cloud storage integration
5. **Incremental Sync**: Smart file change detection

### Advanced Options

1. **Multi-Environment**: Staging/production deployments
2. **Rollback Support**: Automatic rollback capabilities
3. **Health Checks**: Application health monitoring
4. **Metrics Collection**: Performance metrics
5. **Security Scanning**: Automated security checks
