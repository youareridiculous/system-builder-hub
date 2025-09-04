# Evaluation Lab v1

A comprehensive benchmarking system for System Builder Hub that runs benchmarks on a schedule and on PRs, computes quality/latency/cost KPIs, enforces regression gates in CI, respects Privacy Modes, and provides dashboards/reports.

## Overview

The Evaluation Lab provides:

- **Golden Test Cases**: Predefined test scenarios with expected outcomes
- **Scenario Bundles**: Multi-step evaluation workflows
- **KPI Guards**: Automated quality gates and regression detection
- **Cost Tracking**: Detailed cost analysis and budgeting
- **Privacy Compliance**: Respects privacy modes and data governance
- **CI/CD Integration**: Automated evaluation on PRs and nightly builds
- **Observability**: Comprehensive metrics and reporting

## Architecture

### Core Components

1. **Specs** (`src/eval_lab/specs.py`)
   - Defines schemas for `GoldenCase`, `ScenarioBundle`, `KPIGuard`
   - YAML-based suite configuration
   - SLA classes (fast, normal, thorough)

2. **Runner** (`src/eval_lab/runner.py`)
   - Main orchestrator for evaluation execution
   - Handles async execution of cases and scenarios
   - Integrates with Meta-Builder for actual test execution

3. **Assertions** (`src/eval_lab/assertions.py`)
   - Evaluates test results against expected outcomes
   - Supports multiple assertion types (contains, regex, file exists, etc.)
   - Provides detailed assertion results and summaries

4. **Storage** (`src/eval_lab/storage.py`)
   - Persists evaluation data to database
   - Tracks runs, cases, metrics, and artifacts
   - Supports historical analysis and trend detection

5. **Comparison** (`src/eval_lab/compare.py`)
   - Detects regressions by comparing runs
   - Provides trend analysis and performance insights
   - Generates comparison reports

6. **Costs** (`src/eval_lab/costs.py`)
   - Calculates and tracks evaluation costs
   - Supports multiple cost models (LLM, compute, storage, network)
   - Provides cost estimation and budgeting

7. **API** (`src/eval_lab/api.py`)
   - REST API endpoints for evaluation management
   - JSON:API style responses
   - Supports run creation, monitoring, and reporting

## Usage

### Running Evaluations

#### Command Line

```bash
# Run a specific suite
python -m eval_lab.runner run-suite suites/core_crm.yaml

# Check for regressions
python -m eval_lab.runner check-regressions --run-id eval_run_123

# Generate a report
python -m eval_lab.runner generate-report --run-id eval_run_123 --output report.json

# Check KPI guards
python -m eval_lab.runner check-kpi-guards suites/core_crm.yaml
```

#### Make Targets

```bash
# Run evaluation lab tests
make eval

# Run a specific suite
make eval-suite SUITE=core_crm

# Check regression gates
make eval-regression

# Generate evaluation report
make eval-report

# Run all evaluation components
make eval-all
```

#### API

```bash
# List available suites
curl /api/v1/eval-lab/suites

# Create a new evaluation run
curl -X POST /api/v1/eval-lab/runs \
  -H "Content-Type: application/json" \
  -d '{"suite_name": "core_crm", "privacy_mode": "private_cloud"}'

# Get run details
curl /api/v1/eval-lab/runs/eval_run_123

# Check regressions
curl /api/v1/eval-lab/runs/eval_run_123/regressions

# Generate report
curl /api/v1/eval-lab/runs/eval_run_123/report
```

### Suite Configuration

Evaluation suites are defined in YAML files:

```yaml
name: "Core CRM"
description: "Core CRM functionality evaluation suite"

golden_cases:
  - name: "Create Contact"
    description: "Create a new contact with basic information"
    prompt: "Create a contact for John Doe with email john@example.com"
    sla_class: "normal"
    assertions:
      - name: "contact_created"
        type: "contains"
        expected: "John Doe"
        description: "Contact name should be present"

scenario_bundles:
  - name: "CRM Template Launch"
    description: "Launch CRM template and validate functionality"
    natural_language: "Launch a CRM template with basic features"
    sla_class: "thorough"
    steps:
      - name: "Launch Template"
        action: "launch"
        inputs:
          template: "crm_basic"
        assertions:
          - name: "template_launched"
            type: "contains"
            expected: "success"

kpi_guards:
  - name: "pass_rate_minimum"
    metric: "pass_rate"
    threshold: 0.95
    operator: ">="
    description: "Minimum 95% pass rate required"
    severity: "error"
```

### Assertion Types

- `contains`: Check if output contains expected text
- `not_contains`: Check if output doesn't contain text
- `equals`: Exact string match
- `regex_match`: Regular expression match
- `file_exists`: Check if file was created
- `not_empty`: Check if value is not empty
- `greater_than`, `less_than`: Numeric comparisons

### SLA Classes

