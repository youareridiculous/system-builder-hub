import * as vscode from 'vscode';

export class SBHMetaBuilderProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'sbhMetaBuilder';
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
                case 'generateScaffold':
                    vscode.commands.executeCommand('sbh.metaBuilder.generate', data.idea);
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
                <title>SBH Meta-Builder</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        padding: 10px;
                        margin: 0;
                        background: var(--vscode-editor-background);
                        color: var(--vscode-editor-foreground);
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
                    .input-section {
                        margin-bottom: 15px;
                    }
                    label {
                        display: block;
                        margin-bottom: 5px;
                        font-size: 12px;
                        color: var(--vscode-editor-foreground);
                    }
                    textarea {
                        width: 100%;
                        height: 100px;
                        padding: 8px;
                        border: 1px solid var(--vscode-panel-border);
                        border-radius: 4px;
                        background: var(--vscode-input-background);
                        color: var(--vscode-input-foreground);
                        font-family: inherit;
                        font-size: 12px;
                        resize: vertical;
                    }
                    textarea:focus {
                        outline: 1px solid var(--vscode-focusBorder);
                    }
                    button {
                        background: var(--vscode-button-background);
                        color: var(--vscode-button-foreground);
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 12px;
                        width: 100%;
                    }
                    button:hover {
                        background: var(--vscode-button-hoverBackground);
                    }
                    button:disabled {
                        background: var(--vscode-button-secondaryBackground);
                        color: var(--vscode-button-secondaryForeground);
                        cursor: not-allowed;
                    }
                    .examples {
                        margin-top: 15px;
                        padding-top: 15px;
                        border-top: 1px solid var(--vscode-panel-border);
                    }
                    .examples h3 {
                        margin: 0 0 10px 0;
                        font-size: 14px;
                        color: var(--vscode-editor-foreground);
                    }
                    .example {
                        background: var(--vscode-editor-background);
                        border: 1px solid var(--vscode-panel-border);
                        padding: 8px;
                        margin: 5px 0;
                        border-radius: 4px;
                        font-size: 11px;
                        color: var(--vscode-descriptionForeground);
                        cursor: pointer;
                    }
                    .example:hover {
                        background: var(--vscode-list-hoverBackground);
                    }
                    .loading {
                        display: none;
                        text-align: center;
                        padding: 10px;
                        color: var(--vscode-descriptionForeground);
                        font-size: 12px;
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>SBH Meta-Builder</h2>
                </div>
                
                <div class="input-section">
                    <label for="idea">Describe your system idea in natural language:</label>
                    <textarea id="idea" placeholder="I want to build a customer support system with ticket management, knowledge base, and customer portal..."></textarea>
                </div>
                
                <button id="generateBtn" onclick="generateScaffold()">Generate Scaffold</button>
                
                <div id="loading" class="loading">
                    Generating scaffold... This may take a few moments.
                </div>
                
                <div class="examples">
                    <h3>Example Ideas:</h3>
                    <div class="example" onclick="useExample(this)">
                        "I need a project management system with task tracking, team collaboration, and time reporting"
                    </div>
                    <div class="example" onclick="useExample(this)">
                        "Build an e-commerce platform with product catalog, shopping cart, and payment processing"
                    </div>
                    <div class="example" onclick="useExample(this)">
                        "Create a learning management system with courses, assessments, and student progress tracking"
                    </div>
                    <div class="example" onclick="useExample(this)">
                        "Design a customer relationship management system with contact management, sales pipeline, and analytics"
                    </div>
                </div>
                
                <script>
                    const vscode = acquireVsCodeApi();
                    
                    function generateScaffold() {
                        const idea = document.getElementById('idea').value.trim();
                        if (!idea) {
                            alert('Please describe your system idea');
                            return;
                        }
                        
                        const btn = document.getElementById('generateBtn');
                        const loading = document.getElementById('loading');
                        
                        btn.disabled = true;
                        loading.style.display = 'block';
                        
                        vscode.postMessage({
                            type: 'generateScaffold',
                            idea: idea
                        });
                        
                        // Reset after a delay
                        setTimeout(() => {
                            btn.disabled = false;
                            loading.style.display = 'none';
                        }, 5000);
                    }
                    
                    function useExample(element) {
                        document.getElementById('idea').value = element.textContent.trim();
                    }
                    
                    // Handle Enter key in textarea
                    document.getElementById('idea').addEventListener('keydown', function(e) {
                        if (e.key === 'Enter' && e.ctrlKey) {
                            generateScaffold();
                        }
                    });
                </script>
            </body>
            </html>
        `;
    }
}
