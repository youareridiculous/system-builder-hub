#!/usr/bin/env python3
"""
System Builder Hub - Enhanced Server with OpenAI Integration and System Generation

Configuration:
- OPENAI_API_KEY: Required in production (provided via ECS task definition secrets)
- OPENAI_MODEL: Default gpt-4o-mini
- OPENAI_TIMEOUT_SECONDS: Default 20 seconds
"""
import os
import time
import uuid
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from flask import Flask, jsonify, request
from flask_cors import CORS
import openai
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_openai_config() -> Dict[str, Any]:
    """Get OpenAI configuration from environment variables"""
    return {
        'api_key': os.getenv('OPENAI_API_KEY'),
        'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        'timeout': int(os.getenv('OPENAI_TIMEOUT_SECONDS', '20'))
    }

def create_openai_client() -> Optional[OpenAI]:
    """Create OpenAI client if API key is available"""
    config = get_openai_config()
    if not config['api_key']:
        return None
    
    try:
        return OpenAI(
            api_key=config['api_key'],
            timeout=config['timeout']
        )
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {e}")
        return None

def generate_system_architecture(spec):
    """Generate system architecture based on specifications"""
    architecture = {
        'components': [],
        'dataFlow': [],
        'infrastructure': [],
        'security': [],
        'scalability': []
    }
    
    # Add components based on system type
    if spec['type'] == 'web-app':
        architecture['components'] = [
            {'name': 'Frontend', 'type': 'React App', 'port': 3000},
            {'name': 'Backend API', 'type': 'Node.js/Express', 'port': 8000},
            {'name': 'Database', 'type': 'PostgreSQL', 'port': 5432}
        ]
    elif spec['type'] == 'api':
        architecture['components'] = [
            {'name': 'API Gateway', 'type': 'Express.js', 'port': 8000},
            {'name': 'Database', 'type': 'PostgreSQL', 'port': 5432}
        ]
    elif spec['type'] == 'ecommerce-platform':
        architecture['components'] = [
            {'name': 'Frontend', 'type': 'Next.js', 'port': 3000},
            {'name': 'API Gateway', 'type': 'Node.js/Express', 'port': 8000},
            {'name': 'Payment Service', 'type': 'Stripe Integration', 'port': 8001},
            {'name': 'Database', 'type': 'PostgreSQL', 'port': 5432},
            {'name': 'File Storage', 'type': 'AWS S3', 'port': None}
        ]
    elif spec['type'] == 'data-pipeline':
        architecture['components'] = [
            {'name': 'Data Ingestion', 'type': 'AWS Lambda', 'port': None},
            {'name': 'Data Processing', 'type': 'AWS ECS', 'port': 8000},
            {'name': 'Data Storage', 'type': 'AWS S3', 'port': None},
            {'name': 'Data Warehouse', 'type': 'AWS Redshift', 'port': 5439}
        ]
    elif spec['type'] == 'ml-service':
        architecture['components'] = [
            {'name': 'Model API', 'type': 'FastAPI', 'port': 8000},
            {'name': 'Model Storage', 'type': 'AWS S3', 'port': None},
            {'name': 'Database', 'type': 'PostgreSQL', 'port': 5432},
            {'name': 'Monitoring', 'type': 'CloudWatch', 'port': None}
        ]
    elif spec['type'] == 'microservice':
        architecture['components'] = [
            {'name': 'Service API', 'type': 'Express.js', 'port': 8000},
            {'name': 'Database', 'type': 'PostgreSQL', 'port': 5432},
            {'name': 'Message Queue', 'type': 'AWS SQS', 'port': None}
        ]
    elif spec['type'] == 'cms':
        architecture['components'] = [
            {'name': 'Frontend', 'type': 'Next.js', 'port': 3000},
            {'name': 'Admin Panel', 'type': 'React', 'port': 3001},
            {'name': 'API Gateway', 'type': 'Node.js/Express', 'port': 8000},
            {'name': 'Database', 'type': 'PostgreSQL', 'port': 5432},
            {'name': 'File Storage', 'type': 'AWS S3', 'port': None}
        ]
    elif spec['type'] == 'dashboard':
        architecture['components'] = [
            {'name': 'Dashboard UI', 'type': 'React', 'port': 3000},
            {'name': 'API Gateway', 'type': 'Node.js/Express', 'port': 8000},
            {'name': 'Data Processing', 'type': 'AWS Lambda', 'port': None},
            {'name': 'Database', 'type': 'PostgreSQL', 'port': 5432},
            {'name': 'Cache', 'type': 'Redis', 'port': 6379}
        ]
    
    # Add infrastructure based on selections
    if 'AWS ECS Fargate' in spec['infrastructure']:
        architecture['infrastructure'].append({
            'name': 'Container Orchestration',
            'type': 'AWS ECS Fargate',
            'description': 'Serverless container platform'
        })
    
    if 'AWS RDS' in spec['infrastructure']:
        architecture['infrastructure'].append({
            'name': 'Database',
            'type': 'AWS RDS PostgreSQL',
            'description': 'Managed PostgreSQL database'
        })
    
    if 'AWS S3' in spec['infrastructure']:
        architecture['infrastructure'].append({
            'name': 'File Storage',
            'type': 'AWS S3',
            'description': 'Object storage for files and assets'
        })
    
    if 'AWS ALB' in spec['infrastructure']:
        architecture['infrastructure'].append({
            'name': 'Load Balancer',
            'type': 'AWS Application Load Balancer',
            'description': 'Application load balancer for traffic distribution'
        })
    
    return architecture

def generate_system_templates(spec, architecture):
    """Generate real, working system templates and code"""
    templates = {
        'frontend': {},
        'backend': {},
        'infrastructure': {},
        'deployment': {}
    }
    
    # Generate real React/Next.js frontend
    if any('React' in tech for tech in spec['techStack']):
        templates['frontend'] = generate_react_frontend(spec, architecture)
    elif any('Next.js' in tech for tech in spec['techStack']):
        templates['frontend'] = generate_nextjs_frontend(spec, architecture)
    
    # Generate real Node.js/Python backend
    if any('Node.js' in tech for tech in spec['techStack']):
        templates['backend'] = generate_nodejs_backend(spec, architecture)
    elif any('Python' in tech for tech in spec['techStack']):
        templates['backend'] = generate_python_backend(spec, architecture)
    
    # Generate real Terraform infrastructure
    templates['infrastructure'] = generate_terraform_infrastructure(spec, architecture)
    
    # Generate real CI/CD pipeline
    templates['deployment'] = generate_cicd_pipeline(spec, architecture)
    
    # Add Docker Compose and deployment scripts
    templates['docker'] = generate_docker_setup(spec)
    templates['scripts'] = generate_deployment_scripts_wrapper(spec)
    
    # Add comprehensive documentation
    templates['docs'] = generate_documentation(spec)
    
    return templates

def generate_react_frontend(spec, architecture):
    """Generate real React frontend code"""
    return {
        'type': 'React',
        'files': [
            {
                'name': 'package.json',
                'content': generate_react_package_json(spec)
            },
            {
                'name': 'src/App.tsx',
                'content': generate_react_app_component(spec)
            },
            {
                'name': 'src/components/Header.tsx',
                'content': generate_react_header_component(spec)
            },
            {
                'name': 'src/pages/Home.tsx',
                'content': generate_react_home_page(spec)
            },
            {
                'name': 'tailwind.config.js',
                'content': generate_tailwind_config(spec)
            },
            {
                'name': 'tsconfig.json',
                'content': generate_typescript_config(spec)
            }
        ]
    }

def generate_nextjs_frontend(spec, architecture):
    """Generate real Next.js frontend code"""
    return {
        'type': 'Next.js',
        'files': [
            {
                'name': 'package.json',
                'content': generate_nextjs_package_json(spec)
            },
            {
                'name': 'pages/index.tsx',
                'content': generate_nextjs_index_page(spec)
            },
            {
                'name': 'components/Header.tsx',
                'content': generate_nextjs_header_component(spec)
            },
            {
                'name': 'components/Layout.tsx',
                'content': generate_nextjs_layout_component(spec)
            },
            {
                'name': 'tailwind.config.js',
                'content': generate_tailwind_config(spec)
            },
            {
                'name': 'next.config.js',
                'content': generate_nextjs_config(spec)
            },
            {
                'name': 'tsconfig.json',
                'content': generate_typescript_config(spec)
            }
        ]
    }

def generate_nodejs_backend(spec, architecture):
    """Generate real Node.js/Express backend"""
    files = [
        {
            'name': 'package.json',
            'content': generate_nodejs_package_json(spec)
        },
        {
            'name': 'src/app.js',
            'content': generate_express_app(spec)
        },
        {
            'name': 'src/routes/api.js',
            'content': generate_api_routes(spec)
        },
        {
            'name': 'src/models/index.js',
            'content': generate_database_models(spec)
        },
        {
            'name': 'src/middleware/auth.js',
            'content': generate_auth_middleware(spec)
        },
        {
            'name': 'Dockerfile',
            'content': generate_nodejs_dockerfile(spec)
        },
        {
            'name': '.env.example',
            'content': generate_env_example(spec)
        }
    ]
    
    # Add database migration files
    migrations = generate_database_migrations(spec)
    for migration in migrations:
        files.append({
            'name': f'database/migrations/{migration["name"]}',
            'content': migration['content']
        })
    
    # Add migration runner script
    files.append({
        'name': 'scripts/run-migrations.js',
        'content': generate_migration_runner(spec)
    })
    
    return {
        'type': 'Node.js/Express',
        'files': files
    }

def generate_python_backend(spec, architecture):
    """Generate real Python/FastAPI backend"""
    return {
        'type': 'Python/FastAPI',
        'files': [
            {
                'name': 'requirements.txt',
                'content': generate_python_requirements(spec)
            },
            {
                'name': 'src/main.py',
                'content': generate_fastapi_app(spec)
            },
            {
                'name': 'src/models.py',
                'content': generate_sqlalchemy_models(spec)
            },
            {
                'name': 'src/database.py',
                'content': generate_database_config(spec)
            },
            {
                'name': 'src/routes/api.py',
                'content': generate_fastapi_routes(spec)
            },
            {
                'name': 'src/middleware/auth.py',
                'content': generate_python_auth_middleware(spec)
            },
            {
                'name': 'Dockerfile',
                'content': generate_python_dockerfile(spec)
            },
            {
                'name': '.env.example',
                'content': generate_env_example(spec)
            }
        ]
    }

