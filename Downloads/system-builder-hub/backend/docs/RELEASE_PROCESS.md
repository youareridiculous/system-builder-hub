# Release Process

This document describes the release process for System Builder Hub, including Release Candidates (RC) and General Availability (GA) releases.

## Release Candidate (RC) Process

### 1. Creating a Release Candidate

```bash
# Create and push an RC tag
make rc TAG=v1.2.0-rc1
```

This command will:
- Run all tests (unit + integration)
- Run linting checks
- Create a VERSION file
- Create and push a git tag
- Trigger the CI/CD pipeline

### 2. CI/CD Pipeline

The RC pipeline (`.github/workflows/release.yml`) runs on tags matching `v*-rc*`:

1. **Lint Job**: Runs flake8, black, isort, and mypy
2. **Test Job**: Runs unit and integration tests
3. **Smoke Test Job**: Optional, runs only if `RUN_SMOKE=true` or `SMOKE_BASE_URL` is set
4. **Build Job**: Creates Docker image and uploads as artifact
5. **Release Job**: Creates GitHub Release (draft) with changelog

### 3. Smoke Testing

Smoke tests are opt-in and can be run in several ways:

```bash
# Run locally
RUN_SMOKE=true python -m pytest tests/smoke/

# Run against staging
SMOKE_BASE_URL=https://staging.example.com python -m pytest tests/smoke/

# Run in CI (set GitHub variable)
RUN_SMOKE=true
```

### 4. Staging Deployment

After RC is created:

1. Deploy to staging environment
2. Run smoke tests against staging
3. Verify Meta-Builder v3 functionality
4. Test feature flags and settings

## General Availability (GA) Process

### 1. Promoting RC to GA

```bash
# Create GA tag from RC
git tag v1.2.0 v1.2.0-rc1
git push origin v1.2.0
```

### 2. Production Deployment

1. Deploy to production environment
2. Enable Meta-Builder v3 for production tenants
3. Monitor metrics and logs
4. Verify functionality

### 3. Feature Flag Management

- **Staging**: `FEATURE_META_V3_AUTOFIX=true` (default)
- **Production**: `FEATURE_META_V3_AUTOFIX=false` (default, enable per tenant)

## Versioning

- **RC**: `vX.Y.Z-rcN` (e.g., `v1.2.0-rc1`)
- **GA**: `vX.Y.Z` (e.g., `v1.2.0`)

## Rollback Process

If issues are discovered:

1. Disable feature flags for affected tenants
2. Rollback to previous version if necessary
3. Investigate and fix issues
4. Create new RC with fixes

## Monitoring

Monitor the following during releases:

- Auto-fix success ratio
- Error rates
- Performance metrics
- User feedback
- System logs
