"""
Marketplace documentation and metadata for CRM/Ops Template
"""
from typing import Dict, Any, List

class CRMOpsMarketplace:
    """Marketplace metadata and documentation for CRM/Ops Template"""
    
    @staticmethod
    def get_template_metadata() -> Dict[str, Any]:
        """Get template metadata for marketplace"""
        return {
            'slug': 'crm-ops',
            'name': 'CRM/Ops Template',
            'description': 'Complete CRM and Operations Management System',
            'category': 'Sales & Ops',
            'version': '1.0.0',
            'author': 'SBH Team',
            'tags': ['crm', 'sales', 'operations', 'project-management', 'analytics'],
            'badges': [
                'Multi-tenant',
                'Stripe Integration',
                'S3 Storage',
                'RBAC Security',
                'API-First',
                'Real-time Analytics'
            ],
            'features': [
                'Contact Management',
                'Deal Pipeline',
                'Project Management',
                'Task Tracking',
                'Team Messaging',
                'Analytics Dashboard',
                'CSV Import/Export',
                'Email Notifications',
                'Role-Based Access Control',
                'Multi-tenant Architecture'
            ],
            'integrations': [
                'Stripe (Billing)',
                'AWS SES (Email)',
                'AWS S3 (File Storage)',
                'Redis (Caching)',
                'PostgreSQL (Database)'
            ],
            'screenshots': [
                {
                    'title': 'CRM Dashboard',
                    'description': 'Overview of contacts, deals, and key metrics',
                    'url': '/static/screenshots/crm-dashboard.png'
                },
                {
                    'title': 'Deal Pipeline',
                    'description': 'Kanban board for managing sales pipeline',
                    'url': '/static/screenshots/deal-pipeline.png'
                },
                {
                    'title': 'Analytics',
                    'description': 'Comprehensive analytics and reporting',
                    'url': '/static/screenshots/analytics.png'
                }
            ],
            'pricing': {
                'starter': {
                    'price': 29,
                    'currency': 'USD',
                    'period': 'month',
                    'features': [
                        'Up to 1,000 contacts',
                        'Basic analytics',
                        'Email support',
                        'CSV import/export'
                    ]
                },
                'professional': {
                    'price': 99,
                    'currency': 'USD',
                    'period': 'month',
                    'features': [
                        'Up to 10,000 contacts',
                        'Advanced analytics',
                        'Priority support',
                        'Custom integrations',
                        'Team messaging'
                    ]
                },
                'enterprise': {
                    'price': 'Custom',
                    'currency': 'USD',
                    'period': 'month',
                    'features': [
                        'Unlimited contacts',
                        'Full analytics suite',
                        'Dedicated support',
                        'Custom development',
                        'White-label options'
                    ]
                }
            },
            'setup_instructions': {
                'prerequisites': [
                    'AWS account with SES and S3 configured',
                    'Stripe account for billing',
                    'PostgreSQL database',
                    'Redis instance'
                ],
                'installation_steps': [
                    'Deploy the template to your environment',
                    'Configure environment variables',
                    'Run database migrations',
                    'Set up email templates',
                    'Configure Stripe webhooks',
                    'Test the onboarding flow'
                ],
                'configuration': {
                    'environment_variables': [
                        'AWS_ACCESS_KEY_ID',
                        'AWS_SECRET_ACCESS_KEY',
                        'AWS_REGION',
                        'SES_FROM_EMAIL',
                        'S3_BUCKET_NAME',
                        'STRIPE_SECRET_KEY',
                        'STRIPE_WEBHOOK_SECRET',
                        'DATABASE_URL',
                        'REDIS_URL'
                    ]
                }
            }
        }
    
    @staticmethod
    def get_documentation() -> Dict[str, Any]:
        """Get comprehensive documentation"""
        return {
            'overview': {
                'title': 'CRM/Ops Template Overview',
                'content': '''
The CRM/Ops Template is a comprehensive customer relationship management and operations system designed for modern businesses. It provides a complete solution for managing contacts, deals, projects, and team collaboration.

## Key Features

### Contact Management
- Store and organize customer information
- Custom fields and tagging system
- Import/export via CSV
- Contact activity tracking

### Deal Pipeline
- Visual Kanban board for deal management
- Pipeline stage tracking
- Deal value and forecasting
- Win/loss analysis

### Project Management
- Project creation and organization
- Task assignment and tracking
- Time tracking and reporting
- Team collaboration tools

### Analytics & Reporting
- Real-time dashboard metrics
- Deal pipeline analytics
- Contact growth tracking
- Performance insights

### Team Collaboration
- Real-time messaging
- File sharing and attachments
- Role-based access control
- Activity notifications
                '''
            },
            'setup': {
                'title': 'Setup Guide',
                'content': '''
## Quick Start Guide

### 1. Deploy the Template
```bash
# Clone the repository
git clone <repository-url>
cd crm-ops-template

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 2. Database Setup
```bash
# Run migrations
alembic upgrade head

# Seed initial data (optional)
python scripts/seed_demo_data.py
```

### 3. Configure Integrations
- Set up AWS SES for email notifications
- Configure Stripe for billing
- Set up S3 for file storage
- Configure Redis for caching

### 4. Test the System
- Create a test tenant
- Complete the onboarding flow
- Test contact import/export
- Verify email notifications
                '''
            },
            'api_documentation': {
                'title': 'API Documentation',
                'content': '''
## REST API Endpoints

### Authentication
All API requests require authentication via JWT tokens.

### Contacts API
```
GET    /api/contacts                    # List contacts
POST   /api/contacts                    # Create contact
GET    /api/contacts/{id}               # Get contact
PUT    /api/contacts/{id}               # Update contact
DELETE /api/contacts/{id}               # Delete contact
POST   /api/contacts/import             # Import CSV
GET    /api/contacts/export.csv         # Export CSV
```

### Deals API
```
GET    /api/deals                       # List deals
POST   /api/deals                       # Create deal
GET    /api/deals/{id}                  # Get deal
PUT    /api/deals/{id}                  # Update deal
PATCH  /api/deals/{id}/status           # Update status
DELETE /api/deals/{id}                  # Delete deal
GET    /api/deals/export.csv            # Export CSV
```

### Projects API
```
GET    /api/projects                    # List projects
POST   /api/projects                    # Create project
GET    /api/projects/{id}               # Get project
PUT    /api/projects/{id}               # Update project
DELETE /api/projects/{id}               # Delete project
```

### Tasks API
```
GET    /api/tasks                       # List tasks
POST   /api/tasks                       # Create task
GET    /api/tasks/{id}                  # Get task
PUT    /api/tasks/{id}                  # Update task
PATCH  /api/tasks/{id}/status           # Update status
DELETE /api/tasks/{id}                  # Delete task
```

### Analytics API
```
GET    /api/analytics/crm               # CRM analytics
GET    /api/analytics/ops               # Operations analytics
GET    /api/analytics/activities        # Activity analytics
```

### Admin API
```
GET    /api/admin/subscriptions         # Get subscription info
PUT    /api/admin/subscriptions         # Update subscription
GET    /api/admin/domains               # Get domain info
POST   /api/admin/domains               # Add domain
GET    /api/admin/users                 # Get users
PUT    /api/admin/users/{id}/role       # Update user role
POST   /api/admin/demo-seed             # Seed demo data
```

## Response Format
All API responses follow the JSON:API 1.0 specification:

```json
{
  "data": {
    "id": "contact_123",
    "type": "contact",
    "attributes": {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com"
    }
  }
}
```

## Error Handling
Errors follow a consistent format:

```json
{
  "errors": [
    {
      "status": 400,
      "code": "VALIDATION_ERROR",
      "detail": "Field is required"
    }
  ]
}
```
                '''
            },
            'rbac': {
                'title': 'Role-Based Access Control',
                'content': '''
## RBAC Overview

The CRM/Ops Template implements a comprehensive role-based access control system with four main roles:

### Role Hierarchy
1. **Owner** - Full system access
2. **Admin** - Administrative access
3. **Member** - Standard user access
4. **Viewer** - Read-only access

### Permission Matrix

| Resource | Owner | Admin | Member | Viewer |
|----------|-------|-------|--------|--------|
| Contacts | CRUD | CRUD | CRUD | R |
| Deals | CRUD | CRUD | CRUD | R |
| Projects | CRUD | CRUD | CRUD | R |
| Tasks | CRUD | CRUD | CRUD | R |
| Analytics | R | R | R | R |
| Admin Settings | CRUD | CRUD | - | - |
| User Management | CRUD | CRUD | - | - |
| Billing | CRUD | CRUD | - | - |

### Field-Level Security
- **Owner/Admin**: Access to all fields including custom fields
- **Member**: Access to standard fields, limited custom field access
- **Viewer**: Access to basic fields only

### API Permissions
All API endpoints are protected by role-based permissions. Users can only access resources and perform actions according to their role.
                '''
            },
            'csv_format': {
                'title': 'CSV Import/Export Format',
                'content': '''
## CSV Import Format

### Required Fields
- `first_name` - Contact's first name
- `last_name` - Contact's last name

### Optional Fields
- `email` - Contact's email address
- `phone` - Contact's phone number
- `company` - Contact's company
- `tags` - Comma-separated list of tags

### Custom Fields
Any additional columns will be stored in the `custom_fields` JSON field.

### Example CSV
```csv
first_name,last_name,email,phone,company,tags,linkedin_url
John,Doe,john@example.com,+1234567890,Acme Corp,"lead,customer",https://linkedin.com/in/johndoe
Jane,Smith,jane@example.com,+1234567891,Tech Inc,"prospect",https://linkedin.com/in/janesmith
```

## CSV Export Format

### Contacts Export
Exports include all standard fields plus custom fields as separate columns.

### Deals Export
```csv
title,contact_id,pipeline_stage,value,status,notes,expected_close_date
Enterprise Deal,contact_123,proposal,50000,open,Key decision maker,2024-02-15
SMB Deal,contact_456,negotiation,15000,open,Final contract review,2024-01-30
```

### Export Filters
- Search by name, email, or company
- Filter by status (active/inactive)
- Filter by tags
- Date range filtering
- Limit to 50,000 records per export
                '''
            },
            'onboarding': {
                'title': 'Onboarding Guide',
                'content': '''
## First-Run Onboarding

### Automatic Redirect
New tenants are automatically redirected to the onboarding wizard on first login.

### Onboarding Steps

1. **Company Profile**
   - Company name
   - Brand color selection

2. **Team Invitations**
   - Invite team members by email
   - Assign roles (Admin, Member, Viewer)
   - Send invitation emails

3. **Plan Selection**
   - Choose subscription plan
   - Configure billing settings

4. **Data Import**
   - Load demo data
   - Import CSV file
   - Start with empty workspace

5. **Completion**
   - Review setup
   - Access dashboard

### Demo Data
The system includes realistic demo data:
- 20 sample contacts
- 5 sample deals
- 2 sample projects
- 8 tasks per project
- Sample activities and messages

### Customization
- Modify demo data parameters
- Customize onboarding flow
- Add additional steps
                '''
            },
            'analytics': {
                'title': 'Analytics & Reporting',
                'content': '''
## Analytics Overview

### CRM Analytics
- Contact growth trends
- Deal pipeline metrics
- Win/loss ratios
- Revenue forecasting
- Activity tracking

### Operations Analytics
- Project completion rates
- Task performance metrics
- Team productivity
- Time tracking insights
- Resource utilization

### Activity Analytics
- Communication patterns
- Meeting frequency
- Task completion rates
- User engagement metrics

### Custom Reports
- Build custom dashboards
- Export data for external analysis
- Schedule automated reports
- Real-time metrics

### Data Export
- CSV export for all entities
- API access for custom integrations
- Webhook notifications
- Real-time data streaming
                '''
            },
            'extensibility': {
                'title': 'Extensibility Points',
                'content': '''
## Plugin System

### Available Hooks
- `auth.user.created` - New user registration
- `contact.created` - New contact added
- `deal.stage_changed` - Deal pipeline movement
- `task.completed` - Task completion
- `project.archived` - Project archiving

### Custom Integrations
- Webhook endpoints
- API extensions
- Custom workflows
- Third-party integrations

### Development
- Plugin SDK
- Sandboxed execution
- Permission system
- Audit logging

### Marketplace
- Share custom plugins
- Install community plugins
- Version management
- Security scanning
                '''
            },
            'troubleshooting': {
                'title': 'Troubleshooting',
                'content': '''
## Common Issues

### Import/Export Issues
- **Large CSV files**: Limit to 10MB, 50k rows
- **Encoding problems**: Use UTF-8 encoding
- **Missing required fields**: Ensure first_name and last_name are present
- **Duplicate emails**: System will update existing contacts

### Email Notifications
- **SES configuration**: Verify AWS SES setup
- **Email templates**: Check template syntax
- **Delivery issues**: Monitor SES bounce/complaint rates

### Performance Issues
- **Database queries**: Check query performance
- **Caching**: Verify Redis configuration
- **File uploads**: Monitor S3 connectivity

### Security Issues
- **RBAC**: Verify role assignments
- **API access**: Check authentication tokens
- **Data isolation**: Confirm tenant boundaries

## Support
- Documentation: `/ui/docs/crm`
- API Reference: `/api/docs`
- Community: GitHub Discussions
- Support: support@example.com
                '''
            }
        }
    
    @staticmethod
    def get_support_info() -> Dict[str, Any]:
        """Get support information"""
        return {
            'documentation_url': '/ui/docs/crm',
            'api_docs_url': '/api/docs',
            'github_url': 'https://github.com/example/crm-ops-template',
            'support_email': 'support@example.com',
            'community_url': 'https://github.com/example/crm-ops-template/discussions',
            'status_page': 'https://status.example.com',
            'changelog_url': 'https://github.com/example/crm-ops-template/releases'
        }