def generate_terraform_infrastructure(spec, architecture):
    """Generate real Terraform infrastructure"""
    return {
        'type': 'Terraform',
        'files': [
            {
                'name': 'main.tf',
                'content': generate_terraform_main(spec, architecture)
            },
            {
                'name': 'variables.tf',
                'content': generate_terraform_variables(spec)
            },
            {
                'name': 'outputs.tf',
                'content': generate_terraform_outputs(spec)
            },
            {
                'name': 'modules/vpc/main.tf',
                'content': generate_vpc_module(spec)
            },
            {
                'name': 'modules/ecs/main.tf',
                'content': generate_ecs_module(spec)
            },
            {
                'name': 'modules/rds/main.tf',
                'content': generate_rds_module(spec)
            },
            {
                'name': 'modules/alb/main.tf',
                'content': generate_alb_module(spec)
            }
        ]
    }

def generate_cicd_pipeline(spec, architecture):
    """Generate real GitHub Actions CI/CD pipeline"""
    return {
        'type': 'GitHub Actions',
        'files': [
            {
                'name': '.github/workflows/deploy.yml',
                'content': generate_github_actions_workflow(spec)
            },
            {
                'name': '.github/workflows/test.yml',
                'content': generate_test_workflow(spec)
            },
            {
                'name': '.github/workflows/security.yml',
                'content': generate_security_workflow(spec)
            }
        ]
    }

def generate_docker_setup(spec):
    """Generate Docker Compose setup"""
    return {
        'type': 'Docker Compose',
        'files': [
            {
                'name': 'docker-compose.yml',
                'content': generate_docker_compose(spec)
            },
            {
                'name': 'docker-compose.prod.yml',
                'content': generate_docker_compose_prod(spec)
            },
            {
                'name': '.env.example',
                'content': generate_docker_env_example(spec)
            }
        ]
    }

def generate_deployment_scripts_wrapper(spec):
    """Generate deployment scripts for multiple cloud providers"""
    scripts = generate_deployment_scripts(spec)
    return {
        'type': 'Deployment Scripts',
        'files': scripts
    }

def generate_docker_compose_prod(spec):
    """Generate production Docker Compose"""
    system_name = spec['name'].lower().replace(' ', '-').replace('_', '-')
    
    return f'''version: '3.8'

services:
  # Backend API (Production)
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: {system_name}-backend-prod
    environment:
      NODE_ENV: production
      DATABASE_URL: ${{DATABASE_URL}}
      REDIS_URL: ${{REDIS_URL}}
      PORT: 8000
    ports:
      - "8000:8000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'

  # Frontend (Production)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: {system_name}-frontend-prod
    environment:
      NEXT_PUBLIC_API_URL: ${{NEXT_PUBLIC_API_URL}}
      NODE_ENV: production
    ports:
      - "3000:3000"
    restart: unless-stopped
    depends_on:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
        reservations:
          memory: 128M
          cpus: '0.1'

networks:
  default:
    name: {system_name}-network-prod
'''

def generate_docker_env_example(spec):
    """Generate Docker environment example"""
    system_name = spec['name'].lower().replace(' ', '-').replace('_', '-')
    
    return f'''# {spec['name']} Environment Configuration
# Copy this file to .env and update the values

# Database Configuration
DATABASE_URL=postgresql://{system_name}_user:{system_name}_password@localhost:5432/{system_name}

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Application Configuration
NODE_ENV=development
PORT=8000
NEXT_PUBLIC_API_URL=http://localhost:8000

# Security
JWT_SECRET=your-super-secret-jwt-key-here
SESSION_SECRET=your-super-secret-session-key-here

# AWS Configuration (for production)
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET_NAME=your-s3-bucket-name

# Email Configuration (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# External APIs (optional)
OPENAI_API_KEY=your-openai-api-key
STRIPE_SECRET_KEY=your-stripe-secret-key
'''

def generate_documentation(spec):
    """Generate comprehensive documentation"""
    return {
        'type': 'Documentation',
        'files': [
            {
                'name': 'README.md',
                'content': generate_comprehensive_readme(spec)
            },
            {
                'name': 'DEPLOYMENT.md',
                'content': generate_deployment_guide(spec)
            },
            {
                'name': 'API.md',
                'content': generate_api_documentation(spec)
            }
        ]
    }

def generate_deployment_guide(spec):
    """Generate detailed deployment guide"""
    system_name = spec['name']
    
    return f'''# {system_name} - Deployment Guide

**Generated by System Builder Hub (SBH)**

## 🚀 Deployment Options

### 1. AWS Deployment (Recommended)

#### Prerequisites
- AWS CLI configured
- Docker installed
- AWS account with appropriate permissions

#### Steps
1. **Configure AWS CLI:**
   ```bash
   aws configure
   ```

2. **Set environment variables:**
   ```bash
   export AWS_ACCOUNT_ID=your-account-id
   export AWS_REGION=us-west-2
   ```

3. **Deploy:**
   ```bash
   chmod +x deploy-aws.sh
   ./deploy-aws.sh
   ```

#### What gets deployed:
- ECS Fargate cluster
- RDS PostgreSQL database
- Application Load Balancer
- CloudFront distribution
- Route 53 DNS (if configured)

### 2. Google Cloud Platform

#### Prerequisites
- Google Cloud CLI installed
- Docker installed
- GCP project with billing enabled

#### Steps
1. **Authenticate:**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Deploy:**
   ```bash
   chmod +x deploy-gcp.sh
   ./deploy-gcp.sh
   ```

### 3. Microsoft Azure

#### Prerequisites
- Azure CLI installed
- Docker installed
- Azure subscription

#### Steps
1. **Authenticate:**
   ```bash
   az login
   az account set --subscription YOUR_SUBSCRIPTION_ID
   ```

2. **Deploy:**
   ```bash
   chmod +x deploy-azure.sh
   ./deploy-azure.sh
   ```

### 4. Docker Compose (Any Server)

#### Prerequisites
- Docker and Docker Compose
- Server with public IP
- Domain name (optional)

#### Steps
1. **Upload files to server:**
   ```bash
   scp -r . user@your-server:/path/to/app
   ```

2. **Deploy:**
   ```bash
   ssh user@your-server
   cd /path/to/app
   docker-compose -f docker-compose.prod.yml up -d
   ```

## 🔧 Environment Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# Application
NODE_ENV=production
PORT=8000
JWT_SECRET=your-super-secret-jwt-key

# External Services (if used)
OPENAI_API_KEY=your-openai-key
STRIPE_SECRET_KEY=your-stripe-key
```

### AWS-Specific Variables
```bash
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=your-bucket-name
```

## 📊 Monitoring & Health Checks

### Health Endpoints
- **Application**: `GET /health`
- **Database**: Connection status in health check
- **External APIs**: Service availability

### Logs
```bash
# AWS ECS
aws logs tail /ecs/{system_name.lower().replace(' ', '-')} --follow

# Docker Compose
docker-compose logs -f backend
```

## 🔒 Security Considerations

### Production Security
- Use strong JWT secrets
- Enable HTTPS/TLS
- Configure CORS properly
- Use environment variables for secrets
- Regular security updates

### Database Security
- Use connection encryption
- Regular backups
- Access control
- Parameterized queries

## 🆘 Troubleshooting

### Common Issues

1. **Deployment Fails:**
   - Check AWS/GCP/Azure credentials
   - Verify Docker is running
   - Check resource limits

2. **Database Connection Issues:**
   - Verify DATABASE_URL format
   - Check network connectivity
   - Verify database exists

3. **Application Won't Start:**
   - Check environment variables
   - Verify port availability
   - Check application logs

## 📞 Support

- **Documentation**: This guide
- **Issues**: GitHub Issues
- **Generated by**: System Builder Hub (SBH)
'''

