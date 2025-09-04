import { Command } from '@oclif/core';
import { UI } from '../utils/ui';
import * as fs from 'fs-extra';
import * as path from 'path';
import { spawn, execSync } from 'child_process';

export default class Run extends Command {
  static description = 'Run scaffold locally (dev server + migrations)';

  static examples = [
    '$ sbh run',
    '$ sbh run --dev',
    '$ sbh run --migrate',
    '$ sbh run --port 8000',
  ];

  static flags = {
    dev: {
      char: 'd',
      description: 'Run in development mode',
      default: false,
    },
    migrate: {
      char: 'm',
      description: 'Run database migrations',
      default: false,
    },
    port: {
      char: 'p',
      description: 'Port to run on',
      default: '5000',
    },
    host: {
      char: 'h',
      description: 'Host to bind to',
      default: 'localhost',
    },
  };

  async run() {
    const { flags } = await this.parse(Run);
    const ui = new UI();

    try {
      // Check if we're in a project directory
      const projectConfigPath = path.join(process.cwd(), '.sbh', 'project.json');
      if (!fs.existsSync(projectConfigPath)) {
        ui.error('Not in an SBH project directory. Run "sbh init" first.');
        return;
      }

      const projectConfig = fs.readJsonSync(projectConfigPath);
      ui.info(`Running project: ${projectConfig.name}`);
      ui.info(`Template: ${projectConfig.template}`);

      // Check if requirements.txt exists
      const requirementsPath = path.join(process.cwd(), 'requirements.txt');
      if (!fs.existsSync(requirementsPath)) {
        ui.error('requirements.txt not found. Please ensure this is a Python project.');
        return;
      }

      // Install dependencies if needed
      ui.startSpinner('Checking dependencies...');
      try {
        execSync('python -c "import flask"', { stdio: 'ignore' });
        ui.stopSpinner(true, 'Dependencies already installed');
      } catch {
        ui.stopSpinner(false, 'Installing dependencies...');
        ui.startSpinner('Installing Python dependencies...');
        try {
          execSync('pip install -r requirements.txt', { stdio: 'pipe' });
          ui.stopSpinner(true, 'Dependencies installed');
        } catch (error: any) {
          ui.stopSpinner(false, 'Failed to install dependencies');
          ui.error(error.message);
          return;
        }
      }

      // Run migrations if requested
      if (flags.migrate) {
        ui.startSpinner('Running database migrations...');
        try {
          // Check if alembic.ini exists
          const alembicPath = path.join(process.cwd(), 'alembic.ini');
          if (fs.existsSync(alembicPath)) {
            execSync('alembic upgrade head', { stdio: 'pipe' });
            ui.stopSpinner(true, 'Migrations completed');
          } else {
            ui.stopSpinner(false, 'No migrations found');
            ui.warning('No alembic.ini found. Skipping migrations.');
          }
        } catch (error: any) {
          ui.stopSpinner(false, 'Migration failed');
          ui.error(error.message);
          return;
        }
      }

      // Set environment variables
      const env = {
        ...process.env,
        FLASK_ENV: flags.dev ? 'development' : 'production',
        FLASK_DEBUG: flags.dev ? '1' : '0',
        PORT: flags.port,
        HOST: flags.host,
      };

      // Start the application
      ui.startSpinner(`Starting server on ${flags.host}:${flags.port}...`);
      
      const appPath = path.join(process.cwd(), 'src', 'app.py');
      if (!fs.existsSync(appPath)) {
        ui.stopSpinner(false, 'app.py not found');
        ui.error('src/app.py not found. Please ensure this is a valid SBH project.');
        return;
      }

      ui.stopSpinner(true, 'Server started');
      ui.success(`🚀 Server running at http://${flags.host}:${flags.port}`);
      ui.info('Press Ctrl+C to stop');

      // Start the Python process
      const pythonProcess = spawn('python', [appPath], {
        stdio: 'inherit',
        env,
        cwd: process.cwd(),
      });

      // Handle process exit
      pythonProcess.on('close', (code) => {
        if (code === 0) {
          ui.success('Server stopped gracefully');
        } else {
          ui.error(`Server stopped with code ${code}`);
        }
      });

      // Handle process errors
      pythonProcess.on('error', (error) => {
        ui.error(`Failed to start server: ${error.message}`);
      });

      // Handle SIGINT (Ctrl+C)
      process.on('SIGINT', () => {
        ui.info('\nStopping server...');
        pythonProcess.kill('SIGINT');
      });

    } catch (error: any) {
      ui.error(error.message || 'Failed to run project');
      this.exit(1);
    }
  }
}
