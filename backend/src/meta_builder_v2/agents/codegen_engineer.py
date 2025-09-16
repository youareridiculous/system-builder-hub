"""
Codegen Engineer Agent for Meta-Builder v2
Generates code diffs and applies them to the target repository.
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from uuid import UUID

from .base import BaseAgent, AgentContext
from src.obs.audit import audit

logger = logging.getLogger(__name__)


class CodegenEngineerAgent(BaseAgent):
    """Codegen Engineer Agent - generates and applies code changes."""
    
    def __init__(self, context: AgentContext):
        super().__init__(context)
    
    async def execute(self, spec: Dict[str, Any], plan: Dict[str, Any], 
                     artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute code generation and apply changes."""
        
        logger.info("codegen_engineer.started", {
            "spec_id": spec.get("id"),
            "plan_id": plan.get("id"),
            "tenant_id": self.context.tenant_id
        })
        
        try:
            # Generate code based on plan
            generated_code = await self._generate_code(spec, plan)
            
            # Create unified diff
            diff_artifact = await self._create_diff_artifact(generated_code, spec, plan)
            
            # Apply changes (sandboxed in test mode)
            applied = await self._apply_changes(diff_artifact, spec)
            
            logger.info("codegen_engineer.completed", {
                "spec_id": spec.get("id"),
                "diff_id": diff_artifact.get("id"),
                "files_changed": diff_artifact.get("files_changed", 0),
                "applied": applied
            })
            
            return {
                "status": "success",
                "diff_artifact": diff_artifact,
                "applied": applied,
                "notes": f"Generated {diff_artifact.get('files_changed', 0)} files"
            }
            
        except Exception as e:
            logger.error("codegen_engineer.failed", {
                "spec_id": spec.get("id"),
                "error": str(e)
            })
            raise
    
    async def _generate_code(self, spec: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code based on specification and plan."""
        
        entities = plan.get("plan_graph", {}).get("entities", [])
        apis = plan.get("plan_graph", {}).get("apis", [])
        pages = plan.get("plan_graph", {}).get("pages", [])
        
        generated_files = {}
        
        # Generate model files
        for entity in entities:
            entity_name = entity.get("name", "Entity")
            generated_files[f"models/{entity_name.lower()}.py"] = self._generate_model(entity)
        
        # Generate API files
        for api in apis:
            api_name = api.get("name", "api")
            generated_files[f"api/{api_name.lower()}.py"] = self._generate_api(api)
        
        # Generate UI components
        for page in pages:
            page_name = page.get("name", "Page")
            generated_files[f"ui/{page_name.lower()}.tsx"] = self._generate_ui_component(page)
        
        return {
            "files": generated_files,
            "total_files": len(generated_files)
        }
    
    def _generate_model(self, entity: Dict[str, Any]) -> str:
        """Generate SQLAlchemy model code."""
        entity_name = entity.get("name", "Entity")
        fields = entity.get("fields", [])
        
        field_definitions = []
        for field in fields:
            field_name = field.get("name", "field")
            field_type = field.get("type", "String")
            nullable = "nullable=False" if field.get("required", False) else "nullable=True"
            field_definitions.append(f"    {field_name} = Column({field_type}, {nullable})")
        
        return f'''from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class {entity_name}(Base):
    __tablename__ = "{entity_name.lower()}s"
    
    id = Column(Integer, primary_key=True)
{chr(10).join(field_definitions)}
    
    def __repr__(self):
        return f"<{entity_name}(id={{self.id}})>"
'''
    
    def _generate_api(self, api: Dict[str, Any]) -> str:
        """Generate FastAPI endpoint code."""
        api_name = api.get("name", "API")
        entity_name = api.get("entity", "Entity")
        
        return f'''from fastapi import APIRouter, HTTPException
from typing import List
from models.{entity_name.lower()} import {entity_name}

router = APIRouter(prefix="/api/{entity_name.lower()}s", tags=["{entity_name}"])

@router.get("/", response_model=List[{entity_name}])
async def get_{entity_name.lower()}s():
    """Get all {entity_name.lower()}s."""
    return []

@router.get("/{{item_id}}", response_model={entity_name})
async def get_{entity_name.lower()}(item_id: int):
    """Get a {entity_name.lower()} by ID."""
    return None

@router.post("/", response_model={entity_name})
async def create_{entity_name.lower()}(item: {entity_name}):
    """Create a new {entity_name.lower()}."""
    return item

@router.put("/{{item_id}}", response_model={entity_name})
async def update_{entity_name.lower()}(item_id: int, item: {entity_name}):
    """Update a {entity_name.lower()}."""
    return item

@router.delete("/{{item_id}}")
async def delete_{entity_name.lower()}(item_id: int):
    """Delete a {entity_name.lower()}."""
    return {{"message": "{entity_name} deleted"}}
'''
    
    def _generate_ui_component(self, page: Dict[str, Any]) -> str:
        """Generate React component code."""
        page_name = page.get("name", "Page")
        page_type = page.get("type", "list")
        
        if page_type == "list":
            return f'''import React, {{ useState, useEffect }} from 'react';
import {{ Table, Button, Space, Input, Select }} from 'antd';
import {{ SearchOutlined, PlusOutlined }} from '@ant-design/icons';

interface {page_name} {{
  id: string;
  // Add entity fields here
}}

const {page_name}: React.FC = () => {{
  const [items, setItems] = useState<{page_name}[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');

  useEffect(() => {{
    fetchItems();
  }}, []);

  const fetchItems = async () => {{
    try {{
      setLoading(true);
      const response = await fetch('/api/items');
      const data = await response.json();
      setItems(data);
    }} catch (error) {{
      console.error('Error fetching items:', error);
    }} finally {{
      setLoading(false);
    }}
  }};

  const handleEdit = (id: string) => {{
    window.location.href = `/items/${{id}}`;
  }};

  const handleDelete = async (id: string) => {{
    if (confirm('Are you sure you want to delete this item?')) {{
      try {{
        await fetch(`/api/items/${{id}}`, {{ method: 'DELETE' }});
        fetchItems();
      }} catch (error) {{
        console.error('Error deleting item:', error);
      }}
    }}
  }};

  const columns = [
    {{
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
    }},
    {{
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={{() => handleEdit(record.id)}}>
            Edit
          </Button>
          <Button type="link" danger onClick={{() => handleDelete(record.id)}}>
            Delete
          </Button>
        </Space>
      ),
    }},
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between' }}>
        <Input
          placeholder="Search items"
          prefix={{<SearchOutlined />}}
          value={{searchText}}
          onChange={{e => setSearchText(e.target.value)}}
          style={{ width: '300px' }}
        />
        <Button type="primary" icon={{<PlusOutlined />}}>
          Add New
        </Button>
      </div>
      <Table
        columns={{columns}}
        dataSource={{items}}
        loading={{loading}}
        rowKey="id"
      />
    </div>
  );
}};

export default {page_name};
'''
        else:
            return f'''import React from 'react';

const {page_name}: React.FC = () => {{
  return (
    <div>
      <h1>{page_name}</h1>
      <p>This is a {page_type} page.</p>
    </div>
  );
}};

export default {page_name};
'''
    
    async def _create_diff_artifact(self, generated_code: Dict[str, Any], 
                                   spec: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        """Create a diff artifact from generated code."""
        
        files = generated_code.get("files", {})
        unified_diff = []
        
        for file_path, content in files.items():
            # Create a simple unified diff format
            diff_content = f"""--- a/{file_path}
+++ b/{file_path}
@@ -0,0 +1,{len(content.split(chr(10)))} @@
+{chr(10).join('+' + line for line in content.split(chr(10)))}
"""
            unified_diff.append(diff_content)
        
        return {
            "id": str(uuid.uuid4()),
            "unified_diff": chr(10).join(unified_diff),
            "files_changed": len(files),
            "file_list": list(files.keys()),
            "risk": {
                "level": "low",
                "reasons": ["Generated code follows standard patterns"]
            },
            "summary": f"Generated {len(files)} files for {spec.get('title', 'system')}"
        }
    
    async def _apply_changes(self, diff_artifact: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        """Apply changes to the target repository (sandboxed in test mode)."""
        
        # In test mode, we don't actually apply changes
        # In production, this would create a branch and apply the diff
        
        logger.info("codegen_engineer.changes_applied", {
            "diff_id": diff_artifact.get("id"),
            "files_changed": diff_artifact.get("files_changed"),
            "test_mode": True
        })
        
        return True