def generate_api_documentation(spec):
    """Generate API documentation"""
    system_name = spec['name']
    system_type = spec.get('type', 'web-app')
    features = spec.get('features', [])
    
    api_doc = f'''# {system_name} - API Documentation

**Generated by System Builder Hub (SBH)**

## Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

## Authentication

All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### Health Check
- **GET** `/health`
- **Description**: Check application health
- **Response**: `{{"status": "healthy", "timestamp": "..."}}`

### Authentication

#### Login
- **POST** `/api/auth/login`
- **Body**: `{{"email": "user@example.com", "password": "password"}}`
- **Response**: `{{"token": "jwt-token", "user": {{"id": 1, "email": "..."}}}}`

#### Register
- **POST** `/api/auth/register`
- **Body**: `{{"email": "user@example.com", "password": "password", "name": "User Name"}}`
- **Response**: `{{"token": "jwt-token", "user": {{"id": 1, "email": "..."}}}}`

#### Profile
- **GET** `/api/auth/profile`
- **Headers**: `Authorization: Bearer <token>`
- **Response**: `{{"id": 1, "email": "user@example.com", "name": "User Name"}}`
'''

    if system_type == 'web-app' and any('content' in feature.lower() or 'post' in feature.lower() for feature in features):
        api_doc += '''
### Posts (Content Management)

#### List Posts
- **GET** `/api/posts`
- **Query Parameters**: `?limit=10&offset=0&status=published`
- **Response**: `[{"id": 1, "title": "...", "content": "...", "author": {...}}]`

#### Get Post
- **GET** `/api/posts/:id`
- **Response**: `{"id": 1, "title": "...", "content": "...", "author": {...}}`

#### Create Post
- **POST** `/api/posts`
- **Headers**: `Authorization: Bearer <token>`
- **Body**: `{"title": "Post Title", "content": "Post content"}`
- **Response**: `{"id": 1, "title": "...", "content": "...", "status": "draft"}`

#### Update Post
- **PUT** `/api/posts/:id`
- **Headers**: `Authorization: Bearer <token>`
- **Body**: `{"title": "Updated Title", "content": "Updated content"}`
- **Response**: `{"id": 1, "title": "...", "content": "...", "updated_at": "..."}`

#### Delete Post
- **DELETE** `/api/posts/:id`
- **Headers**: `Authorization: Bearer <token>`
- **Response**: `{"message": "Post deleted successfully"}`
'''

    if system_type == 'web-app' and any('comment' in feature.lower() or 'interaction' in feature.lower() for feature in features):
        api_doc += '''
### Comments (User Interactions)

#### List Comments
- **GET** `/api/posts/:postId/comments`
- **Query Parameters**: `?limit=50&offset=0`
- **Response**: `[{"id": 1, "content": "...", "author": {...}, "created_at": "..."}]`

#### Create Comment
- **POST** `/api/posts/:postId/comments`
- **Headers**: `Authorization: Bearer <token>`
- **Body**: `{"content": "Comment content"}`
- **Response**: `{"id": 1, "content": "...", "author": {...}, "created_at": "..."}`

#### Update Comment
- **PUT** `/api/comments/:id`
- **Headers**: `Authorization: Bearer <token>`
- **Body**: `{"content": "Updated comment content"}`
- **Response**: `{"id": 1, "content": "...", "updated_at": "..."}`

#### Delete Comment
- **DELETE** `/api/comments/:id`
- **Headers**: `Authorization: Bearer <token>`
- **Response**: `{"message": "Comment deleted successfully"}`
'''

    api_doc += '''
## Error Responses

### 400 Bad Request
```json
{
  "error": "Validation failed",
  "details": ["Email is required", "Password must be at least 8 characters"]
}
```

### 401 Unauthorized
```json
{
  "error": "Authentication required",
  "message": "Please provide a valid JWT token"
}
```

### 403 Forbidden
```json
{
  "error": "Access denied",
  "message": "You don't have permission to perform this action"
}
```

### 404 Not Found
```json
{
  "error": "Resource not found",
  "message": "The requested resource does not exist"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred"
}
```

## Rate Limiting

- **Limit**: 100 requests per minute per IP
- **Headers**: 
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset time

## Testing

### Using curl
```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email": "user@example.com", "password": "password"}'

# Get posts (with token)
curl http://localhost:8000/api/posts \\
  -H "Authorization: Bearer <your-token>"
```

### Using Postman
1. Import the API collection
2. Set base URL to your application URL
3. Configure authentication token
4. Test endpoints

## Generated by System Builder Hub (SBH)
'''

    return api_doc

def generate_deployment_config(spec, architecture):
    """Generate deployment configuration"""
    return {
        'platform': 'AWS',
        'services': [
            {'name': 'ECS Fargate', 'status': 'configured'},
            {'name': 'RDS PostgreSQL', 'status': 'configured'},
            {'name': 'S3 Bucket', 'status': 'configured'},
            {'name': 'Application Load Balancer', 'status': 'configured'}
        ],
        'ci_cd': {
            'platform': 'GitHub Actions',
            'workflows': ['build.yml', 'deploy.yml', 'test.yml']
        },
        'monitoring': {
            'platform': 'CloudWatch',
            'alarms': ['cpu_utilization', 'memory_utilization', 'error_rate']
        }
    }

# Enhanced template generation functions
def generate_react_package_json(spec):
    """Generate real package.json for React"""
    return json.dumps({
        "name": spec['name'].lower().replace(' ', '-'),
        "version": "1.0.0",
        "private": True,
        "scripts": {
            "dev": "react-scripts start",
            "build": "react-scripts build",
            "test": "react-scripts test",
            "eject": "react-scripts eject"
        },
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "react-router-dom": "^6.8.0",
            "axios": "^1.4.0",
            "tailwindcss": "^3.3.5",
            "lucide-react": "^0.292.0"
        },
        "devDependencies": {
            "@types/react": "^18.2.0",
            "@types/react-dom": "^18.2.0",
            "typescript": "^5.2.0",
            "react-scripts": "5.0.1"
        }
    }, indent=2)

def generate_nextjs_package_json(spec):
    """Generate real package.json for Next.js"""
    return json.dumps({
        "name": spec['name'].lower().replace(' ', '-'),
        "version": "1.0.0",
        "private": True,
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "lint": "next lint"
        },
        "dependencies": {
            "next": "14.0.0",
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "axios": "^1.4.0",
            "tailwindcss": "^3.3.5",
            "lucide-react": "^0.292.0"
        },
        "devDependencies": {
            "@types/node": "^20.0.0",
            "@types/react": "^18.2.0",
            "@types/react-dom": "^18.2.0",
            "typescript": "^5.2.0"
        }
    }, indent=2)

def generate_nodejs_package_json(spec):
    """Generate real package.json for Node.js backend"""
    return json.dumps({
        "name": f"{spec['name'].lower().replace(' ', '-')}-backend",
        "version": "1.0.0",
        "description": f"Backend API for {spec['name']}",
        "main": "src/app.js",
        "scripts": {
            "start": "node src/app.js",
            "dev": "nodemon src/app.js",
            "test": "jest",
            "lint": "eslint src/"
        },
        "dependencies": {
            "express": "^4.18.0",
            "cors": "^2.8.5",
            "helmet": "^7.0.0",
            "pg": "^8.11.0",
            "bcryptjs": "^2.4.3",
            "jsonwebtoken": "^9.0.0",
            "dotenv": "^16.0.0",
            "joi": "^17.9.0"
        },
        "devDependencies": {
            "nodemon": "^3.0.0",
            "jest": "^29.0.0",
            "eslint": "^8.0.0"
        }
    }, indent=2)

def generate_python_requirements(spec):
    """Generate real requirements.txt for Python backend"""
    return f"""fastapi==0.104.1
uvicorn==0.24.0
psycopg2-binary==2.9.9
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
pydantic==2.4.0
sqlalchemy==2.0.0
alembic==1.12.0
pytest==7.4.0
pytest-asyncio==0.21.0
"""

def generate_express_app(spec):
    """Generate real Express.js app"""
    return f'''const express = require('express')
const cors = require('cors')
const helmet = require('helmet')
const dotenv = require('dotenv')

// Load environment variables
dotenv.config()

const app = express()
const PORT = process.env.PORT || 8000

// Middleware
app.use(helmet())
app.use(cors())
app.use(express.json())

// Health check endpoint
app.get('/health', (req, res) => {{
  res.json({{ 
    status: 'healthy', 
    service: '{spec['name']}',
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  }})
}})

// API routes
app.get('/api/status', (req, res) => {{
  res.json({{ 
    message: 'Welcome to {spec['name']} API',
    version: '1.0.0',
    features: {json.dumps(spec['features'])},
    infrastructure: {json.dumps(spec['infrastructure'])}
  }})
}})

// Error handling middleware
app.use((err, req, res, next) => {{
  console.error(err.stack)
  res.status(500).json({{ 
    error: 'Something went wrong!',
    message: err.message 
  }})
}})

// 404 handler
app.use('*', (req, res) => {{
  res.status(404).json({{ 
    error: 'Route not found',
    path: req.originalUrl 
  }})
}})

// Start server
app.listen(PORT, () => {{
  console.log(`{spec['name']} API server running on port ${{PORT}}`)
  console.log(`Health check available at http://localhost:${{PORT}}/health`)
}})

module.exports = app'''

def generate_fastapi_app(spec):
    """Generate real FastAPI app"""
    return f'''from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
from datetime import datetime

app = FastAPI(
    title="{spec['name']}",
    description="{spec['description']}",
    version="1.0.0"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]
)

@app.get("/health")
async def health():
    return {{
        "status": "healthy",
        "service": "{spec['name']}",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }}

@app.get("/api/status")
async def status():
    return {{
        "message": "Welcome to {spec['name']} API",
        "version": "1.0.0",
        "features": {spec['features']},
        "infrastructure": {spec['infrastructure']}
    }}

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {{
        "error": "Route not found",
        "path": str(request.url)
    }}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {{
        "error": "Internal server error",
        "message": str(exc)
    }}

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )'''

def generate_react_app_component(spec):
    """Generate real React App component"""
    return f'''import React from 'react'
import {{ useState, useEffect }} from 'react'
import Header from './components/Header'
import Home from './pages/Home'
import './App.css'

function App() {{
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {{
    // Fetch initial data
    fetch('/api/status')
      .then(response => response.json())
      .then(data => {{
        setData(data)
        setLoading(false)
      }})
      .catch(error => {{
        console.error('Error fetching data:', error)
        setLoading(false)
      }})
  }}, [])

  if (loading) {{
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }}

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Home data={{data}} />
      </main>
    </div>
  )
}}

export default App'''

def generate_nextjs_index_page(spec):
    """Generate real Next.js index page"""
    return f'''import Head from 'next/head'
import Header from '../components/Header'
import Layout from '../components/Layout'
import {{ useState, useEffect }} from 'react'

export default function Home() {{
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {{
    // Fetch initial data
    fetch('/api/status')
      .then(response => response.json())
      .then(data => {{
        setData(data)
        setLoading(false)
      }})
      .catch(error => {{
        console.error('Error fetching data:', error)
        setLoading(false)
      }})
  }}, [])

  if (loading) {{
    return (
      <Layout>
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </Layout>
    )
  }}

  return (
    <Layout>
      <Head>
        <title>{spec['name']}</title>
        <meta name="description" content="{spec['description']}" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            {spec['name']}
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            {spec['description']}
          </p>
          
          {{data && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-2xl font-semibold mb-4">System Status</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h3 className="font-medium text-gray-900">Features</h3>
                  <ul className="mt-2 space-y-1">
                    {{data.features?.map((feature, index) => (
                      <li key={{index}} className="text-sm text-gray-600">
                        • {{feature}}
                      </li>
                    ))}}
                  </ul>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">Infrastructure</h3>
                  <ul className="mt-2 space-y-1">
                    {{data.infrastructure?.map((infra, index) => (
                      <li key={{index}} className="text-sm text-gray-600">
                        • {{infra}}
                      </li>
                    ))}}
                  </ul>
                </div>
              </div>
            </div>
          )}}
        </div>
      </main>
    </Layout>
  )
}}'''

