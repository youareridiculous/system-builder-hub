// Export JavaScript
let currentProjectId = null;
let currentManifest = null;

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadProjects();
});

// Load projects
async function loadProjects() {
    try {
        const response = await fetch('/api/projects', {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const data = await response.json();
            const projectSelect = document.getElementById('projectSelect');
            
            // Clear existing options
            projectSelect.innerHTML = '<option value="">Choose a project...</option>';
            
            // Add project options
            data.projects.forEach(project => {
                const option = document.createElement('option');
                option.value = project.id;
                option.textContent = project.name || project.id;
                projectSelect.appendChild(option);
            });
        } else {
            showError('Failed to load projects');
        }
    } catch (error) {
        console.error('Error loading projects:', error);
        showError('Failed to load projects');
    }
}

// Load project export
function loadProjectExport() {
    currentProjectId = document.getElementById('projectSelect').value;
    
    if (currentProjectId) {
        // Enable export buttons
        document.getElementById('planBtn').disabled = false;
        document.getElementById('downloadBtn').disabled = false;
        document.getElementById('githubBtn').disabled = false;
        
        // Clear previous results
        document.getElementById('exportResults').style.display = 'none';
        currentManifest = null;
    } else {
        // Disable export buttons
        document.getElementById('planBtn').disabled = true;
        document.getElementById('downloadBtn').disabled = true;
        document.getElementById('githubBtn').disabled = true;
    }
}

// Plan export
async function planExport() {
    if (!currentProjectId) {
        showError('Please select a project first');
        return;
    }
    
    try {
        showExportLoading(true);
        
        const includeRuntime = document.getElementById('includeRuntime').checked;
        
        const response = await fetch('/api/export/plan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            },
            body: JSON.stringify({
                project_id: currentProjectId,
                include_runtime: includeRuntime
            })
        });

        if (response.ok) {
            const data = await response.json();
            currentManifest = data.data.manifest;
            
            showExportPlan(data.data);
        } else {
            const error = await response.json();
            showError(error.error || 'Failed to plan export');
        }
    } catch (error) {
        console.error('Error planning export:', error);
        showError('Failed to plan export');
    } finally {
        showExportLoading(false);
    }
}

// Show export plan
function showExportPlan(data) {
    const resultsDiv = document.getElementById('exportResults');
    const contentDiv = document.getElementById('exportPlanContent');
    
    const files = data.manifest.files || [];
    
    let filesHtml = '';
    if (files.length > 0) {
        filesHtml = `
        <div class="table-responsive">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>File</th>
                        <th>Size</th>
                        <th>SHA256</th>
                    </tr>
                </thead>
                <tbody>
                    ${files.map(file => `
                    <tr>
                        <td><code>${file.path}</code></td>
                        <td>${formatBytes(file.size)}</td>
                        <td><code>${file.sha256.substring(0, 8)}...</code></td>
                    </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        `;
    }
    
    contentDiv.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6>Export Summary</h6>
                <ul class="list-unstyled">
                    <li><strong>Project ID:</strong> ${data.manifest.project_id}</li>
                    <li><strong>Files:</strong> ${data.files_count}</li>
                    <li><strong>Total Size:</strong> ${formatBytes(data.total_size)}</li>
                    <li><strong>Generated:</strong> ${new Date(data.manifest.export_timestamp).toLocaleString()}</li>
                </ul>
            </div>
            <div class="col-md-6">
                <h6>Bundle Checksum</h6>
                <code>${data.manifest.checksum}</code>
            </div>
        </div>
        
        <div class="mt-4">
            <h6>Files to be exported:</h6>
            ${filesHtml}
        </div>
    `;
    
    resultsDiv.style.display = 'block';
}

// Download export
async function downloadExport() {
    if (!currentProjectId) {
        showError('Please select a project first');
        return;
    }
    
    try {
        showExportLoading(true);
        
        const includeRuntime = document.getElementById('includeRuntime').checked;
        
        const response = await fetch('/api/export/archive', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            },
            body: JSON.stringify({
                project_id: currentProjectId,
                include_runtime: includeRuntime
            })
        });

        if (response.ok) {
            // Get filename from response headers
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'sbh-export.zip';
            if (contentDisposition) {
                const match = contentDisposition.match(/filename="(.+)"/);
                if (match) {
                    filename = match[1];
                }
            }
            
            // Download file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showSuccess('Export downloaded successfully');
        } else {
            const error = await response.json();
            showError(error.error || 'Failed to download export');
        }
    } catch (error) {
        console.error('Error downloading export:', error);
        showError('Failed to download export');
    } finally {
        showExportLoading(false);
    }
}

