# SBH Meta-Builder v1

The SBH Meta-Builder enables users to describe an idea in natural language and get a production-ready scaffold in one pass, then iteratively refine it. This system provides guided scaffold generation, template composition, and comprehensive evaluation.

## Overview

The Meta-Builder consists of several key components:

- **Guided Prompt Composer**: UI for structured or freeform input
- **Pattern Library**: Catalog of reusable build patterns
- **Template Composition**: Rules for combining marketplace templates
- **Visual Plan Inspector**: Diff viewer and collision resolver
- **Evaluation Harness**: Golden tests for quality assurance

## Architecture

### Data Models

#### ScaffoldSession
Represents a scaffold generation session:
- `id`: Unique identifier
- `tenant_id`: Multi-tenant isolation
- `user_id`: User who created the session
- `goal_text`: Natural language description
- `mode`: 'guided' or 'freeform'
- `guided_input`: Structured input data
- `pattern_slugs`: Selected patterns
- `template_slugs`: Selected templates
- `composition_rules`: Template composition rules
- `status`: 'draft', 'planned', 'built', 'failed'

#### ScaffoldPlan
Represents a generated plan:
- `id`: Unique identifier
- `session_id`: Associated session
- `version`: Plan version number
- `planner_kind`: 'heuristic' or 'llm'
- `plan_json`: BuilderState draft
- `diffs_json`: Changes from previous version
- `scorecard_json`: Quality metrics
- `rationale`: Planning explanation
- `risks`: Identified risks
- `build_status`: Build status
- `build_results`: Build artifacts

#### PatternLibrary
Catalog of build patterns:
- `slug`: Pattern identifier
- `name`: Human-readable name
- `description`: Pattern description
- `tags`: Categorization tags
- `inputs_schema`: Expected inputs
- `outputs_schema`: Generated outputs
- `compose_points`: Integration points

#### TemplateLink
References to marketplace templates:
- `template_slug`: Template identifier
- `template_version`: Version number
- `merge_strategy`: How to combine templates
- `compose_points`: Integration points
- `dependencies`: Required templates
- `conflicts`: Conflicting templates

#### EvaluationCase
Golden test cases:
- `name`: Test case name
- `golden_prompt`: Input prompt
- `expected_assertions`: Expected outputs
- `pattern_slugs`: Related patterns
- `template_slugs`: Related templates

## API Endpoints

### Planning

#### POST /api/meta/scaffold/plan
Generate a scaffold plan from natural language goal.

**Request Body:**
```json
{
  "goal_text": "Build a helpdesk system with knowledge base",
  "mode": "guided",
  "guided_input": {
    "role": "Developer",
    "context": "Internal support team",
    "task": "Create ticketing system",
    "audience": "Support agents",
    "output": "Web application"
  },
  "pattern_slugs": ["helpdesk", "ai-rag-app"],
  "template_slugs": ["flagship-crm"],
  "composition": {
    "merge_strategy": "compose",
    "resolve_conflicts": true
  },
  "options": {
    "llm": true,
    "dry_run": false
  }
}
```

**Response:**
```json
{
  "data": {
    "id": "plan-uuid",
    "type": "scaffold_plan",
    "attributes": {
      "session_id": "session-uuid",
      "version": 1,
      "planner_kind": "llm",
      "rationale": "Planning explanation...",
      "risks": ["Risk 1", "Risk 2"],
      "scorecard": {
        "completeness": 85,
        "complexity": "medium",
        "estimated_effort": "2-3 days"
      }
    }
  }
}
```

### Building

#### POST /api/meta/scaffold/build
Build a scaffold from a plan.

**Request Body:**
```json
{
  "session_id": "session-uuid",
  "plan_id": "plan-uuid",
  "export": {
    "zip": true,
    "github": {
      "owner": "sbh-user",
      "repo": "generated-app",
      "branch": "main"
    }
  },
  "run_tests": true
}
```