def generate_react_header_component(spec):
    return f'''import React from 'react'

export default function Header() {{
  return (
    <header className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <h1 className="text-xl font-bold text-gray-900">
              {spec['name']}
            </h1>
          </div>
          <nav className="flex space-x-4">
            <a href="/" className="text-gray-600 hover:text-gray-900">Home</a>
            <a href="/about" className="text-gray-600 hover:text-gray-900">About</a>
          </nav>
        </div>
      </div>
    </header>
  )
}}'''

def generate_nextjs_header_component(spec):
    return f'''import React from 'react'
import Link from 'next/link'

export default function Header() {{
  return (
    <header className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <Link href="/" className="text-xl font-bold text-gray-900">
              {spec['name']}
            </Link>
          </div>
          <nav className="flex space-x-4">
            <Link href="/" className="text-gray-600 hover:text-gray-900">Home</Link>
            <Link href="/about" className="text-gray-600 hover:text-gray-900">About</Link>
          </nav>
        </div>
      </div>
    </header>
  )
}}'''

def generate_nextjs_layout_component(spec):
    return f'''import React from 'react'
import Header from './Header'

export default function Layout({{ children }}) {{
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      {{children}}
    </div>
  )
}}'''

def generate_react_home_page(spec):
    return f'''import React from 'react'

export default function Home({{ data }}) {{
  return (
    <div className="text-center">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">
        {spec['name']}
      </h1>
      <p className="text-xl text-gray-600 mb-8">
        {spec['description']}
      </p>
      
      {{data && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-semibold mb-4">System Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="font-medium text-gray-900">Features</h3>
              <ul className="mt-2 space-y-1">
                {{data.features?.map((feature, index) => (
                  <li key={{index}} className="text-sm text-gray-600">
                    • {{feature}}
                  </li>
                ))}}
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Infrastructure</h3>
              <ul className="mt-2 space-y-1">
                {{data.infrastructure?.map((infra, index) => (
                  <li key={{index}} className="text-sm text-gray-600">
                    • {{infra}}
                  </li>
                ))}}
              </ul>
            </div>
          </div>
        </div>
      )}}
    </div>
  )
}}'''

def generate_tailwind_config(spec):
    return f'''/** @type {{import('tailwindcss').Config}} */
module.exports = {{
  content: [
    './src/**/*.{{js,jsx,ts,tsx}}',
    './pages/**/*.{{js,jsx,ts,tsx}}',
    './components/**/*.{{js,jsx,ts,tsx}}',
  ],
  theme: {{
    extend: {{
      colors: {{
        primary: {{
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        }}
      }}
    }},
  }},
  plugins: [],
}}'''

def generate_typescript_config(spec):
    return f'''{{
  "compilerOptions": {{
    "target": "es5",
    "lib": ["dom", "dom.iterable", "es6"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true
  }},
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}}'''

def generate_nextjs_config(spec):
    return f'''/** @type {{import('next').NextConfig}} */
const nextConfig = {{
  reactStrictMode: true,
  swcMinify: true,
  images: {{
    unoptimized: true
  }}
}}

module.exports = nextConfig'''

def generate_api_routes(spec):
    return f'''const express = require('express')
const router = express.Router()

// {spec['name']} API routes
router.get('/health', (req, res) => {{
    res.json({{ 
        status: 'healthy',
        service: '{spec['name']}',
        timestamp: new Date().toISOString()
    }})
}})

router.get('/status', (req, res) => {{
    res.json({{ 
        message: 'Welcome to {spec['name']} API',
        version: '1.0.0',
        features: {json.dumps(spec['features'])},
        infrastructure: {json.dumps(spec['infrastructure'])}
    }})
}})

module.exports = router'''

def generate_fastapi_routes(spec):
    return f'''from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health():
    return {{
        "status": "healthy",
        "service": "{spec['name']}",
        "timestamp": datetime.utcnow().isoformat()
    }}

@router.get("/status")
async def status():
    return {{
        "message": "Welcome to {spec['name']} API",
        "version": "1.0.0",
        "features": {spec['features']},
        "infrastructure": {spec['infrastructure']}
    }}'''

def generate_database_models(spec):
    """Generate real, system-specific database models based on system type and features"""
    
    # Determine system type and generate appropriate models
    system_type = spec.get('type', 'web-app')
    features = spec.get('features', [])
    
    if system_type == 'web-app':
        return generate_webapp_models(spec, features)
    elif system_type == 'ecommerce-platform':
        return generate_ecommerce_models(spec, features)
    elif system_type == 'api-service':
        return generate_api_models(spec, features)
    else:
        return generate_generic_models(spec)

def generate_webapp_models(spec, features):
    """Generate models for a web application with users, posts, comments"""
    system_name = spec['name'].replace(' ', '').replace('-', '')
    
    models = f'''const {{ Pool }} = require('pg')

// Database connection
const pool = new Pool({{
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? {{ rejectUnauthorized: false }} : false
}})

// {spec['name']} Database Models

// User Model
class User {{
  static async create(userData) {{
    const {{ email, password_hash, name, role = 'user' }} = userData
    const query = `
      INSERT INTO users (email, password_hash, name, role, created_at, updated_at)
      VALUES ($1, $2, $3, $4, NOW(), NOW())
      RETURNING id, email, name, role, created_at, updated_at
    `
    const values = [email, password_hash, name, role]
    const result = await pool.query(query, values)
    return result.rows[0]
  }}

  static async findByEmail(email) {{
    const query = 'SELECT * FROM users WHERE email = $1'
    const result = await pool.query(query, [email])
    return result.rows[0]
  }}

  static async findById(id) {{
    const query = 'SELECT id, email, name, role, created_at, updated_at FROM users WHERE id = $1'
    const result = await pool.query(query, [id])
    return result.rows[0]
  }}

  static async update(id, updateData) {{
    const fields = []
    const values = []
    let paramCount = 1

    for (const [key, value] of Object.entries(updateData)) {{
      if (key !== 'id') {{
        fields.push(`${{key}} = ${{paramCount}}`)
        values.push(value)
        paramCount++
      }}
    }}

    if (fields.length === 0) return null

    fields.push('updated_at = NOW()')
    values.push(id)

    const query = `
      UPDATE users 
      SET ${{fields.join(', ')}}
      WHERE id = ${{paramCount}}
      RETURNING id, email, name, role, created_at, updated_at
    `
    const result = await pool.query(query, values)
    return result.rows[0]
  }}

  static async delete(id) {{
    const query = 'DELETE FROM users WHERE id = $1 RETURNING id'
    const result = await pool.query(query, [id])
    return result.rows[0]
  }}
}}'''

    # Add Post model if content management is a feature
    if any('content' in feature.lower() or 'post' in feature.lower() or 'blog' in feature.lower() for feature in features):
        models += f'''

// Post Model
class Post {{
  static async create(postData) {{
    const {{ title, content, author_id, status = 'draft' }} = postData
    const query = `
      INSERT INTO posts (title, content, author_id, status, created_at, updated_at)
      VALUES ($1, $2, $3, $4, NOW(), NOW())
      RETURNING *
    `
    const values = [title, content, author_id, status]
    const result = await pool.query(query, values)
    return result.rows[0]
  }}

  static async findById(id) {{
    const query = `
      SELECT p.*, u.name as author_name, u.email as author_email
      FROM posts p
      JOIN users u ON p.author_id = u.id
      WHERE p.id = $1
    `
    const result = await pool.query(query, [id])
    return result.rows[0]
  }}

  static async findByAuthor(authorId, limit = 10, offset = 0) {{
    const query = `
      SELECT p.*, u.name as author_name
      FROM posts p
      JOIN users u ON p.author_id = u.id
      WHERE p.author_id = $1
      ORDER BY p.created_at DESC
      LIMIT $2 OFFSET $3
    `
    const result = await pool.query(query, [authorId, limit, offset])
    return result.rows
  }}

  static async findAll(limit = 10, offset = 0, status = 'published') {{
    const query = `
      SELECT p.*, u.name as author_name
      FROM posts p
      JOIN users u ON p.author_id = u.id
      WHERE p.status = $1
      ORDER BY p.created_at DESC
      LIMIT $2 OFFSET $3
    `
    const result = await pool.query(query, [status, limit, offset])
    return result.rows
  }}

  static async update(id, updateData) {{
    const fields = []
    const values = []
    let paramCount = 1

    for (const [key, value] of Object.entries(updateData)) {{
      if (key !== 'id') {{
        fields.push(`${{key}} = ${{paramCount}}`)
        values.push(value)
        paramCount++
      }}
    }}

    if (fields.length === 0) return null

    fields.push('updated_at = NOW()')
    values.push(id)

    const query = `
      UPDATE posts 
      SET ${{fields.join(', ')}}
      WHERE id = ${{paramCount}}
      RETURNING *
    `
    const result = await pool.query(query, values)
    return result.rows[0]
  }}

  static async delete(id) {{
    const query = 'DELETE FROM posts WHERE id = $1 RETURNING id'
    const result = await pool.query(query, [id])
    return result.rows[0]
  }}
}}'''

    # Add Comment model if user interactions are a feature
    if any('comment' in feature.lower() or 'interaction' in feature.lower() or 'social' in feature.lower() for feature in features):
        models += f'''

// Comment Model
class Comment {{
  static async create(commentData) {{
    const {{ content, author_id, post_id, parent_id = null }} = commentData
    const query = `
      INSERT INTO comments (content, author_id, post_id, parent_id, created_at, updated_at)
      VALUES ($1, $2, $3, $4, NOW(), NOW())
      RETURNING *
    `
    const values = [content, author_id, post_id, parent_id]
    const result = await pool.query(query, values)
    return result.rows[0]
  }}

  static async findByPost(postId, limit = 50, offset = 0) {{
    const query = `
      SELECT c.*, u.name as author_name, u.email as author_email
      FROM comments c
      JOIN users u ON c.author_id = u.id
      WHERE c.post_id = $1 AND c.parent_id IS NULL
      ORDER BY c.created_at ASC
      LIMIT $2 OFFSET $3
    `
    const result = await pool.query(query, [postId, limit, offset])
    return result.rows
  }}

  static async findReplies(parentId, limit = 20, offset = 0) {{
    const query = `
      SELECT c.*, u.name as author_name, u.email as author_email
      FROM comments c
      JOIN users u ON c.author_id = u.id
      WHERE c.parent_id = $1
      ORDER BY c.created_at ASC
      LIMIT $2 OFFSET $3
    `
    const result = await pool.query(query, [parentId, limit, offset])
    return result.rows
  }}

  static async update(id, updateData) {{
    const fields = []
    const values = []
    let paramCount = 1

    for (const [key, value] of Object.entries(updateData)) {{
      if (key !== 'id') {{
        fields.push(`${{key}} = ${{paramCount}}`)
        values.push(value)
        paramCount++
      }}
    }}

    if (fields.length === 0) return null

    fields.push('updated_at = NOW()')
    values.push(id)

    const query = `
      UPDATE comments 
      SET ${{fields.join(', ')}}
      WHERE id = ${{paramCount}}
      RETURNING *
    `
    const result = await pool.query(query, values)
    return result.rows[0]
  }}

  static async delete(id) {{
    const query = 'DELETE FROM comments WHERE id = $1 RETURNING id'
    const result = await pool.query(query, [id])
    return result.rows[0]
  }}
}}'''

    # Export all models
    models += f'''

module.exports = {{
  pool,
  User,
'''
    
    if any('content' in feature.lower() or 'post' in feature.lower() or 'blog' in feature.lower() for feature in features):
        models += '  Post,\n'
    
    if any('comment' in feature.lower() or 'interaction' in feature.lower() or 'social' in feature.lower() for feature in features):
        models += '  Comment,\n'
    
    models += '}'
    
    return models

