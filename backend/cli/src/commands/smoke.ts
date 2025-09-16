import { Command } from '@oclif/core';
import { UI } from '../utils/ui';
import { SBHAPI } from '../utils/api';
import * as fs from 'fs-extra';
import * as path from 'path';
import { spawn } from 'child_process';

export default class Smoke extends Command {
  static description = 'Run smoke tests (seed_verify + smoke_e2e)';

  static examples = [
    '$ sbh smoke',
    '$ sbh smoke --verbose',
    '$ sbh smoke --tests seed_verify',
  ];

  static flags = {
    verbose: {
      char: 'v',
      description: 'Verbose output',
      default: false,
    },
    tests: {
      char: 't',
      description: 'Specific tests to run (comma-separated)',
      default: 'all',
    },
    timeout: {
      char: 'o',
      description: 'Test timeout in seconds',
      default: '300',
    },
  };

  async run() {
    const { flags } = await this.parse(Smoke);
    const ui = new UI();

    try {
      // Check if we're in a project directory
      const projectConfigPath = path.join(process.cwd(), '.sbh', 'project.json');
      if (!fs.existsSync(projectConfigPath)) {
        ui.error('Not in an SBH project directory. Run "sbh init" first.');
        return;
      }

      const projectConfig = fs.readJsonSync(projectConfigPath);
      ui.info(`Running smoke tests for: ${projectConfig.name}`);
      ui.info(`Template: ${projectConfig.template}`);

      const testsToRun = flags.tests === 'all' 
        ? ['seed_verify', 'smoke_e2e', 'unit_tests']
        : flags.tests.split(',');

      let allTestsPassed = true;
      const results: any[] = [];

      // Run unit tests
      if (testsToRun.includes('unit_tests')) {
        const unitTestResult = await this.runUnitTests(ui, flags.verbose);
        results.push(unitTestResult);
        if (!unitTestResult.passed) allTestsPassed = false;
      }

      // Run seed verification
      if (testsToRun.includes('seed_verify')) {
        const seedResult = await this.runSeedVerification(ui, projectConfig, flags.verbose);
        results.push(seedResult);
        if (!seedResult.passed) allTestsPassed = false;
      }

      // Run smoke E2E tests
      if (testsToRun.includes('smoke_e2e')) {
        const e2eResult = await this.runSmokeE2E(ui, projectConfig, flags.verbose);
        results.push(e2eResult);
        if (!e2eResult.passed) allTestsPassed = false;
      }

      // Display results
      this.displayResults(ui, results);

      if (allTestsPassed) {
        ui.success('All smoke tests passed! 🎉');
      } else {
        ui.error('Some smoke tests failed');
        this.exit(1);
      }

    } catch (error: any) {
      ui.error(error.message || 'Smoke tests failed');
      this.exit(1);
    }
  }

  private async runUnitTests(ui: UI, verbose: boolean): Promise<any> {
    ui.startSpinner('Running unit tests...');

    return new Promise((resolve) => {
      const testsDir = path.join(process.cwd(), 'tests');
      if (!fs.existsSync(testsDir)) {
        ui.stopSpinner(false, 'No tests directory found');
        resolve({
          name: 'Unit Tests',
          passed: false,
          error: 'No tests directory found',
          duration: 0,
        });
        return;
      }

      const startTime = Date.now();
      const pytest = spawn('python', ['-m', 'pytest', 'tests/', '-v'], {
        stdio: verbose ? 'inherit' : 'pipe',
        cwd: process.cwd(),
      });

      let output = '';
      let errorOutput = '';

      pytest.stdout?.on('data', (data) => {
        output += data.toString();
      });

      pytest.stderr?.on('data', (data) => {
        errorOutput += data.toString();
      });

      pytest.on('close', (code) => {
        const duration = (Date.now() - startTime) / 1000;
        
        if (code === 0) {
          ui.stopSpinner(true, 'Unit tests passed');
          resolve({
            name: 'Unit Tests',
            passed: true,
            output,
            duration,
          });
        } else {
          ui.stopSpinner(false, 'Unit tests failed');
          resolve({
            name: 'Unit Tests',
            passed: false,
            error: errorOutput || 'Tests failed',
            output,
            duration,
          });
        }
      });

      pytest.on('error', (error) => {
        const duration = (Date.now() - startTime) / 1000;
        ui.stopSpinner(false, 'Failed to run unit tests');
        resolve({
          name: 'Unit Tests',
          passed: false,
          error: error.message,
          duration,
        });
      });
    });
  }