**Response:**
```json
{
  "data": {
    "id": "plan-uuid",
    "type": "scaffold_build",
    "attributes": {
      "session_id": "session-uuid",
      "success": true,
      "artifacts": [
        {
          "type": "zip",
          "filename": "scaffold_session-uuid.zip",
          "file_key": "scaffolds/session-uuid/scaffold_session-uuid.zip",
          "size": 1024000
        }
      ],
      "preview_urls": [
        "http://localhost:5000",
        "http://localhost:5000/api/docs"
      ],
      "test_results": {
        "status": "passed",
        "tests_run": 5,
        "tests_passed": 5,
        "coverage": 85.5
      }
    }
  }
}
```

### Revision

#### POST /api/meta/scaffold/revise
Revise a scaffold plan based on feedback.

**Request Body:**
```json
{
  "session_id": "session-uuid",
  "plan_id": "plan-uuid",
  "feedback_text": "Add user authentication",
  "constraints": {
    "max_complexity": "medium",
    "required_features": ["auth", "rbac"]
  },
  "add_modules": ["auth"],
  "remove_modules": ["complex-analytics"]
}
```

### Patterns & Templates

#### GET /api/meta/patterns
List available patterns.

**Query Parameters:**
- `tags`: Filter by tags
- `active_only`: Show only active patterns

#### GET /api/meta/templates
List available templates.

**Query Parameters:**
- `active_only`: Show only active templates

### Evaluation

#### POST /api/meta/eval/run
Run evaluation cases against the planner pipeline.

**Response:**
```json
{
  "data": {
    "type": "evaluation_results",
    "attributes": {
      "summary": {
        "total_cases": 5,
        "passed": 4,
        "failed": 1,
        "pass_rate": 80.0,
        "avg_score": 85.2
      },
      "results": [
        {
          "case_id": "case-uuid",
          "case_name": "Helpdesk with KB + AI search",
          "status": "pass",
          "score": 90.0,
          "details": {
            "entities": "pass",
            "api_endpoints": "pass",
            "features": "pass"
          }
        }
      ]
    }
  }
}
```

## Patterns

### CRUD Application
Basic Create, Read, Update, Delete application with REST API.

**Input Schema:**
```json
{
  "entities": {
    "type": "array",
    "items": {"type": "string"}
  },
  "fields_per_entity": {
    "type": "integer",
    "default": 5
  }
}
```

**Output Schema:**
```json
{
  "models": {"type": "array"},
  "api_endpoints": {"type": "array"},
  "ui_pages": {"type": "array"}
}
```

### Analytics Dashboard
Data visualization and analytics application.

**Input Schema:**
```json
{
  "data_sources": {
    "type": "array",
    "items": {"type": "string"}
  },
  "chart_types": {
    "type": "array",
    "items": {"type": "string"}
  }
}
```

### Marketplace Platform
Multi-vendor marketplace with listings and transactions.

**Input Schema:**
```json
{
  "vendor_types": {
    "type": "array",
    "items": {"type": "string"}
  },
  "product_categories": {
    "type": "array",
    "items": {"type": "string"}
  }
}
```

### Helpdesk System
Customer support ticketing system with knowledge base.

**Input Schema:**
```json
{
  "ticket_categories": {
    "type": "array",
    "items": {"type": "string"}
  },
  "support_channels": {
    "type": "array",
    "items": {"type": "string"}
  }
}
```

### AI RAG Application
Retrieval-Augmented Generation application with vector search.

**Input Schema:**
```json
{
  "data_sources": {
    "type": "array",
    "items": {"type": "string"}
  },
  "embedding_model": {
    "type": "string",
    "default": "text-embedding-ada-002"
  }
}
```

## Template Composition

### Merge Strategies

#### Append
Add new components without modifying existing ones.

#### Extend
Modify existing components to add new functionality.

#### Compose
Intelligently combine multiple templates with conflict resolution.

### Composition Rules

#### Database
- Prefix or merge tables
- Create join edges
- Add foreign keys safely

#### API
- Mount under `/api/{module}` namespaces
- Avoid slug conflicts
- Maintain consistent structure

#### UI
- Mount in navigation sections
- Deduplicate shared primitives
- Maintain design consistency

#### Auth/Payments/FileStore/Analytics
- Reuse existing nodes
- Extend configuration
- Maintain security

