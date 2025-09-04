import { Command } from '@oclif/core';
import { UI } from '../utils/ui';
import * as fs from 'fs-extra';
import * as path from 'path';
import { execSync } from 'child_process';
import * as archiver from 'archiver';

export default class Deploy extends Command {
  static description = 'Deploy scaffold to AWS EB or export bundle';

  static examples = [
    '$ sbh deploy',
    '$ sbh deploy --platform aws',
    '$ sbh deploy --platform render',
    '$ sbh deploy --export',
  ];

  static flags = {
    platform: {
      char: 'p',
      description: 'Deployment platform (aws, render, export)',
      default: 'export',
    },
    environment: {
      char: 'e',
      description: 'Environment name',
      default: 'production',
    },
    export: {
      char: 'x',
      description: 'Export deployment bundle',
      default: false,
    },
    bundle: {
      char: 'b',
      description: 'Bundle name',
      default: 'sbh-deploy',
    },
  };

  async run() {
    const { flags } = await this.parse(Deploy);
    const ui = new UI();

    try {
      // Check if we're in a project directory
      const projectConfigPath = path.join(process.cwd(), '.sbh', 'project.json');
      if (!fs.existsSync(projectConfigPath)) {
        ui.error('Not in an SBH project directory. Run "sbh init" first.');
        return;
      }

      const projectConfig = fs.readJsonSync(projectConfigPath);
      ui.info(`Deploying project: ${projectConfig.name}`);
      ui.info(`Template: ${projectConfig.template}`);

      if (flags.platform === 'export' || flags.export) {
        await this.exportBundle(ui, projectConfig, flags.bundle);
      } else if (flags.platform === 'aws') {
        await this.deployToAWS(ui, projectConfig, flags.environment);
      } else if (flags.platform === 'render') {
        await this.deployToRender(ui, projectConfig, flags.environment);
      } else {
        ui.error(`Unsupported platform: ${flags.platform}`);
        ui.info('Supported platforms: aws, render, export');
        return;
      }

    } catch (error: any) {
      ui.error(error.message || 'Deployment failed');
      this.exit(1);
    }
  }

  private async exportBundle(ui: UI, projectConfig: any, bundleName: string) {
    ui.startSpinner('Creating deployment bundle...');

    const bundlePath = path.join(process.cwd(), `${bundleName}.zip`);
    const output = fs.createWriteStream(bundlePath);
    const archive = archiver('zip', { zlib: { level: 9 } });

    output.on('close', () => {
      ui.stopSpinner(true, 'Bundle created successfully');
      ui.success(`Deployment bundle: ${bundlePath}`);
      ui.info(`Size: ${(archive.pointer() / 1024 / 1024).toFixed(2)} MB`);
    });

    archive.on('error', (err) => {
      ui.stopSpinner(false, 'Failed to create bundle');
      ui.error(err.message);
    });

    archive.pipe(output);

    // Add project files
    const filesToInclude = [
      'src/**/*',
      'requirements.txt',
      'README.md',
      '.env.example',
      'alembic.ini',
      'migrations/**/*',
      'tests/**/*',
    ];

    const filesToExclude = [
      '.git/**/*',
      '__pycache__/**/*',
      '*.pyc',
      '.env',
      'node_modules/**/*',
      '.DS_Store',
    ];

    // Add files
    for (const pattern of filesToInclude) {
      const files = fs.readdirSync(process.cwd(), { recursive: true });
      for (const file of files) {
        if (this.matchesPattern(file.toString(), pattern)) {
          const filePath = path.join(process.cwd(), file.toString());
          if (fs.statSync(filePath).isFile()) {
            archive.file(filePath, { name: file.toString() });
          }
        }
      }
    }

    // Create deployment manifest
    const manifest = {
      project: projectConfig.name,
      template: projectConfig.template,
      templateVersion: projectConfig.templateVersion,
      sbhVersion: projectConfig.sbhVersion,
      deployedAt: new Date().toISOString(),
      features: projectConfig.features,
      deployment: {
        platform: 'export',
        bundle: bundleName,
        environment: 'production',
      },
    };

    archive.append(JSON.stringify(manifest, null, 2), { name: 'EXPORT_MANIFEST.json' });

    // Create deployment docs
    const deploymentDocs = `# Deployment Guide

## Project Information
- **Name**: ${projectConfig.name}
- **Template**: ${projectConfig.template}
- **Version**: ${projectConfig.templateVersion}
- **SBH Version**: ${projectConfig.sbhVersion}

## Features
${projectConfig.features.map((f: string) => `- ${f}`).join('\n')}

## Deployment Options

### AWS Elastic Beanstalk
1. Upload this bundle to AWS EB
2. Configure environment variables
3. Deploy

### Render
1. Create new Web Service
2. Upload this bundle
3. Set build command: \`pip install -r requirements.txt\`
4. Set start command: \`python src/app.py\`

### Manual Deployment
1. Extract this bundle
2. Install dependencies: \`pip install -r requirements.txt\`
3. Set up environment variables
4. Run migrations: \`alembic upgrade head\`
5. Start server: \`python src/app.py\`

## Environment Variables
Copy .env.example to .env and configure:
- DATABASE_URL
- SECRET_KEY
- FLASK_ENV
- SBH_API_URL
- SBH_TENANT_ID

Generated with SBH CLI v1.0.0
`;

    archive.append(deploymentDocs, { name: 'DEPLOYMENT_GUIDE.md' });

    await archive.finalize();
  }

