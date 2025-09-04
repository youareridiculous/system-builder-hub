"""
Agent Ecosystem - Modular, reusable, and composable agents
"""

import json
import secrets as py_secrets
import docker
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import shutil
import zipfile


class AgentType(Enum):
    """Agent types"""
    QA = "qa"
    SCRAPER = "scraper"
    OPTIMIZER = "optimizer"
    BUILDER = "builder"
    ANALYZER = "analyzer"
    INTEGRATOR = "integrator"
    CUSTOM = "custom"


class AgentStatus(Enum):
    """Agent status"""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ExportFormat(Enum):
    """Export formats"""
    DOCKER = "docker"
    PYTHON_PACKAGE = "python_package"
    NODE_PACKAGE = "node_package"
    EMBEDDED_WIDGET = "embedded_widget"
    MICROSERVICE = "microservice"


class AgentCategory(Enum):
    """Agent categories"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    INTEGRATION = "integration"
    OPTIMIZATION = "optimization"
    SECURITY = "security"
    ANALYTICS = "analytics"


@dataclass
class AgentBlock:
    """Modular agent logic block"""
    block_id: str
    name: str
    description: str
    category: AgentCategory
    inputs: List[str]
    outputs: List[str]
    code: str
    dependencies: List[str]
    version: str = "1.0.0"
    author: str = None
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class Agent:
    """Agent entity"""
    agent_id: str
    name: str
    description: str
    agent_type: AgentType
    category: AgentCategory
    version: str
    author: str
    organization_id: str
    status: AgentStatus
    blocks: List[AgentBlock]
    configuration: Dict[str, Any]
    metadata: Dict[str, Any]
    rating: float = 0.0
    usage_count: int = 0
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow().isoformat()


@dataclass
class AgentComposition:
    """Agent composition configuration"""
    composition_id: str
    name: str
    description: str
    agent_blocks: List[str]  # Block IDs in execution order
    connections: List[Dict[str, str]]  # Block output -> Block input mappings
    configuration: Dict[str, Any]
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class AgentExport:
    """Agent export configuration"""
    export_id: str
    agent_id: str
    export_format: ExportFormat
    configuration: Dict[str, Any]
    output_path: str
    status: str = "pending"
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class AgentRating:
    """Agent rating and feedback"""
    rating_id: str
    agent_id: str
    user_id: str
    rating: float
    review: str
    use_case: str
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class AgentEcosystem:
    """Agent ecosystem management system"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.agents_dir = base_dir / "agents"
        self.blocks_dir = base_dir / "agent_blocks"
        self.exports_dir = base_dir / "agent_exports"
        self.ratings_file = base_dir / "agent_ratings.json"
        
        # Create directories
        self.agents_dir.mkdir(exist_ok=True)
        self.blocks_dir.mkdir(exist_ok=True)
        self.exports_dir.mkdir(exist_ok=True)
        
        # Initialize data storage
        self.agents: Dict[str, Agent] = {}
        self.blocks: Dict[str, AgentBlock] = {}
        self.compositions: Dict[str, AgentComposition] = {}
        self.exports: Dict[str, AgentExport] = {}
        self.ratings: Dict[str, List[AgentRating]] = {}
        
        self._load_data()

    def _load_data(self):
        """Load existing data from files"""
        # Load agents
        agents_file = self.base_dir / "agents.json"
        if agents_file.exists():
            with open(agents_file, 'r') as f:
                data = json.load(f)
                for agent_data in data.values():
                    agent = Agent(**agent_data)
                    agent.blocks = [AgentBlock(**block) for block in agent_data.get('blocks', [])]
                    self.agents[agent.agent_id] = agent

        # Load blocks
        blocks_file = self.base_dir / "agent_blocks.json"
        if blocks_file.exists():
            with open(blocks_file, 'r') as f:
                data = json.load(f)
                for block_data in data.values():
                    self.blocks[block_data['block_id']] = AgentBlock(**block_data)

        # Load compositions
        compositions_file = self.base_dir / "agent_compositions.json"
        if compositions_file.exists():
            with open(compositions_file, 'r') as f:
                data = json.load(f)
                for comp_data in data.values():
                    self.compositions[comp_data['composition_id']] = AgentComposition(**comp_data)

        # Load ratings
        if self.ratings_file.exists():
            with open(self.ratings_file, 'r') as f:
                data = json.load(f)
                for agent_id, ratings_data in data.items():
                    self.ratings[agent_id] = [AgentRating(**rating) for rating in ratings_data]

    def _save_data(self):
        """Save data to files"""
        # Save agents
        agents_data = {}
        for agent_id, agent in self.agents.items():
            agent_dict = asdict(agent)
            agent_dict['blocks'] = [asdict(block) for block in agent.blocks]
            agents_data[agent_id] = agent_dict
        
        with open(self.base_dir / "agents.json", 'w') as f:
            json.dump(agents_data, f, indent=2)

        # Save blocks
        blocks_data = {block_id: asdict(block) for block_id, block in self.blocks.items()}
        with open(self.base_dir / "agent_blocks.json", 'w') as f:
            json.dump(blocks_data, f, indent=2)

        # Save compositions
        compositions_data = {comp_id: asdict(comp) for comp_id, comp in self.compositions.items()}
        with open(self.base_dir / "agent_compositions.json", 'w') as f:
            json.dump(compositions_data, f, indent=2)

        # Save ratings
        ratings_data = {}
        for agent_id, ratings in self.ratings.items():
            ratings_data[agent_id] = [asdict(rating) for rating in ratings]
        
        with open(self.ratings_file, 'w') as f:
            json.dump(ratings_data, f, indent=2)

    def create_agent_block(self, name: str, description: str, category: AgentCategory,
                          inputs: List[str], outputs: List[str], code: str,
                          dependencies: List[str], author: str) -> AgentBlock:
        """Create a new agent block"""
        block_id = f"block_{py_secrets.token_hex(8)}"
        
        block = AgentBlock(
            block_id=block_id,
            name=name,
            description=description,
            category=category,
            inputs=inputs,
            outputs=outputs,
            code=code,
            dependencies=dependencies,
            author=author
        )
        
        self.blocks[block_id] = block
        self._save_data()
        
        return block

    def create_agent(self, name: str, description: str, agent_type: AgentType,
                    category: AgentCategory, author: str, organization_id: str,
                    blocks: List[AgentBlock], configuration: Dict[str, Any]) -> Agent:
        """Create a new agent"""
        agent_id = f"agent_{py_secrets.token_hex(8)}"
        
        agent = Agent(
            agent_id=agent_id,
            name=name,
            description=description,
            agent_type=agent_type,
            category=category,
            version="1.0.0",
            author=author,
            organization_id=organization_id,
            status=AgentStatus.DRAFT,
            blocks=blocks,
            configuration=configuration,
            metadata={}
        )
        
        self.agents[agent_id] = agent
        self._save_data()
        
        return agent

    def create_agent_composition(self, name: str, description: str,
                               agent_blocks: List[str], connections: List[Dict[str, str]],
                               configuration: Dict[str, Any]) -> AgentComposition:
        """Create a new agent composition"""
        composition_id = f"comp_{py_secrets.token_hex(8)}"
        
        composition = AgentComposition(
            composition_id=composition_id,
            name=name,
            description=description,
            agent_blocks=agent_blocks,
            connections=connections,
            configuration=configuration
        )
        
        self.compositions[composition_id] = composition
        self._save_data()
        
        return composition

    def publish_agent(self, agent_id: str) -> bool:
        """Publish an agent"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        agent.status = AgentStatus.PUBLISHED
        agent.updated_at = datetime.utcnow().isoformat()
        
        self._save_data()
        return True

    def deprecate_agent(self, agent_id: str) -> bool:
        """Deprecate an agent"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        agent.status = AgentStatus.DEPRECATED
        agent.updated_at = datetime.utcnow().isoformat()
        
        self._save_data()
        return True

    def export_agent(self, agent_id: str, export_format: ExportFormat,
                    configuration: Dict[str, Any]) -> AgentExport:
        """Export an agent in specified format"""
        if agent_id not in self.agents:
            raise ValueError("Agent not found")
        
        agent = self.agents[agent_id]
        export_id = f"export_{py_secrets.token_hex(8)}"
        output_path = str(self.exports_dir / f"{agent_id}_{export_format.value}")
        
        export = AgentExport(
            export_id=export_id,
            agent_id=agent_id,
            export_format=export_format,
            configuration=configuration,
            output_path=output_path
        )
        
        self.exports[export_id] = export
        
        # Perform export based on format
        if export_format == ExportFormat.DOCKER:
            self._export_as_docker(agent, export, configuration)
        elif export_format == ExportFormat.PYTHON_PACKAGE:
            self._export_as_python_package(agent, export, configuration)
        elif export_format == ExportFormat.NODE_PACKAGE:
            self._export_as_node_package(agent, export, configuration)
        elif export_format == ExportFormat.EMBEDDED_WIDGET:
            self._export_as_embedded_widget(agent, export, configuration)
        elif export_format == ExportFormat.MICROSERVICE:
            self._export_as_microservice(agent, export, configuration)
        
        return export

    def _export_as_docker(self, agent: Agent, export: AgentExport, config: Dict[str, Any]):
        """Export agent as Docker container"""
        docker_dir = Path(export.output_path)
        docker_dir.mkdir(exist_ok=True)
        
        # Create Dockerfile
        dockerfile_content = f"""
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy agent code
COPY agent_code/ .

# Create agent configuration
COPY config.json .

# Run agent
CMD ["python", "main.py"]
"""
        
        with open(docker_dir / "Dockerfile", 'w') as f:
            f.write(dockerfile_content)
        
        # Create requirements.txt
        requirements = ["flask", "requests", "json"]
        with open(docker_dir / "requirements.txt", 'w') as f:
            f.write('\n'.join(requirements))
        
        # Create agent code
        agent_code_dir = docker_dir / "agent_code"
        agent_code_dir.mkdir(exist_ok=True)
        
        # Generate main.py from agent blocks
        main_code = self._generate_agent_code(agent)
        with open(agent_code_dir / "main.py", 'w') as f:
            f.write(main_code)
        
        # Create config.json
        with open(docker_dir / "config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        export.status = "completed"

    def _export_as_python_package(self, agent: Agent, export: AgentExport, config: Dict[str, Any]):
        """Export agent as Python package"""
        package_dir = Path(export.output_path)
        package_dir.mkdir(exist_ok=True)
        
        # Create setup.py
        setup_content = f"""
from setuptools import setup, find_packages

setup(
    name="{agent.name.lower().replace(' ', '-')}",
    version="{agent.version}",
    description="{agent.description}",
    author="{agent.author}",
    packages=find_packages(),
    install_requires=[
        "flask",
        "requests",
        "json"
    ],
    python_requires=">=3.8",
)
"""
        
        with open(package_dir / "setup.py", 'w') as f:
            f.write(setup_content)
        
        # Create package directory
        package_name = agent.name.lower().replace(' ', '_')
        package_src_dir = package_dir / package_name
        package_src_dir.mkdir(exist_ok=True)
        
        # Create __init__.py
        init_content = f"""
\"\"\"
{agent.name} - {agent.description}
\"\"\"

from .agent import {agent.name.replace(' ', '')}Agent

__version__ = "{agent.version}"
__author__ = "{agent.author}"
"""
        
        with open(package_src_dir / "__init__.py", 'w') as f:
            f.write(init_content)
        
        # Create agent.py
        agent_code = self._generate_agent_code(agent)
        with open(package_src_dir / "agent.py", 'w') as f:
            f.write(agent_code)
        
        export.status = "completed"

    def _export_as_node_package(self, agent: Agent, export: AgentExport, config: Dict[str, Any]):
        """Export agent as Node.js package"""
        package_dir = Path(export.output_path)
        package_dir.mkdir(exist_ok=True)
        
        # Create package.json
        package_json = {
            "name": agent.name.lower().replace(' ', '-'),
            "version": agent.version,
            "description": agent.description,
            "author": agent.author,
            "main": "index.js",
            "scripts": {
                "start": "node index.js",
                "test": "jest"
            },
            "dependencies": {
                "express": "^4.17.1",
                "axios": "^0.21.1"
            },
            "devDependencies": {
                "jest": "^27.0.6"
            }
        }
        
        with open(package_dir / "package.json", 'w') as f:
            json.dump(package_json, f, indent=2)
        
        # Create index.js
        index_content = f"""
const express = require('express');
const app = express();

app.use(express.json());

// {agent.name} Agent
class {agent.name.replace(' ', '')}Agent {{
    constructor(config) {{
        this.config = config;
    }}
    
    async process(input) {{
        // Agent logic here
        return {{ result: 'processed' }};
    }}
}}

const agent = new {agent.name.replace(' ', '')}Agent({json.dumps(config)});

app.post('/process', async (req, res) => {{
    try {{
        const result = await agent.process(req.body);
        res.json(result);
    }} catch (error) {{
        res.status(500).json({{ error: error.message }});
    }}
}});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {{
    console.log(`{agent.name} agent running on port ${{PORT}}`);
}});
"""
        
        with open(package_dir / "index.js", 'w') as f:
            f.write(index_content)
        
        export.status = "completed"

    def _export_as_embedded_widget(self, agent: Agent, export: AgentExport, config: Dict[str, Any]):
        """Export agent as embedded widget"""
        widget_dir = Path(export.output_path)
        widget_dir.mkdir(exist_ok=True)
        
        # Create widget HTML
        widget_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{agent.name} Widget</title>
    <style>
        .agent-widget {{
            border: 1px solid #ccc;
            padding: 20px;
            border-radius: 8px;
            max-width: 400px;
        }}
        .agent-title {{
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .agent-input {{
            width: 100%;
            padding: 8px;
            margin-bottom: 10px;
        }}
        .agent-button {{
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
        }}
        .agent-result {{
            margin-top: 10px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="agent-widget">
        <div class="agent-title">{agent.name}</div>
        <div>{agent.description}</div>
        <input type="text" class="agent-input" id="agentInput" placeholder="Enter input...">
        <button class="agent-button" onclick="processInput()">Process</button>
        <div class="agent-result" id="agentResult"></div>
    </div>
    
    <script>
        async function processInput() {{
            const input = document.getElementById('agentInput').value;
            const resultDiv = document.getElementById('agentResult');
            
            try {{
                const response = await fetch('/api/agent/{agent.agent_id}/process', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ input: input }})
                }});
                
                const result = await response.json();
                resultDiv.innerHTML = '<strong>Result:</strong> ' + JSON.stringify(result);
            }} catch (error) {{
                resultDiv.innerHTML = '<strong>Error:</strong> ' + error.message;
            }}
        }}
    </script>
