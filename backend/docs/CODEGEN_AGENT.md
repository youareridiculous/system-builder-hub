# Codegen Agent Guide

This document explains SBH's Codegen Agent system for automated code generation, testing, and deployment.

## Overview

The SBH Codegen Agent provides:

1. **Repository Management**: Local export bundles and GitHub repositories
2. **LLM-Powered Planning**: Natural language goal to code changes
3. **Diff Generation**: Unified diffs with file adds/edits/deletes
4. **Testing & Linting**: Automated test execution and code quality checks
5. **Branch Management**: Automatic branch creation and PR generation
6. **Safety Guardrails**: File access control and security validation

## Repository Sources

### Local Export Bundles

```python
from src.agent_codegen.schema import RepoRef

repo_ref = RepoRef(
    type='local',
    project_id='project-123'
)
```

### GitHub Repositories

```python
repo_ref = RepoRef(
    type='github',
    owner='username',
    repo='repository-name',
    branch='main'
)
```

## Codegen Goals

### Goal Structure

```python
from src.agent_codegen.schema import CodegenGoal

goal = CodegenGoal(
    repo_ref=repo_ref,
    branch_base='main',
    goal_text='Add user authentication endpoints',
    constraints={
        'max_files': 10,
        'test_coverage': 0.8
    },
    allow_paths=['src/**', 'tests/**'],
    deny_globs=['.env', '**/secrets/**'],
    dry_run=True
)
```

### Goal Examples

#### Add API Endpoint
```python
goal = CodegenGoal(
    repo_ref=repo_ref,
    goal_text='Add a new API endpoint for user profile management with GET and PUT methods',
    branch_base='main'
)
```

#### Refactor Code
```python
goal = CodegenGoal(
    repo_ref=repo_ref,
    goal_text='Refactor the authentication module to use JWT tokens instead of sessions',
    branch_base='feature/auth-refactor'
)
```

#### Add Tests
```python
goal = CodegenGoal(
    repo_ref=repo_ref,
    goal_text='Add comprehensive unit tests for the user management module',
    branch_base='main'
)
```

## Planning Process

### LLM-Powered Planning

The codegen agent uses LLM orchestration to:

1. **Analyze Repository**: Scan file structure and content
2. **Generate Plan**: Create structured plan with diffs
3. **Validate Changes**: Check file access permissions
4. **Risk Assessment**: Evaluate change impact

### Plan Structure

```python
from src.agent_codegen.schema import ProposedChange, UnifiedDiff

plan = ProposedChange(
    summary='Add user authentication endpoints',
    diffs=[
        UnifiedDiff(
            file_path='src/auth.py',
            operation='add',
            diff_content='@@ -0,0 +1,50 @@\n+from flask import Blueprint, request, jsonify\n+...',
            new_content='from flask import Blueprint, request, jsonify\n...'
        )
    ],
    risk=RiskLevel.LOW,
    files_touched=['src/auth.py', 'tests/test_auth.py'],
    tests_touched=['tests/test_auth.py']
)
```

## Execution Process

### Execution Pipeline

1. **Workspace Setup**: Create or clone repository
2. **Branch Creation**: Create new feature branch
3. **Patch Application**: Apply unified diffs
4. **Testing**: Run test suite
5. **Linting**: Execute code quality checks
6. **Commit**: Commit changes with descriptive message
7. **Push**: Push branch to remote
8. **PR Creation**: Create pull request

### Execution Results

```python
from src.agent_codegen.schema import ExecutionResult

result = ExecutionResult(
    branch='sbh/codegen-add-auth-20240115-143022',
    commit_sha='abc123...',
    tests=TestResult(passed=5, failed=0, duration=2.3),
    lint=LintResult(ok=True, issues=[]),
    status=ExecutionStatus.APPLIED,
    pr_url='https://github.com/user/repo/pull/123'
)
```

## Safety Guardrails