  private async deployToAWS(ui: UI, projectConfig: any, environment: string) {
    ui.startSpinner('Deploying to AWS Elastic Beanstalk...');

    // Check if EB CLI is installed
    try {
      execSync('eb --version', { stdio: 'ignore' });
    } catch {
      ui.stopSpinner(false, 'EB CLI not found');
      ui.error('Please install AWS EB CLI: pip install awsebcli');
      ui.info('Or use --export to create a deployment bundle');
      return;
    }

    // Check if .elasticbeanstalk directory exists
    const ebDir = path.join(process.cwd(), '.elasticbeanstalk');
    if (!fs.existsSync(ebDir)) {
      ui.stopSpinner(false, 'EB configuration not found');
      ui.info('Initializing EB configuration...');
      
      try {
        execSync('eb init', { stdio: 'pipe' });
      } catch (error: any) {
        ui.error('Failed to initialize EB: ' + error.message);
        return;
      }
    }

    // Deploy
    try {
      execSync(`eb deploy ${environment}`, { stdio: 'inherit' });
      ui.stopSpinner(true, 'Deployed to AWS EB successfully');
      ui.success(`Application deployed to environment: ${environment}`);
    } catch (error: any) {
      ui.stopSpinner(false, 'AWS EB deployment failed');
      ui.error(error.message);
    }
  }

  private async deployToRender(ui: UI, projectConfig: any, environment: string) {
    ui.startSpinner('Preparing for Render deployment...');

    // Create render.yaml if it doesn't exist
    const renderYamlPath = path.join(process.cwd(), 'render.yaml');
    if (!fs.existsSync(renderYamlPath)) {
      const renderConfig = `services:
  - type: web
    name: ${projectConfig.name}
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python src/app.py
    envVars:
      - key: FLASK_ENV
        value: production
      - key: PYTHON_VERSION
        value: 3.9.0
`;

      fs.writeFileSync(renderYamlPath, renderConfig);
      ui.info('Created render.yaml configuration');
    }

    ui.stopSpinner(true, 'Render configuration ready');
    ui.success('Render configuration created');
    ui.info('Deploy to Render:');
    ui.info('1. Push to GitHub');
    ui.info('2. Connect repository to Render');
    ui.info('3. Deploy automatically');
  }

  private matchesPattern(file: string, pattern: string): boolean {
    // Simple pattern matching - can be enhanced with glob
    if (pattern.includes('**')) {
      const regex = pattern.replace(/\*\*/g, '.*').replace(/\*/g, '[^/]*');
      return new RegExp(regex).test(file);
    }
    return file.includes(pattern.replace('*', ''));
  }
}
