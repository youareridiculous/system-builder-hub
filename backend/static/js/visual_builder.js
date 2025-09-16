/**
 * Visual Builder JavaScript
 * Handles canvas interactions, save/generate, and preview with route-first logic, REST API support, and DB table binding
 */
class VisualBuilder {
    constructor() {
        this.state = {
            project_id: this.getProjectId(),
            version: 'v1',
            nodes: [],
            edges: [],
            metadata: {},
            _lastPreview: null,
            _dirty: false
        };
        
        this.selectedNode = null;
        
        if (!this.state.project_id) {
            this.showError('No project ID found. Please provide a project parameter.');
            this.disableUI();
            return;
        }
        
        this.initializeEventListeners();
        this.loadState();
    }
    
    getProjectId() {
        // Try window.SBH_PROJECT_ID first, then URL params
        if (window.SBH_PROJECT_ID) {
            return window.SBH_PROJECT_ID;
        }
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('project');
    }
    
    disableUI() {
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(btn => btn.disabled = true);
    }
    
    initializeEventListeners() {
        // Save button
        const saveBtn = document.getElementById('btn-save');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveBuilderState());
        }
        
        // Generate Build button
        const generateBtn = document.getElementById('btn-generate');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generateBuild());
        }
        
        // Open Preview button
        const previewBtn = document.getElementById('btn-open-preview');
        if (previewBtn) {
            previewBtn.addEventListener('click', () => this.openPreview());
        }
        
        // Node palette
        this.initializeNodePalette();
        
        // Canvas click to deselect
        const canvas = document.getElementById('canvas');
        if (canvas) {
            canvas.addEventListener('click', (e) => {
                if (e.target === canvas) {
                    this.deselectNode();
                }
            });
        }
    }
    
    initializeNodePalette() {
        const paletteItems = document.querySelectorAll('.palette li[data-type]');
        paletteItems.forEach(item => {
            item.addEventListener('click', () => {
                const type = item.getAttribute('data-type');
                this.addNode(type);
            });
            
            // Make draggable
            item.draggable = true;
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', item.getAttribute('data-type'));
            });
        });
        
        // Canvas drop target
        const canvas = document.getElementById('canvas');
        if (canvas) {
            canvas.addEventListener('dragover', (e) => {
                e.preventDefault();
                canvas.style.backgroundColor = '#e3f2fd';
            });
            
            canvas.addEventListener('dragleave', (e) => {
                canvas.style.backgroundColor = '#f8f9fa';
            });
            
            canvas.addEventListener('drop', (e) => {
                e.preventDefault();
                canvas.style.backgroundColor = '#f8f9fa';
                const type = e.dataTransfer.getData('text/plain');
                if (type) {
                    this.addNode(type, {
                        x: e.offsetX,
                        y: e.offsetY
                    });
                }
            });
        }
    }
    
    addNode(type, position = null) {
        const nodeId = this.generateId();
        const node = {
            id: nodeId,
            type: type,
            props: this.getDefaultProps(type),
            meta: position ? { x: position.x, y: position.y } : {}
        };
        
        this.state.nodes.push(node);
        this.renderNode(node);
        this.markDirty();
        this.showToast(`Added ${type} node`);
    }
    
    getDefaultProps(type) {
        switch (type) {
            case 'ui_page':
                return {
                    name: 'NewPage',
                    title: 'New Page',
                    route: '/new-page',
                    content: '<h1>New Page</h1><p>Content goes here.</p>',
                    consumes: {},
                    bind_table: null,
                    form: { enabled: false, fields: [] }
                };
            case 'rest_api':
                return {
                    name: 'NewAPI',
                    route: '/api/new-api',
                    method: 'GET',
                    sample_response: '{"ok": true}'
                };
            case 'db_table':
                return {
                    name: 'table',
                    columns: [
                        {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                        {"name": "title", "type": "TEXT"}
                    ]
                };
            case 'auth':
                return {
                    name: 'Auth',
                    type: 'jwt'
                };
            case 'agent_tool':
                return {
                    name: 'NewTool',
                    description: 'Agent tool description'
                };
            default:
                return {};
        }
    }
    
    generateId() {
        return 'node_' + Math.random().toString(36).substr(2, 9);
    }
    
    renderNode(node) {
        const canvas = document.getElementById('canvas');
        if (!canvas) return;
        
        const nodeElement = document.createElement('div');
        nodeElement.className = 'canvas-node';
        nodeElement.id = `node-${node.id}`;
        nodeElement.innerHTML = `
            <div class="node-header">
                <span class="node-type">${node.type}</span>
                <button class="node-delete" onclick="builder.deleteNode('${node.id}')">×</button>
            </div>
            <div class="node-content">
                <div class="node-name">${node.props.name || 'Unnamed'}</div>
            </div>
        `;
        
        // Position if specified
        if (node.meta.x !== undefined && node.meta.y !== undefined) {
            nodeElement.style.position = 'absolute';
            nodeElement.style.left = node.meta.x + 'px';
            nodeElement.style.top = node.meta.y + 'px';
        }
        
        // Make draggable
        nodeElement.draggable = true;
        nodeElement.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', node.id);
        });
        
        // Click to select
        nodeElement.addEventListener('click', (e) => {
            if (e.target.classList.contains('node-delete')) return;
            this.selectNode(node);
        });
        
        // Remove hint if it exists
        const hint = canvas.querySelector('.hint');
        if (hint) {
            hint.remove();
        }
        
        canvas.appendChild(nodeElement);
    }
    
    selectNode(node) {
        this.selectedNode = node;
        
        // Update visual selection
        document.querySelectorAll('.canvas-node').forEach(el => {
            el.classList.remove('selected');
        });
        const nodeElement = document.getElementById(`node-${node.id}`);
        if (nodeElement) {
            nodeElement.classList.add('selected');
        }
        
        // Render properties panel
        this.renderPropertiesPanel(node);
    }
    
    deselectNode() {
        this.selectedNode = null;
        document.querySelectorAll('.canvas-node').forEach(el => {
            el.classList.remove('selected');
        });
        this.renderPropertiesPanel(null);
    }
    
    renderPropertiesPanel(node) {
        const propsPanel = document.getElementById('props-panel');
        if (!propsPanel) return;
        
        if (!node) {
            propsPanel.innerHTML = '<p>Select a block to edit its properties</p>';
            return;
        }
        
        let html = `<h3>${node.type.replace('_', ' ').toUpperCase()}</h3>`;
        
        switch (node.type) {
            case 'ui_page':
                const previewUrl = this.state._lastPreview ? 
                    this.state._lastPreview.preview_url : 
                    `/ui/${this.slugify(node.props.name || 'page')}`;
                
                html += `
                    <div class="prop-group">
                        <label>Name:</label>
                        <input type="text" id="prop-name" value="${node.props.name || ''}" 
                               onchange="builder.updateNodeProp('name', this.value)">
                    </div>
                    <div class="prop-group">
                        <label>Route:</label>
                        <div class="route-input-group">
                            <input type="text" id="prop-route" value="${node.props.route || ''}" 
                                   onchange="builder.updateNodeProp('route', this.value)">
                            <button class="link-btn" onclick="builder.copyPreviewUrl()" title="Copy preview URL">
                                🔗
                            </button>
                        </div>
                        <small class="preview-url">Preview: ${previewUrl}</small>
                    </div>
                    <div class="prop-group">
                        <label>Title:</label>
                        <input type="text" id="prop-title" value="${node.props.title || ''}" 
                               onchange="builder.updateNodeProp('title', this.value)">
                    </div>
                    <div class="prop-group">
                        <label>Content:</label>
                        <textarea id="prop-content" rows="4" 
                                  onchange="builder.updateNodeProp('content', this.value)">${node.props.content || ''}</textarea>
                    </div>
                    <div class="prop-group">
                        <label>Consumes API:</label>
                        <input type="text" id="prop-consumes-api" placeholder="API route or node ID" 
                               value="${node.props.consumes?.api || ''}" 
                               onchange="builder.updateNodeProp('consumes.api', this.value)">
                        <select id="prop-consumes-render" onchange="builder.updateNodeProp('consumes.render', this.value)">
                            <option value="raw" ${node.props.consumes?.render === 'raw' ? 'selected' : ''}>Raw JSON</option>
                            <option value="list" ${node.props.consumes?.render === 'list' ? 'selected' : ''}>List</option>
                        </select>
                    </div>
                    <div class="prop-group">
                        <label>Bind Table:</label>
                        <input type="text" id="prop-bind-table" placeholder="Table name or node ID" 
                               value="${node.props.bind_table || ''}" 
                               onchange="builder.updateNodeProp('bind_table', this.value)">
                    </div>
                    <div class="prop-group">
                        <label>Form Fields:</label>
                        <input type="text" id="prop-form-fields" placeholder="title,description (comma separated)" 
                               value="${node.props.form?.fields?.join(', ') || ''}" 
                               onchange="builder.updateNodeProp('form.fields', this.value)">
                        <label style="display:block; margin-top:0.5rem;">
                            <input type="checkbox" id="prop-form-enabled" 
                                   ${node.props.form?.enabled ? 'checked' : ''} 
                                   onchange="builder.updateNodeProp('form.enabled', this.checked)">
                            Enable form
                        </label>
                    </div>
                `;
                break;
                
            case 'rest_api':
                html += `
                    <div class="prop-group">
                        <label>Name:</label>
                        <input type="text" id="prop-name" value="${node.props.name || ''}" 
                               onchange="builder.updateNodeProp('name', this.value)">
                    </div>
                    <div class="prop-group">
                        <label>Route:</label>
                        <input type="text" id="prop-route" value="${node.props.route || ''}" 
                               onchange="builder.updateNodeProp('route', this.value)">
                    </div>
                    <div class="prop-group">
                        <label>Method:</label>
                        <select id="prop-method" onchange="builder.updateNodeProp('method', this.value)">
                            <option value="GET" ${node.props.method === 'GET' ? 'selected' : ''}>GET</option>
                            <option value="POST" ${node.props.method === 'POST' ? 'selected' : ''}>POST</option>
                            <option value="PATCH" ${node.props.method === 'PATCH' ? 'selected' : ''}>PATCH</option>
                            <option value="DELETE" ${node.props.method === 'DELETE' ? 'selected' : ''}>DELETE</option>
                        </select>
                    </div>
                    <div class="prop-group">
                        <label>Sample Response:</label>
                        <textarea id="prop-sample_response" rows="6" 
                                  onchange="builder.updateNodeProp('sample_response', this.value)">${node.props.sample_response || ''}</textarea>
                        <small>Enter valid JSON</small>
                    </div>
                `;
                break;
                
            case 'db_table':
                html += `
                    <div class="prop-group">
                        <label>Name:</label>
                        <input type="text" id="prop-name" value="${node.props.name || ''}" 
                               onchange="builder.updateNodeProp('name', this.value)">
                    </div>
                    <div class="prop-group">
                        <label>Columns:</label>
                        <textarea id="prop-columns" rows="8" 
                                  onchange="builder.updateNodeProp('columns', this.value)">${JSON.stringify(node.props.columns || [], null, 2)}</textarea>
                        <small>Enter JSON array of column definitions. Default: id (auto), title</small>
                    </div>
                `;
                break;
                
            default:
                html += `<p>Properties for ${node.type} nodes are not yet implemented.</p>`;
        }
        
        propsPanel.innerHTML = html;
    }
    
    updateNodeProp(field, value) {
        if (!this.selectedNode) return;
        
        // Handle nested properties like 'consumes.api'
        if (field.includes('.')) {
            const [parent, child] = field.split('.');
            if (!this.selectedNode.props[parent]) {
                this.selectedNode.props[parent] = {};
            }
            this.selectedNode.props[parent][child] = value;
        } else {
            this.selectedNode.props[field] = value;
        }
        
        // Special handling for form.fields (comma-separated string to array)
        if (field === 'form.fields') {
            if (typeof value === 'string') {
                this.selectedNode.props.form.fields = value.split(',').map(f => f.trim()).filter(f => f);
            }
        }
        
        // Special handling for columns (JSON string to array)
        if (field === 'columns') {
            try {
                if (typeof value === 'string') {
                    this.selectedNode.props.columns = JSON.parse(value);
                }
            } catch (e) {
                // Keep the string value if JSON parsing fails
                console.warn('Invalid JSON for columns:', e);
            }
        }
        
        // Auto-sync Name ↔ Route for ui_page nodes
        if (this.selectedNode.type === 'ui_page') {
            if (field === 'name') {
                // If route is empty or auto-derived, update it
                const currentRoute = this.selectedNode.props.route || '';
                const nameSlug = this.slugify(value);
                const expectedRoute = `/${nameSlug}`;
                
                if (!currentRoute || currentRoute === expectedRoute || currentRoute === `/${this.slugify(this.selectedNode.props.name || '')}`) {
                    this.selectedNode.props.route = expectedRoute;
                    // Update the route input field
                    const routeInput = document.getElementById('prop-route');
                    if (routeInput) {
                        routeInput.value = expectedRoute;
                    }
                }
            }
        }
        
        this.markDirty();
        
        // Update node display
        const nodeElement = document.getElementById(`node-${this.selectedNode.id}`);
        if (nodeElement) {
            const nameElement = nodeElement.querySelector('.node-name');
            if (nameElement && field === 'name') {
                nameElement.textContent = value || 'Unnamed';
            }
        }
        
        // Update preview URL display
        if (field === 'name' || field === 'route') {
            this.updatePreviewUrlDisplay();
        }
    }
    
    slugify(text) {
        if (!text) return '';
        return text.toLowerCase()
            .replace(/[^a-z0-9\s-]/g, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-')
            .replace(/^-|-$/g, '');
    }
    
    updatePreviewUrlDisplay() {
        if (!this.selectedNode || this.selectedNode.type !== 'ui_page') return;
        
        const previewUrlElement = document.querySelector('.preview-url');
        if (previewUrlElement) {
            const route = this.selectedNode.props.route || '';
            const slug = this.routeToSlug(route);
            const previewUrl = `/ui/${slug}`;
            previewUrlElement.textContent = `Preview: ${previewUrl}`;
        }
    }
    
    routeToSlug(route) {
        if (!route) return 'page';
        const segments = route.split('/').filter(s => s);
        return this.slugify(segments[segments.length - 1] || 'page');
    }
    
    copyPreviewUrl() {
        if (!this.selectedNode || this.selectedNode.type !== 'ui_page') return;
        
        const route = this.selectedNode.props.route || '';
        const slug = this.routeToSlug(route);
        const previewUrl = `${window.location.origin}/ui/${slug}`;
        
        navigator.clipboard.writeText(previewUrl).then(() => {
            this.showToast('Preview URL copied to clipboard');
        }).catch(() => {
            this.showToast('Failed to copy URL');
        });
    }
    
    deleteNode(nodeId) {
        this.state.nodes = this.state.nodes.filter(n => n.id !== nodeId);
        const nodeElement = document.getElementById(`node-${nodeId}`);
        if (nodeElement) {
            nodeElement.remove();
        }
        
        if (this.selectedNode && this.selectedNode.id === nodeId) {
            this.deselectNode();
        }
        
        this.markDirty();
        this.showToast('Node deleted');
        
        // Show hint if no nodes left
        const canvas = document.getElementById('canvas');
        if (canvas && this.state.nodes.length === 0) {
            const hint = document.createElement('div');
            hint.className = 'hint';
            hint.textContent = 'Drag blocks here to build your system';
            canvas.appendChild(hint);
        }
    }
    
    async loadState() {
        try {
            const response = await fetch(`/api/builder/state/${this.state.project_id}`);
            if (response.ok) {
                const data = await response.json();
                
                // Update state with loaded data
                this.state.nodes = data.nodes || [];
                this.state.edges = data.edges || [];
                this.state.metadata = data.metadata || {};
                this.state.version = data.version || 'v1';
                this.state._dirty = false;
                
                // Render existing nodes
                this.state.nodes.forEach(node => this.renderNode(node));
                
                this.updateStatusBar();
            }
        } catch (error) {
            console.log('No existing state found, starting fresh');
        }
    }
    
    async saveBuilderState() {
        const saveBtn = document.getElementById('btn-save');
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
        }
        
        try {
            const payload = {
                project_id: this.state.project_id,
                version: this.state.version,
                nodes: this.state.nodes,
                edges: this.state.edges,
                metadata: this.state.metadata
            };
            
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                console.log('Save payload:', payload);
            }
            
            const response = await fetch('/api/builder/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.state._dirty = false;
                this.updateStatusBar();
                this.showToast('Saved successfully');
            } else {
                // Handle structured errors
                if (response.status === 422) {
                    if (data.errors && Array.isArray(data.errors)) {
                        this.showFieldErrors(data.errors);
                        this.showError('Validation errors occurred. Please check the fields above.');
                    } else {
                        this.showError(data.message || 'Save failed');
                    }
                } else {
                    this.showError(data.message || 'Save failed');
                }
            }
            
        } catch (error) {
            this.showError('Network error: ' + error.message);
        } finally {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = 'Save';
            }
        }
    }
    
    showFieldErrors(errors) {
        errors.forEach(error => {
            const fieldId = `prop-${error.field}`;
            const field = document.getElementById(fieldId);
            if (field) {
                field.style.borderColor = '#dc3545';
                field.title = error.message;
            }
        });
    }
    
    async generateBuild() {
        const generateBtn = document.getElementById('btn-generate');
        if (generateBtn) {
            generateBtn.disabled = true;
            generateBtn.textContent = 'Generating...';
        }
        
        try {
            const payload = {
                project_id: this.state.project_id
            };
            
            const response = await fetch('/api/builder/generate-build', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.state._lastPreview = {
                    preview_url: data.preview_url,
                    preview_url_project: data.preview_url_project,
                    pages: data.emitted_pages || [],
                    apis: data.apis || [],
                    tables: data.tables || []
                };
                this.updateStatusBar();
                this.showToast('Build generated successfully');
                
                // Enable preview button
                const previewBtn = document.getElementById('btn-open-preview');
                if (previewBtn) {
                    previewBtn.disabled = false;
                    previewBtn.textContent = 'Open Preview';
                }
                
                // Update preview URL display for selected node
                if (this.selectedNode) {
                    this.updatePreviewUrlDisplay();
                }
            } else {
                this.showError(data.message || 'Build generation failed');
            }
            
        } catch (error) {
            this.showError('Network error: ' + error.message);
        } finally {
            if (generateBtn) {
                generateBtn.disabled = false;
                generateBtn.textContent = 'Generate Build';
            }
        }
    }
    
    openPreview() {
        if (this.state._lastPreview) {
            // Navigate in order: preview_url, preview_url_project, fallback
            const url = this.state._lastPreview.preview_url || 
                       this.state._lastPreview.preview_url_project || 
                       `/preview/${this.state.project_id}`;
            window.location.href = url;
        } else {
            this.showError('No preview available. Generate a build first.');
        }
    }
    
    markDirty() {
        this.state._dirty = true;
        this.updateStatusBar();
    }
    
    updateStatusBar() {
        const statusBar = document.getElementById('status-bar');
        if (statusBar) {
            let status = `Project: ${this.state.project_id}`;
            status += this.state._dirty ? ' | Unsaved changes' : ' | Saved';
            if (this.state._lastPreview) {
                status += ' | Preview available';
            }
            statusBar.textContent = status;
        }
    }
    
    showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
    
    showError(message) {
        const error = document.createElement('div');
        error.className = 'error-toast';
        error.textContent = 'Error: ' + message;
        document.body.appendChild(error);
        
        setTimeout(() => {
            error.remove();
        }, 5000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.builder = new VisualBuilder();
});
