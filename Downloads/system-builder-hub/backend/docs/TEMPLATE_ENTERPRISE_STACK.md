# Enterprise Stack Template Guide

This document explains the Enterprise Stack template, a comprehensive multi-tenant SaaS solution with Auth, Subscriptions, Files, CRUD, Analytics, and Custom Domains.

## Overview

The Enterprise Stack template provides:

- **Multi-tenant Architecture**: Complete tenant isolation and management
- **Authentication & Authorization**: JWT-based auth with role-based access
- **Subscription Management**: Stripe integration with plan-based features
- **File Storage**: S3-based file management with upload/download
- **CRUD Operations**: Projects and tasks with full CRUD capabilities
- **Analytics Dashboard**: Comprehensive analytics and reporting
- **Custom Domains**: Tenant-specific domain management
- **Admin Interface**: Complete admin dashboard for management

## Template Structure

### Models

#### Authentication (`auth`)
- **Provider**: JWT
- **Features**: Session management, refresh tokens, password policies
- **Configuration**: Configurable session duration and security policies

#### Payment (`payment`)
- **Provider**: Stripe
- **Features**: Subscription management, webhook handling
- **Configuration**: Webhook endpoints, usage billing options

#### File Store (`file_store`)
- **Provider**: S3 (production) / Local (development)
- **Features**: File upload/download, bucket management
- **Configuration**: Bucket naming, region, access policies

### Database Tables

#### Accounts
```sql
CREATE TABLE accounts (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    plan VARCHAR(50) NOT NULL DEFAULT 'basic',
    custom_domain VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
```

#### Users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
```

#### Projects
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
```

