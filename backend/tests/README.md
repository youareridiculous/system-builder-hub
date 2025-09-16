# SBH Meta-Builder v2 Testing Framework

This directory contains the comprehensive testing framework for SBH Meta-Builder v2, a multi-agent, iterative scaffold generation system.

## Overview

The testing framework provides:

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Load and stress testing
- **Security Tests**: Security and compliance validation
- **Golden Tasks**: Pre-defined test scenarios
- **Coverage Reporting**: Code coverage analysis
- **CI/CD Integration**: Automated testing pipeline

## Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── test_meta_builder_v2.py  # Main test suite
├── run_tests.py             # Test runner script
├── requirements-test.txt    # Testing dependencies
└── README.md               # This file
```

## Quick Start

### 1. Install Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install testing dependencies
pip install -r tests/requirements-test.txt

# Install Playwright browsers (for UI testing)
playwright install --with-deps
```

### 2. Run Tests

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run with coverage
make test-coverage

# Run performance tests
make test-performance

# Run security tests
make test-security
```

### 3. Using the Test Runner

```bash
# Run all tests
python tests/run_tests.py

# Run with coverage and HTML report
python tests/run_tests.py --coverage --html-report

# Run unit tests only
python tests/run_tests.py --unit

# Run integration tests only
python tests/run_tests.py --integration

# Run with verbose output
python tests/run_tests.py --verbose

# Run specific test pattern
python tests/run_tests.py --pattern "test_meta_spec"

# Run in parallel
python tests/run_tests.py --parallel 4
```

## Test Categories

### Unit Tests

Test individual components in isolation:

- **Models**: Data model validation and serialization
- **Agents**: Individual agent functionality
- **Orchestrator**: Core orchestration logic
- **Evaluator**: Evaluation and scoring logic

### Integration Tests

Test complete workflows:

- **API Endpoints**: HTTP API functionality
- **Full Run Workflow**: Complete build process
- **Auto-Fix Workflow**: Failure detection and repair
- **Approval Workflow**: Human review process

### Performance Tests

Load and stress testing:

- **Large Specifications**: Performance with complex specs
- **Concurrent Runs**: Multiple simultaneous builds
- **Memory Usage**: Resource consumption analysis
- **Response Times**: API performance benchmarks

### Security Tests

Security and compliance validation:

- **Input Validation**: Malicious input handling
- **Authentication**: Access control testing
- **Data Protection**: PII and sensitive data handling
- **RBAC Testing**: Role-based access control

## Test Fixtures

The `conftest.py` file provides comprehensive test fixtures:

### Mock Services
- `mock_llm`: Mock LLM client
- `mock_db`: Mock database session
- `mock_redis`: Mock Redis client
- `mock_s3`: Mock S3 client
- `mock_http_client`: Mock HTTP client
- `mock_playwright`: Mock Playwright for UI testing

### Sample Data
- `sample_spec`: CRM specification
- `sample_run`: Test run instance
- `sample_artifacts`: Generated code artifacts
- `sample_evaluation_report`: Test evaluation results
- `lms_spec`: LMS domain specification
- `helpdesk_spec`: Helpdesk domain specification
- `large_spec`: Enterprise-scale specification
- `security_test_spec`: Security-focused specification

## Golden Tasks

The evaluation system includes 30+ pre-defined test scenarios:

### CRUD Operations
- Create, read, update, delete entities
- Bulk operations
- Soft deletes
- Audit logging

### Authentication & Authorization
- User registration and login
- Password management
- Role-based access control
- Multi-factor authentication

### Payment Processing
- Stripe integration
- Payment flow validation
- Refund processing
- Subscription management

### File Management
- Upload and download
- File validation
- Storage integration
- Access control

### Workflow Automation
- State transitions
- Trigger validation
- Scheduled tasks
- Event handling

### AI Features
- Copilot responses
- RAG functionality
- Content generation
- Recommendation systems

## Coverage Reporting

Generate detailed coverage reports:

```bash
# Terminal coverage report
make test-coverage

# HTML coverage report
python tests/run_tests.py --coverage --html-report