def generate_ecommerce_models(spec, features):
    """Generate models for an e-commerce platform"""
    # TODO: Implement e-commerce specific models
    return generate_generic_models(spec)

def generate_api_models(spec, features):
    """Generate models for an API service"""
    # TODO: Implement API service specific models
    return generate_generic_models(spec)

def generate_generic_models(spec):
    """Generate generic models as fallback"""
    return f'''const {{ Pool }} = require('pg')

// Database connection
const pool = new Pool({{
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? {{ rejectUnauthorized: false }} : false
}})

// {spec['name']} Models
class {spec['name'].replace(' ', '')}Model {{
  static async create(data) {{
    const query = 'INSERT INTO {spec['name'].lower().replace(' ', '_')} (data) VALUES ($1) RETURNING *'
    const values = [JSON.stringify(data)]
    const result = await pool.query(query, values)
    return result.rows[0]
  }}

  static async findById(id) {{
    const query = 'SELECT * FROM {spec['name'].lower().replace(' ', '_')} WHERE id = $1'
    const result = await pool.query(query, [id])
    return result.rows[0]
  }}

  static async findAll() {{
    const query = 'SELECT * FROM {spec['name'].lower().replace(' ', '_')}'
    const result = await pool.query(query)
    return result.rows
  }}
}}

module.exports = {{
  pool,
  {spec['name'].replace(' ', '')}Model
}}'''

def generate_database_migrations(spec):
    """Generate real database migration files"""
    system_type = spec.get('type', 'web-app')
    features = spec.get('features', [])
    
    if system_type == 'web-app':
        return generate_webapp_migrations(spec, features)
    else:
        return generate_generic_migrations(spec)

def generate_webapp_migrations(spec, features):
    """Generate migration files for web application"""
    migrations = []
    
    # Initial migration - create users table
    migrations.append({
        'name': '001_create_users_table.sql',
        'content': f'''-- Migration: Create users table
-- Generated for: {spec['name']}

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
'''
    })
    
    # Add posts table if content management is a feature
    if any('content' in feature.lower() or 'post' in feature.lower() or 'blog' in feature.lower() for feature in features):
        migrations.append({
            'name': '002_create_posts_table.sql',
            'content': f'''-- Migration: Create posts table
-- Generated for: {spec['name']}

CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    excerpt TEXT,
    slug VARCHAR(500) UNIQUE,
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'draft',
    featured_image VARCHAR(500),
    meta_description TEXT,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_published_at ON posts(published_at);
CREATE INDEX IF NOT EXISTS idx_posts_slug ON posts(slug);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);

-- Create updated_at trigger
CREATE TRIGGER update_posts_updated_at 
    BEFORE UPDATE ON posts 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
'''
        })
    
    # Add comments table if user interactions are a feature
    if any('comment' in feature.lower() or 'interaction' in feature.lower() or 'social' in feature.lower() for feature in features):
        migrations.append({
            'name': '003_create_comments_table.sql',
            'content': f'''-- Migration: Create comments table
-- Generated for: {spec['name']}

CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'approved',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_comments_author_id ON comments(author_id);
CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments(parent_id);
CREATE INDEX IF NOT EXISTS idx_comments_status ON comments(status);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at);

-- Create updated_at trigger
CREATE TRIGGER update_comments_updated_at 
    BEFORE UPDATE ON comments 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
'''
        })
    
    # Add seed data migration
    migrations.append({
        'name': '004_seed_data.sql',
        'content': f'''-- Migration: Seed initial data
-- Generated for: {spec['name']}

-- Insert admin user (password: admin123 - change in production!)
INSERT INTO users (email, password_hash, name, role, email_verified) 
VALUES (
    'admin@{spec['name'].lower().replace(' ', '')}.com',
    '$2b$10$rQZ8K9vX8K9vX8K9vX8K9e', -- bcrypt hash for 'admin123'
    'Admin User',
    'admin',
    true
) ON CONFLICT (email) DO NOTHING;

-- Insert sample user
INSERT INTO users (email, password_hash, name, role, email_verified) 
VALUES (
    'user@{spec['name'].lower().replace(' ', '')}.com',
    '$2b$10$rQZ8K9vX8K9vX8K9vX8K9e', -- bcrypt hash for 'user123'
    'Sample User',
    'user',
    true
) ON CONFLICT (email) DO NOTHING;
'''
    })
    
    return migrations

def generate_generic_migrations(spec):
    """Generate generic migration files"""
    return [{
        'name': '001_create_initial_table.sql',
        'content': f'''-- Migration: Create initial table
-- Generated for: {spec['name']}

CREATE TABLE IF NOT EXISTS {spec['name'].lower().replace(' ', '_')} (
    id SERIAL PRIMARY KEY,
    data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_{spec['name'].lower().replace(' ', '_')}_created_at ON {spec['name'].lower().replace(' ', '_')}(created_at);
'''
    }]

def generate_migration_runner(spec):
    """Generate migration runner script"""
    return f'''const {{ Pool }} = require('pg')
const fs = require('fs')
const path = require('path')

// Database connection
const pool = new Pool({{
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? {{ rejectUnauthorized: false }} : false
}})

async function runMigrations() {{
  try {{
    console.log('🚀 Starting database migrations for {spec['name']}...')
    
    // Create migrations table if it doesn't exist
    await pool.query(`
      CREATE TABLE IF NOT EXISTS migrations (
        id SERIAL PRIMARY KEY,
        filename VARCHAR(255) UNIQUE NOT NULL,
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `)
    
    // Get list of migration files
    const migrationsDir = path.join(__dirname, '../database/migrations')
    const migrationFiles = fs.readdirSync(migrationsDir)
      .filter(file => file.endsWith('.sql'))
      .sort()
    
    console.log(`Found ${{migrationFiles.length}} migration files`)
    
    // Run each migration
    for (const filename of migrationFiles) {{
      // Check if migration already ran
      const result = await pool.query(
        'SELECT id FROM migrations WHERE filename = $1',
        [filename]
      )
      
      if (result.rows.length > 0) {{
        console.log(`⏭️  Skipping ${{filename}} (already executed)`)
        continue
      }}
      
      // Read and execute migration
      const migrationPath = path.join(migrationsDir, filename)
      const migrationSQL = fs.readFileSync(migrationPath, 'utf8')
      
      console.log(`🔄 Running migration: ${{filename}}`)
      await pool.query(migrationSQL)
      
      // Record migration as executed
      await pool.query(
        'INSERT INTO migrations (filename) VALUES ($1)',
        [filename]
      )
      
      console.log(`✅ Completed migration: ${{filename}}`)
    }}
    
    console.log('🎉 All migrations completed successfully!')
    
  }} catch (error) {{
    console.error('❌ Migration failed:', error)
    process.exit(1)
  }} finally {{
    await pool.end()
  }}
}}

// Run migrations if this script is executed directly
if (require.main === module) {{
  runMigrations()
}}

module.exports = {{ runMigrations }}
'''

def generate_docker_compose(spec):
    """Generate Docker Compose for local development"""
    system_name = spec['name'].lower().replace(' ', '-').replace('_', '-')
    
    return f'''version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: {system_name}-postgres
    environment:
      POSTGRES_DB: {system_name}
      POSTGRES_USER: {system_name}_user
      POSTGRES_PASSWORD: {system_name}_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/migrations:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U {system_name}_user -d {system_name}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache (optional)
  redis:
    image: redis:7-alpine
    container_name: {system_name}-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Backend API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: {system_name}-backend
    environment:
      NODE_ENV: development
      DATABASE_URL: postgresql://{system_name}_user:{system_name}_password@postgres:5432/{system_name}
      REDIS_URL: redis://redis:6379
      PORT: 8000
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - /app/node_modules
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: npm run dev
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Frontend (if Next.js)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: {system_name}-frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NODE_ENV: development
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    depends_on:
      - backend
    command: npm run dev
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
  redis_data:

networks:
  default:
    name: {system_name}-network
'''