#### Tasks
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'todo',
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date TIMESTAMP,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
```

### APIs

#### Projects API (`/api/projects`)
- **Methods**: GET, POST, PUT, DELETE
- **Authentication**: Required
- **Subscription**: Required
- **Features**: Full CRUD operations for projects

#### Tasks API (`/api/tasks`)
- **Methods**: GET, POST, PUT, DELETE
- **Authentication**: Required
- **Subscription**: Required
- **Features**: Full CRUD operations for tasks

#### Users API (`/api/users`)
- **Methods**: GET, PUT
- **Authentication**: Required
- **Subscription**: Not required
- **Features**: User profile management

### Pages

#### Authentication Pages
- **Login** (`/ui/login`): User authentication
- **Register** (`/ui/register`): User registration

#### Main Application
- **Dashboard** (`/ui/dashboard`): Main application dashboard
- **Projects** (`/ui/projects`): Project management interface
- **Tasks** (`/ui/tasks`): Task management interface
- **Files** (`/ui/files`): File management interface
- **Billing** (`/ui/billing`): Subscription and billing management

#### Admin Pages
- **Analytics** (`/ui/admin/analytics`): Analytics dashboard (Pro+)
- **Domains** (`/ui/admin/domains`): Custom domain management (Pro+)
- **Integrations** (`/ui/admin/integrations`): API keys and webhooks (Pro+)

## Guided Prompt Schema

### Company Information
- **Company Name**: Your company or organization name
- **Primary Color**: Brand color (hex code)
- **Enable Custom Domains**: Allow customers to use their own domains

### Subscription Plans
Default plans included:

#### Basic ($29/month)
- Up to 10 projects
- Basic analytics
- Email support

#### Pro ($99/month)
- Unlimited projects
- Advanced analytics
- Custom domains
- Priority support
- API access

#### Enterprise ($299/month)
- Everything in Pro
- SSO integration
- Dedicated support
- Custom integrations
- Advanced security

### Demo Options
- **Seed Demo Data**: Create sample projects and tasks
- **Demo Tenant Slug**: Slug for the demo tenant

## Feature Flags

The template includes feature flags for plan-based access:

- **custom_domains**: Enable custom domain support
- **advanced_analytics**: Enable advanced analytics features
- **api_access**: Enable API access
- **sso_integration**: Enable SSO integration (Enterprise)
- **dedicated_support**: Enable dedicated support (Enterprise)

## Usage

### 1. Template Selection
Navigate to the Marketplace and select "Enterprise Stack"

### 2. Guided Configuration
Fill out the guided prompt form:
- Enter your company name and brand color
- Choose subscription plan structure
- Enable/disable custom domains
- Configure demo data options

### 3. Template Deployment
Click "Use Template" to:
- Generate BuilderState from guided input
- Create database migrations
- Set up authentication and payment providers
- Configure file storage
- Deploy the application

### 4. Demo Data Seeding
If demo seeding is enabled:
- Creates sample account and users
- Generates demo projects and tasks
- Uploads placeholder files
- Sends welcome email

## Customization

### Adding Custom Fields
To add custom fields to projects or tasks:

1. **Database Migration**: Use the `db.migrate` tool to add columns
2. **API Updates**: Extend the API endpoints
3. **UI Updates**: Update the frontend forms and displays

### Custom Integrations
To add custom integrations:

1. **Webhook Configuration**: Add webhook endpoints
2. **API Extensions**: Create new API endpoints
3. **Admin Interface**: Add integration management pages

### Branding Customization
To customize branding:

1. **Colors**: Update the primary color in guided input
2. **Logo**: Replace logo assets
3. **Email Templates**: Customize email templates
4. **Domain**: Configure custom domains

## Deployment

### Environment Configuration
```bash
# Required environment variables
AUTH_JWT_SECRET=your_jwt_secret
STRIPE_SECRET_KEY=your_stripe_secret
STRIPE_WEBHOOK_SECRET=your_webhook_secret
S3_BUCKET_NAME=your_s3_bucket
S3_REGION=us-east-1
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
```

### Database Setup
The template automatically creates:
- Database tables with proper relationships
- Indexes for performance
- Foreign key constraints
- Multi-tenant isolation

### File Storage Setup
Configure S3 bucket:
- Create bucket with appropriate permissions
- Configure CORS for file uploads
- Set up lifecycle policies for file management

### Email Configuration
Configure email provider:
- Set up SES or other email provider
- Configure email templates
- Test email delivery

## Monitoring & Analytics

### Built-in Analytics
The template includes:
- User activity tracking
- Subscription metrics
- API usage monitoring
- File upload/download statistics

### Admin Dashboard
Access admin features at `/ui/admin/analytics`:
- KPI cards with key metrics
- Charts and graphs
- Event filtering and export
- Real-time monitoring

## Security

### Authentication Security
- JWT tokens with configurable expiration
- Password policies and validation
- Role-based access control
- Session management

### Data Security
- Multi-tenant data isolation
- SQL injection prevention
- XSS protection
- CSRF protection

### API Security
- Rate limiting
- API key authentication
- Request validation
- Error handling

## Troubleshooting

### Common Issues

#### Database Migration Errors
```bash
# Check migration status
python -c "from src.releases.service import ReleaseService; print(ReleaseService().get_releases('tenant-id'))"

# Rollback failed migration
curl -X POST /api/releases/rollback -d '{"release_id": "rel_20240115_1200"}'
```

#### File Upload Issues
```bash
# Check S3 configuration
aws s3 ls s3://your-bucket-name

# Test file upload
curl -X POST /api/files/upload -F "file=@test.txt"
```

#### Email Delivery Issues
```bash
# Test email configuration
curl -X POST /api/admin/integrations/test-email \
  -d '{"to_email": "test@example.com", "template": "welcome"}'
```

### Support

For Enterprise Stack template support:
- **Basic Plan**: Email support
- **Pro Plan**: Priority support
- **Enterprise Plan**: Dedicated support

## Best Practices

### Development
1. **Use Feature Flags**: Gate new features by subscription plan
2. **Test Migrations**: Always test migrations in staging first
3. **Monitor Analytics**: Track user engagement and feature usage
4. **Security First**: Implement proper authentication and authorization

### Production
1. **Environment Separation**: Use separate environments for dev/staging/prod
2. **Database Backups**: Regular database backups and testing
3. **Monitoring**: Set up comprehensive monitoring and alerting
4. **Scaling**: Plan for horizontal scaling as user base grows

### Maintenance
1. **Regular Updates**: Keep dependencies and security patches updated
2. **Performance Monitoring**: Monitor application performance
3. **User Feedback**: Collect and act on user feedback
4. **Feature Iteration**: Continuously improve based on usage data
