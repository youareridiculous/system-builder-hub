# Template Marketplace Guide

This document explains SBH's template marketplace system, including guided prompts, template management, and one-click deployment.

## Overview

The SBH Template Marketplace provides:

1. **Pre-built Templates**: Ready-to-use application templates
2. **Guided Prompts**: Customizable templates with guided input
3. **One-click Deployment**: Instant project creation and generation
4. **Template Management**: Admin tools for template creation and publishing

## Template Categories

### Available Templates

#### Task Tracker
- **Category**: Productivity
- **Description**: A simple task management application with CRUD operations
- **Features**: Task creation, editing, deletion, status tracking
- **Guided Fields**: Table name, task fields complexity

#### Blog
- **Category**: Content
- **Description**: A modern blog with articles, categories, and comments
- **Features**: Article management, categories, tags, comments
- **Guided Fields**: Article table name, include comments

#### Contact Form
- **Category**: Communication
- **Description**: A simple contact form with email notifications
- **Features**: Form collection, email notifications
- **Guided Fields**: Contact table name, notification email

## Guided Prompt System

### Prompt Structure

All templates use a standard prompt structure:

1. **Role**: Who will use this application? (e.g., Founder, Manager, Developer)
2. **Context**: What is the context? (e.g., Track tasks, Manage content)
3. **Task**: What tasks need to be performed? (e.g., CRUD operations, Data management)
4. **Audience**: Who is the target audience? (e.g., Team, Customers, Public)
5. **Output**: What type of output? (e.g., Web application, Dashboard)

### Custom Fields

Each template can define additional custom fields:

```json
{
  "fields": [
    {
      "name": "table_name",
      "label": "Task Table Name",
      "type": "string",
      "required": true,
      "default": "tasks",
      "max_length": 50,
      "description": "Name for the tasks table"
    },
    {
      "name": "include_comments",
      "label": "Include Comments",
      "type": "boolean",
      "required": false,
      "default": true,
      "description": "Add comment functionality"
    }
  ]
}
```

### Field Types

- **string**: Text input with optional max length
- **number**: Numeric input
- **boolean**: Checkbox input
- **select**: Dropdown with predefined options

## Using Templates

### Browse Templates

1. Navigate to `/ui/market`
2. Browse available templates by category
3. Use search and filters to find specific templates
4. Click "View Details" to see template information

### Use a Template

1. **Select Template**: Choose a template from the marketplace
2. **Fill Guided Prompt**: Complete the guided prompt form
3. **Preview**: Click "Plan Template" to see a preview
4. **Deploy**: Click "Use Template" to create your application

### Example: Task Tracker

```javascript
// Guided input
{
  "role": "Founder",
  "context": "Track tasks",
  "task": "CRUD operations",
  "audience": "Team",
  "output": "Web application",
  "table_name": "tasks",
  "task_fields": "detailed"
}

// Generated application
{
  "project_id": "proj-123",
  "project_slug": "tasks-20240115-143022",
  "preview_url": "/preview/proj-123",
  "preview_url_project": "/ui/preview/proj-123"
}
```

## Template Management (Admin)

### Creating Templates

#### Via API
```bash
curl -X POST https://myapp.com/api/market/templates \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  -d '{
    "slug": "my-template",
    "name": "My Template",
    "short_desc": "A custom template",
    "long_desc": "Detailed description...",
    "category": "Productivity",
    "tags": ["custom", "productivity"],
    "guided_schema": {
      "fields": [...]
    },
    "builder_state": {
      "nodes": [...],
      "connections": [...]
    }
  }'
```

#### Template Structure

```json
{
  "slug": "unique-template-slug",
  "name": "Template Name",
  "short_desc": "Brief description",
  "long_desc": "Detailed description",
  "category": "Productivity",
  "tags": ["tag1", "tag2"],
  "price_cents": null,
  "requires_plan": null,
  "is_public": false,
  "guided_schema": {
    "fields": [...]
  },
  "builder_state": {
    "nodes": [...],
    "connections": [...]
  },
  "assets": {
    "cover_image_url": "/static/images/template-cover.png",
    "gallery": ["/static/images/template-1.png"],
    "sample_screens": [...]
  }
}
```