def generate_deployment_scripts(spec):
    """Generate deployment scripts for different cloud providers"""
    system_name = spec['name'].lower().replace(' ', '-').replace('_', '-')
    
    scripts = []
    
    # AWS deployment script
    scripts.append({
        'name': 'deploy-aws.sh',
        'content': f'''#!/bin/bash
# AWS Deployment Script for {spec['name']}
# Generated by System Builder Hub (SBH)

set -e

echo "🚀 Deploying {spec['name']} to AWS..."

# Configuration
PROJECT_NAME="{system_name}"
AWS_REGION="us-west-2"
ECR_REPO="$PROJECT_NAME-repo"
ECS_CLUSTER="$PROJECT_NAME-cluster"
ECS_SERVICE="$PROJECT_NAME-service"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "📦 Building Docker image..."
docker build -t $PROJECT_NAME:latest ./backend

echo "🏷️  Tagging image for ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
docker tag $PROJECT_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest

echo "⬆️  Pushing image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest

echo "🔄 Updating ECS service..."
aws ecs update-service \\
    --cluster $ECS_CLUSTER \\
    --service $ECS_SERVICE \\
    --force-new-deployment

echo "⏳ Waiting for deployment to complete..."
aws ecs wait services-stable \\
    --cluster $ECS_CLUSTER \\
    --services $ECS_SERVICE

echo "✅ Deployment completed successfully!"
echo "🌐 Your application should be available at: https://$PROJECT_NAME.sbh.umbervale.com"
'''
    })
    
    # GCP deployment script
    scripts.append({
        'name': 'deploy-gcp.sh',
        'content': f'''#!/bin/bash
# Google Cloud Platform Deployment Script for {spec['name']}
# Generated by System Builder Hub (SBH)

set -e

echo "🚀 Deploying {spec['name']} to Google Cloud Platform..."

# Configuration
PROJECT_NAME="{system_name}"
GCP_PROJECT_ID="$GCP_PROJECT_ID"
GCP_REGION="us-west1"
SERVICE_NAME="$PROJECT_NAME-service"

# Check if gcloud CLI is configured
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null 2>&1; then
    echo "❌ Google Cloud CLI not configured. Please run 'gcloud auth login' first."
    exit 1
fi

# Set the project
gcloud config set project $GCP_PROJECT_ID

echo "📦 Building and pushing to Google Container Registry..."
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/$PROJECT_NAME ./backend

echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \\
    --image gcr.io/$GCP_PROJECT_ID/$PROJECT_NAME \\
    --platform managed \\
    --region $GCP_REGION \\
    --allow-unauthenticated \\
    --port 8000 \\
    --memory 512Mi \\
    --cpu 1 \\
    --max-instances 10

echo "✅ Deployment completed successfully!"
echo "🌐 Your application is available at the URL shown above."
'''
    })
    
    # Azure deployment script
    scripts.append({
        'name': 'deploy-azure.sh',
        'content': f'''#!/bin/bash
# Microsoft Azure Deployment Script for {spec['name']}
# Generated by System Builder Hub (SBH)

set -e

echo "🚀 Deploying {spec['name']} to Microsoft Azure..."

# Configuration
PROJECT_NAME="{system_name}"
AZURE_RESOURCE_GROUP="$PROJECT_NAME-rg"
AZURE_LOCATION="westus2"
CONTAINER_APP_NAME="$PROJECT_NAME-app"

# Check if Azure CLI is configured
if ! az account show > /dev/null 2>&1; then
    echo "❌ Azure CLI not configured. Please run 'az login' first."
    exit 1
fi

echo "📦 Building and pushing to Azure Container Registry..."
az acr build --registry $AZURE_ACR_NAME --image $PROJECT_NAME:latest ./backend

echo "🚀 Deploying to Azure Container Apps..."
az containerapp create \\
    --name $CONTAINER_APP_NAME \\
    --resource-group $AZURE_RESOURCE_GROUP \\
    --location $AZURE_LOCATION \\
    --image $AZURE_ACR_NAME.azurecr.io/$PROJECT_NAME:latest \\
    --target-port 8000 \\
    --ingress external \\
    --cpu 0.5 \\
    --memory 1Gi \\
    --min-replicas 1 \\
    --max-replicas 10

echo "✅ Deployment completed successfully!"
echo "🌐 Your application is available at the URL shown above."
'''
    })
    
    return scripts

def generate_comprehensive_readme(spec):
    """Generate comprehensive README for the generated system"""
    system_name = spec['name']
    system_type = spec.get('type', 'web-app')
    features = spec.get('features', [])
    tech_stack = spec.get('techStack', [])
    
    readme = f'''# {system_name}

**Generated by System Builder Hub (SBH) - The AI-powered system that builds complete, deployable applications.**

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- PostgreSQL (or use Docker)
- Git

### Local Development

1. **Clone and setup:**
   ```bash
   git clone <your-repo-url>
   cd {system_name.lower().replace(' ', '-')}
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Run database migrations:**
   ```bash
   docker-compose exec backend node scripts/run-migrations.js
   ```

4. **Access your application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Health: http://localhost:8000/health

## 🏗️ Architecture

### System Type: {system_type.title()}

### Tech Stack:
'''
    
    for tech in tech_stack:
        readme += f'- {tech}\n'
    
    readme += f'''
### Features:
'''
    
    for feature in features:
        readme += f'- {feature}\n'
    
    readme += f'''
## 📁 Project Structure

```
{system_name.lower().replace(' ', '-')}/
├── frontend/                 # Next.js frontend application
│   ├── pages/               # Next.js pages
│   ├── components/          # React components
│   ├── styles/              # CSS and styling
│   └── package.json         # Frontend dependencies
├── backend/                 # Node.js/Express backend
│   ├── src/                 # Source code
│   │   ├── models/          # Database models
│   │   ├── routes/          # API routes
│   │   └── middleware/      # Express middleware
│   ├── database/            # Database files
│   │   └── migrations/      # SQL migration files
│   └── scripts/             # Utility scripts
├── infrastructure/          # Terraform infrastructure
│   ├── main.tf             # Main Terraform configuration
│   ├── variables.tf        # Terraform variables
│   └── modules/            # Terraform modules
├── .github/workflows/       # GitHub Actions CI/CD
├── docker-compose.yml       # Local development setup
├── docker-compose.prod.yml  # Production setup
└── README.md               # This file
```

## 🗄️ Database Schema

### Tables:
'''
    
    if system_type == 'web-app':
        readme += '''- **users** - User authentication and profiles
- **posts** - Content management (if content features enabled)
- **comments** - User interactions (if interaction features enabled)
'''
    else:
        readme += f'- **{system_name.lower().replace(' ', '_')}** - Main data table\n'
    
    readme += f'''
### Migrations:
- `001_create_users_table.sql` - User authentication
- `002_create_posts_table.sql` - Content management
- `003_create_comments_table.sql` - User interactions
- `004_seed_data.sql` - Initial data

## 🚀 Deployment

### Option 1: AWS Deployment
```bash
chmod +x deploy-aws.sh
./deploy-aws.sh
```

### Option 2: Google Cloud Platform
```bash
chmod +x deploy-gcp.sh
./deploy-gcp.sh
```

### Option 3: Microsoft Azure
```bash
chmod +x deploy-azure.sh
./deploy-azure.sh
```

### Option 4: Docker Compose (Any Server)
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/database

# Application
NODE_ENV=development
PORT=8000
JWT_SECRET=your-secret-key

# External Services
OPENAI_API_KEY=your-openai-key
STRIPE_SECRET_KEY=your-stripe-key
```

## 🧪 Testing

### Run Tests
```bash
# Backend tests
cd backend
npm test

# Frontend tests
cd frontend
npm test
```

### API Testing
```bash
# Health check
curl http://localhost:8000/health

# API endpoints
curl http://localhost:8000/api/status
```

## 📊 Monitoring

### Health Checks
- **Application**: `/health`
- **Database**: Connection status
- **External APIs**: Service availability

### Logs
```bash
# View application logs
docker-compose logs -f backend

# View database logs
docker-compose logs -f postgres
```

## 🔒 Security

### Authentication
- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control

### Database Security
- Parameterized queries (no SQL injection)
- Connection encryption in production
- Regular security updates

## 🛠️ Development

### Adding New Features

1. **Database Changes:**
   ```bash
   # Create new migration
   touch database/migrations/005_add_new_feature.sql
   # Add your SQL changes
   # Run migration
   node scripts/run-migrations.js
   ```

2. **API Endpoints:**
   - Add routes in `backend/src/routes/`
   - Add models in `backend/src/models/`
   - Update tests

3. **Frontend Components:**
   - Add components in `frontend/components/`
   - Add pages in `frontend/pages/`
   - Update styling

## 📚 API Documentation

### Authentication Endpoints
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/profile` - Get user profile

### Content Endpoints (if enabled)
- `GET /api/posts` - List posts
- `POST /api/posts` - Create post
- `GET /api/posts/:id` - Get post
- `PUT /api/posts/:id` - Update post
- `DELETE /api/posts/:id` - Delete post

### Comment Endpoints (if enabled)
- `GET /api/posts/:id/comments` - List comments
- `POST /api/posts/:id/comments` - Add comment
- `PUT /api/comments/:id` - Update comment
- `DELETE /api/comments/:id` - Delete comment

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Failed:**
   ```bash
   # Check if PostgreSQL is running
   docker-compose ps postgres
   # Check logs
   docker-compose logs postgres
   ```

2. **Port Already in Use:**
   ```bash
   # Change ports in docker-compose.yml
   # Or stop conflicting services
   ```

3. **Migration Errors:**
   ```bash
   # Check migration files
   ls -la database/migrations/
   # Run migrations manually
   docker-compose exec backend node scripts/run-migrations.js
   ```

## 📞 Support

- **Documentation**: This README
- **Issues**: GitHub Issues
- **Generated by**: System Builder Hub (SBH)

---

**Built with ❤️ by System Builder Hub - The AI-powered system that builds complete, deployable applications.**
'''
    
    return readme

def generate_sqlalchemy_models(spec):
    return f'''from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class {spec['name'].replace(' ', '')}Model(Base):
    __tablename__ = '{spec['name'].lower().replace(' ', '_')}'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    data = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<{spec['name'].replace(' ', '')}Model(id={{self.id}}, name={{self.name}})>"'''

def generate_database_config(spec):
    return f'''from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/{spec['name'].lower().replace(' ', '_')}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()'''

def generate_auth_middleware(spec):
    return f'''const jwt = require('jsonwebtoken')

const authenticateToken = (req, res, next) => {{
  const authHeader = req.headers['authorization']
  const token = authHeader && authHeader.split(' ')[1]

  if (!token) {{
    return res.status(401).json({{ error: 'Access token required' }})
  }}

  jwt.verify(token, process.env.JWT_SECRET, (err, user) => {{
    if (err) {{
      return res.status(403).json({{ error: 'Invalid token' }})
    }}
    req.user = user
    next()
  }})
}}

module.exports = {{ authenticateToken }}'''

def generate_python_auth_middleware(spec):
    return f'''from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import os

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={{"WWW-Authenticate": "Bearer"}},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    return username'''

