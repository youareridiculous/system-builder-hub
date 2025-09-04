import * as vscode from 'vscode';
import { SBHMarketplaceProvider } from './marketplace';
import { SBHMetaBuilderProvider } from './metaBuilder';
import { SBHProjectsProvider } from './projects';
import { SBHCLI } from './cli';

export function activate(context: vscode.ExtensionContext) {
    console.log('SBH Extension is now active!');

    // Initialize CLI wrapper
    const cli = new SBHCLI();

    // Register marketplace view
    const marketplaceProvider = new SBHMarketplaceProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('sbhMarketplace', marketplaceProvider)
    );

    // Register meta-builder view
    const metaBuilderProvider = new SBHMetaBuilderProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('sbhMetaBuilder', metaBuilderProvider)
    );

    // Register projects view
    const projectsProvider = new SBHProjectsProvider();
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('sbhProjects', projectsProvider)
    );

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('sbh.scaffoldProject', async () => {
            await scaffoldProject(cli);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('sbh.runSmokeTests', async () => {
            await runSmokeTests(cli);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('sbh.deploy', async () => {
            await deploy(cli);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('sbh.marketplace', async () => {
            await openMarketplace();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('sbh.metaBuilder', async () => {
            await openMetaBuilder();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('sbh.login', async () => {
            await login(cli);
        })
    );

    // Register hover provider for scaffold plan context
    context.subscriptions.push(
        vscode.languages.registerHoverProvider('python', new SBHHoverProvider())
    );

    context.subscriptions.push(
        vscode.languages.registerHoverProvider('typescript', new SBHHoverProvider())
    );

    context.subscriptions.push(
        vscode.languages.registerHoverProvider('javascript', new SBHHoverProvider())
    );
}

async function scaffoldProject(cli: SBHCLI) {
    try {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('No workspace folder found');
            return;
        }

        const template = await vscode.window.showQuickPick([
            'flagship-crm',
            'learning-management-system',
            'recruiting-ats',
            'helpdesk-support',
            'analytics-dashboard'
        ], {
            placeHolder: 'Select a template'
        });

        if (!template) {
            return;
        }

        const projectName = await vscode.window.showInputBox({
            prompt: 'Enter project name',
            value: 'my-sbh-project'
        });

        if (!projectName) {
            return;
        }

        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Scaffolding project...',
            cancellable: false
        }, async (progress) => {
            try {
                await cli.init({
                    template,
                    name: projectName,
                    interactive: false
                });
                
                vscode.window.showInformationMessage(`Project ${projectName} scaffolded successfully!`);
                
                // Open the new project
                const uri = vscode.Uri.file(workspaceFolder.uri.fsPath + '/' + projectName);
                await vscode.commands.executeCommand('vscode.openFolder', uri);
            } catch (error: any) {
                vscode.window.showErrorMessage(`Failed to scaffold project: ${error.message}`);
            }
        });

    } catch (error: any) {
        vscode.window.showErrorMessage(`Error: ${error.message}`);
    }
}

async function runSmokeTests(cli: SBHCLI) {
    try {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('No workspace folder found');
            return;
        }

        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Running smoke tests...',
            cancellable: false
        }, async (progress) => {
            try {
                const result = await cli.smoke({
                    verbose: true,
                    tests: 'all'
                });
                
                if (result.success) {
                    vscode.window.showInformationMessage('All smoke tests passed! 🎉');
                } else {
                    vscode.window.showErrorMessage('Some smoke tests failed');
                }
            } catch (error: any) {
                vscode.window.showErrorMessage(`Failed to run smoke tests: ${error.message}`);
            }
        });

    } catch (error: any) {
        vscode.window.showErrorMessage(`Error: ${error.message}`);
    }
}

async function deploy(cli: SBHCLI) {
    try {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('No workspace folder found');
            return;
        }

        const platform = await vscode.window.showQuickPick([
            'export',
            'aws',
            'render'
        ], {
            placeHolder: 'Select deployment platform'
        });

        if (!platform) {
            return;
        }

        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Deploying...',
            cancellable: false
        }, async (progress) => {
            try {
                await cli.deploy({
                    platform,
                    environment: 'production'
                });
                
                vscode.window.showInformationMessage('Deployment completed successfully!');
            } catch (error: any) {
                vscode.window.showErrorMessage(`Failed to deploy: ${error.message}`);
            }
        });

    } catch (error: any) {
        vscode.window.showErrorMessage(`Error: ${error.message}`);
    }
}