// Show GitHub sync modal
function showGitHubSync() {
    if (!currentProjectId) {
        showError('Please select a project first');
        return;
    }
    
    // Set default branch name
    const now = new Date();
    const branchName = `sbh-sync-${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;
    document.getElementById('githubBranch').value = branchName;
    
    // Clear previous results
    document.getElementById('githubSyncResults').style.display = 'none';
    
    new bootstrap.Modal(document.getElementById('githubSyncModal')).show();
}

// Perform GitHub sync
async function performGitHubSync() {
    try {
        const form = document.getElementById('githubSyncForm');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        const owner = document.getElementById('githubOwner').value;
        const repo = document.getElementById('githubRepo').value;
        const branch = document.getElementById('githubBranch').value;
        const syncMode = document.getElementById('syncMode').value;
        const includeRuntime = document.getElementById('githubIncludeRuntime').checked;
        const dryRun = document.getElementById('githubDryRun').checked;
        
        const response = await fetch('/api/export/github/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            },
            body: JSON.stringify({
                project_id: currentProjectId,
                owner: owner,
                repo: repo,
                branch: branch,
                sync_mode: syncMode,
                include_runtime: includeRuntime,
                dry_run: dryRun
            })
        });

        if (response.ok) {
            const data = await response.json();
            showGitHubSyncResults(data.data);
        } else {
            const error = await response.json();
            showError(error.error || 'Failed to sync to GitHub');
        }
    } catch (error) {
        console.error('Error syncing to GitHub:', error);
        showError('Failed to sync to GitHub');
    }
}

// Show GitHub sync results
function showGitHubSyncResults(data) {
    const resultsDiv = document.getElementById('githubSyncResults');
    
    let prHtml = '';
    if (data.pr_url) {
        prHtml = `
        <div class="alert alert-info">
            <strong>Pull Request Created:</strong>
            <a href="${data.pr_url}" target="_blank" class="btn btn-sm btn-outline-info ms-2">
                <i class="bi bi-github"></i> View PR
            </a>
            <button class="btn btn-sm btn-outline-secondary ms-2" onclick="copyToClipboard('${data.pr_url}')">
                <i class="bi bi-clipboard"></i> Copy URL
            </button>
        </div>
        `;
    }
    
    resultsDiv.innerHTML = `
        <div class="alert alert-success">
            <h6>GitHub Sync ${data.dry_run ? '(Dry Run)' : 'Completed'}</h6>
            <ul class="list-unstyled mb-0">
                <li><strong>Repository:</strong> <a href="${data.repo_url}" target="_blank">${data.repo_url}</a></li>
                <li><strong>Branch:</strong> ${data.branch}</li>
                <li><strong>Files:</strong> ${data.files_count}</li>
                <li><strong>Total Size:</strong> ${formatBytes(data.total_size)}</li>
                ${data.commit_sha ? `<li><strong>Commit:</strong> <code>${data.commit_sha.substring(0, 8)}</code></li>` : ''}
            </ul>
            
            <div class="mt-3">
                <button class="btn btn-sm btn-outline-secondary" onclick="copyToClipboard('${data.repo_url}')">
                    <i class="bi bi-clipboard"></i> Copy Repo URL
                </button>
            </div>
        </div>
        
        ${prHtml}
    `;
    
    resultsDiv.style.display = 'block';
}

// Utility functions
function showExportLoading(show) {
    document.getElementById('exportLoading').style.display = show ? 'block' : 'none';
}

function refreshExport() {
    loadProjects();
    if (currentProjectId) {
        loadProjectExport();
    }
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showSuccess('Copied to clipboard');
    }).catch(() => {
        showError('Failed to copy to clipboard');
    });
}

function showSuccess(message) {
    alert('Success: ' + message);
}

function showError(message) {
    alert('Error: ' + message);
}

function getAuthToken() {
    return localStorage.getItem('authToken') || '';
}

function getCurrentTenant() {
    return localStorage.getItem('currentTenant') || 'primary';
}