  private async runSeedVerification(ui: UI, projectConfig: any, verbose: boolean): Promise<any> {
    ui.startSpinner('Running seed verification...');

    return new Promise((resolve) => {
      const startTime = Date.now();

      // Check if seed data exists and is valid
      const seedScripts = [
        path.join(process.cwd(), 'scripts', 'seed_verify.py'),
        path.join(process.cwd(), 'src', 'seeds', 'verify.py'),
        path.join(process.cwd(), 'tests', 'test_seeds.py'),
      ];

      let seedScript = null;
      for (const script of seedScripts) {
        if (fs.existsSync(script)) {
          seedScript = script;
          break;
        }
      }

      if (!seedScript) {
        ui.stopSpinner(false, 'No seed verification script found');
        resolve({
          name: 'Seed Verification',
          passed: false,
          error: 'No seed verification script found',
          duration: 0,
        });
        return;
      }

      const python = spawn('python', [seedScript], {
        stdio: verbose ? 'inherit' : 'pipe',
        cwd: process.cwd(),
      });

      let output = '';
      let errorOutput = '';

      python.stdout?.on('data', (data) => {
        output += data.toString();
      });

      python.stderr?.on('data', (data) => {
        errorOutput += data.toString();
      });

      python.on('close', (code) => {
        const duration = (Date.now() - startTime) / 1000;
        
        if (code === 0) {
          ui.stopSpinner(true, 'Seed verification passed');
          resolve({
            name: 'Seed Verification',
            passed: true,
            output,
            duration,
          });
        } else {
          ui.stopSpinner(false, 'Seed verification failed');
          resolve({
            name: 'Seed Verification',
            passed: false,
            error: errorOutput || 'Seed verification failed',
            output,
            duration,
          });
        }
      });

      python.on('error', (error) => {
        const duration = (Date.now() - startTime) / 1000;
        ui.stopSpinner(false, 'Failed to run seed verification');
        resolve({
          name: 'Seed Verification',
          passed: false,
          error: error.message,
          duration,
        });
      });
    });
  }

  private async runSmokeE2E(ui: UI, projectConfig: any, verbose: boolean): Promise<any> {
    ui.startSpinner('Running smoke E2E tests...');

    return new Promise((resolve) => {
      const startTime = Date.now();

      // Check if smoke test script exists
      const smokeScripts = [
        path.join(process.cwd(), 'tests', 'smoke', 'test_smoke.py'),
        path.join(process.cwd(), 'scripts', 'smoke_prod.py'),
        path.join(process.cwd(), 'tests', 'test_e2e_flow.py'),
      ];

      let smokeScript = null;
      for (const script of smokeScripts) {
        if (fs.existsSync(script)) {
          smokeScript = script;
          break;
        }
      }

      if (!smokeScript) {
        ui.stopSpinner(false, 'No smoke E2E test script found');
        resolve({
          name: 'Smoke E2E',
          passed: false,
          error: 'No smoke E2E test script found',
          duration: 0,
        });
        return;
      }

      const python = spawn('python', [smokeScript], {
        stdio: verbose ? 'inherit' : 'pipe',
        cwd: process.cwd(),
        env: {
          ...process.env,
          SMOKE_TEST: 'true',
          VERBOSE: verbose ? 'true' : 'false',
        },
      });

      let output = '';
      let errorOutput = '';

      python.stdout?.on('data', (data) => {
        output += data.toString();
      });

      python.stderr?.on('data', (data) => {
        errorOutput += data.toString();
      });

      python.on('close', (code) => {
        const duration = (Date.now() - startTime) / 1000;
        
        if (code === 0) {
          ui.stopSpinner(true, 'Smoke E2E tests passed');
          resolve({
            name: 'Smoke E2E',
            passed: true,
            output,
            duration,
          });
        } else {
          ui.stopSpinner(false, 'Smoke E2E tests failed');
          resolve({
            name: 'Smoke E2E',
            passed: false,
            error: errorOutput || 'Smoke E2E tests failed',
            output,
            duration,
          });
        }
      });

      python.on('error', (error) => {
        const duration = (Date.now() - startTime) / 1000;
        ui.stopSpinner(false, 'Failed to run smoke E2E tests');
        resolve({
          name: 'Smoke E2E',
          passed: false,
          error: error.message,
          duration,
        });
      });
    });
  }

  private displayResults(ui: UI, results: any[]) {
    console.log('\n📊 Test Results:');
    console.log('='.repeat(50));

    for (const result of results) {
      const status = result.passed ? '✅ PASS' : '❌ FAIL';
      const duration = `${result.duration.toFixed(2)}s`;
      
      console.log(`${status} ${result.name} (${duration})`);
      
      if (!result.passed && result.error) {
        console.log(`   Error: ${result.error}`);
      }
      
      if (result.output) {
        console.log(`   Output: ${result.output.substring(0, 200)}...`);
      }
    }

    console.log('='.repeat(50));
    
    const passed = results.filter(r => r.passed).length;
    const total = results.length;
    
    console.log(`Results: ${passed}/${total} tests passed`);
  }
}
