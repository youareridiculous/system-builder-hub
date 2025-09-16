// Marketplace JavaScript
let currentTemplates = [];
let currentPage = 1;
let totalPages = 1;
let currentTemplate = null;

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadTemplates();
    checkUserRole();
});

// Load templates
async function loadTemplates(page = 1) {
    try {
        showTemplatesLoading(true);
        
        const params = new URLSearchParams();
        params.append('page', page);
        params.append('per_page', 12);
        
        // Add filters
        const category = document.getElementById('categoryFilter').value;
        const search = document.getElementById('searchInput').value;
        const price = document.getElementById('priceFilter').value;
        
        if (category) params.append('category', category);
        if (search) params.append('q', search);
        if (price) params.append('price', price);
        
        const response = await fetch(`/api/market/templates?${params}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const data = await response.json();
            currentTemplates = data.data.templates;
            currentPage = data.data.page;
            totalPages = data.data.pages;
            
            renderTemplates();
            updatePagination();
        } else {
            showError('Failed to load templates');
        }
    } catch (error) {
        console.error('Error loading templates:', error);
        showError('Failed to load templates');
    } finally {
        showTemplatesLoading(false);
    }
}

// Render templates grid
function renderTemplates() {
    const grid = document.getElementById('templatesGrid');
    const emptyState = document.getElementById('templatesEmpty');
    
    if (currentTemplates.length === 0) {
        grid.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }
    
    emptyState.style.display = 'none';
    
    grid.innerHTML = currentTemplates.map(template => `
        <div class="col-md-6 col-lg-4 mb-4">
            <div class="card template-card">
                <div class="template-cover position-relative">
                    <i class="bi bi-file-earmark-text"></i>
                    ${template.requires_plan ? '<span class="badge bg-warning template-badge">Pro</span>' : ''}
                    ${template.price_cents ? '<span class="badge bg-info template-badge">Paid</span>' : ''}
                </div>
                <div class="card-body">
                    <h5 class="card-title">${template.name}</h5>
                    <p class="card-text text-muted">${template.short_desc || 'No description available'}</p>
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="badge bg-secondary">${template.category}</span>
                        <button class="btn btn-primary btn-sm" onclick="viewTemplate('${template.slug}')">
                            View Details
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

// View template details
async function viewTemplate(slug) {
    try {
        const response = await fetch(`/api/market/templates/${slug}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const data = await response.json();
            currentTemplate = data.data;
            
            showTemplateDetails(currentTemplate);
        } else {
            showError('Failed to load template details');
        }
    } catch (error) {
        console.error('Error loading template details:', error);
        showError('Failed to load template details');
    }
}

// Show template details modal
function showTemplateDetails(template) {
    const modal = document.getElementById('templateDetailModal');
    const title = document.getElementById('templateDetailTitle');
    const content = document.getElementById('templateDetailContent');
    
    title.textContent = template.name;
    
    let badges = '';
    if (template.requires_plan) {
        badges += '<span class="badge bg-warning me-2">Pro Plan Required</span>';
    }
    if (template.price_cents) {
        badges += '<span class="badge bg-info me-2">Paid Template</span>';
    }
    
    content.innerHTML = `
        <div class="row">
            <div class="col-md-8">
                <h4>${template.name}</h4>
                <div class="mb-3">
                    ${badges}
                </div>
                <p class="text-muted">${template.long_desc || template.short_desc || 'No description available'}</p>
                
                <div class="mb-3">
                    <strong>Category:</strong> ${template.category}
                </div>
                
                ${template.tags && template.tags.length > 0 ? `
                <div class="mb-3">
                    <strong>Tags:</strong>
                    ${template.tags.map(tag => `<span class="badge bg-light text-dark me-1">${tag}</span>`).join('')}
                </div>
                ` : ''}
                
                ${template.assets && template.assets.sample_screens ? `
                <div class="mb-3">
                    <strong>Sample Screens:</strong>
                    <div class="row mt-2">
                        ${template.assets.sample_screens.map(screen => `
                        <div class="col-md-6 mb-2">
                            <div class="card">
                                <div class="card-body">
                                    <h6 class="card-title">${screen.title}</h6>
                                    <p class="card-text small">${screen.description}</p>
                                </div>
                            </div>
                        </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
            </div>
            <div class="col-md-4">
                <div class="d-grid gap-2">
                    <button class="btn btn-primary" onclick="showGuidedPrompt('${template.slug}')">
                        <i class="bi bi-magic"></i> Use Template
                    </button>
                    <button class="btn btn-outline-secondary" onclick="previewTemplate('${template.slug}')">
                        <i class="bi bi-eye"></i> Preview
                    </button>
                </div>
            </div>
        </div>
    `;
    
    new bootstrap.Modal(modal).show();
}

// Show guided prompt form
async function showGuidedPrompt(slug) {
    try {
        const response = await fetch(`/api/market/templates/${slug}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const data = await response.json();
            const template = data.data;
            
            showGuidedPromptModal(template);
        } else {
            showError('Failed to load template');
        }
    } catch (error) {
        console.error('Error loading template:', error);
        showError('Failed to load template');
    }
}

// Show guided prompt modal
function showGuidedPromptModal(template) {
    const modal = document.getElementById('useTemplateModal');
    const title = document.getElementById('useTemplateTitle');
    const content = document.getElementById('useTemplateContent');
    
    title.textContent = `Use Template: ${template.name}`;
    
    // Build guided prompt form
    let formFields = '';
    
    // Standard prompt structure fields
    const standardFields = [
        { name: 'role', label: 'Role', placeholder: 'e.g., Founder, Manager, Developer' },
        { name: 'context', label: 'Context', placeholder: 'e.g., Track tasks, Manage content' },
        { name: 'task', label: 'Task', placeholder: 'e.g., CRUD operations, Data management' },
        { name: 'audience', label: 'Audience', placeholder: 'e.g., Team, Customers, Public' },
        { name: 'output', label: 'Output', placeholder: 'e.g., Web application, Dashboard' }
    ];
    
    standardFields.forEach(field => {
        formFields += `
        <div class="mb-3">
            <label for="${field.name}" class="form-label">${field.label}</label>
            <input type="text" class="form-control" id="${field.name}" placeholder="${field.placeholder}" required>
        </div>
        `;
    });
    
    // Custom schema fields
    if (template.guided_schema && template.guided_schema.fields) {
        template.guided_schema.fields.forEach(field => {
            let inputHtml = '';
            
            if (field.type === 'string') {
                inputHtml = `<input type="text" class="form-control" id="${field.name}" value="${field.default || ''}" ${field.required ? 'required' : ''}>`;
            } else if (field.type === 'number') {
                inputHtml = `<input type="number" class="form-control" id="${field.name}" value="${field.default || ''}" ${field.required ? 'required' : ''}>`;
            } else if (field.type === 'boolean') {
                inputHtml = `<input type="checkbox" class="form-check-input" id="${field.name}" ${field.default ? 'checked' : ''}>`;
            } else if (field.type === 'select') {
                const options = field.options.map(opt => `<option value="${opt}" ${opt === field.default ? 'selected' : ''}>${opt}</option>`).join('');
                inputHtml = `<select class="form-select" id="${field.name}" ${field.required ? 'required' : ''}>${options}</select>`;
            }
            
            formFields += `
            <div class="mb-3">
                <label for="${field.name}" class="form-label">${field.label}</label>
                ${inputHtml}
                ${field.description ? `<div class="form-text">${field.description}</div>` : ''}
            </div>
            `;
        });
    }
    
    content.innerHTML = `
        <div class="guided-prompt-form">
            <h6>Customize Your Template</h6>
            <p class="text-muted">Fill in the details below to customize your template.</p>
            
            <form id="guidedPromptForm">
                ${formFields}
            </form>
        </div>
        
        <div class="preview-section">
            <h6>Preview</h6>
            <p class="text-muted">Click "Plan Template" to see a preview of your customized application.</p>
            <button type="button" class="btn btn-outline-primary" onclick="planTemplate('${template.slug}')">
                <i class="bi bi-eye"></i> Plan Template
            </button>
            <div id="previewContent" class="mt-3"></div>
        </div>
    `;
    
    new bootstrap.Modal(modal).show();
}

// Plan template
async function planTemplate(slug) {
    try {
        const guidedInput = getGuidedInput();
        
        const response = await fetch(`/api/market/templates/${slug}/plan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            },
            body: JSON.stringify({
                guided_input: guidedInput
            })
        });

        if (response.ok) {
            const data = await response.json();
            showPreview(data.data);
        } else {
            const error = await response.json();
            showError(error.error || 'Failed to plan template');
        }
    } catch (error) {
        console.error('Error planning template:', error);
        showError('Failed to plan template');
    }
}

// Use template
async function useTemplate() {
    try {
        const guidedInput = getGuidedInput();
        
        const response = await fetch(`/api/market/templates/${currentTemplate.slug}/use`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            },
            body: JSON.stringify({
                guided_input: guidedInput
            })
        });

        if (response.ok) {
            const data = await response.json();
            
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('useTemplateModal')).hide();
            
            // Show success message
            showSuccess('Template deployed successfully!');
            
            // Redirect to preview
            setTimeout(() => {
                window.location.href = data.data.preview_url_project;
            }, 2000);
            
        } else {
            const error = await response.json();
            if (error.requires_subscription) {
                showError(`This template requires a ${error.requires_subscription} subscription`);
            } else {
                showError(error.error || 'Failed to use template');
            }
        }
    } catch (error) {
        console.error('Error using template:', error);
        showError('Failed to use template');
    }
}

// Get guided input from form
function getGuidedInput() {
    const form = document.getElementById('guidedPromptForm');
    const formData = new FormData(form);
    const guidedInput = {};
    
    // Get standard fields
    ['role', 'context', 'task', 'audience', 'output'].forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            guidedInput[field] = element.value;
        }
    });
    
    // Get custom fields
    if (currentTemplate && currentTemplate.guided_schema && currentTemplate.guided_schema.fields) {
        currentTemplate.guided_schema.fields.forEach(field => {
            const element = document.getElementById(field.name);
            if (element) {
                if (field.type === 'boolean') {
                    guidedInput[field.name] = element.checked;
                } else {
                    guidedInput[field.name] = element.value;
                }
            }
        });
    }
    
    return guidedInput;
}

// Show preview
function showPreview(data) {
    const previewContent = document.getElementById('previewContent');
    
    previewContent.innerHTML = `
        <div class="alert alert-info">
            <h6>Generated Application Structure</h6>
            <ul class="mb-0">
                ${data.builder_state.nodes ? data.builder_state.nodes.map(node => `
                <li><strong>${node.type}:</strong> ${node.name}</li>
                `).join('') : '<li>No nodes generated</li>'}
            </ul>
        </div>
    `;
}

// Filter templates
function filterTemplates() {
    loadTemplates(1);
}

// Refresh templates
function refreshTemplates() {
    loadTemplates(currentPage);
}

// Pagination
function previousPage() {
    if (currentPage > 1) {
        loadTemplates(currentPage - 1);
    }
}

function nextPage() {
    if (currentPage < totalPages) {
        loadTemplates(currentPage + 1);
    }
}

function updatePagination() {
    const paginationNav = document.getElementById('paginationNav');
    const pageInfo = document.getElementById('pageInfo');
    
    if (totalPages > 1) {
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        paginationNav.style.display = 'block';
    } else {
        paginationNav.style.display = 'none';
    }
}

// Check user role for admin features
async function checkUserRole() {
    try {
        const response = await fetch('/api/auth/me', {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.user && data.user.role === 'admin') {
                document.getElementById('manageTemplatesBtn').style.display = 'block';
            }
        }
    } catch (error) {
        console.error('Error checking user role:', error);
    }
}

// Show manage templates (admin only)
function showManageTemplates() {
    // This would open a template management interface
    alert('Template management interface coming soon!');
}

// Utility functions
function showTemplatesLoading(show) {
    document.getElementById('templatesLoading').style.display = show ? 'block' : 'none';
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