</body>
</html>
"""
        
        with open(widget_dir / "widget.html", 'w') as f:
            f.write(widget_html)
        
        # Create widget.js for iframe integration
        widget_js = f"""
// {agent.name} Widget Integration
(function() {{
    window.{agent.name.replace(' ', '')}Widget = {{
        init: function(containerId, config) {{
            const container = document.getElementById(containerId);
            if (!container) {{
                console.error('Container not found:', containerId);
                return;
            }}
            
            // Load widget HTML
            fetch('/widgets/{agent.agent_id}/widget.html')
                .then(response => response.text())
                .then(html => {{
                    container.innerHTML = html;
                }})
                .catch(error => {{
                    console.error('Failed to load widget:', error);
                }});
        }},
        
        process: async function(input) {{
            try {{
                const response = await fetch('/api/agent/{agent.agent_id}/process', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ input: input }})
                }});
                
                return await response.json();
            }} catch (error) {{
                throw new Error('Widget processing failed: ' + error.message);
            }}
        }}
    }};
}})();
"""
        
        with open(widget_dir / "widget.js", 'w') as f:
            f.write(widget_js)
        
        export.status = "completed"

    def _export_as_microservice(self, agent: Agent, export: AgentExport, config: Dict[str, Any]):
        """Export agent as microservice"""
        service_dir = Path(export.output_path)
        service_dir.mkdir(exist_ok=True)
        
        # Create docker-compose.yml
        compose_content = f"""