## Evaluation Cases

### Golden Tests

#### Helpdesk with KB + AI search
**Prompt:** "Build a helpdesk system with knowledge base and AI search capabilities"

**Expected Assertions:**
```json
{
  "entities": ["ticket", "knowledge_article", "user", "category"],
  "api_endpoints": {"count": 8},
  "ui_pages": ["tickets", "knowledge_base", "search"],
  "features": {
    "auth": true,
    "ai": true,
    "search": true
  }
}
```

#### Internal LMS with quizzes + payments
**Prompt:** "Create an internal learning management system with quizzes and payment processing"

**Expected Assertions:**
```json
{
  "entities": ["course", "quiz", "user", "enrollment", "payment"],
  "api_endpoints": {"count": 10},
  "ui_pages": ["courses", "quizzes", "dashboard", "payments"],
  "features": {
    "auth": true,
    "payments": true,
    "assessments": true
  }
}
```

#### Customer portal + ticketing + Slack alerts
**Prompt:** "Build a customer portal with ticketing system and Slack notifications"

**Expected Assertions:**
```json
{
  "entities": ["customer", "ticket", "message", "notification"],
  "api_endpoints": {"count": 6},
  "ui_pages": ["portal", "tickets", "profile"],
  "features": {
    "auth": true,
    "notifications": true,
    "integrations": true
  }
}
```

## Usage Examples

### Guided Input
```json
{
  "role": "Startup Founder",
  "context": "Building a SaaS platform for project management",
  "task": "Create a project management app with team collaboration",
  "audience": "Small to medium teams",
  "output": "Web application with mobile support"
}
```

### Freeform Input
```
Build a project management application for remote teams with real-time collaboration, file sharing, and time tracking. Include user authentication, role-based access control, and integrations with popular tools like Slack and GitHub.
```

### Pattern Selection
```json
{
  "pattern_slugs": ["crud-app", "analytics-app"],
  "template_slugs": ["flagship-crm", "stripe-payments"]
}
```

## Security & Observability

### Rate Limits
- Planning: 20 requests per minute per tenant
- Building: 10 requests per minute per tenant
- Evaluation: 5 requests per minute per tenant

### Audit Events
- `scaffold.plan.created`
- `scaffold.build.completed`
- `scaffold.plan.revised`
- `evaluation.run.completed`

### Metrics
- `planner_invocations_total`
- `planner_success_rate`
- `planner_latency_seconds`
- `build_success_rate`
- `evaluation_pass_rate`

## Development

### Running Tests
```bash
# Run all meta-builder tests
pytest tests/test_meta_builder.py

# Run specific test categories
pytest tests/test_meta_builder.py::TestScaffoldPlanner
pytest tests/test_meta_builder.py::TestScaffoldImplementer
pytest tests/test_meta_builder.py::TestScaffoldEvaluator
```

### Adding New Patterns
1. Define pattern in `src/meta_builder/seeds.py`
2. Add to `PatternLibrary` table
3. Create evaluation cases
4. Update documentation

### Adding New Templates
1. Create template in marketplace
2. Add `TemplateLink` entry
3. Define composition rules
4. Test integration

### Running Evaluations
```bash
# Run all evaluation cases
curl -X POST /api/meta/eval/run \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json"

# Check evaluation results
curl -X GET /api/meta/eval/results \
  -H "Authorization: Bearer token"
```

## Troubleshooting

### Common Issues

#### Plan Generation Fails
- Check LLM orchestration configuration
- Verify pattern/template availability
- Review rate limits and quotas

#### Build Fails
- Check tool kernel configuration
- Verify file storage permissions
- Review migration conflicts

#### Evaluation Fails
- Check evaluation case definitions
- Verify assertion schemas
- Review planner output format

### Debug Mode
Enable debug logging:
```python
import logging
logging.getLogger('src.meta_builder').setLevel(logging.DEBUG)
```

### Health Checks
```bash
# Check planner health
curl -X GET /api/meta/health/planner

# Check implementer health
curl -X GET /api/meta/health/implementer

# Check evaluator health
curl -X GET /api/meta/health/evaluator
```