### Publishing Templates

```bash
# Publish template
curl -X POST https://myapp.com/api/market/templates/my-template/publish \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>"

# Unpublish template
curl -X POST https://myapp.com/api/market/templates/my-template/unpublish \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>"
```

## API Endpoints

### List Templates
```http
GET /api/market/templates?category=Productivity&q=task&page=1&per_page=20
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "templates": [...],
    "total": 50,
    "page": 1,
    "per_page": 20,
    "pages": 3
  }
}
```

### Get Template Details
```http
GET /api/market/templates/task-tracker
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "template-123",
    "slug": "task-tracker",
    "name": "Task Tracker",
    "guided_schema": {...},
    "assets": {...}
  }
}
```

### Plan Template
```http
POST /api/market/templates/task-tracker/plan
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
Content-Type: application/json

{
  "guided_input": {
    "role": "Founder",
    "context": "Track tasks",
    "task": "CRUD operations",
    "audience": "Team",
    "output": "Web application",
    "table_name": "tasks"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "template": {...},
    "guided_input": {...},
    "builder_state": {...}
  }
}
```

### Use Template
```http
POST /api/market/templates/task-tracker/use
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
Content-Type: application/json

{
  "guided_input": {...}
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "project_id": "proj-123",
    "project_slug": "tasks-20240115-143022",
    "preview_url": "/preview/proj-123",
    "preview_url_project": "/ui/preview/proj-123"
  }
}
```

## Template Builder State

### Node Types

Templates define builder state with different node types:

#### UI Page Node
```json
{
  "id": "ui_page_tasks",
  "type": "ui_page",
  "name": "{{table_name}}",
  "config": {
    "title": "{{table_name.title()}} Management",
    "description": "Manage your {{table_name}}"
  }
}
```

#### REST API Node
```json
{
  "id": "rest_api_tasks",
  "type": "rest_api",
  "name": "{{api_name}}",
  "config": {
    "base_path": "/api/{{api_name}}",
    "description": "{{table_name.title()}} API"
  }
}
```

#### Database Table Node
```json
{
  "id": "db_table_tasks",
  "type": "db_table",
  "name": "{{table_name}}",
  "config": {
    "fields": [
      {"name": "id", "type": "uuid", "primary": true},
      {"name": "title", "type": "string", "required": true},
      {"name": "status", "type": "enum", "options": ["pending", "completed"]}
    ]
  }
}
```

### Placeholder Substitution

Templates use placeholders that are substituted with guided input:

- `{{table_name}}` → Guided input table_name
- `{{api_name}}` → Slugified table_name
- `{{role}}` → Guided input role
- `{{context}}` → Guided input context
- `{{task}}` → Guided input task
- `{{audience}}` → Guided input audience
- `{{output}}` → Guided input output

## Pricing & Plans

### Free Templates
- No cost
- Available to all users
- Basic functionality

### Paid Templates
- Require payment or subscription
- Enhanced features
- Premium support

### Plan Requirements
- Templates can require specific subscription plans
- Pro templates require Pro subscription
- Enterprise templates require Enterprise subscription

## Analytics & Events

### Template Events
- `market.template.view` - Template viewed
- `market.template.use.start` - Template planning started
- `market.template.use.success` - Template deployed successfully
- `market.template.use.error` - Template deployment failed

### Event Properties
```json
{
  "template_slug": "task-tracker",
  "template_name": "Task Tracker",
  "project_id": "proj-123",
  "guided_input": {...},
  "error": "Error message"
}
```

## Security & RBAC

### Access Control
- **View Templates**: All authenticated users
- **Use Templates**: All authenticated users
- **Create Templates**: Admin/Owner only
- **Publish Templates**: Admin/Owner only