async function openMarketplace() {
    const panel = vscode.window.createWebviewPanel(
        'sbhMarketplace',
        'SBH Marketplace',
        vscode.ViewColumn.One,
        {
            enableScripts: true,
            retainContextWhenHidden: true
        }
    );

    panel.webview.html = getMarketplaceHTML();
}

async function openMetaBuilder() {
    const panel = vscode.window.createWebviewPanel(
        'sbhMetaBuilder',
        'SBH Meta-Builder',
        vscode.ViewColumn.One,
        {
            enableScripts: true,
            retainContextWhenHidden: true
        }
    );

    panel.webview.html = getMetaBuilderHTML();
}

async function login(cli: SBHCLI) {
    try {
        const email = await vscode.window.showInputBox({
            prompt: 'Enter your email',
            placeHolder: 'user@example.com'
        });

        if (!email) {
            return;
        }

        const password = await vscode.window.showInputBox({
            prompt: 'Enter your password',
            password: true
        });

        if (!password) {
            return;
        }

        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Logging in...',
            cancellable: false
        }, async (progress) => {
            try {
                await cli.login({
                    email,
                    password
                });
                
                vscode.window.showInformationMessage('Successfully logged in to SBH!');
            } catch (error: any) {
                vscode.window.showErrorMessage(`Login failed: ${error.message}`);
            }
        });

    } catch (error: any) {
        vscode.window.showErrorMessage(`Error: ${error.message}`);
    }
}

function getMarketplaceHTML() {
    return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>SBH Marketplace</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; }
                .template { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .template h3 { margin: 0 0 10px 0; color: #333; }
                .template p { margin: 5px 0; color: #666; }
                .badge { background: #007acc; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; margin-right: 5px; }
                button { background: #007acc; color: white; border: none; padding: 8px 16px; border-radius: 3px; cursor: pointer; }
                button:hover { background: #005a9e; }
            </style>
        </head>
        <body>
            <h1>SBH Marketplace</h1>
            <div id="templates">
                <div class="template">
                    <h3>Flagship CRM & Ops</h3>
                    <p>Complete CRM and operations management system</p>
                    <span class="badge">Multi-tenant</span>
                    <span class="badge">AI</span>
                    <span class="badge">Automations</span>
                    <br><br>
                    <button onclick="launchTemplate('flagship-crm')">Launch Template</button>
                </div>
                <div class="template">
                    <h3>Learning Management System</h3>
                    <p>Complete LMS for online learning</p>
                    <span class="badge">Multi-tenant</span>
                    <span class="badge">Assessments</span>
                    <span class="badge">Certificates</span>
                    <br><br>
                    <button onclick="launchTemplate('learning-management-system')">Launch Template</button>
                </div>
            </div>
            <script>
                function launchTemplate(template) {
                    vscode.postMessage({ command: 'launchTemplate', template });
                }
            </script>
        </body>
        </html>
    `;
}

function getMetaBuilderHTML() {
    return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>SBH Meta-Builder</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; }
                textarea { width: 100%; height: 150px; margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }
                button { background: #007acc; color: white; border: none; padding: 10px 20px; border-radius: 3px; cursor: pointer; }
                button:hover { background: #005a9e; }
            </style>
        </head>
        <body>
            <h1>SBH Meta-Builder</h1>
            <p>Describe your system idea in natural language:</p>
            <textarea id="idea" placeholder="I want to build a customer support system with ticket management, knowledge base, and customer portal..."></textarea>
            <br>
            <button onclick="generateScaffold()">Generate Scaffold</button>
            <div id="result"></div>
            <script>
                function generateScaffold() {
                    const idea = document.getElementById('idea').value;
                    if (!idea) {
                        alert('Please describe your system idea');
                        return;
                    }
                    vscode.postMessage({ command: 'generateScaffold', idea });
                }
            </script>
        </body>
        </html>
    `;
}

class SBHHoverProvider implements vscode.HoverProvider {
    provideHover(document: vscode.TextDocument, position: vscode.Position, token: vscode.CancellationToken): vscode.ProviderResult<vscode.Hover> {
        const line = document.lineAt(position.line);
        const text = line.text;

        // Check for SBH-related patterns
        if (text.includes('@auth.require') || text.includes('useSBH') || text.includes('sbh.sdk')) {
            return new vscode.Hover([
                '**SBH Scaffold Context**',
                'This code was generated by SBH Meta-Builder',
                'Template: Flagship CRM & Ops',
                'Features: Multi-tenant, RBAC, AI Assist'
            ]);
        }

        return null;
    }
}

export function deactivate() {}