### File Access Control

#### Default Allow Patterns
- `src/**` - Source code files
- `templates/**` - Template files
- `static/**` - Static assets
- `tests/**` - Test files
- `README.md` - Documentation
- `requirements.txt` - Dependencies
- `Dockerfile` - Container configuration
- `.github/workflows/**` - CI/CD workflows

#### Default Deny Patterns
- `.env` - Environment variables
- `**/secrets/**` - Secret files
- `**/*.pem` - Private keys
- `**/*.key` - API keys
- `**/.ssh/**` - SSH keys
- `**/.aws/**` - AWS credentials
- `**/terraform.tfstate*` - Terraform state

#### Custom Patterns

```python
goal = CodegenGoal(
    repo_ref=repo_ref,
    goal_text='Add feature',
    allow_paths=['custom/**', 'special.py'],
    deny_globs=['**/temp/**', '*.tmp']
)
```

### Validation

```python
from src.agent_codegen.repo import RepoManager

repo_manager = RepoManager()

# Validate file path
is_valid = repo_manager.validate_path(
    'src/main.py',
    allow_paths=['src/**'],
    deny_globs=['**/secrets/**']
)
```

## API Endpoints

### Plan Changes

```http
POST /api/agent/codegen/plan
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "repo_ref": {
    "type": "local",
    "project_id": "project-123"
  },
  "goal_text": "Add user authentication endpoints",
  "branch_base": "main",
  "dry_run": true
}
```

### Apply Changes

```http
POST /api/agent/codegen/apply
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "repo_ref": {
    "type": "local",
    "project_id": "project-123"
  },
  "goal_text": "Add user authentication endpoints",
  "plan": {
    "summary": "Add user authentication endpoints",
    "diffs": [...],
    "risk": "low",
    "files_touched": ["src/auth.py"],
    "tests_touched": ["tests/test_auth.py"]
  }
}
```

### Async Execution

```http
POST /api/agent/codegen/apply/async
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "repo_ref": {...},
  "goal_text": "Add feature",
  "plan": {...}
}
```

### Job Status

```http
GET /api/agent/codegen/status/<job_id>
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

### Validate Goal

```http
POST /api/agent/codegen/validate
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "repo_ref": {...},
  "goal_text": "Add feature",
  "file_paths": ["src/main.py", ".env"]
}
```

## Web Interface

### Usage Flow

1. **Repository Selection**: Choose local export or GitHub repo
2. **Goal Definition**: Enter natural language goal
3. **Configuration**: Set options and access patterns
4. **Plan Generation**: Generate and review proposed changes
5. **Execution**: Apply changes and run tests
6. **Review**: Check results and PR creation

### Features

- **Diff Viewer**: Side-by-side diff visualization
- **Risk Assessment**: Change impact evaluation
- **Test Results**: Automated test execution display
- **Job Management**: Async job monitoring
- **Validation**: Goal and file path validation

## Configuration

### Environment Variables

```bash
# Codegen Agent
FEATURE_CODEGEN_AGENT=true
CODEGEN_MAX_DIFF_FILES=50
CODEGEN_FAIL_ON_TESTS=true

# Repository Access
GITHUB_TOKEN=your_github_token

