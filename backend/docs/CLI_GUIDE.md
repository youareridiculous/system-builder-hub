# SBH CLI Guide

The SBH CLI provides a comprehensive command-line interface for managing SBH scaffolds, templates, and deployments.

## Installation

```bash
# Install globally
npm install -g @sbh/cli

# Or use npx
npx @sbh/cli --help
```

## Authentication

Before using the CLI, you need to authenticate with your SBH account:

```bash
# Interactive login
sbh login

# Login with token
sbh login --token your-api-token

# Login with custom API URL
sbh login --api-url https://your-sbh-instance.com
```

## Project Management

### Initialize a New Project

```bash
# Interactive initialization
sbh init

# Initialize with specific template
sbh init --template flagship-crm

# Initialize with custom name
sbh init --name my-crm-project

# Non-interactive mode
sbh init --template flagship-crm --name my-project --no-interactive
```

### Run Project Locally

```bash
# Start development server
sbh run

# Run in development mode
sbh run --dev

# Run with database migrations
sbh run --migrate

# Run on specific port
sbh run --port 8000

# Run on specific host
sbh run --host 0.0.0.0
```

### Run Smoke Tests

```bash
# Run all tests
sbh smoke

# Run specific tests
sbh smoke --tests unit_tests,seed_verify

# Verbose output
sbh smoke --verbose

# Set timeout
sbh smoke --timeout 600
```

### Deploy Project

```bash
# Export deployment bundle
sbh deploy --export

# Deploy to AWS Elastic Beanstalk
sbh deploy --platform aws

# Deploy to Render
sbh deploy --platform render

# Deploy with custom environment
sbh deploy --platform aws --environment staging
```

## Marketplace Operations

### List Templates

```bash
# List all templates
sbh marketplace list

# Filter by category
sbh marketplace list --category "Sales & Ops"

# Search templates
sbh marketplace list --search "crm"

# Filter by tags
sbh marketplace list --tags "ai,automations"
```

### Launch Templates

```bash
# Launch template interactively
sbh marketplace launch flagship-crm

# Launch with specific name
sbh marketplace launch flagship-crm --name "My CRM"

# Launch with custom plan
sbh marketplace launch flagship-crm --plan pro

# Launch without demo data
sbh marketplace launch flagship-crm --no-seed-demo
```

## Configuration

The CLI stores configuration in `~/.config/sbh-cli/config.json`:

```json
{
  "apiToken": "your-api-token",
  "apiUrl": "http://localhost:5001",
  "tenantId": "your-tenant-id",
  "defaultTemplate": "flagship-crm",
  "lastLogin": "2024-01-01T00:00:00Z"
}
```

## Environment Variables

- `SBH_API_TOKEN` - API token for authentication
- `SBH_API_URL` - SBH API URL
- `SBH_TENANT_ID` - Default tenant ID
- `SBH_DEFAULT_TEMPLATE` - Default template for new projects

## Examples

### Complete Workflow

```bash
# 1. Login to SBH
sbh login

# 2. Browse available templates
sbh marketplace list

# 3. Initialize a new project
sbh init --template flagship-crm --name my-crm

# 4. Run the project locally
sbh run --dev

# 5. Run tests
sbh smoke

# 6. Deploy to production
sbh deploy --platform aws
```

### Development Workflow

```bash
# Start development
sbh run --dev --migrate

# In another terminal, run tests
sbh smoke --tests unit_tests

# Deploy changes
sbh deploy --export
```

### Template Management

```bash
# List all CRM templates
sbh marketplace list --category "Sales & Ops"

# Launch multiple instances
sbh marketplace launch flagship-crm --name "CRM-Prod"
sbh marketplace launch flagship-crm --name "CRM-Staging"
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   ```bash
   # Clear stored credentials
   rm ~/.config/sbh-cli/config.json
   sbh login
   ```

2. **Project Not Found**
   ```bash
   # Ensure you're in the right directory
   ls -la .sbh/project.json
   ```

3. **Dependencies Missing**
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   ```

4. **Port Already in Use**
   ```bash
   # Use different port
   sbh run --port 8001
   ```

### Debug Mode

Enable debug output:

```bash
# Set debug environment variable
export DEBUG=sbh:*

# Run commands with debug info
sbh run --dev
```

## Security

- API tokens are stored securely in the system keychain
- All API requests use HTTPS
- Sensitive data is not logged
- Audit logs are maintained for all CLI actions

## Rate Limits

- Template launches: 5 per hour per tenant
- Scaffold generation: 5 per day per tenant
- API requests: Standard rate limits apply

## Support

For issues and questions:

- Check the troubleshooting section above
- Review the SBH documentation
- Contact support at support@sbh.com
- Join the community at community.sbh.com
