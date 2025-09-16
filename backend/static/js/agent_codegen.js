// Codegen Agent JavaScript
let currentPlan = null;
let currentJobId = null;

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadProjects();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Repository type radio buttons
    document.querySelectorAll('input[name="repoType"]').forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'local') {
                document.getElementById('localConfig').style.display = 'block';
                document.getElementById('githubConfig').style.display = 'none';
            } else {
                document.getElementById('localConfig').style.display = 'none';
                document.getElementById('githubConfig').style.display = 'block';
            }
        });
    });
}

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
                option.textContent = project.name;
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

// Generate plan
async function generatePlan() {
    const goalData = buildGoalData();
    
    if (!goalData) {
        return;
    }
    
    try {
        showLoading(true);
        
        const response = await fetch('/api/agent/codegen/plan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            },
            body: JSON.stringify(goalData)
        });

        if (response.ok) {
            const data = await response.json();
            currentPlan = data.data;
            
            displayPlan(currentPlan);
            displayDiffs(currentPlan.diffs);
            
            // Enable apply button
            document.getElementById('applyBtn').disabled = false;
            
            // Track analytics
            trackAnalytics('codegen.ui.plan', {
                repo_type: goalData.repo_ref.type,
                files_count: currentPlan.files_touched.length
            });
        } else {
            const error = await response.json();
            showError(error.error || 'Failed to generate plan');
        }
    } catch (error) {
        console.error('Error generating plan:', error);
        showError('Failed to generate plan');
    } finally {
        showLoading(false);
    }
}

// Apply changes
async function applyChanges() {
    if (!currentPlan) {
        showError('No plan to apply');
        return;
    }
    
    const goalData = buildGoalData();
    if (!goalData) {
        return;
    }
    
    // Add plan to goal data
    goalData.plan = currentPlan;
    
    try {
        showLoading(true);
        
        const response = await fetch('/api/agent/codegen/apply', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            },
            body: JSON.stringify(goalData)
        });

        if (response.ok) {
            const data = await response.json();
            const result = data.data;
            
            displayExecutionResult(result);
            
            // Track analytics
            trackAnalytics('codegen.ui.apply', {
                repo_type: goalData.repo_ref.type,
                status: result.status,
                files_count: currentPlan.files_touched.length
            });
        } else {
            const error = await response.json();
            showError(error.error || 'Failed to apply changes');
        }
    } catch (error) {
        console.error('Error applying changes:', error);
        showError('Failed to apply changes');
    } finally {
        showLoading(false);
    }
}

// Validate goal
async function validateGoal() {
    const goalData = buildGoalData();
    if (!goalData) {
        return;
    }
    
    try {
        showLoading(true);
        
        const response = await fetch('/api/agent/codegen/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            },
            body: JSON.stringify(goalData)
        });

        if (response.ok) {
            const data = await response.json();
            showSuccess('Goal validation passed');
        } else {
            const error = await response.json();
            showError(error.error || 'Goal validation failed');
        }
    } catch (error) {
        console.error('Error validating goal:', error);
        showError('Failed to validate goal');
    } finally {
        showLoading(false);
    }
}

// Build goal data from form
function buildGoalData() {
    const repoType = document.querySelector('input[name="repoType"]:checked').value;
    
    let repoRef = {};
    
    if (repoType === 'local') {
        const projectId = document.getElementById('projectSelect').value;
        if (!projectId) {
            showError('Please select a project');
            return null;
        }
        repoRef = {
            type: 'local',
            project_id: projectId
        };
    } else {
        const owner = document.getElementById('githubOwner').value;
        const repo = document.getElementById('githubRepo').value;
        const branch = document.getElementById('githubBranch').value;
        
        if (!owner || !repo) {
            showError('Please enter GitHub owner and repository');
            return null;
        }
        
        repoRef = {
            type: 'github',
            owner: owner,
            repo: repo,
            branch: branch
        };
    }
    
    const goalText = document.getElementById('goalText').value;
    if (!goalText) {
        showError('Please enter a goal');
        return null;
    }
    
    const baseBranch = document.getElementById('baseBranch').value;
    const dryRun = document.getElementById('dryRun').checked;
    
    // Parse allow/deny patterns
    const allowPaths = document.getElementById('allowPaths').value
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);
    
    const denyGlobs = document.getElementById('denyGlobs').value
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);
    
    return {
        repo_ref: repoRef,
        goal_text: goalText,
        branch_base: baseBranch,
        dry_run: dryRun,
        allow_paths: allowPaths.length > 0 ? allowPaths : undefined,
        deny_globs: denyGlobs.length > 0 ? denyGlobs : undefined
    };
}

