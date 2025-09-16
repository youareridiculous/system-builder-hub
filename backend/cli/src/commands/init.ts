import { Command } from '@oclif/core';
import { UI } from '../utils/ui';
import { SBHAPI } from '../utils/api';
import config from '../utils/config';
import * as fs from 'fs-extra';
import * as path from 'path';
import { execSync } from 'child_process';

export default class Init extends Command {
  static description = 'Initialize a new SBH scaffold project locally';

  static examples = [
    '$ sbh init',
    '$ sbh init --template flagship-crm',
    '$ sbh init --name my-project',
  ];

  static flags = {
    template: {
      char: 't',
      description: 'Template to use for initialization',
      default: 'flagship-crm',
    },
    name: {
      char: 'n',
      description: 'Project name',
    },
    interactive: {
      char: 'i',
      description: 'Run in interactive mode',
      default: true,
    },
  };

  async run() {
    const { flags } = await this.parse(Init);
    const ui = new UI();

    try {
      // Get project name
      let projectName = flags.name;
      if (!projectName || flags.interactive) {
        projectName = await ui.input('Enter project name:', 'my-sbh-project');
      }

      // Validate project name
      if (!/^[a-zA-Z0-9-_]+$/.test(projectName)) {
        ui.error('Project name can only contain letters, numbers, hyphens, and underscores');
        return;
      }

      // Check if directory exists
      const projectPath = path.resolve(projectName);
      if (fs.existsSync(projectPath)) {
        const overwrite = await ui.confirm(
          `Directory "${projectName}" already exists. Overwrite?`,
          false
        );
        if (!overwrite) {
          ui.info('Operation cancelled');
          return;
        }
        fs.removeSync(projectPath);
      }

      // Get template
      let templateSlug = flags.template;
      if (flags.interactive) {
        ui.info('Fetching available templates...');
        const templates = await SBHAPI.listTemplates();
        const templateChoices = templates.data.map((t: any) => ({
          name: `${t.attributes.name} - ${t.attributes.description}`,
          value: t.attributes.slug,
        }));
        
        templateSlug = await ui.select('Select template:', templateChoices.map(t => t.value));
      }

      // Create project directory
      ui.startSpinner('Creating project directory...');
      fs.mkdirSync(projectPath, { recursive: true });
      ui.stopSpinner(true, 'Project directory created');

      // Get template details
      ui.startSpinner('Fetching template details...');
      const template = await SBHAPI.getTemplate(templateSlug);
      ui.stopSpinner(true, 'Template details fetched');

      // Create project structure
      ui.startSpinner('Setting up project structure...');
      
      // Create basic project files
      const packageJson = {
        name: projectName,
        version: '1.0.0',
        description: `SBH scaffold project using ${template.data.attributes.name}`,
        main: 'src/app.py',
        scripts: {
          start: 'python src/app.py',
          dev: 'python src/app.py --dev',
          test: 'python -m pytest tests/',
          migrate: 'alembic upgrade head',
        },
        dependencies: {
          flask: '^2.3.0',
          sqlalchemy: '^2.0.0',
          alembic: '^1.12.0',
          'flask-jwt-extended': '^4.5.0',
          'flask-cors': '^4.0.0',
        },
        devDependencies: {
          pytest: '^7.4.0',
          'pytest-cov': '^4.1.0',
        },
      };

      fs.writeJsonSync(path.join(projectPath, 'package.json'), packageJson, { spaces: 2 });

      // Create README
      const readme = `# ${projectName}

This project was generated using the SBH ${template.data.attributes.name} template.

## Features

${template.data.attributes.features.map((f: string) => `- ${f}`).join('\n')}

## Getting Started

1. Install dependencies:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

2. Set up environment:
   \`\`\`bash
   cp .env.example .env
   # Edit .env with your configuration
   \`\`\`

3. Run migrations:
   \`\`\`bash
   sbh run --migrate
   \`\`\`

4. Start development server:
   \`\`\`bash
   sbh run
   \`\`\`

## Development

- \`sbh run\` - Start development server
- \`sbh test\` - Run tests
- \`sbh deploy\` - Deploy to production
- \`sbh export\` - Export project bundle

## Template Information

- **Template**: ${template.data.attributes.name}
- **Version**: ${template.data.attributes.version}
- **Category**: ${template.data.attributes.category}
- **Documentation**: ${template.data.attributes.documentation || 'N/A'}

Generated with SBH CLI v1.0.0
`;

      fs.writeFileSync(path.join(projectPath, 'README.md'), readme);

      // Create .sbh directory with project metadata
      const sbhDir = path.join(projectPath, '.sbh');
      fs.mkdirSync(sbhDir, { recursive: true });

      const projectConfig = {
        name: projectName,
        template: templateSlug,
        templateVersion: template.data.attributes.version,
        createdAt: new Date().toISOString(),
        sbhVersion: '1.0.0',
        features: template.data.attributes.features,
        plans: template.data.attributes.plans,
      };

      fs.writeJsonSync(path.join(sbhDir, 'project.json'), projectConfig, { spaces: 2 });

      // Create basic source structure
      const srcDir = path.join(projectPath, 'src');
      fs.mkdirSync(srcDir, { recursive: true });

      // Create basic app.py
      const appPy = `"""
${projectName} - Generated by SBH CLI
Template: ${template.data.attributes.name}
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/healthz')
def health():
    return jsonify({
        'status': 'ok',
        'service': '${projectName}',
        'template': '${template.data.attributes.name}',
        'version': '1.0.0'
    })

@app.route('/')
def index():
    return jsonify({
        'message': 'Welcome to ${projectName}',
        'template': '${template.data.attributes.name}',
        'features': ${JSON.stringify(template.data.attributes.features)}
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
`;

      fs.writeFileSync(path.join(srcDir, 'app.py'), appPy);

      // Create requirements.txt
      const requirements = `Flask==2.3.0
Flask-CORS==4.0.0
Flask-JWT-Extended==4.5.0
SQLAlchemy==2.0.0
Alembic==1.12.0
psycopg2-binary==2.9.0
python-dotenv==1.0.0
`;

      fs.writeFileSync(path.join(projectPath, 'requirements.txt'), requirements);

      // Create .env.example
      const envExample = `# Database
DATABASE_URL=postgresql://user:password@localhost/${projectName}

# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# SBH Configuration
SBH_API_URL=http://localhost:5001
SBH_TENANT_ID=your-tenant-id
`;

      fs.writeFileSync(path.join(projectPath, '.env.example'), envExample);

      // Create tests directory
      const testsDir = path.join(projectPath, 'tests');
      fs.mkdirSync(testsDir, { recursive: true });

      const testInit = `"""
Tests for ${projectName}
"""

import pytest
from src.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    response = client.get('/healthz')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert data['service'] == '${projectName}'

def test_index_endpoint(client):
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Welcome to ${projectName}'
`;

      fs.writeFileSync(path.join(testsDir, 'test_app.py'), testInit);

      ui.stopSpinner(true, 'Project structure created');

      // Success message
      ui.success(`Project "${projectName}" initialized successfully!`);
      ui.info(`Template: ${template.data.attributes.name}`);
      ui.info(`Features: ${template.data.attributes.features.length} features included`);
      
      console.log('\nNext steps:');
      console.log(`  cd ${projectName}`);
      console.log('  sbh run --dev');
      console.log('  sbh test');
      console.log('  sbh deploy');

    } catch (error: any) {
      ui.stopSpinner(false, 'Failed to initialize project');
      ui.error(error.message || 'Unknown error occurred');
      this.exit(1);
    }
  }
}
