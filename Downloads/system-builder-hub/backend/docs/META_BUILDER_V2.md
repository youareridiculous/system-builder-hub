# SBH Meta-Builder v2 Documentation

## Overview

SBH Meta-Builder v2 is a self-refining, evaluation-driven scaffold builder with human approval gates. It transforms natural language specifications into production-ready scaffolds through a multi-agent, iterative system with automatic testing, self-remediation, and human review capabilities.

## Key Features

### Multi-Agent Orchestration
- **Product Architect**: Converts goals into formal specifications
- **System Designer**: Maps specifications to scaffold plans
- **Security/Compliance**: Injects RBAC, RLS, PII redaction, rate limits, audit
- **Codegen Engineer**: Produces diffs over target repo/export bundle
- **QA/Evaluator**: Runs tests, smoke, golden tasks; summarizes failures
- **Auto-Fixer**: Proposes & applies targeted patches until pass or budget exhausted
- **DevOps**: Ensures migrations, seed, envs, CI steps, deploy preview
- **Reviewer**: Composes PR body with risks, migrations, test results, and rollout notes

### Iterative Build Loop
1. **Plan**: Spec → ScaffoldPlan
2. **Generate**: Codegen Agent → unified diff
3. **Apply**: Migrate + Seed
4. **Evaluate**: Tests/smoke/golden; JSON report
5. **Decide**: If failures → Auto-Fix (constrained diffs); else Finish
6. **Cap**: Max iterations, cost budget, time budget

### Human-in-the-Loop Review
- Diff viewer with file tree, inline diff, risk flags
- Approval gates with rollback plans
- PR generation with comprehensive documentation

## Specification DSL

The Meta-Builder v2 uses a compact, typed Specification DSL:

```json
{
  "name": "string",
  "domain": "crm|lms|helpdesk|custom",
  "entities": [
    {
      "name": "Contact",
      "fields": [
        {
          "name": "email",
          "type": "email",
          "unique": true
        }
      ]
    }
  ],
  "workflows": [
    {
      "name": "deal_pipeline",
      "states": ["open", "won", "lost"],
      "transitions": [...]
    }
  ],
  "integrations": ["stripe", "ses", "webhooks", "slack", "drive"],
  "ai": {
    "copilots": ["sales", "ops"],
    "rag": true
  },
  "non_functional": {
    "multi_tenant": true,
    "rbac": true,
    "observability": true
  },
  "acceptance": [
    {
      "id": "A1",
      "text": "Create contact via API and see it in UI list",
      "category": "functional"
    }
  ]
}
```

## Import Sources

### OpenAPI/Swagger
```bash
POST /api/meta/v2/spec/import
{
  "type": "openapi",
  "data": {
    "openapi": "3.0.0",
    "paths": {...},
    "components": {...}
  }
}
```

### CSV Samples
```bash
POST /api/meta/v2/spec/import
{
  "type": "csv",
  "data": [
    {"name": "John", "email": "john@example.com"},
    {"name": "Jane", "email": "jane@example.com"}
  ]
}
```

### ERD JSON
```bash
POST /api/meta/v2/spec/import
{
  "type": "erd",
  "data": {
    "entities": [
      {
        "name": "User",
        "fields": [
          {"name": "id", "type": "uuid", "primary": true},
          {"name": "email", "type": "string", "unique": true}
        ]
      }
    ]
  }
}
```

## API Endpoints

### Run Management
```bash
# Create and start a new run
POST /api/meta/v2/build/run
{
  "name": "My CRM System",
  "goal_text": "Build a CRM system with contacts and deals",
  "limits": {
    "max_iters": 4,
    "token_budget": 2000000,
    "timeout_s": 900
  },
  "review": {
    "require_approval": true
  }
}

# Get run details
GET /api/meta/v2/build/{run_id}

# List runs
GET /api/meta/v2/runs?page=1&per_page=20&status=completed
```

### Review & Approval
```bash
# Approve a run
POST /api/meta/v2/review/approve
{
  "run_id": "uuid",
  "approved": true,
  "comments": "Looks good, ready for deployment"
}

# Reject a run
POST /api/meta/v2/review/reject
{
  "run_id": "uuid",
  "approved": false,
  "comments": "Security concerns need to be addressed"
}
```

### Evaluation
```bash
# Run evaluation
POST /api/meta/v2/eval/run
{
  "run_id": "uuid",
  "iteration": 1
}

# Get evaluation report
GET /api/meta/v2/eval/report/{report_id}
```

## Configuration & Limits

### Run Limits
- **Max Iterations**: 4 (default)
- **Token Budget**: 2,000,000 (default)
- **Timeout**: 900 seconds (15 minutes)

### Rate Limits
- **Runs**: 5 per day per tenant
- **Evaluations**: 20 per hour per tenant
- **Spec Imports**: 10 per hour per tenant

### Safety Policies
- **File Allow/Deny**: Blocks secrets, CI tokens, deployment manifests
- **DB Safety**: Migrations must be additive; destructive ops require approval
- **PII/Secrets**: Redacted in logs; never included in diffs
- **Determinism**: Temperature=0 "stable mode" toggle available

## Evaluation System

