# SBH Meta-Builder v2

Multi-agent, iterative scaffold generation with approval gates and human-in-the-loop review.

## Overview

SBH Meta-Builder v2 is a comprehensive system for generating production-ready application scaffolds from natural language specifications. It uses a multi-agent architecture with iterative refinement, automatic testing, and human approval gates.

## Key Features

### �� Multi-Agent Orchestration
- **Product Architect**: Converts goals into formal specifications
- **System Designer**: Maps specifications to scaffold plans
- **Security/Compliance**: Injects RBAC, RLS, PII redaction, rate limits, audit
- **Codegen Engineer**: Produces diffs over target repo/export bundle
- **QA/Evaluator**: Runs tests, smoke flows, golden tasks
- **Auto-Fixer**: Proposes & applies targeted patches
- **DevOps**: Ensures migrations, seed, envs, CI steps, deploy preview
- **Reviewer**: Composes PR body with risks, migrations, test results

### 🔄 Iterative Build Loop
1. **Plan**: Spec → ScaffoldPlan
2. **Generate**: Codegen Agent → unified diff
3. **Apply**: Migrate + Seed
4. **Evaluate**: Tests/smoke/golden; JSON report
5. **Decide**: If failures → Auto-Fix (constrained diffs); else Finish
6. **Cap**: Max iterations, cost budget, time budget

### 👥 Human-in-the-Loop Review
- Diff viewer with file tree, inline diff, risk flags
- Approval gates with rollback plans
- PR generation with comprehensive documentation

## Architecture

### Data Models
- `ScaffoldSpec`: Specification with guided/freeform input
- `ScaffoldPlan`: Generated plan with risk assessment
- `BuildRun`: Orchestrates the multi-agent build process
- `BuildStep`: Individual agent execution within a run
- `DiffArtifact`: Unified diff from codegen step
- `EvalReport`: Test results and scoring
- `ApprovalGate`: Human review checkpoint
- `BuildArtifact`: Final outputs (ZIP, PR, manifest)

### Agents
Each agent has a specific role and uses LLM orchestration with caching:

- **ProductArchitectAgent**: Analyzes requirements and creates specifications
- **SystemDesignerAgent**: Designs system architecture and implementation plans
- **SecurityComplianceAgent**: Reviews security and compliance requirements
- **CodegenEngineerAgent**: Generates code artifacts and unified diffs
- **QAEvaluatorAgent**: Runs tests and evaluates code quality
- **AutoFixerAgent**: Analyzes failures and generates fixes
- **DevOpsAgent**: Handles deployment and infrastructure
- **ReviewerAgent**: Summarizes runs and manages approval gates

### Orchestrator
The `MetaBuilderOrchestrator` coordinates the entire process:
- Manages build runs and iterations
- Handles agent execution and error recovery
- Enforces approval policies and gates
- Provides idempotent and resumable operations

## API Endpoints

### Specifications
- `POST /api/meta/v2/specs` - Create specification
- `GET /api/meta/v2/specs/:id` - Get specification details
- `POST /api/meta/v2/specs/:id/plan` - Generate plan

### Build Runs
- `POST /api/meta/v2/specs/:id/runs` - Start build run
- `GET /api/meta/v2/runs/:id` - Get run details
- `POST /api/meta/v2/runs/:id/approve` - Approve run
- `POST /api/meta/v2/runs/:id/reject` - Reject run
- `POST /api/meta/v2/runs/:id/cancel` - Cancel run
- `GET /api/meta/v2/runs` - List runs

## Usage

### 1. Create Specification

```python
from src.meta_builder_v2.models import create_spec, SpecMode

spec = create_spec(
    tenant_id=tenant_id,
    created_by=user_id,
    title="My CRM System",
    description="Build a CRM system with contacts and deals",
    mode=SpecMode.FREEFORM
)
```

### 2. Generate Plan

```python
from src.meta_builder_v2.orchestrator import MetaBuilderOrchestrator

orchestrator = MetaBuilderOrchestrator()
plan = await orchestrator.plan_spec(spec_id, db_session, agent_context)
```

### 3. Start Build Run

