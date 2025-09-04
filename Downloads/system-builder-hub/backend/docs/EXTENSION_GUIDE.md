# SBH VSCode/Cursor Extension Guide

The SBH Extension provides seamless integration between VSCode/Cursor and the SBH platform, enabling scaffold development, template management, and deployment directly from your IDE.

## Installation

### From VSIX
1. Download the SBH extension VSIX file
2. In VSCode/Cursor, go to Extensions (Ctrl+Shift+X)
3. Click the "..." menu and select "Install from VSIX..."
4. Select the downloaded file

### From Source
```bash
# Clone the extension
git clone https://github.com/sbh/sbh-extension

# Install dependencies
cd sbh-extension
npm install

# Build the extension
npm run compile

# Package for distribution
npm run package
```

## Features

### SBH Sidebar

The extension adds an "SBH" section to the activity bar with three main views:

#### 1. Marketplace
- Browse available templates
- View template details and features
- Launch templates directly from the sidebar
- Filter by category and tags

#### 2. Meta-Builder
- Natural language scaffold generation
- Interactive prompt composer
- Real-time scaffold preview
- Template suggestions and examples

#### 3. Projects
- List SBH projects in workspace
- Quick access to project details
- Open project folders
- View project status

### Commands

Access SBH commands through the Command Palette (Ctrl+Shift+P):

#### Project Commands
- `SBH: Scaffold Project` - Initialize new SBH project
- `SBH: Run Smoke Tests` - Execute project tests
- `SBH: Deploy` - Deploy project to cloud

#### Platform Commands
- `SBH: Open Marketplace` - Open marketplace in new tab
- `SBH: Open Meta-Builder` - Open meta-builder interface
- `SBH: Login` - Authenticate with SBH

### Context Menu Integration

Right-click in the Explorer to access SBH commands:
- Scaffold Project
- Run Smoke Tests
- Deploy

### Hover Information

Hover over SBH-generated code to see:
- Scaffold context and template information
- Generated features and capabilities
- RBAC and security information

## Configuration

### Extension Settings

Configure the extension in VSCode/Cursor settings:

```json
{
  "sbh.apiToken": "your-api-token",
  "sbh.apiUrl": "http://localhost:5001",
  "sbh.tenantId": "your-tenant-id",
  "sbh.defaultTemplate": "flagship-crm"
}
```

### Workspace Settings

Project-specific settings in `.vscode/settings.json`:

```json
{
  "sbh.project.template": "flagship-crm",
  "sbh.project.autoTest": true,
  "sbh.project.autoDeploy": false
}
```

## Usage Examples

### Creating a New Project

1. Open Command Palette (Ctrl+Shift+P)
2. Type "SBH: Scaffold Project"
3. Select template from dropdown
4. Enter project name
5. Project is created and opened

### Running Tests

1. Open Command Palette (Ctrl+Shift+P)
2. Type "SBH: Run Smoke Tests"
3. View test results in Output panel
4. Check status in status bar

### Deploying

1. Open Command Palette (Ctrl+Shift+P)
2. Type "SBH: Deploy"
3. Select deployment platform
4. Monitor deployment progress
5. View deployment URL

### Using Marketplace

1. Click SBH icon in activity bar
2. Select "Marketplace" view
3. Browse available templates
4. Click "Launch" on desired template
5. Configure launch options
6. Template is deployed to your tenant

### Using Meta-Builder

1. Click SBH icon in activity bar
2. Select "Meta-Builder" view
3. Describe your system idea
4. Click "Generate Scaffold"
5. Review generated plan
6. Build and deploy scaffold

## Keyboard Shortcuts

Default keyboard shortcuts:

```json
{
  "key": "ctrl+shift+s",
  "command": "sbh.scaffoldProject",
  "when": "workspaceFolderCount > 0"
},
{
  "key": "ctrl+shift+t",
  "command": "sbh.runSmokeTests",
  "when": "workspaceFolderCount > 0"
},
{
  "key": "ctrl+shift+d",
  "command": "sbh.deploy",
  "when": "workspaceFolderCount > 0"
}
```

## Integration with CLI

The extension uses the SBH CLI under the hood:

- All commands execute through the CLI
- CLI output is displayed in Output panel
- CLI configuration is shared
- CLI authentication is used

## Troubleshooting

### Extension Not Loading

1. Check VSCode/Cursor console for errors
2. Reload the window (Ctrl+Shift+P > "Developer: Reload Window")
3. Check extension is enabled in Extensions panel

### Authentication Issues

1. Run "SBH: Login" command
2. Check API token in settings
3. Verify API URL is correct
4. Check network connectivity

### CLI Not Found

1. Install SBH CLI: `npm install -g @sbh/cli`
2. Ensure CLI is in PATH
3. Restart VSCode/Cursor

### Project Detection Issues

1. Ensure `.sbh/project.json` exists
2. Check project configuration
3. Reload workspace

## Development

### Building from Source

```bash
# Clone repository
git clone https://github.com/sbh/sbh-extension

# Install dependencies
npm install

# Build extension
npm run compile

# Run tests
npm test

# Package extension
npm run package
```

### Debugging

1. Open extension in VSCode
2. Press F5 to start debugging
3. New VSCode window opens with extension loaded
4. Set breakpoints and debug

### Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## Security

- API tokens are stored securely
- All communications use HTTPS
- No sensitive data is logged
- Extension follows VSCode security guidelines

## Support

For issues and questions:

- Check the troubleshooting section
- Review extension logs
- Contact support at support@sbh.com
- Join the community at community.sbh.com
