import * as vscode from 'vscode';

export class SBHMarketplaceProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'sbhMarketplace';
    private _view?: vscode.WebviewView;

    constructor(
        private readonly _extensionUri: vscode.Uri,
    ) { }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [
                this._extensionUri
            ]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(data => {
            switch (data.type) {
                case 'launchTemplate':
                    vscode.commands.executeCommand('sbh.marketplace.launch', data.template);
                    break;
            }
        });
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        return `
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>SBH Marketplace</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        padding: 10px;
                        margin: 0;
                        background: var(--vscode-editor-background);
                        color: var(--vscode-editor-foreground);
                    }
                    .template {
                        border: 1px solid var(--vscode-panel-border);
                        padding: 10px;
                        margin: 8px 0;
                        border-radius: 4px;
                        background: var(--vscode-editor-background);
                    }
                    .template h3 {
                        margin: 0 0 8px 0;
                        color: var(--vscode-editor-foreground);
                        font-size: 14px;
                    }
                    .template p {
                        margin: 4px 0;
                        color: var(--vscode-descriptionForeground);
                        font-size: 12px;
                    }
                    .badge {
                        background: var(--vscode-button-background);
                        color: var(--vscode-button-foreground);
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-size: 11px;
                        margin-right: 4px;
                        display: inline-block;
                    }
                    button {
                        background: var(--vscode-button-background);
                        color: var(--vscode-button-foreground);
                        border: none;
                        padding: 6px 12px;
                        border-radius: 3px;
                        cursor: pointer;
                        font-size: 12px;
                        margin-top: 8px;
                    }
                    button:hover {
                        background: var(--vscode-button-hoverBackground);
                    }
                    .header {
                        margin-bottom: 15px;
                        padding-bottom: 10px;
                        border-bottom: 1px solid var(--vscode-panel-border);
                    }
                    .header h2 {
                        margin: 0;
                        font-size: 16px;
                        color: var(--vscode-editor-foreground);
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>SBH Marketplace</h2>
                </div>
                <div id="templates">
                    <div class="template">
                        <h3>Flagship CRM & Ops</h3>
                        <p>Complete CRM and operations management system</p>
                        <span class="badge">Multi-tenant</span>
                        <span class="badge">AI</span>
                        <span class="badge">Automations</span>
                        <br>
                        <button onclick="launchTemplate('flagship-crm')">Launch</button>
                    </div>
                    <div class="template">
                        <h3>Learning Management System</h3>
                        <p>Complete LMS for online learning</p>
                        <span class="badge">Multi-tenant</span>
                        <span class="badge">Assessments</span>
                        <span class="badge">Certificates</span>
                        <br>
                        <button onclick="launchTemplate('learning-management-system')">Launch</button>
                    </div>
                    <div class="template">
                        <h3>Recruiting & ATS</h3>
                        <p>Applicant tracking system</p>
                        <span class="badge">Multi-tenant</span>
                        <span class="badge">Scheduling</span>
                        <span class="badge">RBAC</span>
                        <br>
                        <button onclick="launchTemplate('recruiting-ats')">Launch</button>
                    </div>
                    <div class="template">
                        <h3>Helpdesk & Support</h3>
                        <p>Customer support system</p>
                        <span class="badge">Multi-tenant</span>
                        <span class="badge">SLA</span>
                        <span class="badge">Portal</span>
                        <br>
                        <button onclick="launchTemplate('helpdesk-support')">Launch</button>
                    </div>
                    <div class="template">
                        <h3>Analytics Dashboard</h3>
                        <p>Comprehensive analytics platform</p>
                        <span class="badge">Multi-tenant</span>
                        <span class="badge">Real-time</span>
                        <span class="badge">Customizable</span>
                        <br>
                        <button onclick="launchTemplate('analytics-dashboard')">Launch</button>
                    </div>
                </div>
                <script>
                    const vscode = acquireVsCodeApi();
                    
                    function launchTemplate(template) {
                        vscode.postMessage({
                            type: 'launchTemplate',
                            template: template
                        });
                    }
                </script>
            </body>
            </html>
        `;
    }
}