- **fast**: < 5 seconds, basic validation
- **normal**: < 15 seconds, comprehensive validation
- **thorough**: < 30 seconds, full system validation

## CI/CD Integration

### GitHub Actions

The evaluation lab integrates with GitHub Actions via `.github/workflows/eval.yml`:

- Runs on PRs when evaluation files change
- Scheduled nightly runs
- Manual trigger with suite selection
- Regression gate enforcement
- PR comments with results

### Configuration

```yaml
# eval_lab/guards.yaml
global_kpi_guards:
  - name: "overall_pass_rate_minimum"
    metric: "pass_rate"
    threshold: 0.90
    operator: ">="
    severity: "error"

regression_gates:
  - name: "pass_rate_regression"
    metric: "pass_rate"
    threshold: 0.05
    operator: ">="
    severity: "error"
```

## Privacy and Security

### Privacy Mode Support

- **local_only**: Skips evaluation (no external calls)
- **byo_keys**: Skips evaluation (customer-managed keys)
- **private_cloud**: Full evaluation (SBH-managed infrastructure)

### Data Governance

- Automatic redaction of sensitive data
- Configurable retention policies
- Audit logging of all evaluation activities
- Customer-managed key support

## Monitoring and Observability

### Metrics

- Pass/fail rates
- Latency percentiles (P50, P95, P99)
- Cost tracking and budgeting
- Token usage and efficiency
- Regression detection

### Dashboards

- Real-time evaluation status
- Historical trend analysis
- Cost breakdown and optimization
- Regression alerts and notifications

### Alerts

- KPI guard violations
- Regression detection
- Cost threshold breaches
- System health issues

## Database Schema

### Core Tables

- `eval_runs`: Evaluation run metadata and summary
- `eval_cases`: Individual test case results
- `eval_metrics`: KPI and performance metrics
- `eval_artifacts`: Generated files and artifacts
- `eval_regressions`: Regression analysis results

### Key Fields

- Run tracking with unique IDs
- SLA class and privacy mode
- Cost breakdown and token usage
- Assertion results and error details
- Timestamps and execution metadata

## Cost Management

### Cost Models

- **LLM Costs**: Token-based pricing for different models
- **Compute Costs**: CPU, memory, and GPU usage
- **Storage Costs**: File storage and retention
- **Network Costs**: Data transfer and API calls

### Budgeting

- Per-run cost limits
- Suite-level cost estimates
- Tenant-level cost quotas
- Cost optimization recommendations

## Troubleshooting

### Common Issues

1. **Suite Loading Errors**
   - Check YAML syntax
   - Verify file paths
   - Validate schema compliance

2. **Assertion Failures**
   - Review expected vs actual output
   - Check assertion type and parameters
   - Verify test data and environment

3. **Performance Issues**
   - Monitor SLA compliance
   - Check resource utilization
   - Review cost optimization opportunities

4. **Privacy Mode Conflicts**
   - Verify privacy mode configuration
   - Check external service dependencies
   - Review data handling compliance

### Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python -m eval_lab.runner run-suite suites/core_crm.yaml --verbose

# Check database state
python -c "from eval_lab.storage import EvaluationStorage; s = EvaluationStorage('sqlite:///eval_lab.db'); print(s.get_recent_runs())"
```

## Future Enhancements

### Planned Features

1. **Advanced Assertions**
   - Semantic similarity matching
   - Image and file content validation
   - Custom assertion plugins

2. **Distributed Execution**
   - Parallel test execution
   - Load balancing and scaling
   - Multi-region evaluation

3. **Machine Learning Integration**
   - Automated test generation
   - Anomaly detection
   - Predictive performance analysis

4. **Enhanced Reporting**
   - Custom report templates
   - Automated insights and recommendations
   - Integration with external tools

### Roadmap

- **v1.1**: Enhanced assertion types and ML integration
- **v1.2**: Distributed execution and advanced reporting
- **v2.0**: Full AI-powered evaluation automation

## Contributing

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/eval_lab/

# Run linting
make lint

# Run evaluation lab tests
make eval
```

### Adding New Features

1. **New Assertion Types**
   - Add to `AssertionType` enum in `specs.py`
   - Implement evaluation logic in `assertions.py`
   - Add tests in `tests/eval_lab/test_assertions.py`

2. **New Metrics**
   - Add to database schema in `storage.py`
   - Implement calculation in `runner.py`
   - Add to API endpoints in `api.py`

3. **New Suite Types**
   - Create YAML configuration
   - Add to suite loader in `specs.py`
   - Update documentation and examples

### Testing

```bash
# Unit tests
python -m pytest tests/eval_lab/test_*.py

# Integration tests
python -m pytest tests/eval_lab/test_integration.py

# End-to-end tests
python -m pytest tests/eval_lab/test_e2e.py
```

## Support

For questions and support:

- **Documentation**: See this file and inline code comments
- **Issues**: Create GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Slack**: Join the #eval-lab channel for real-time support