def generate_nodejs_dockerfile(spec):
    return f'''FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 8000

CMD ["npm", "start"]'''

def generate_python_dockerfile(spec):
    return f'''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]'''

def generate_env_example(spec):
    return f'''# {spec['name']} Environment Variables
NODE_ENV=production
PORT=8000

# Database
DATABASE_URL=postgresql://user:password@localhost/{spec['name'].lower().replace(' ', '_')}

# JWT
JWT_SECRET=your-secret-key-here

# AWS (if applicable)
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key'''

def generate_terraform_main(spec, architecture):
    """Generate real Terraform main configuration"""
    return f'''# {spec['name']} Infrastructure
terraform {{
  required_version = ">= 1.0"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = var.aws_region
}}

# VPC and Networking
module "vpc" {{
  source = "./modules/vpc"
  
  project_name = var.project_name
  environment  = var.environment
}}

# ECS Cluster
module "ecs" {{
  source = "./modules/ecs"
  
  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id
  subnets      = module.vpc.private_subnets
}}

# RDS Database
module "rds" {{
  source = "./modules/rds"
  
  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id
  subnets      = module.vpc.private_subnets
}}

# Application Load Balancer
module "alb" {{
  source = "./modules/alb"
  
  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id
  subnets      = module.vpc.public_subnets
}}

# S3 Bucket
module "s3" {{
  source = "./modules/s3"
  
  project_name = var.project_name
  environment  = var.environment
}}

# Outputs
output "cluster_name" {{
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}}

output "db_endpoint" {{
  description = "RDS endpoint"
  value       = module.rds.db_endpoint
}}

output "alb_dns_name" {{
  description = "ALB DNS name"
  value       = module.alb.alb_dns_name
}}

output "s3_bucket_name" {{
  description = "S3 bucket name"
  value       = module.s3.bucket_name
}}'''

def generate_github_actions_workflow(spec):
    """Generate real GitHub Actions workflow"""
    return f'''name: Deploy {spec['name']}

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    permissions:
      id-token: write
      contents: read
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-region: us-west-2
        role-to-assume: ${{{{ secrets.AWS_ROLE_ARN }}}}
        role-session-name: {spec['name'].lower().replace(' ', '-')}-deploy
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v2
    
    - name: Build, tag, and push image to Amazon ECR
      env:
        ECR_REGISTRY: ${{{{ steps.login-ecr.outputs.registry }}}}
        ECR_REPOSITORY: {spec['name'].lower().replace(' ', '-')}-repo
        IMAGE_TAG: ${{{{ github.sha }}}}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
    
    - name: Deploy to ECS
      run: |
        aws ecs update-service \\
          --cluster {spec['name'].lower().replace(' ', '-')}-cluster \\
          --service {spec['name'].lower().replace(' ', '-')}-service \\
          --force-new-deployment
    
    - name: Wait for deployment to complete
      run: |
        aws ecs wait services-stable \\
          --cluster {spec['name'].lower().replace(' ', '-')}-cluster \\
          --services {spec['name'].lower().replace(' ', '-')}-service'''

def generate_test_workflow(spec):
    """Generate test workflow"""
    return f'''name: Test {spec['name']}

on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Run tests
      run: npm test
    
    - name: Run linting
      run: npm run lint'''

def generate_security_workflow(spec):
    """Generate security workflow"""
    return f'''name: Security Scan {spec['name']}

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  security:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'''

def generate_terraform_variables(spec):
    return f'''variable "project_name" {{
  description = "Name of the project"
  type        = string
  default     = "{spec['name'].lower().replace(' ', '-')}"
}}

variable "environment" {{
  description = "Environment name"
  type        = string
  default     = "dev"
}}

variable "aws_region" {{
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}}

variable "db_password" {{
  description = "Database password"
  type        = string
  sensitive   = true
}}'''

def generate_terraform_outputs(spec):
    return f'''output "cluster_name" {{
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}}

output "db_endpoint" {{
  description = "RDS endpoint"
  value       = module.rds.db_endpoint
}}

output "alb_dns_name" {{
  description = "ALB DNS name"
  value       = module.alb.alb_dns_name
}}

output "s3_bucket_name" {{
  description = "S3 bucket name"
  value       = module.s3.bucket_name
}}'''

def generate_vpc_module(spec):
    return f'''# VPC Module for {spec['name']}
resource "aws_vpc" "main" {{
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {{
    Name = "${{var.project_name}}-vpc"
    Environment = var.environment
  }}
}}

resource "aws_internet_gateway" "main" {{
  vpc_id = aws_vpc.main.id

  tags = {{
    Name = "${{var.project_name}}-igw"
    Environment = var.environment
  }}
}}

resource "aws_subnet" "public" {{
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${{count.index + 1}}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {{
    Name = "${{var.project_name}}-public-subnet-${{count.index + 1}}"
    Environment = var.environment
  }}
}}

resource "aws_subnet" "private" {{
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${{count.index + 10}}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {{
    Name = "${{var.project_name}}-private-subnet-${{count.index + 1}}"
    Environment = var.environment
  }}
}}

data "aws_availability_zones" "available" {{
  state = "available"
}}

output "vpc_id" {{
  value = aws_vpc.main.id
}}

output "public_subnets" {{
  value = aws_subnet.public[*].id
}}

output "private_subnets" {{
  value = aws_subnet.private[*].id
}}'''

def generate_ecs_module(spec):
    return f'''# ECS Module for {spec['name']}
resource "aws_ecs_cluster" "main" {{
  name = "${{var.project_name}}-cluster"

  setting {{
    name  = "containerInsights"
    value = "enabled"
  }}

  tags = {{
    Name = "${{var.project_name}}-cluster"
    Environment = var.environment
  }}
}}

resource "aws_ecs_task_definition" "main" {{
  family                   = "${{var.project_name}}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn

  container_definitions = jsonencode([{{
    name  = "${{var.project_name}}-container"
    image = "${{var.project_name}}-image:latest"
    portMappings = [{{
      containerPort = 8000
      hostPort      = 8000
    }}]
    environment = [
      {{
        name  = "NODE_ENV"
        value = "production"
      }}
    ]
    logConfiguration = {{
      logDriver = "awslogs"
      options = {{
        awslogs-group         = "/ecs/${{var.project_name}}"
        awslogs-region        = "us-west-2"
        awslogs-stream-prefix = "ecs"
      }}
    }}
  }}])

  tags = {{
    Name = "${{var.project_name}}-task"
    Environment = var.environment
  }}
}}

output "cluster_name" {{
  value = aws_ecs_cluster.main.name
}}'''

def generate_rds_module(spec):
    return f'''# RDS Module for {spec['name']}
resource "aws_db_subnet_group" "main" {{
  name       = "${{var.project_name}}-db-subnet-group"
  subnet_ids = var.subnets

  tags = {{
    Name = "${{var.project_name}}-db-subnet-group"
    Environment = var.environment
  }}
}}

resource "aws_db_instance" "main" {{
  identifier = "${{var.project_name}}-db"
  engine     = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"
  allocated_storage = 20
  max_allocated_storage = 100
  storage_type = "gp2"
  storage_encrypted = true

  db_name  = "${{var.project_name}}"
  username = "admin"
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  skip_final_snapshot = true
  deletion_protection = false

  tags = {{
    Name = "${{var.project_name}}-db"
    Environment = var.environment
  }}
}}

output "db_endpoint" {{
  value = aws_db_instance.main.endpoint
}}'''

def generate_alb_module(spec):
    return f'''# ALB Module for {spec['name']}
resource "aws_lb" "main" {{
  name               = "${{var.project_name}}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.subnets

  enable_deletion_protection = false

  tags = {{
    Name = "${{var.project_name}}-alb"
    Environment = var.environment
  }}
}}

resource "aws_lb_target_group" "main" {{
  name     = "${{var.project_name}}-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  target_type = "ip"

  health_check {{
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }}

  tags = {{
    Name = "${{var.project_name}}-tg"
    Environment = var.environment
  }}
}}

resource "aws_lb_listener" "main" {{
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {{
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }}
}}

output "alb_dns_name" {{
  value = aws_lb.main.dns_name
}}'''

# Add these imports at the top with the other imports
import zipfile
import io
import base64
import json
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# S3 client for persistent storage
s3_client = boto3.client('s3')
S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'sbh-generated-systems')

def save_system_to_s3(system_id, system_data):
    """Save system to S3"""
    try:
        key = f"systems/{system_id}.json"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(system_data, default=str),
            ContentType='application/json'
        )
        return True
    except ClientError as e:
        logger.error(f"Error saving system to S3: {e}")
        return False

def load_system_from_s3(system_id):
    """Load system from S3"""
    try:
        key = f"systems/{system_id}.json"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        return json.loads(response['Body'].read().decode('utf-8'))
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
        logger.error(f"Error loading system from S3: {e}")
        return None

def delete_system_from_s3(system_id):
    """Delete system from S3"""
    try:
        key = f"systems/{system_id}.json"
        s3_client.delete_object(Bucket=S3_BUCKET, Key=key)
        return True
    except ClientError as e:
        logger.error(f"Error deleting system from S3: {e}")
        return False