### Multi-Tenant Isolation
- Templates are tenant-scoped
- Admin users can manage templates for their tenant
- Template usage is tracked per tenant

## Configuration

### Environment Variables
```bash
# Enable marketplace
FEATURE_MARKETPLACE=true

# Enable commerce features (future)
FEATURE_MARKET_COMMERCE=false
```

### Feature Flags
- `FEATURE_MARKETPLACE`: Enable/disable marketplace
- `FEATURE_MARKET_COMMERCE`: Enable paid templates

## Best Practices

### Template Design
1. **Clear Naming**: Use descriptive names and slugs
2. **Comprehensive Schema**: Define all necessary guided fields
3. **Good Documentation**: Provide clear descriptions and examples
4. **Test Thoroughly**: Ensure templates work correctly

### Guided Prompts
1. **Logical Flow**: Structure prompts logically
2. **Clear Labels**: Use descriptive field labels
3. **Helpful Defaults**: Provide sensible default values
4. **Validation**: Include proper validation rules

### Builder State
1. **Modular Design**: Use separate nodes for different concerns
2. **Consistent Naming**: Use consistent naming conventions
3. **Proper Connections**: Define clear node relationships
4. **Placeholder Usage**: Use placeholders for customization

## Troubleshooting

### Common Issues

#### Template Not Found
- Check template slug is correct
- Verify template is published
- Ensure user has access permissions

#### Guided Input Validation Errors
- Check required fields are provided
- Verify field types match schema
- Ensure values meet length/format requirements

#### Deployment Failures
- Check builder state is valid
- Verify all placeholders are substituted
- Ensure project generation succeeds

### Debug Commands
```bash
# Check template exists
curl -H "Authorization: Bearer <token>" \
  https://myapp.com/api/market/templates/task-tracker

# Test guided input validation
curl -X POST https://myapp.com/api/market/templates/task-tracker/plan \
  -H "Authorization: Bearer <token>" \
  -d '{"guided_input": {...}}'

# Check analytics events
curl -H "Authorization: Bearer <token>" \
  https://myapp.com/api/analytics/metrics
```

## Examples

### Creating a Custom Template

1. **Define Schema**
```json
{
  "fields": [
    {
      "name": "entity_name",
      "label": "Entity Name",
      "type": "string",
      "required": true,
      "default": "items"
    },
    {
      "name": "include_search",
      "label": "Include Search",
      "type": "boolean",
      "default": true
    }
  ]
}
```

2. **Create Builder State**
```json
{
  "nodes": [
    {
      "id": "ui_page_entity",
      "type": "ui_page",
      "name": "{{entity_name}}",
      "config": {
        "title": "{{entity_name.title()}} Management"
      }
    },
    {
      "id": "rest_api_entity",
      "type": "rest_api",
      "name": "{{entity_name}}_api",
      "config": {
        "base_path": "/api/{{entity_name}}"
      }
    }
  ],
  "connections": [
    {
      "from": "ui_page_entity",
      "to": "rest_api_entity",
      "type": "data_source"
    }
  ]
}
```

3. **Publish Template**
```bash
curl -X POST https://myapp.com/api/market/templates/my-template/publish \
  -H "Authorization: Bearer <token>"
```

### Using a Template

1. **Browse and Select**
```javascript
// Get available templates
const response = await fetch('/api/market/templates');
const templates = await response.json();
```

2. **Fill Guided Prompt**
```javascript
const guidedInput = {
  role: 'Manager',
  context: 'Track inventory',
  task: 'CRUD operations',
  audience: 'Warehouse staff',
  output: 'Web application',
  entity_name: 'inventory',
  include_search: true
};
```

3. **Deploy Template**
```javascript
const response = await fetch('/api/market/templates/inventory-tracker/use', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({ guided_input: guidedInput })
});

const result = await response.json();
window.location.href = result.data.preview_url_project;
```
