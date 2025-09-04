/**
 * Enhanced Build Wizard - LLM Integration with No-LLM Mode
 */
class BuildWizardEnhanced {
    constructor() {
        this.llmStatus = null;
        this.noLLMMode = false;
        this.isLoading = false;
        this.testConnectionTimeout = null;
        
        this.initializeEventListeners();
        this.loadLLMStatus();
    }
    
    initializeEventListeners() {
        // LLM Provider Setup
        document.getElementById('llm-provider-select')?.addEventListener('change', (e) => {
            this.updateModelOptions(e.target.value);
        });
        
        document.getElementById('test-connection-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.testConnection();
        });
        
        document.getElementById('save-llm-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.saveLLMProvider();
        });
        
        // No-LLM Mode Toggle
        document.getElementById('no-llm-toggle')?.addEventListener('change', (e) => {
            this.toggleNoLLMMode(e.target.checked);
        });
        
        // Dry-Run Prompt
        document.getElementById('dry-run-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.dryRunPrompt();
        });
        
        // API Key Reveal/Copy
        document.getElementById('reveal-api-key')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleAPIKeyVisibility();
        });
        
        document.getElementById('copy-api-key')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.copyAPIKey();
        });
        
        // Form submission
        document.getElementById('build-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitBuild();
        });
        
        // Debounced API key input
        const apiKeyInput = document.getElementById('llm-api-key');
        if (apiKeyInput) {
            apiKeyInput.addEventListener('input', this.debounce(() => {
                this.validateAPIKey();
            }, 500));
        }
    }
    
    async loadLLMStatus() {
        try {
            const response = await fetch('/api/llm/status');
            if (response.ok) {
                this.llmStatus = await response.json();
                this.updateUI();
            }
        } catch (error) {
            console.error('Failed to load LLM status:', error);
        }
    }
    
    updateUI() {
        this.updateStatusPill();
        this.updateStartButton();
        this.updateLLMCard();
        this.updateProviderPill();
    }
    
    updateStatusPill() {
        const statusPill = document.getElementById('llm-status-pill');
        if (!statusPill) return;
        
        if (this.noLLMMode) {
            statusPill.textContent = 'LLM: Off';
            statusPill.className = 'status-pill status-off';
        } else if (this.llmStatus?.available) {
            statusPill.textContent = `LLM: ${this.llmStatus.provider}`;
            statusPill.className = 'status-pill status-connected';
        } else {
            statusPill.textContent = 'LLM: Not Configured';
            statusPill.className = 'status-pill status-error';
        }
    }
    
    updateStartButton() {
        const startButton = document.getElementById('start-build-btn');
        const tooltip = document.getElementById('start-button-tooltip');
        if (!startButton) return;
        
        const canStart = this.canStartBuild();
        startButton.disabled = !canStart;
        
        if (!canStart) {
            const reason = this.getStartButtonDisabledReason();
            tooltip.textContent = reason;
            tooltip.style.display = 'block';
        } else {
            tooltip.style.display = 'none';
        }
    }
    
    canStartBuild() {
        return this.noLLMMode || (this.llmStatus?.available && this.llmStatus.provider);
    }
    
    getStartButtonDisabledReason() {
        if (this.noLLMMode) {
            return 'No-LLM mode is enabled';
        }
        if (!this.llmStatus?.available) {
            return 'LLM provider not configured or validated';
        }
        return 'LLM provider not ready';
    }
    
    updateLLMCard() {
        const llmCard = document.getElementById('llm-provider-card');
        if (!llmCard) return;
        
        const noLLMToggle = document.getElementById('no-llm-toggle');
        const llmConfigSection = document.getElementById('llm-config-section');
        const dryRunSection = document.getElementById('dry-run-section');
        
        if (this.noLLMMode) {
            llmConfigSection.style.display = 'none';
            dryRunSection.style.display = 'none';
            noLLMToggle.checked = true;
        } else {
            llmConfigSection.style.display = 'block';
            dryRunSection.style.display = 'block';
            noLLMToggle.checked = false;
        }
    }
    
    updateProviderPill() {
        const providerPill = document.getElementById('provider-pill');
        if (!providerPill) return;
        
        if (this.noLLMMode) {
            providerPill.textContent = 'LLM: Off';
            providerPill.className = 'provider-pill provider-off';
        } else if (this.llmStatus?.available) {
            providerPill.textContent = `${this.llmStatus.provider}`;
            providerPill.className = 'provider-pill provider-connected';
        } else {
            providerPill.textContent = 'LLM: Error';
            providerPill.className = 'provider-pill provider-error';
        }
    }
    
    toggleNoLLMMode(enabled) {
        this.noLLMMode = enabled;
        this.updateUI();
        
        // Persist choice
        localStorage.setItem('sbh_no_llm_mode', enabled);
        
        // Show feedback
        this.showAlert(
            enabled ? 'No-LLM mode enabled. Builds will use templates only.' : 'LLM mode enabled.',
            'info'
        );
    }
    
    async testConnection() {
        const testBtn = document.getElementById('test-connection-btn');
        const apiKey = document.getElementById('llm-api-key')?.value;
        
        if (!apiKey?.trim()) {
            this.showAlert('Please enter an API key before testing', 'warning');
            return;
        }
        
        // Clear previous timeout
        if (this.testConnectionTimeout) {
            clearTimeout(this.testConnectionTimeout);
        }
        
        // Set loading state
        testBtn.disabled = true;
        testBtn.textContent = 'Testing...';
        this.isLoading = true;
        
        try {
            const response = await fetch('/api/llm/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    provider: document.getElementById('llm-provider-select')?.value,
                    api_key: apiKey,
                    model: document.getElementById('llm-model-input')?.value
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showAlert(
                    `Connection successful! Latency: ${result.latency_ms}ms`,
                    'success'
                );
                this.updateLLMStatus(result);
            } else {
                this.showAlert(
                    `Connection failed: ${result.error}`,
                    'error'
                );
            }
        } catch (error) {
            this.showAlert('Connection test failed. Please try again.', 'error');
        } finally {
            testBtn.disabled = false;
            testBtn.textContent = 'Test Connection';
            this.isLoading = false;
        }
    }
    
    async dryRunPrompt() {
        const dryRunBtn = document.getElementById('dry-run-btn');
        const modal = document.getElementById('dry-run-modal');
        const resultDiv = document.getElementById('dry-run-result');
        
        if (!this.llmStatus?.available) {
            this.showAlert('LLM provider not configured', 'warning');
            return;
        }
        
        // Show modal
        modal.style.display = 'block';
        resultDiv.innerHTML = '<div class="loading">Running dry-run prompt...</div>';
        
        try {
            const response = await fetch('/api/llm/dry-run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: 'echo ping'
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                resultDiv.innerHTML = `
                    <div class="dry-run-success">
                        <h4>Dry-Run Results</h4>
                        <p><strong>Response:</strong> ${result.content}</p>
                        <p><strong>Latency:</strong> ${result.latency_ms}ms</p>
                        <p><strong>Tokens Used:</strong> ${result.tokens_used || 'N/A'}</p>
                        <p><strong>Provider:</strong> ${result.provider}</p>
                        <p><strong>Model:</strong> ${result.model}</p>
                    </div>
                `;
            } else {
                resultDiv.innerHTML = `
                    <div class="dry-run-error">
                        <h4>Dry-Run Failed</h4>
                        <p><strong>Error:</strong> ${result.error}</p>
                    </div>
                `;
            }
        } catch (error) {
            resultDiv.innerHTML = `
                <div class="dry-run-error">
                    <h4>Dry-Run Failed</h4>
                    <p><strong>Error:</strong> ${error.message}</p>
                </div>
            `;
        }
    }
    
    async saveLLMProvider() {
        const saveBtn = document.getElementById('save-llm-btn');
        const provider = document.getElementById('llm-provider-select')?.value;
        const apiKey = document.getElementById('llm-api-key')?.value;
        const model = document.getElementById('llm-model-input')?.value;
        
        if (!provider || !apiKey || !model) {
            this.showAlert('Please fill in all LLM provider fields', 'warning');
            return;
        }
        
        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving...';
        
        try {
            const response = await fetch('/api/llm/provider/configure', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    provider,
                    api_key: apiKey,
                    default_model: model
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showAlert('LLM provider configured successfully!', 'success');
                await this.loadLLMStatus();
            } else {
                this.showAlert(`Failed to configure LLM provider: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showAlert('Failed to save LLM provider configuration', 'error');
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save Configuration';
        }
    }
    
    toggleAPIKeyVisibility() {
        const apiKeyInput = document.getElementById('llm-api-key');
        const revealBtn = document.getElementById('reveal-api-key');
        
        if (apiKeyInput.type === 'password') {
            apiKeyInput.type = 'text';
            revealBtn.textContent = 'Hide';
        } else {
            apiKeyInput.type = 'password';
            revealBtn.textContent = 'Reveal';
        }
    }
    
    async copyAPIKey() {
        const apiKeyInput = document.getElementById('llm-api-key');
        
        try {
            await navigator.clipboard.writeText(apiKeyInput.value);
            this.showAlert('API key copied to clipboard', 'success');
        } catch (error) {
            this.showAlert('Failed to copy API key', 'error');
        }
    }
    
    validateAPIKey() {
        const apiKeyInput = document.getElementById('llm-api-key');
        const apiKey = apiKeyInput.value;
        
        // Basic validation patterns
        const patterns = {
            'openai': /^sk-[a-zA-Z0-9]{48}$/,
            'anthropic': /^sk-ant-[a-zA-Z0-9]{48}$/,
            'groq': /^gsk_[a-zA-Z0-9]{48}$/
        };
        
        const provider = document.getElementById('llm-provider-select')?.value;
        const pattern = patterns[provider];
        
        if (pattern && !pattern.test(apiKey)) {
            apiKeyInput.classList.add('invalid');
            this.showAlert('Invalid API key format for selected provider', 'warning');
        } else {
            apiKeyInput.classList.remove('invalid');
        }
    }
    
    async submitBuild() {
        const startButton = document.getElementById('start-build-btn');
        const formData = new FormData(document.getElementById('build-form'));
        
        if (!this.canStartBuild()) {
            this.showAlert('Please configure LLM provider or enable No-LLM mode', 'warning');
            return;
        }
        
        startButton.disabled = true;
        startButton.textContent = 'Starting Build...';
        
        try {
            const buildData = {
                name: formData.get('project_name'),
                description: formData.get('project_description'),
                template_slug: formData.get('template_slug'),
                mode: formData.get('build_mode'),
                initial_prompt: formData.get('initial_prompt'),
                no_llm_mode: this.noLLMMode
            };
            
            const response = await fetch('/api/build/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(buildData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showAlert('Build started successfully!', 'success');
                // Redirect to visual builder
                window.location.href = `/ui/visual-builder?project=${result.project_id}`;
            } else {
                this.showAlert(`Failed to start build: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showAlert('Failed to start build', 'error');
        } finally {
            startButton.disabled = false;
            startButton.textContent = 'Start Building';
        }
    }
    
    updateLLMStatus(result) {
        this.llmStatus = {
            available: result.success,
            provider: result.provider,
            model: result.model,
            latency_ms: result.latency_ms
        };
        this.updateUI();
    }
    
    showAlert(message, type = 'info', duration = 5000) {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) return;
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `
            <span>${message}</span>
            <button class="alert-close" onclick="this.parentElement.remove()">&times;</button>
        `;
        
        alertContainer.appendChild(alert);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (alert.parentElement) {
                alert.remove();
            }
        }, duration);
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.buildWizard = new BuildWizardEnhanced();
});