### Golden Tasks Library
30+ pre-defined test scenarios across:
- **CRUD**: Create, read, update, delete operations
- **Auth**: User registration, login, password management
- **Payments**: Stripe integration, payment processing
- **Files**: Upload, download, storage management
- **Automations**: Workflow triggers, scheduled tasks
- **AI**: Copilot responses, RAG functionality

### Assertion Types
- **HTTP Status/Shape**: API response validation
- **DB Invariants**: Database state verification
- **Migration State**: Schema change validation
- **UI Smoke**: Playwright-based UI testing
- **Analytics Events**: Event tracking verification
- **RBAC Checks**: Permission enforcement testing

### Scoring Rubric
- **Overall Score**: 0-100 with per-criterion breakdown
- **Pass/Fail**: Per acceptance criterion
- **JUnit + Markdown**: Comprehensive reporting
- **S3 Storage**: Presigned links for reports

## Observability & Analytics

### Agent Spans
Structured traces for each agent role:
- **Timing**: Start/end times, duration
- **Success/Failure**: Execution status
- **Metrics**: Token usage, cache hits
- **Context**: Inputs/outputs for debugging

### Prometheus Metrics
- `meta_runs_total`: Total runs created
- `meta_fix_iterations`: Auto-fix iteration count
- `meta_eval_score`: Evaluation scores
- `meta_cost_tokens_total`: Token usage

### UI Dashboard
- **Run Timeline**: Steps, logs, diffs, metrics
- **Cost Tracking**: Token usage and provider costs
- **Performance**: Duration and success rates
- **Trends**: Historical analysis and improvements

## UI Components

### Meta-Builder Portal
- **Dashboard**: Overview of runs, metrics, and status
- **Quick Actions**: Start new runs, view history
- **Real-time Updates**: Live status and progress

### Playground
- **Left Panel**: Goal/spec inputs (natural language + DSL + imports)
- **Center Panel**: Plan preview and diffs
- **Right Panel**: Failures and fix suggestions in real time

### History & Analytics
- **Search**: Filter by goal, score, date
- **Re-run**: Execute with tweaks and modifications
- **Comparison**: Side-by-side run analysis
- **Trends**: Performance and quality metrics

## Workflow Examples

### Basic CRM System
```bash
# 1. Create run
POST /api/meta/v2/build/run
{
  "name": "Simple CRM",
  "goal_text": "Build a CRM system with contact management and deal tracking"
}

# 2. Monitor progress
GET /api/meta/v2/build/{run_id}

# 3. Review and approve
POST /api/meta/v2/review/approve
{
  "run_id": "{run_id}",
  "approved": true
}
```

### Complex LMS with AI
```bash
# 1. Import existing schema
POST /api/meta/v2/spec/import
{
  "type": "erd",
  "data": {...}
}

# 2. Create enhanced run
POST /api/meta/v2/build/run
{
  "name": "AI-Powered LMS",
  "goal_text": "Enhance the LMS with AI copilot and RAG capabilities",
  "inputs": {
    "erd": {...}
  }
}
```

## Best Practices

### Specification Design
1. **Be Specific**: Clear, detailed requirements
2. **Include Examples**: Sample data and use cases
3. **Define Acceptance**: Measurable success criteria
4. **Consider Security**: RBAC, data protection, compliance

### Run Management
1. **Start Small**: Begin with simple systems
2. **Iterate Gradually**: Use feedback to improve
3. **Monitor Costs**: Track token usage and budgets
4. **Review Carefully**: Human oversight for safety

### Evaluation Strategy
1. **Comprehensive Testing**: Cover all acceptance criteria
2. **Security Focus**: Prioritize security and compliance
3. **Performance Testing**: Load and stress testing
4. **User Experience**: UI/UX validation

## Troubleshooting

### Common Issues

#### Run Stuck in Planning
- Check token budget and limits
- Verify specification format
- Review agent logs for errors

#### Evaluation Failures
- Examine failed assertions
- Check acceptance criteria
- Review auto-fix suggestions

#### Approval Rejected
- Address security concerns
- Fix identified issues
- Re-run with improvements

### Debug Mode
Enable detailed logging:
```bash
export META_BUILDER_DEBUG=true
export META_BUILDER_LOG_LEVEL=DEBUG
```

### Support
- **Documentation**: This guide and API reference
- **Community**: SBH community forums
- **Support**: Technical support team
- **Issues**: GitHub issue tracker

## Future Enhancements

### Planned Features
1. **Advanced AI**: More sophisticated LLM integration
2. **Custom Agents**: User-defined agent roles
3. **Template Library**: Pre-built specification templates
4. **Collaboration**: Team-based review and approval
5. **Integration**: CI/CD pipeline integration

### Roadmap
- **v2.1**: Enhanced evaluation system
- **v2.2**: Advanced security features
- **v2.3**: Performance optimizations
- **v3.0**: Full AI-driven development

## Conclusion

SBH Meta-Builder v2 represents a significant advancement in automated scaffold generation, combining the power of multi-agent systems with human oversight and iterative refinement. By following this documentation and best practices, you can effectively leverage the system to create production-ready applications from natural language specifications.