def create_app():
    """Create Flask application with OpenAI integration and system generation"""
    app = Flask(__name__)
    
    # Basic Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # CORS Configuration
    cors_origins = [
        'http://localhost:3000',
        'https://sbh.umbervale.com'
    ]
    CORS(app, 
         origins=cors_origins,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'OPTIONS'],
         supports_credentials=False)
    
    # Get OpenAI configuration
    openai_config = get_openai_config()
    openai_client = create_openai_client()
    
    logger.info(f"OpenAI configured: {bool(openai_config['api_key'])}")
    logger.info(f"OpenAI model: {openai_config['model']}")

    @app.route('/api/health')
    def health():
        """Health check endpoint"""
        return jsonify({
            "ok": True, 
            "status": "healthy",
            "openai_configured": bool(openai_config['api_key']),
            "environment": os.getenv('FLASK_ENV', 'production')
        })

    @app.route('/')
    def index():
        return jsonify({
            "name": "System Builder Hub",
            "version": "1.0.0",
            "status": "running"
        })

    @app.route('/api/ai-chat/health', methods=['GET'])
    def ai_chat_health():
        """Health check for AI Chat service"""
        return jsonify({
            'status': 'healthy',
            'openai_configured': bool(openai_config['api_key']),
            'model': openai_config['model'] if openai_config['api_key'] else None,
            'timestamp': int(time.time())
        })

    @app.route('/api/ai-chat/chat', methods=['POST'])
    def ai_chat():
        """AI Chat endpoint with real OpenAI integration"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
    
            message = data.get('message', '')
            if not message:
                return jsonify({'error': 'No message provided'}), 400
    
            # Get conversation context and model selection
            conversation_history = data.get('conversation_history', [])
            conversation_id = data.get('conversation_id', f'conv_{int(time.time())}_{str(uuid.uuid4())[:8]}')
            system_message = data.get('system', 'You are an AI assistant for the System Builder Hub (SBH) - an AI-assisted platform that designs, scaffolds, deploys, and monitors complete software systems onto AWS. SBH is better than Cursor because it takes high-level specifications and outputs complete, bootable applications with their own infrastructure, CI/CD, and monitoring. You help users create comprehensive specifications for any type of system they want to build, then guide them through the process of generating working applications that are ready to deploy independently. Ask relevant questions to understand their requirements, provide architecture guidance, and help them create detailed specifications that SBH can use to build their complete system with Terraform, ECS, ALB, RDS, S3, and GitHub Actions.')
            
            # Model selection with validation
            requested_model = data.get('model', 'gpt-4o')  # Default to gpt-4o
            valid_models = ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo']
            if requested_model not in valid_models:
                requested_model = 'gpt-4o'  # Fallback to default
            
            # If no OpenAI client, return echo behavior
            if not openai_client:
                return jsonify({
                    'success': True,
                    'response': f'You said: {message}',
                    'conversation_id': conversation_id,
                    'note': 'openai not configured'
                })
    
            # Build messages for OpenAI
            messages = [{"role": "system", "content": system_message}]
            
            # Add conversation history
            for msg in conversation_history:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    messages.append(msg)
            
            # Add current message
            messages.append({"role": "user", "content": message})
    
            # Call OpenAI API with selected model
            try:
                response = openai_client.chat.completions.create(
                    model=requested_model,  # Use the selected model
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content
                usage = response.usage
                
                return jsonify({
                    'success': True,
                    'response': ai_response,
                    'usage': {
                        'prompt_tokens': usage.prompt_tokens,
                        'completion_tokens': usage.completion_tokens,
                        'total_tokens': usage.total_tokens
                    },
                    'model': requested_model,  # Return the actual model used
                    'conversation_id': conversation_id
                })
                
            except openai.APIError as e:
                logger.error(f"OpenAI API error: {e}")
                return jsonify({
                    'error_code': 'openai_api_error',
                    'message': f'OpenAI API error: {str(e)}'
                }), 502
                
            except openai.Timeout as e:
                logger.error(f"OpenAI timeout: {e}")
                return jsonify({
                    'error_code': 'openai_timeout',
                    'message': f'OpenAI request timed out after {openai_config["timeout"]} seconds'
                }), 502
                
            except Exception as e:
                logger.error(f"OpenAI client error: {e}")
                return jsonify({
                    'error_code': 'openai_client_error',
                    'message': f'OpenAI client error: {str(e)}'
                }), 502
            
        except Exception as e:
            logger.error(f"AI Chat endpoint error: {e}")
            return jsonify({'error': 'AI Chat failed', 'details': str(e)}), 500

    @app.route('/api/system/generate', methods=['POST'])
    def generate_system():
        """Generate a complete system based on specifications"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['name', 'description', 'type', 'techStack', 'features', 'infrastructure']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }), 400
            
            # Generate system ID
            system_id = str(uuid.uuid4())
            
            # Create system specification
            system_spec = {
                'id': system_id,
                'name': data['name'],
                'description': data['description'],
                'type': data['type'],
                'techStack': data['techStack'],
                'features': data['features'],
                'infrastructure': data['infrastructure'],
                'createdAt': datetime.utcnow().isoformat(),
                'status': 'generating'
            }
            
            # Generate system architecture
            architecture = generate_system_architecture(system_spec)
            
            # Generate system templates
            templates = generate_system_templates(system_spec, architecture)
            
            # Generate deployment configuration
            deployment_config = generate_deployment_config(system_spec, architecture)
            
            # Create complete system output
            system_output = {
                'systemId': system_id,
                'specification': system_spec,
                'architecture': architecture,
                'templates': templates,
                'deployment': deployment_config,
                'status': 'generated',
                'generatedAt': datetime.utcnow().isoformat()
            }
            
            # Store system for preview/testing in S3
            save_system_to_s3(system_id, system_output)
            
            return jsonify({
                'success': True,
                'system': system_output
            })
            
        except Exception as e:
            logger.error(f"System generation error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/system/preview/<system_id>', methods=['GET'])
    def preview_system(system_id):
        """Preview a generated system with code viewer and architecture"""
        try:
            system = load_system_from_s3(system_id)
            if not system:
                return jsonify({
                    'success': False,
                    'error': 'System not found'
                }), 404
            
            # Create preview data with file contents
            preview_data = {
                'systemId': system_id,
                'specification': system['specification'],
                'architecture': system['architecture'],
                'templates': system['templates'],
                'deployment': system['deployment'],
                'preview': {
                    'fileCount': count_files(system['templates']),
                    'components': len(system['architecture']['components']),
                    'infrastructure': len(system['architecture']['infrastructure']),
                    'generatedAt': system['generatedAt']
                }
            }
            
            return jsonify({
                'success': True,
                'preview': preview_data
            })
            
        except Exception as e:
            logger.error(f"System preview error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/system/test/<system_id>', methods=['POST'])
    def test_system(system_id):
        """Deploy and test a generated system"""
        try:
            system = load_system_from_s3(system_id)
            if not system:
                return jsonify({
                    'success': False,
                    'error': 'System not found'
                }), 404
            
            # Create test deployment
            test_deployment = create_test_deployment(system)
            
            # Store test deployment info and save back to S3
            system['testDeployment'] = test_deployment
            save_system_to_s3(system_id, system)
            
            return jsonify({
                'success': True,
                'testDeployment': test_deployment
            })
            
        except Exception as e:
            logger.error(f"System test error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/system/validate/<system_id>', methods=['GET'])
    def validate_system(system_id):
        """Validate a generated system"""
        try:
            system = load_system_from_s3(system_id)
            if not system:
                return jsonify({
                    'success': False,
                    'error': 'System not found'
                }), 404
            
            # Run validation checks
            validation_results = validate_system_components(system)
            
            return jsonify({
                'success': True,
                'validation': validation_results
            })
            
        except Exception as e:
            logger.error(f"System validation error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/system/download/<system_id>', methods=['GET'])
    def download_system(system_id):
        """Download a generated system as ZIP file"""
        try:
            system = load_system_from_s3(system_id)
            if not system:
                return jsonify({
                    'success': False,
                    'error': 'System not found'
                }), 404
            
            # Create ZIP file
            zip_buffer = create_system_zip(system)
            
            # Return ZIP file
            return send_file(
                io.BytesIO(zip_buffer),
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"{system['specification']['name'].lower().replace(' ', '-')}-system.zip"
            )
            
        except Exception as e:
            logger.error(f"System download error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    return app

# Helper functions
def count_files(templates):
    """Count total files in templates"""
    total = 0
    for template_type, template_data in templates.items():
        if 'files' in template_data:
            total += len(template_data['files'])
    return total

def create_test_deployment(system):
    """Create test deployment configuration"""
    return {
        'testId': f"test_{system['systemId'][:8]}",
        'status': 'deploying',
        'frontendUrl': f"https://test-{system['systemId'][:8]}.sbh.umbervale.com",
        'backendUrl': f"https://api-test-{system['systemId'][:8]}.sbh.umbervale.com",
        'deployedAt': datetime.utcnow().isoformat(),
        'estimatedTime': '2-3 minutes'
    }

def validate_system_components(system):
    """Validate system components"""
    validation = {
        'overall': 'valid',
        'checks': [],
        'warnings': [],
        'errors': []
    }
    
    # Check required files
    required_files = ['package.json', 'main.tf', 'Dockerfile']
    for template_type, template_data in system['templates'].items():
        if 'files' in template_data:
            for file_info in template_data['files']:
                if file_info['name'] in required_files:
                    validation['checks'].append({
                        'type': 'file',
                        'name': file_info['name'],
                        'status': 'found',
                        'template': template_type
                    })
    
    # Check infrastructure components
    if len(system['architecture']['infrastructure']) < 2:
        validation['warnings'].append('Minimal infrastructure components')
    
    # Check for security
    if 'User Authentication' in system['specification']['features']:
        validation['checks'].append({
            'type': 'security',
            'name': 'Authentication',
            'status': 'configured'
        })
    
    return validation

def create_system_zip(system):
    """Create ZIP file from system templates"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add README
        readme_content = f"""# {system['specification']['name']}

{system['specification']['description']}

## Generated System Components

### Frontend
- Type: {system['templates'].get('frontend', {}).get('type', 'N/A')}
- Files: {len(system['templates'].get('frontend', {}).get('files', []))}

### Backend  
- Type: {system['templates'].get('backend', {}).get('type', 'N/A')}
- Files: {len(system['templates'].get('backend', {}).get('files', []))}

### Infrastructure
- Type: {system['templates'].get('infrastructure', {}).get('type', 'N/A')}
- Files: {len(system['templates'].get('infrastructure', {}).get('files', []))}

## Deployment Instructions

1. Review the generated code
2. Update environment variables
3. Deploy infrastructure with Terraform
4. Deploy applications to ECS
5. Configure CI/CD pipelines

Generated by System Builder Hub (SBH)
Generated at: {system['generatedAt']}
"""
        zip_file.writestr('README.md', readme_content)
        
        # Add all template files
        for template_type, template_data in system['templates'].items():
            if 'files' in template_data:
                for file_info in template_data['files']:
                    file_path = f"{template_type}/{file_info['name']}"
                    zip_file.writestr(file_path, file_info['content'])
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# Create the Flask app instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
