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
    """Generate system templates and code"""
    templates = {
        'frontend': {},
        'backend': {},
        'infrastructure': {},
        'deployment': {}
    }
    
    # Generate frontend template
    if any('React' in tech for tech in spec['techStack']):
        templates['frontend'] = {
            'type': 'React',
            'files': [
                {'name': 'package.json', 'content': generate_react_package_json(spec)},
                {'name': 'src/App.js', 'content': generate_react_app(spec)},
                {'name': 'src/components/Header.js', 'content': generate_react_header(spec)}
            ]
        }
    elif any('Next.js' in tech for tech in spec['techStack']):
        templates['frontend'] = {
            'type': 'Next.js',
            'files': [
                {'name': 'package.json', 'content': generate_nextjs_package_json(spec)},
                {'name': 'pages/index.js', 'content': generate_nextjs_page(spec)},
                {'name': 'components/Header.js', 'content': generate_nextjs_header(spec)}
            ]
        }
    
    # Generate backend template
    if any('Node.js' in tech for tech in spec['techStack']):
        templates['backend'] = {
            'type': 'Node.js/Express',
            'files': [
                {'name': 'package.json', 'content': generate_node_package_json(spec)},
                {'name': 'server.js', 'content': generate_express_server(spec)},
                {'name': 'routes/api.js', 'content': generate_api_routes(spec)}
            ]
        }
    elif any('Python' in tech for tech in spec['techStack']):
        templates['backend'] = {
            'type': 'Python/FastAPI',
            'files': [
                {'name': 'requirements.txt', 'content': generate_python_requirements(spec)},
                {'name': 'main.py', 'content': generate_fastapi_server(spec)},
                {'name': 'routes/api.py', 'content': generate_fastapi_routes(spec)}
            ]
        }
    
    # Generate infrastructure template
    templates['infrastructure'] = {
        'type': 'Terraform',
        'files': [
            {'name': 'main.tf', 'content': generate_terraform_main(spec, architecture)},
            {'name': 'variables.tf', 'content': generate_terraform_variables(spec)},
            {'name': 'outputs.tf', 'content': generate_terraform_outputs(spec)}
        ]
    }
    
    return templates

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
            'workflows': ['build.yml', 'deploy.yml']
        },
        'monitoring': {
            'platform': 'CloudWatch',
            'alarms': ['cpu_utilization', 'memory_utilization', 'error_rate']
        }
    }

# Template generation functions
def generate_react_package_json(spec):
    return json.dumps({
        "name": spec['name'].lower().replace(' ', '-'),
        "version": "1.0.0",
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "axios": "^1.4.0"
        }
    }, indent=2)

def generate_nextjs_package_json(spec):
    return json.dumps({
        "name": spec['name'].lower().replace(' ', '-'),
        "version": "1.0.0",
        "dependencies": {
            "next": "^14.0.0",
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "axios": "^1.4.0"
        }
    }, indent=2)

def generate_node_package_json(spec):
    return json.dumps({
        "name": f"{spec['name'].lower().replace(' ', '-')}-backend",
        "version": "1.0.0",
        "dependencies": {
            "express": "^4.18.0",
            "cors": "^2.8.5",
            "pg": "^8.11.0"
        }
    }, indent=2)

def generate_python_requirements(spec):
    return f"""fastapi==0.104.1
uvicorn==0.24.0
psycopg2-binary==2.9.9
python-multipart==0.0.6
"""

def generate_express_server(spec):
    return f"""const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

// API routes
app.get('/api/health', (req, res) => {{
    res.json({{ status: 'healthy', system: '{spec['name']}' }});
}});

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => {{
    console.log(`Server running on port ${{PORT}}`);
}});
"""

def generate_fastapi_server(spec):
    return f"""from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="{spec['name']}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {{"status": "healthy", "system": "{spec['name']}"}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

def generate_react_app(spec):
    return f"""import React from 'react';
import './App.css';

function App() {{
  return (
    <div className="App">
      <header className="App-header">
        <h1>{spec['name']}</h1>
        <p>{spec['description']}</p>
      </header>
    </div>
  );
}}

export default App;
"""

def generate_nextjs_page(spec):
    return f"""import Head from 'next/head'
import Header from '../components/Header'

export default function Home() {{
  return (
    <div>
      <Head>
        <title>{spec['name']}</title>
        <meta name="description" content="{spec['description']}" />
      </Head>
      <Header />
      <main>
        <h1>{spec['name']}</h1>
        <p>{spec['description']}</p>
      </main>
    </div>
  )
}}
"""

def generate_react_header(spec):
    return f"""import React from 'react';

function Header() {{
  return (
    <header>
      <h1>{spec['name']}</h1>
      <nav>
        <a href="/">Home</a>
        <a href="/about">About</a>
      </nav>
    </header>
  );
}}

export default Header;
"""

def generate_nextjs_header(spec):
    return f"""import React from 'react';

export default function Header() {{
  return (
    <header>
      <h1>{spec['name']}</h1>
      <nav>
        <a href="/">Home</a>
        <a href="/about">About</a>
      </nav>
    </header>
  );
}}
"""

def generate_api_routes(spec):
    return f"""const express = require('express');
const router = express.Router();

// {spec['name']} API routes
router.get('/health', (req, res) => {{
    res.json({{ status: 'healthy' }});
}});

module.exports = router;
"""

def generate_fastapi_routes(spec):
    return f"""from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health():
    return {{"status": "healthy", "system": "{spec['name']}"}}
"""

def generate_terraform_main(spec, architecture):
    return f"""# {spec['name']} Infrastructure
terraform {{
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

# ECS Cluster
resource "aws_ecs_cluster" "main" {{
  name = "${{var.project_name}}-cluster"
}}

# RDS Database
resource "aws_db_instance" "main" {{
  identifier = "${{var.project_name}}-db"
  engine     = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"
  allocated_storage = 20
  db_name = "${{var.project_name}}"
  username = "admin"
  password = var.db_password
  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name = aws_db_subnet_group.main.name
  skip_final_snapshot = true
}}

# S3 Bucket
resource "aws_s3_bucket" "main" {{
  bucket = "${{var.project_name}}-storage"
}}
"""

def generate_terraform_variables(spec):
    return f"""variable "project_name" {{
  description = "Name of the project"
  type        = string
  default     = "{spec['name'].lower().replace(' ', '-')}"
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
}}
"""

def generate_terraform_outputs(spec):
    return f"""output "cluster_name" {{
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}}

output "db_endpoint" {{
  description = "RDS endpoint"
  value       = aws_db_instance.main.endpoint
}}

output "s3_bucket" {{
  description = "S3 bucket name"
  value       = aws_s3_bucket.main.bucket
}}
"""

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

    return app

# Create app instance for WSGI
app = create_app()