// Display plan
function displayPlan(plan) {
    const container = document.getElementById('planSummary');
    const content = document.getElementById('planContent');
    
    const riskClass = `risk-${plan.risk}`;
    
    content.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div>
                <h6>${plan.summary}</h6>
                <p class="text-muted mb-2">Files: ${plan.files_touched.length}</p>
                <p class="text-muted mb-0">Tests: ${plan.tests_touched.length}</p>
            </div>
            <span class="risk-badge ${riskClass}">${plan.risk.toUpperCase()}</span>
        </div>
    `;
    
    container.style.display = 'block';
}

// Display diffs
function displayDiffs(diffs) {
    const container = document.getElementById('diffsSection');
    const content = document.getElementById('diffsContainer');
    
    if (!diffs || diffs.length === 0) {
        content.innerHTML = '<div class="text-muted text-center p-3">No changes proposed</div>';
        container.style.display = 'block';
        return;
    }
    
    let html = '';
    
    diffs.forEach((diff, index) => {
        html += `
            <div class="diff-file">
                <div class="diff-header" onclick="toggleDiff(${index})">
                    <i class="bi bi-chevron-down"></i> ${diff.file_path} (${diff.operation})
                </div>
                <div class="diff-content" id="diff-${index}">
                    ${formatDiff(diff.diff_content)}
                </div>
            </div>
        `;
    });
    
    content.innerHTML = html;
    container.style.display = 'block';
}

// Format diff content
function formatDiff(diffContent) {
    if (!diffContent) {
        return '<div class="text-muted">No diff content</div>';
    }
    
    const lines = diffContent.split('\n');
    let html = '';
    
    lines.forEach(line => {
        let className = 'diff-line';
        
        if (line.startsWith('+')) {
            className += ' added';
        } else if (line.startsWith('-')) {
            className += ' removed';
        } else if (line.startsWith('@@')) {
            className += ' context';
        }
        
        html += `<div class="${className}">${escapeHtml(line)}</div>`;
    });
    
    return html;
}

// Toggle diff visibility
function toggleDiff(index) {
    const diffContent = document.getElementById(`diff-${index}`);
    const header = diffContent.previousElementSibling;
    const icon = header.querySelector('i');
    
    if (diffContent.style.display === 'none') {
        diffContent.style.display = 'block';
        icon.className = 'bi bi-chevron-down';
    } else {
        diffContent.style.display = 'none';
        icon.className = 'bi bi-chevron-right';
    }
}

// Display execution result
function displayExecutionResult(result) {
    // Display test results
    const testContainer = document.getElementById('testResults');
    const testContent = document.getElementById('testContent');
    
    testContent.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <strong>Status:</strong> ${result.status}
            </div>
            <div class="col-md-6">
                <strong>Branch:</strong> ${result.branch}
            </div>
        </div>
        <div class="row mt-2">
            <div class="col-md-4">
                <strong>Tests Passed:</strong> ${result.tests.passed}
            </div>
            <div class="col-md-4">
                <strong>Tests Failed:</strong> ${result.tests.failed}
            </div>
            <div class="col-md-4">
                <strong>Duration:</strong> ${result.tests.duration.toFixed(2)}s
            </div>
        </div>
        <div class="row mt-2">
            <div class="col-md-6">
                <strong>Lint Status:</strong> ${result.lint.ok ? '✅ OK' : '❌ Issues'}
            </div>
            <div class="col-md-6">
                <strong>Issues:</strong> ${result.lint.issues.length}
            </div>
        </div>
        ${result.pr_url ? `<div class="mt-2"><strong>PR URL:</strong> <a href="${result.pr_url}" target="_blank">${result.pr_url}</a></div>` : ''}
        ${result.error ? `<div class="mt-2 text-danger"><strong>Error:</strong> ${result.error}</div>` : ''}
    `;
    
    testContainer.style.display = 'block';
}

// Show jobs
async function showJobs() {
    try {
        const response = await fetch('/api/agent/codegen/jobs', {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const data = await response.json();
            displayJobs(data.data.jobs);
            
            new bootstrap.Modal(document.getElementById('jobsModal')).show();
        } else {
            showError('Failed to load jobs');
        }
    } catch (error) {
        console.error('Error loading jobs:', error);
        showError('Failed to load jobs');
    }
}

// Display jobs
function displayJobs(jobs) {
    const container = document.getElementById('jobsContent');
    
    if (!jobs || jobs.length === 0) {
        container.innerHTML = '<p class="text-muted">No jobs found</p>';
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table table-sm">';
    html += '<thead><tr><th>Job ID</th><th>Goal</th><th>Status</th><th>Created</th></tr></thead><tbody>';
    
    jobs.forEach(job => {
        const statusClass = `job-${job.status}`;
        html += `
            <tr>
                <td><code>${job.job_id.substring(0, 8)}...</code></td>
                <td>${job.goal.goal_text.substring(0, 50)}...</td>
                <td><span class="badge ${statusClass}">${job.status}</span></td>
                <td>${new Date(job.created_at).toLocaleString()}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// Refresh agent
function refreshAgent() {
    loadProjects();
    currentPlan = null;
    currentJobId = null;
    
    // Reset UI
    document.getElementById('planSummary').style.display = 'none';
    document.getElementById('diffsSection').style.display = 'none';
    document.getElementById('testResults').style.display = 'none';
    document.getElementById('jobStatus').style.display = 'none';
    document.getElementById('applyBtn').disabled = true;
}

// Utility functions
function showLoading(show) {
    document.getElementById('loadingSpinner').style.display = show ? 'block' : 'none';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function trackAnalytics(event, props) {
    // Track analytics events
    console.log('Analytics:', event, props);
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