# LLM Integration
LLM_DEFAULT_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
```

### Feature Flags

- `FEATURE_CODEGEN_AGENT`: Enable/disable codegen agent
- `CODEGEN_MAX_DIFF_FILES`: Maximum files per change
- `CODEGEN_FAIL_ON_TESTS`: Rollback on test failure

## Testing

### Test Execution

The codegen agent automatically:

1. **Install Dependencies**: `pip install -r requirements.txt`
2. **Run Tests**: `python -m pytest -v`
3. **Parse Results**: Extract pass/fail counts
4. **Handle Failures**: Rollback on failure if configured

### Test Results

```python
test_result = TestResult(
    passed=5,
    failed=1,
    duration=2.3,
    output='Test output...',
    error='Test error...'
)
```

### Linting

The agent supports multiple linting tools:

1. **Ruff**: Modern Python linter
2. **Flake8**: Traditional Python linter
3. **Custom Tools**: Extensible linting framework

```python
lint_result = LintResult(
    ok=False,
    issues=[
        {
            'tool': 'flake8',
            'message': 'E501 line too long',
            'severity': 'warning'
        }
    ],
    output='Found 1 linting issue'
)
```

## Security & Privacy

### Token Security

- **GitHub Tokens**: Stored securely in SSM
- **Masked Logging**: Tokens redacted in logs
- **Scope Limitation**: Minimal required permissions

### File Security

- **Access Control**: Granular file permissions
- **Secret Protection**: Automatic sensitive file blocking
- **Validation**: Pre-execution security checks

### Audit Logging

- **Operation Tracking**: All codegen operations logged
- **Change History**: Complete diff and result tracking
- **Tenant Isolation**: Multi-tenant operation separation

## Troubleshooting

### Common Issues

#### Repository Access
```bash
# Check GitHub token
echo $GITHUB_TOKEN

# Test repository access
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/username/repo
```

#### Test Failures
```bash
# Check test environment
python -m pytest --version

# Run tests manually
cd workspace && python -m pytest -v
```

#### Linting Issues
```bash
# Install linting tools
pip install ruff flake8

# Run linting manually
ruff check .
flake8 .
```

### Debug Commands

```bash
# Test repository analysis
python -c "
from src.agent_codegen.planner import CodegenPlanner
planner = CodegenPlanner()
repo_context = planner._analyze_repository(Path('tests/fixtures/sample_repo'))
print(f'Files: {len(repo_context[\"files\"])}')
"

# Test goal validation
python -c "
from src.agent_codegen.schema import CodegenGoal, RepoRef
goal = CodegenGoal(repo_ref=RepoRef(type='local', project_id='test'), goal_text='test')
print('Goal valid')
"
```

### Error Handling

#### Validation Errors
```json
{
  "error": "Invalid file path: .env",
  "details": {
    "file_path": ".env",
    "denied_by": ".env"
  }
}
```

#### Execution Errors
```json
{
  "error": "Tests failed, changes rolled back",
  "details": {
    "tests_passed": 3,
    "tests_failed": 1,
    "status": "rolled_back"
  }
}
```

## Best Practices

### Goal Definition

1. **Be Specific**: Clear, actionable goals
2. **Include Context**: Relevant background information
3. **Specify Constraints**: File limits, test requirements
4. **Use Examples**: Reference existing patterns

### Repository Management

1. **Clean Workspaces**: Regular cleanup of temporary files
2. **Branch Naming**: Descriptive branch names
3. **Commit Messages**: Clear, descriptive commits
4. **PR Descriptions**: Comprehensive change documentation

### Security

1. **Access Control**: Use allow/deny patterns
2. **Token Management**: Secure credential storage
3. **Validation**: Pre-execution security checks
4. **Audit Logging**: Complete operation tracking

### Testing

1. **Test Coverage**: Ensure adequate test coverage
2. **Test Quality**: Write meaningful tests
3. **Test Isolation**: Independent test execution
4. **Failure Handling**: Graceful test failure handling

## Future Enhancements

### Planned Features

1. **Advanced LLM Integration**: Multi-step reasoning
2. **Custom Tools**: Plugin architecture for tools
3. **Batch Operations**: Multiple goal execution
4. **Advanced Testing**: Integration and E2E tests
5. **Code Review**: Automated code review integration

### Advanced Options

1. **Template System**: Reusable goal templates
2. **Workflow Integration**: CI/CD pipeline integration
3. **Collaboration**: Multi-user codegen sessions
4. **Analytics**: Advanced usage analytics
5. **Custom Validators**: Extensible validation framework
