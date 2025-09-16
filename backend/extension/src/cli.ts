import * as vscode from 'vscode';
import { spawn } from 'child_process';

export class SBHCLI {
    private cliPath: string;

    constructor() {
        // Try to find the SBH CLI in the system PATH
        this.cliPath = 'sbh';
    }

    async init(options: { template: string; name: string; interactive: boolean }): Promise<void> {
        return this.runCommand(['init', '--template', options.template, '--name', options.name, '--no-interactive']);
    }

    async run(options: { dev?: boolean; migrate?: boolean; port?: string }): Promise<void> {
        const args = ['run'];
        if (options.dev) args.push('--dev');
        if (options.migrate) args.push('--migrate');
        if (options.port) args.push('--port', options.port);
        return this.runCommand(args);
    }

    async deploy(options: { platform: string; environment: string }): Promise<void> {
        return this.runCommand(['deploy', '--platform', options.platform, '--environment', options.environment]);
    }

    async smoke(options: { verbose: boolean; tests: string }): Promise<{ success: boolean; output: string }> {
        const args = ['smoke'];
        if (options.verbose) args.push('--verbose');
        if (options.tests !== 'all') args.push('--tests', options.tests);
        
        try {
            const output = await this.runCommandWithOutput(args);
            return { success: true, output };
        } catch (error: any) {
            return { success: false, output: error.message };
        }
    }

    async login(options: { email: string; password: string }): Promise<void> {
        return this.runCommand(['login', '--email', options.email, '--token', options.password]);
    }

    async marketplaceList(options: { category?: string; search?: string }): Promise<any> {
        const args = ['marketplace', 'list'];
        if (options.category) args.push('--category', options.category);
        if (options.search) args.push('--search', options.search);
        
        const output = await this.runCommandWithOutput(args);
        return JSON.parse(output);
    }

    async marketplaceLaunch(template: string, options: { name: string; plan: string }): Promise<void> {
        return this.runCommand([
            'marketplace', 'launch', template,
            '--name', options.name,
            '--plan', options.plan,
            '--no-interactive'
        ]);
    }

    private runCommand(args: string[]): Promise<void> {
        return new Promise((resolve, reject) => {
            const process = spawn(this.cliPath, args, {
                stdio: 'inherit',
                cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd()
            });

            process.on('close', (code) => {
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error(`Command failed with code ${code}`));
                }
            });

            process.on('error', (error) => {
                reject(new Error(`Failed to run command: ${error.message}`));
            });
        });
    }

    private runCommandWithOutput(args: string[]): Promise<string> {
        return new Promise((resolve, reject) => {
            const process = spawn(this.cliPath, args, {
                stdio: ['pipe', 'pipe', 'pipe'],
                cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd()
            });

            let output = '';
            let errorOutput = '';

            process.stdout?.on('data', (data) => {
                output += data.toString();
            });

            process.stderr?.on('data', (data) => {
                errorOutput += data.toString();
            });

            process.on('close', (code) => {
                if (code === 0) {
                    resolve(output);
                } else {
                    reject(new Error(errorOutput || `Command failed with code ${code}`));
                }
            });

            process.on('error', (error) => {
                reject(new Error(`Failed to run command: ${error.message}`));
            });
        });
    }
}
