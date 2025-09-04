// LLM Playground JavaScript
let currentTemplate = null;
let currentResponse = null;

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadTemplates();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Temperature slider
    const temperatureSlider = document.getElementById('temperatureInput');
    const temperatureValue = document.getElementById('temperatureValue');
    
    temperatureSlider.addEventListener('input', function() {
        temperatureValue.textContent = this.value;
    });
}

// Load templates
async function loadTemplates() {
    try {
        const response = await fetch('/api/llm/v1/prompts', {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const data = await response.json();
            const templateSelect = document.getElementById('templateSelect');
            
            // Clear existing options
            templateSelect.innerHTML = '<option value="">Choose a template...</option>';
            
            // Add template options
            data.data.forEach(template => {
                const option = document.createElement('option');
                option.value = template.slug;
                option.textContent = template.title;
                templateSelect.appendChild(option);
            });
        } else {
            showError('Failed to load templates');
        }
    } catch (error) {
        console.error('Error loading templates:', error);
        showError('Failed to load templates');
    }
}

// Load template
async function loadTemplate() {
    const slug = document.getElementById('templateSelect').value;
    
    if (!slug) {
        document.getElementById('guidedForm').style.display = 'none';
        return;
    }
    
    try {
        const response = await fetch(`/api/llm/v1/prompts/${slug}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const data = await response.json();
            currentTemplate = data.data;
            
            // Show guided form
            document.getElementById('guidedForm').style.display = 'block';
            
            // Populate guided input fields
            populateGuidedInput(currentTemplate);
            
            // Enable render button
            document.getElementById('renderBtn').disabled = false;
        } else {
            showError('Failed to load template');
        }
    } catch (error) {
        console.error('Error loading template:', error);
        showError('Failed to load template');
    }
}

// Populate guided input fields
function populateGuidedInput(template) {
    const structure = template.structure;
    
    // Set default values
    document.getElementById('roleInput').value = structure.role || '';
    document.getElementById('contextInput').value = structure.context || '';
    document.getElementById('taskInput').value = structure.task || '';
    document.getElementById('audienceInput').value = structure.audience || '';
    document.getElementById('outputInput').value = structure.output || '';
    
    // Set options
    document.getElementById('cotEnabled').checked = template.cot_enabled || false;
    document.getElementById('jsonMode').checked = template.json_mode || false;
    
    // Add custom fields if any
    addCustomFields(template);
}

// Add custom fields
function addCustomFields(template) {
    const customFieldsContainer = document.getElementById('customFields');
    customFieldsContainer.innerHTML = '';
    
    // For now, we'll add some common custom fields
    const commonFields = ['customer_name', 'product_name', 'issue_type'];
    
    commonFields.forEach(field => {
        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'mb-3';
        fieldDiv.innerHTML = `
            <label for="${field}Input" class="form-label">${field.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</label>
            <input type="text" class="form-control" id="${field}Input" placeholder="Enter ${field.replace('_', ' ')}">
        `;
        customFieldsContainer.appendChild(fieldDiv);
    });
}

// Render prompt
async function renderPrompt() {
    if (!currentTemplate) {
        showError('Please select a template first');
        return;
    }
    
    try {
        showLoading(true);
        
        const guidedInput = buildGuidedInput();
        
        const response = await fetch('/api/llm/v1/render', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            },
            body: JSON.stringify({
                slug: currentTemplate.slug,
                guided_input: guidedInput
            })
        });

        if (response.ok) {
            const data = await response.json();
            displayMessages(data.data.messages);
            
            // Enable run button
            document.getElementById('runBtn').disabled = false;
            
            // Track analytics
            trackAnalytics('llm.ui.render', {
                template_slug: currentTemplate.slug,
                provider: document.getElementById('providerSelect').value
            });
        } else {
            const error = await response.json();
            showError(error.error || 'Failed to render prompt');
        }
    } catch (error) {
        console.error('Error rendering prompt:', error);
        showError('Failed to render prompt');
    } finally {
        showLoading(false);
    }
}

// Build guided input from form
function buildGuidedInput() {
    const guidedInput = {
        role: document.getElementById('roleInput').value,
        context: document.getElementById('contextInput').value,
        task: document.getElementById('taskInput').value,
        audience: document.getElementById('audienceInput').value,
        output: document.getElementById('outputInput').value,
        custom_fields: {}
    };
    
    // Add custom fields
    const customFields = ['customer_name', 'product_name', 'issue_type'];
    customFields.forEach(field => {
        const value = document.getElementById(`${field}Input`).value;
        if (value) {
            guidedInput.custom_fields[field] = value;
        }
    });
    
    return guidedInput;
}

// Display messages
function displayMessages(messages) {
    const container = document.getElementById('messagesContainer');
    
    if (!messages || messages.length === 0) {
        container.innerHTML = '<div class="text-muted text-center"><p>No messages to display</p></div>';
        return;
    }
    
    let html = '';
    messages.forEach(message => {
        const roleClass = message.role === 'system' ? 'system' : 
                         message.role === 'user' ? 'user' : 'assistant';
        
        html += `
            <div class="message ${roleClass}">
                <strong>${message.role.toUpperCase()}</strong>
                <div class="mt-2">${escapeHtml(message.content)}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Run prompt
async function runPrompt() {
    if (!currentTemplate) {
        showError('Please select a template first');
        return;
    }
    
    try {
        showLoading(true);
        
        const guidedInput = buildGuidedInput();
        const provider = document.getElementById('providerSelect').value;
        const model = document.getElementById('modelSelect').value;
        const temperature = parseFloat(document.getElementById('temperatureInput').value);
        const maxTokens = parseInt(document.getElementById('maxTokensInput').value);
        const jsonMode = document.getElementById('jsonMode').checked;
        
        const response = await fetch('/api/llm/v1/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            },
            body: JSON.stringify({
                slug: currentTemplate.slug,
                guided_input: guidedInput,
                provider: provider,
                model: model,
                temperature: temperature,
                max_tokens: maxTokens,
                json_mode: jsonMode
            })
        });

        if (response.ok) {
            const data = await response.json();
            currentResponse = data.data;
            
            displayResponse(data.data.response);
            displayUsageStats(data.data.response.usage);
            
            // Enable save button
            document.getElementById('saveBtn').disabled = false;
            
            // Track analytics
            trackAnalytics('llm.ui.run', {
                template_slug: currentTemplate.slug,
                provider: provider,
                model: model,
                cached: data.data.cached
            });
        } else {
            const error = await response.json();
            showError(error.error || 'Failed to run prompt');
        }
    } catch (error) {
        console.error('Error running prompt:', error);
        showError('Failed to run prompt');
    } finally {
        showLoading(false);
    }
}

// Display response
function displayResponse(response) {
    const container = document.getElementById('responseContainer');
    
    let html = '';
    
    if (response.cached) {
        html += '<span class="cache-badge">CACHED</span>';
    }
    
    html += `
        <div class="border rounded p-3 bg-light">
            <pre class="mb-0">${escapeHtml(response.text)}</pre>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Show response actions
    document.getElementById('responseActions').style.display = 'block';
}

// Display usage stats
function displayUsageStats(usage) {
    const container = document.getElementById('usageStats');
    
    const html = `
        <div class="row">
            <div class="col-md-4">
                <strong>Prompt Tokens:</strong> ${usage.prompt_tokens}
            </div>
            <div class="col-md-4">
                <strong>Completion Tokens:</strong> ${usage.completion_tokens}
            </div>
            <div class="col-md-4">
                <strong>Total Tokens:</strong> ${usage.total_tokens}
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    container.style.display = 'block';
}

// Save as template
async function saveAsTemplate() {
    if (!currentTemplate || !currentResponse) {
        showError('No template or response to save');
        return;
    }
    
    try {
        const guidedInput = buildGuidedInput();
        
        const templateData = {
            slug: `${currentTemplate.slug}-${Date.now()}`,
            title: `${currentTemplate.title} - Custom`,
            description: `Custom version of ${currentTemplate.title}`,
            structure: {
                role: guidedInput.role,
                context: guidedInput.context,
                task: guidedInput.task,
                audience: guidedInput.audience,
                output: guidedInput.output
            },
            examples: [
                {
                    input: guidedInput,
                    output: currentResponse.response.text
                }
            ],
            system_preamble: currentTemplate.system_preamble,
            cot_enabled: document.getElementById('cotEnabled').checked,
            json_mode: document.getElementById('jsonMode').checked,
            tool_schema: currentTemplate.tool_schema
        };
        
        const response = await fetch('/api/llm/v1/prompts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            },
            body: JSON.stringify(templateData)
        });

        if (response.ok) {
            showSuccess('Template saved successfully');
            loadTemplates(); // Refresh template list
        } else {
            const error = await response.json();
            showError(error.error || 'Failed to save template');
        }
    } catch (error) {
        console.error('Error saving template:', error);
        showError('Failed to save template');
    }
}

// Copy response text
function copyResponse() {
    if (currentResponse) {
        navigator.clipboard.writeText(currentResponse.response.text).then(() => {
            showSuccess('Response copied to clipboard');
        }).catch(() => {
            showError('Failed to copy to clipboard');
        });
    }
}

// Copy response JSON
function copyResponseJSON() {
    if (currentResponse) {
        const jsonData = JSON.stringify(currentResponse, null, 2);
        navigator.clipboard.writeText(jsonData).then(() => {
            showSuccess('Response JSON copied to clipboard');
        }).catch(() => {
            showError('Failed to copy to clipboard');
        });
    }
}

// Show status
async function showStatus() {
    try {
        const response = await fetch('/api/llm/v1/status', {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const data = await response.json();
            displayStatus(data.data);
            
            new bootstrap.Modal(document.getElementById('statusModal')).show();
        } else {
            showError('Failed to load status');
        }
    } catch (error) {
        console.error('Error loading status:', error);
        showError('Failed to load status');
    }
}

// Display status
function displayStatus(status) {
    const container = document.getElementById('statusContent');
    
    let html = '<div class="row">';
    
    // Providers
    html += '<div class="col-md-6"><h6>Providers</h6>';
    status.providers.forEach(provider => {
        const statusIcon = provider.configured && provider.ok ? '✅' : '❌';
        html += `
            <div class="mb-2">
                ${statusIcon} <strong>${provider.name}</strong>
                <br><small class="text-muted">Model: ${provider.model_default}</small>
            </div>
        `;
    });
    html += '</div>';
    
    // Cache
    html += '<div class="col-md-6"><h6>Cache</h6>';
    html += `<div>Enabled: ${status.cache.enabled ? '✅' : '❌'}</div>`;
    if (status.cache.enabled) {
        html += `<div>TTL: ${status.cache.ttl}s</div>`;
        html += `<div>Entries: ${status.cache.total_entries || 0}</div>`;
    }
    html += '</div>';
    
    html += '</div>';
    
    // Quota
    if (status.quota) {
        html += '<div class="mt-3"><h6>Quota</h6>';
        html += `<div>Current: ${status.quota.current} tokens</div>`;
        if (status.quota.limit) {
            html += `<div>Limit: ${status.quota.limit} tokens</div>`;
            html += `<div>Remaining: ${status.quota.remaining} tokens</div>`;
        }
        html += '</div>';
    }
    
    container.innerHTML = html;
}

// Utility functions
function showLoading(show) {
    document.getElementById('loadingSpinner').style.display = show ? 'block' : 'none';
}

function refreshPlayground() {
    loadTemplates();
    if (currentTemplate) {
        loadTemplate();
    }
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
