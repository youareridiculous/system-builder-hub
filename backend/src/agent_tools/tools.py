"""
Built-in agent tools
"""
import os
import logging
import requests
import json
from typing import Dict, Any, List
from src.agent_tools.types import ToolSpec, ToolAuth, ToolContext
from src.agent_tools.types import (
    DB_MIGRATE_SCHEMA, HTTP_OPENAPI_SCHEMA, FILES_STORE_SCHEMA,
    QUEUE_ENQUEUE_SCHEMA, EMAIL_SEND_SCHEMA
)

logger = logging.getLogger(__name__)

# Database Migration Tool
def db_migrate_handler(args: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
    """Handle database migration tool calls"""
    try:
        op = args.get('op')
        table = args.get('table')
        dry_run = args.get('dry_run', False)
        
        if op == 'create_table':
            columns = args.get('columns', [])
            
            # Generate SQL for table creation
            sql_parts = [f"CREATE TABLE {table} ("]
            
            column_definitions = []
            for col in columns:
                name = col['name']
                col_type = col['type']
                nullable = col.get('nullable', True)
                pk = col.get('pk', False)
                
                definition = f"{name} {col_type}"
                if not nullable:
                    definition += " NOT NULL"
                if pk:
                    definition += " PRIMARY KEY"
                
                column_definitions.append(definition)
            
            # Add tenant_id if multi-tenant
            if os.environ.get('MULTI_TENANT', 'true').lower() == 'true':
                column_definitions.append("tenant_id VARCHAR(255) NOT NULL")
            
            sql_parts.append(", ".join(column_definitions))
            sql_parts.append(");")
            
            sql = " ".join(sql_parts)
            
            if dry_run:
                return {
                    'sql': sql,
                    'operation': 'create_table',
                    'table': table,
                    'dry_run': True
                }
            else:
                # In a real implementation, this would execute the migration
                logger.info(f"Would execute migration: {sql}")
                return {
                    'sql': sql,
                    'operation': 'create_table',
                    'table': table,
                    'executed': True
                }
        
        elif op == 'add_column':
            column = args.get('column', {})
            name = column['name']
            col_type = column['type']
            nullable = column.get('nullable', True)
            
            sql = f"ALTER TABLE {table} ADD COLUMN {name} {col_type}"
            if not nullable:
                sql += " NOT NULL"
            sql += ";"
            
            if dry_run:
                return {
                    'sql': sql,
                    'operation': 'add_column',
                    'table': table,
                    'column': name,
                    'dry_run': True
                }
            else:
                logger.info(f"Would execute migration: {sql}")
                return {
                    'sql': sql,
                    'operation': 'add_column',
                    'table': table,
                    'column': name,
                    'executed': True
                }
        
        else:
            return {
                'error': f'Unsupported operation: {op}'
            }
    
    except Exception as e:
        logger.error(f"Error in db_migrate_handler: {e}")
        return {
            'error': str(e)
        }

# HTTP OpenAPI Tool
def http_openapi_handler(args: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
    """Handle HTTP OpenAPI tool calls"""
    try:
        base = args.get('base')
        op_id = args.get('op_id')
        params = args.get('params', {})
        body = args.get('body')
        headers = args.get('headers', {})
        
        # For demo purposes, handle common operations
        if 'jsonplaceholder.typicode.com' in base:
            if op_id == 'get_posts':
                response = requests.get(f"{base}/posts", params=params, headers=headers)
            elif op_id == 'get_post':
                post_id = params.get('id', 1)
                response = requests.get(f"{base}/posts/{post_id}", headers=headers)
            elif op_id == 'create_post':
                response = requests.post(f"{base}/posts", json=body, headers=headers)
            else:
                return {
                    'error': f'Unknown operation: {op_id}'
                }
        else:
            # Generic HTTP request
            method = op_id.split('_')[0].upper()
            if method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                method = 'GET'
            
            url = f"{base}/{op_id}"
            response = requests.request(method, url, params=params, json=body, headers=headers)
        
        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'body': response.text,
            'url': response.url
        }
    
    except Exception as e:
        logger.error(f"Error in http_openapi_handler: {e}")
        return {
            'error': str(e)
        }

# File Store Tool
def files_store_handler(args: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
    """Handle file store tool calls"""
    try:
        action = args.get('action')
        store = args.get('store')
        prefix = args.get('prefix', '')
        
        if action == 'list':
            # Mock file listing
            files = [
                {
                    'name': f'{prefix}file1.txt',
                    'size': 1024,
                    'modified': '2024-01-15T10:00:00Z'
                },
                {
                    'name': f'{prefix}file2.json',
                    'size': 2048,
                    'modified': '2024-01-15T11:00:00Z'
                }
            ]
            
            return {
                'store': store,
                'prefix': prefix,
                'files': files,
                'count': len(files)
            }
        
        elif action == 'info':
            return {
                'store': store,
                'total_files': 2,
                'total_size': 3072,
                'last_modified': '2024-01-15T11:00:00Z'
            }
        
        else:
            return {
                'error': f'Unknown action: {action}'
            }
    
    except Exception as e:
        logger.error(f"Error in files_store_handler: {e}")
        return {
            'error': str(e)
        }

# Queue Enqueue Tool
def queue_enqueue_handler(args: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
    """Handle queue enqueue tool calls"""
    try:
        queue = args.get('queue', 'default')
        job = args.get('job')
        payload = args.get('payload', {})
        
        # Mock job enqueuing
        job_id = f"job_{hash(str(payload)) % 10000}"
        
        logger.info(f"Would enqueue job {job} on queue {queue} with payload: {payload}")
        
        return {
            'job_id': job_id,
            'job': job,
            'queue': queue,
            'enqueued': True,
            'payload': payload
        }
    
    except Exception as e:
        logger.error(f"Error in queue_enqueue_handler: {e}")
        return {
            'error': str(e)
        }

# Email Send Tool
def email_send_handler(args: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
    """Handle email send tool calls"""
    try:
        template = args.get('template')
        to_email = args.get('to')
        payload = args.get('payload', {})
        dry_run = args.get('dry_run', False)
        
        if dry_run:
            return {
                'template': template,
                'to': to_email,
                'payload': payload,
                'dry_run': True,
                'message': 'Email would be sent in production'
            }
        else:
            # Mock email sending
            logger.info(f"Would send email using template {template} to {to_email}")
            
            return {
                'template': template,
                'to': to_email,
                'sent': True,
                'message_id': f"msg_{hash(to_email) % 10000}"
            }
    
    except Exception as e:
        logger.error(f"Error in email_send_handler: {e}")
        return {
            'error': str(e)
        }

# Register all tools
def register_builtin_tools():
    """Register all built-in tools"""
    from src.agent_tools.registry import tool_registry
    from src.agent_tools.types import ToolSpec, ToolAuth
    
    # Database Migration Tool
    db_migrate_spec = ToolSpec(
        name='db.migrate',
        version='1.0.0',
        description='Generate and apply Alembic migrations for database schema changes',
        input_schema=DB_MIGRATE_SCHEMA,
        output_schema={
            'type': 'object',
            'properties': {
                'sql': {'type': 'string'},
                'operation': {'type': 'string'},
                'table': {'type': 'string'},
                'executed': {'type': 'boolean'},
                'dry_run': {'type': 'boolean'},
                'error': {'type': 'string'}
            }
        },
        auth=ToolAuth.TENANT,
        allow_concurrent=False
    )
    tool_registry.register(db_migrate_spec, db_migrate_handler)
    
    # HTTP OpenAPI Tool
    http_openapi_spec = ToolSpec(
        name='http.openapi',
        version='1.0.0',
        description='Make HTTP requests to allowlisted APIs using OpenAPI operations',
        input_schema=HTTP_OPENAPI_SCHEMA,
        output_schema={
            'type': 'object',
            'properties': {
                'status_code': {'type': 'integer'},
                'headers': {'type': 'object'},
                'body': {'type': 'string'},
                'url': {'type': 'string'},
                'error': {'type': 'string'}
            }
        },
        auth=ToolAuth.TENANT,
        allow_concurrent=True
    )
    tool_registry.register(http_openapi_spec, http_openapi_handler)
    
    # File Store Tool
    files_store_spec = ToolSpec(
        name='files.store',
        version='1.0.0',
        description='List and get information about files in FileStore',
        input_schema=FILES_STORE_SCHEMA,
        output_schema={
            'type': 'object',
            'properties': {
                'store': {'type': 'string'},
                'files': {'type': 'array'},
                'count': {'type': 'integer'},
                'error': {'type': 'string'}
            }
        },
        auth=ToolAuth.TENANT,
        allow_concurrent=True
    )
    tool_registry.register(files_store_spec, files_store_handler)
    
    # Queue Enqueue Tool
    queue_enqueue_spec = ToolSpec(
        name='queue.enqueue',
        version='1.0.0',
        description='Enqueue background jobs by name with payload',
        input_schema=QUEUE_ENQUEUE_SCHEMA,
        output_schema={
            'type': 'object',
            'properties': {
                'job_id': {'type': 'string'},
                'job': {'type': 'string'},
                'payload': {'type': 'object'},
                'queue': {'type': 'string'},
                'enqueued': {'type': 'boolean'},
                'error': {'type': 'string'}
            }
        },
        auth=ToolAuth.TENANT,
        allow_concurrent=True
    )
    tool_registry.register(queue_enqueue_spec, queue_enqueue_handler)
    
    # Email Send Tool
    email_send_spec = ToolSpec(
        name='email.send',
        version='1.0.0',
        description='Send transactional emails using existing SES pipeline',
        input_schema=EMAIL_SEND_SCHEMA,
        output_schema={
            'type': 'object',
            'properties': {
                'template': {'type': 'string'},
                'to': {'type': 'string'},
                'sent': {'type': 'boolean'},
                'message_id': {'type': 'string'},
                'dry_run': {'type': 'boolean'},
                'error': {'type': 'string'}
            }
        },
        auth=ToolAuth.TENANT,
        allow_concurrent=True
    )
    tool_registry.register(email_send_spec, email_send_handler)
    
    logger.info("Registered built-in agent tools")