version: '3.8'

services:
  {agent.name.lower().replace(' ', '-')}-agent:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    volumes:
      - ./config:/app/config
    restart: unless-stopped
"""
        
        with open(service_dir / "docker-compose.yml", 'w') as f:
            f.write(compose_content)
        
        # Create Kubernetes deployment
        k8s_deployment = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {agent.name.lower().replace(' ', '-')}-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {agent.name.lower().replace(' ', '-')}-agent
  template:
    metadata:
      labels:
        app: {agent.name.lower().replace(' ', '-')}-agent
    spec:
      containers:
      - name: {agent.name.lower().replace(' ', '-')}-agent
        image: {agent.name.lower().replace(' ', '-')}-agent:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
---
apiVersion: v1
kind: Service
metadata:
  name: {agent.name.lower().replace(' ', '-')}-agent-service
spec:
  selector:
    app: {agent.name.lower().replace(' ', '-')}-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: LoadBalancer
"""
        
        with open(service_dir / "k8s-deployment.yaml", 'w') as f:
            f.write(k8s_deployment)
        
        # Create main service file
        service_code = f"""
import asyncio
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="{agent.name} Agent")

class ProcessRequest(BaseModel):
    input: str
    config: dict = {{}}

class ProcessResponse(BaseModel):
    result: dict
    metadata: dict

@app.post("/process", response_model=ProcessResponse)
async def process_input(request: ProcessRequest):
    try:
        # Agent processing logic here
        result = await process_agent_input(request.input, request.config)
        return ProcessResponse(
            result=result,
            metadata={{
                "agent_id": "{agent.agent_id}",
                "version": "{agent.version}",
                "timestamp": "2024-01-15T10:30:00Z"
            }}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_agent_input(input_data: str, config: dict):
    # Implement agent-specific logic here
    return {{"processed_input": input_data, "config": config}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
"""
        
        with open(service_dir / "main.py", 'w') as f:
            f.write(service_code)
        
        export.status = "completed"

    def _generate_agent_code(self, agent: Agent) -> str:
        """Generate code from agent blocks"""
        code_parts = []
        
        # Add imports
        code_parts.append("import json")
        code_parts.append("import asyncio")
        code_parts.append("from typing import Dict, Any")
        code_parts.append("")
        
        # Add agent class
        code_parts.append(f"class {agent.name.replace(' ', '')}Agent:")
        code_parts.append("    def __init__(self, config: Dict[str, Any]):")
        code_parts.append("        self.config = config")
        code_parts.append("")
        
        # Add block methods
        for block in agent.blocks:
            code_parts.append(f"    async def {block.name.lower().replace(' ', '_')}(self, inputs: Dict[str, Any]):")
            code_parts.append(f'        """{block.description}"""')
            code_parts.append(f"        {block.code}")
            code_parts.append("")
        
        # Add main process method
        code_parts.append("    async def process(self, input_data: str) -> Dict[str, Any]:")
        code_parts.append("        try:")
        
        # Chain blocks together
        for i, block in enumerate(agent.blocks):
            if i == 0:
                code_parts.append(f"            result = await self.{block.name.lower().replace(' ', '_')}({{'input': input_data}})")
            else:
                prev_block = agent.blocks[i-1]
                code_parts.append(f"            result = await self.{block.name.lower().replace(' ', '_')}(result)")
        
        code_parts.append("            return result")
        code_parts.append("        except Exception as e:")
        code_parts.append("            return {'error': str(e)}")
        code_parts.append("")
        
        # Add usage example
        code_parts.append("if __name__ == '__main__':")
        code_parts.append("    import asyncio")
        code_parts.append("    agent = Agent(config={})")
        code_parts.append("    result = asyncio.run(agent.process('test input'))")
        code_parts.append("    print(result)")
        
        return "\n".join(code_parts)

    def rate_agent(self, agent_id: str, user_id: str, rating: float, 
                  review: str, use_case: str) -> AgentRating:
        """Rate an agent"""
        if agent_id not in self.agents:
            raise ValueError("Agent not found")
        
        rating_id = f"rating_{py_secrets.token_hex(8)}"
        
        agent_rating = AgentRating(
            rating_id=rating_id,
            agent_id=agent_id,
            user_id=user_id,
            rating=rating,
            review=review,
            use_case=use_case
        )
        
        if agent_id not in self.ratings:
            self.ratings[agent_id] = []
        
        self.ratings[agent_id].append(agent_rating)
        
        # Update agent rating
        agent = self.agents[agent_id]
        ratings = [r.rating for r in self.ratings[agent_id]]
        agent.rating = sum(ratings) / len(ratings)
        agent.usage_count += 1
        
        self._save_data()
        
        return agent_rating

    def suggest_agents(self, context: Dict[str, Any], limit: int = 5) -> List[Agent]:
        """Suggest agents based on context"""
        suggestions = []
        
        for agent in self.agents.values():
            if agent.status != AgentStatus.PUBLISHED:
                continue
            
            # Calculate relevance score based on context
            score = self._calculate_relevance_score(agent, context)
            
            if score > 0.5:  # Minimum relevance threshold
                suggestions.append((agent, score))
        
        # Sort by relevance score and return top results
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [agent for agent, score in suggestions[:limit]]

    def _calculate_relevance_score(self, agent: Agent, context: Dict[str, Any]) -> float:
        """Calculate relevance score for agent suggestion"""
        score = 0.0
        
        # Check category match
        if 'category' in context and context['category'] == agent.category.value:
            score += 0.3
        
        # Check agent type match
        if 'agent_type' in context and context['agent_type'] == agent.agent_type.value:
            score += 0.2
        
        # Check keyword matches in description
        if 'keywords' in context:
            keywords = context['keywords']
            description_lower = agent.description.lower()
            for keyword in keywords:
                if keyword.lower() in description_lower:
                    score += 0.1
        
        # Consider rating and usage
        score += agent.rating * 0.2
        score += min(agent.usage_count / 100, 0.1)  # Cap usage bonus
        
        return min(score, 1.0)

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)

    def get_agent_block(self, block_id: str) -> Optional[AgentBlock]:
        """Get agent block by ID"""
        return self.blocks.get(block_id)

    def get_agents_by_category(self, category: AgentCategory) -> List[Agent]:
        """Get agents by category"""
        return [agent for agent in self.agents.values() if agent.category == category]

    def get_agents_by_organization(self, organization_id: str) -> List[Agent]:
        """Get agents by organization"""
        return [agent for agent in self.agents.values() if agent.organization_id == organization_id]

    def get_agent_ratings(self, agent_id: str) -> List[AgentRating]:
        """Get ratings for an agent"""
        return self.ratings.get(agent_id, [])

    def search_agents(self, query: str) -> List[Agent]:
        """Search agents by name and description"""
        query_lower = query.lower()
        results = []
        
        for agent in self.agents.values():
            if (query_lower in agent.name.lower() or 
                query_lower in agent.description.lower()):
                results.append(agent)
        
        return results

    def get_agent_export(self, export_id: str) -> Optional[AgentExport]:
        """Get agent export by ID"""
        return self.exports.get(export_id)

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent"""
        if agent_id not in self.agents:
            return False
        
        del self.agents[agent_id]
        
        # Remove associated ratings
        if agent_id in self.ratings:
            del self.ratings[agent_id]
        
        self._save_data()
        return True