```python
run = await orchestrator.start_run(
    spec_id=spec_id,
    plan_id=plan_id,
    max_iterations=4,
    db_session=db_session,
    context=agent_context,
    async_mode=False
)
```

### 4. Monitor Progress

```python
run_details = await orchestrator.get_run(run_id, db_session)
print(f"Status: {run_details['run']['status']}")
print(f"Iteration: {run_details['run']['iteration']}")
```

### 5. Approve/Reject

```python
# If approval is required
await orchestrator.approve_run(run_id, reviewer_id, "Looks good!", db_session)
# or
await orchestrator.reject_run(run_id, reviewer_id, "Security concerns", db_session)
```

## Configuration

### Environment Variables
- `META_BUILDER_MAX_ITERATIONS`: Maximum iterations per run (default: 4)
- `META_BUILDER_TOKEN_BUDGET`: Token budget per run (default: 2,000,000)
- `META_BUILDER_TIMEOUT`: Timeout per run in seconds (default: 900)
- `META_BUILDER_APPROVAL_THRESHOLD`: Risk score threshold for approval (default: 70)

### Rate Limits
- Specifications: 20 per hour per tenant
- Plans: 20 per hour per tenant
- Runs: 10 per hour per tenant
- Approvals: 50 per hour per tenant

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest tests/test_meta_builder_v2.py -v

# Run specific test categories
python -m pytest tests/test_meta_builder_v2.py::TestMetaBuilderV2Models -v
python -m pytest tests/test_meta_builder_v2.py::TestMetaBuilderV2Agents -v
python -m pytest tests/test_meta_builder_v2.py::TestMetaBuilderV2Orchestrator -v
```

## Demo

Run the demo script to see Meta-Builder v2 in action:

```bash
python scripts/meta_demo.py
```

This will:
1. Create a sample CRM specification
2. Run through the complete build process
3. Show the generated artifacts and results

## Security

### Tenant Isolation
- All data is scoped by tenant_id
- Cross-tenant access is prevented at the model level
- API endpoints enforce tenant isolation

### RBAC Integration
- Role-based access control for all operations
- Owner/Admin can create/execute
- Member can plan
- Viewer read-only

### Data Protection
- PII fields are automatically identified and encrypted
- Audit logging for all critical operations
- Rate limiting to prevent abuse

## Observability

### Metrics
- `meta_builder_specs_created_total`
- `meta_builder_plans_generated_total`
- `meta_builder_runs_started_total`
- `meta_builder_runs_succeeded_total`
- `meta_builder_runs_failed_total`
- `meta_builder_autofix_iterations_total`

### Logging
- Structured logs for all agent operations
- Span tracking for distributed tracing
- Error tracking and alerting

### Analytics
- Build success rates and performance
- Agent performance and cache hit rates
- User engagement and feature usage

## Deployment

### Database Migration
```bash
# Run the migration to create Meta-Builder v2 tables
alembic upgrade head
```

### Service Integration
```python
# Register the blueprints
from src.meta_builder_v2 import meta_builder_v2, meta_builder_v2_ui

app.register_blueprint(meta_builder_v2)
app.register_blueprint(meta_builder_v2_ui)
```

### Health Check
```python
# Add to readiness check
def check_meta_builder():
    return {
        "meta_builder": {
            "ok": True,
            "cache": "redis",
            "queue": "redis"
        }
    }
```

## Troubleshooting

### Common Issues

1. **Build Stuck in Planning**
   - Check token budget and limits
   - Verify specification format
   - Review agent logs for errors

2. **Evaluation Failures**
   - Examine failed assertions
   - Check acceptance criteria
   - Review auto-fix suggestions

3. **Approval Rejected**
   - Address security concerns
   - Fix identified issues
   - Re-run with improvements

### Debug Mode
```bash
export META_BUILDER_DEBUG=true
export META_BUILDER_LOG_LEVEL=DEBUG
```

## Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure security and compliance

## License

This project is part of the SBH (System Builder Hub) platform.

## Support

For issues and questions:
- Check the documentation
- Review the test suite
- Contact the development team