# View HTML report
open htmlcov/index.html
```

Coverage includes:
- **Line Coverage**: Percentage of lines executed
- **Branch Coverage**: Conditional branch execution
- **Function Coverage**: Function call coverage
- **Missing Lines**: Lines not covered by tests

## Continuous Integration

GitHub Actions workflow (`.github/workflows/test.yml`):

### Triggers
- Push to main/develop branches
- Pull requests to main branch

### Services
- PostgreSQL 15
- Redis 7
- Multiple Python versions (3.9, 3.10, 3.11)

### Steps
1. **Setup**: Python environment and dependencies
2. **Linting**: Code quality checks
3. **Security**: Security vulnerability scanning
4. **Unit Tests**: Component testing
5. **Integration Tests**: End-to-end testing
6. **Coverage**: Coverage reporting and upload
7. **Performance**: Performance benchmarking
8. **Security Tests**: Security validation

## Debugging Tests

### Verbose Output
```bash
python -m pytest tests/ -v -s
```

### Debug Specific Test
```bash
python -m pytest tests/test_meta_builder_v2.py::TestMetaBuilderV2Models::test_meta_spec_creation -v -s
```

### Debug with PDB
```bash
python -m pytest tests/ --pdb
```

### Debug with IPython
```bash
python -m pytest tests/ --pdbcls=IPython.terminal.debugger:Pdb
```

### Test Isolation
```bash
# Run single test file
python -m pytest tests/test_meta_builder_v2.py

# Run single test class
python -m pytest tests/test_meta_builder_v2.py::TestMetaBuilderV2Models

# Run single test method
python -m pytest tests/test_meta_builder_v2.py::TestMetaBuilderV2Models::test_meta_spec_creation
```

## Performance Testing

### Load Testing
```bash
# Run with locust
locust -f tests/locustfile.py --host=http://localhost:8000
```

### Benchmark Testing
```bash
# Run benchmarks
python -m pytest tests/ -m performance --benchmark-only
```

### Memory Profiling
```bash
# Install memory profiler
pip install memory-profiler

# Run with memory profiling
python -m memory_profiler tests/run_tests.py
```

## Security Testing

### Static Analysis
```bash
# Bandit security scanning
bandit -r src/

# Safety dependency checking
safety check

# Semgrep security scanning
semgrep --config=auto src/
```

### Dynamic Testing
```bash
# Run security tests
make test-security

# OWASP ZAP scanning
zap-baseline.py -t http://localhost:8000
```

## Best Practices

### Writing Tests
1. **Test Naming**: Use descriptive test names
2. **Arrange-Act-Assert**: Structure tests clearly
3. **Test Isolation**: Each test should be independent
4. **Mock External Dependencies**: Don't rely on external services
5. **Use Fixtures**: Leverage pytest fixtures for setup
6. **Test Edge Cases**: Include error conditions and boundaries

### Test Data
1. **Use Realistic Data**: Test with realistic specifications
2. **Vary Test Data**: Test different scenarios and domains
3. **Clean Up**: Ensure test data is cleaned up
4. **Avoid Hardcoding**: Use fixtures and factories

### Performance
1. **Fast Tests**: Keep unit tests fast (< 1 second)
2. **Parallel Execution**: Use pytest-xdist for parallel testing
3. **Resource Management**: Clean up resources properly
4. **Mock Heavy Operations**: Mock database and external calls

### Maintenance
1. **Keep Tests Updated**: Update tests when code changes
2. **Review Coverage**: Maintain high coverage levels
3. **Refactor Tests**: Keep tests clean and maintainable
4. **Document Changes**: Update documentation when needed

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure src is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

#### Database Connection Issues
```bash
# Check database configuration
export DATABASE_URL="postgresql://user:pass@localhost/test_db"
export TESTING=true
```

#### Redis Connection Issues
```bash
# Check Redis configuration
export REDIS_URL="redis://localhost:6379/0"
```

#### Playwright Issues
```bash
# Reinstall Playwright browsers
playwright install --with-deps
```

### Debug Mode
```bash
# Enable debug logging
export META_BUILDER_DEBUG=true
export META_BUILDER_LOG_LEVEL=DEBUG
```

### Test Environment
```bash
# Set test environment
export TESTING=true
export ENVIRONMENT=test
```

## Contributing

### Adding New Tests
1. Create test file in `tests/` directory
2. Follow naming convention: `test_*.py`
3. Use appropriate test markers
4. Add to test suite in `test_meta_builder_v2.py`
5. Update documentation

### Test Guidelines
1. **Coverage**: Aim for >90% code coverage
2. **Performance**: Keep tests fast and efficient
3. **Reliability**: Tests should be deterministic
4. **Maintainability**: Write clear, readable tests
5. **Documentation**: Document complex test scenarios

### Review Process
1. **Code Review**: All tests require code review
2. **CI Checks**: Tests must pass CI pipeline
3. **Coverage**: Maintain or improve coverage
4. **Performance**: No significant performance regression

## Support

For testing-related issues:

1. **Documentation**: Check this README and inline docs
2. **Issues**: Create GitHub issue with test details
3. **Community**: Ask in SBH community forums
4. **Support**: Contact technical support team

## License

This testing framework is part of SBH Meta-Builder v2 and follows the same license terms.
