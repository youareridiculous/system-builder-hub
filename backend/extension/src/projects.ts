import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export class SBHProjectsProvider implements vscode.TreeDataProvider<SBHProject> {
    private _onDidChangeTreeData: vscode.EventEmitter<SBHProject | undefined | null | undefined> = new vscode.EventEmitter<SBHProject | undefined | null | undefined>();
    readonly onDidChangeTreeData: vscode.Event<SBHProject | undefined | null | undefined> = this._onDidChangeTreeData.event;

    constructor() {}

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    getTreeItem(element: SBHProject): vscode.TreeItem {
        return element;
    }

    getChildren(element?: SBHProject): Thenable<SBHProject[]> {
        if (element) {
            return Promise.resolve([]);
        } else {
            return this.getSBHProjects();
        }
    }

    private async getSBHProjects(): Promise<SBHProject[]> {
        const projects: SBHProject[] = [];
        
        // Look for SBH projects in workspace folders
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            return projects;
        }

        for (const folder of workspaceFolders) {
            const sbhConfigPath = path.join(folder.uri.fsPath, '.sbh', 'project.json');
            
            if (fs.existsSync(sbhConfigPath)) {
                try {
                    const config = JSON.parse(fs.readFileSync(sbhConfigPath, 'utf8'));
                    projects.push(new SBHProject(
                        config.name,
                        config.template,
                        config.templateVersion,
                        vscode.TreeItemCollapsibleState.None,
                        folder.uri.fsPath
                    ));
                } catch (error) {
                    console.error('Error reading SBH project config:', error);
                }
            }
        }

        // If no SBH projects found, show a message
        if (projects.length === 0) {
            projects.push(new SBHProject(
                'No SBH projects found',
                '',
                '',
                vscode.TreeItemCollapsibleState.None,
                '',
                true
            ));
        }

        return projects;
    }
}

export class SBHProject extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly template: string,
        public readonly version: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly projectPath: string,
        public readonly isPlaceholder: boolean = false
    ) {
        super(label, collapsibleState);

        if (!isPlaceholder) {
            this.tooltip = `${this.label} (${this.template} v${this.version})`;
            this.description = `${this.template} v${this.version}`;
            this.iconPath = new vscode.ThemeIcon('folder');
            
            this.contextValue = 'sbhProject';
            
            // Add commands
            this.command = {
                command: 'vscode.openFolder',
                title: 'Open Project',
                arguments: [vscode.Uri.file(this.projectPath)]
            };
        } else {
            this.iconPath = new vscode.ThemeIcon('info');
            this.contextValue = 'placeholder';
        }
    }
}
