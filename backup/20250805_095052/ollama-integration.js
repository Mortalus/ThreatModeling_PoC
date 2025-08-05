/**
 * Ollama Integration Utilities
 */
window.OllamaIntegration = {
    /**
     * Fetch available models from Ollama instance
     */
    fetchModels: async function() {
        try {
            const response = await fetch('/api/ollama/models');
            const data = await response.json();
            
            if (data.status === 'success') {
                return {
                    success: true,
                    models: data.models,
                    endpoint: data.endpoint
                };
            } else {
                return {
                    success: false,
                    error: data.error || 'Failed to fetch models',
                    details: data.details
                };
            }
        } catch (error) {
            console.error('Failed to fetch Ollama models:', error);
            return {
                success: false,
                error: 'Network error',
                details: error.message
            };
        }
    },

    /**
     * Update the model dropdown with fetched models
     */
    updateModelDropdown: function(selectElement, models) {
        // Clear existing options
        selectElement.innerHTML = '';
        
        if (!models || models.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No models available';
            selectElement.appendChild(option);
            return;
        }
        
        // Add model options
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = `${model.name} (${this.formatSize(model.size)})`;
            selectElement.appendChild(option);
        });
    },

    /**
     * Format file size in human readable format
     */
    formatSize: function(bytes) {
        if (!bytes) return 'Unknown size';
        
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    },

    /**
     * Test connection to Ollama
     */
    testConnection: async function(endpoint) {
        try {
            const baseUrl = endpoint.replace('/api/generate', '').rstrip('/');
            const response = await fetch(`${baseUrl}/api/tags`, {
                method: 'GET',
                timeout: 5000
            });
            
            return response.ok;
        } catch (error) {
            return false;
        }
    },

    /**
     * Initialize Ollama integration in settings modal
     */
    initializeInSettings: function() {
        // Listen for provider changes
        const providerSelect = document.querySelector('#llm-provider');
        if (providerSelect) {
            providerSelect.addEventListener('change', async (e) => {
                if (e.target.value === 'ollama') {
                    await this.refreshOllamaModels();
                }
            });
        }

        // Add refresh button for Ollama models
        const modelGroup = document.querySelector('#llm-model')?.closest('.form-group');
        if (modelGroup) {
            const refreshBtn = document.createElement('button');
            refreshBtn.className = 'btn btn-sm btn-secondary refresh-ollama-models';
            refreshBtn.innerHTML = '🔄 Refresh Models';
            refreshBtn.style.display = 'none';
            refreshBtn.onclick = () => this.refreshOllamaModels();
            
            modelGroup.appendChild(refreshBtn);
        }
    },

    /**
     * Refresh Ollama models
     */
    refreshOllamaModels: async function() {
        const modelSelect = document.querySelector('#llm-model');
        const refreshBtn = document.querySelector('.refresh-ollama-models');
        const providerSelect = document.querySelector('#llm-provider');
        
        if (!modelSelect || providerSelect?.value !== 'ollama') return;
        
        // Show loading state
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '⏳ Loading...';
        }
        
        modelSelect.disabled = true;
        const originalValue = modelSelect.value;
        
        try {
            const result = await this.fetchModels();
            
            if (result.success) {
                this.updateModelDropdown(modelSelect, result.models);
                
                // Try to restore original selection if it exists
                if (originalValue && result.models.some(m => m.name === originalValue)) {
                    modelSelect.value = originalValue;
                }
                
                // Show success notification
                if (window.showNotification) {
                    window.showNotification('success', `Found ${result.models.length} Ollama models`);
                }
            } else {
                // Show error
                if (window.showNotification) {
                    window.showNotification('error', result.error, result.details);
                }
                
                // Add error option
                modelSelect.innerHTML = '<option value="">Error loading models</option>';
            }
        } finally {
            // Restore button state
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '🔄 Refresh Models';
                refreshBtn.style.display = providerSelect?.value === 'ollama' ? 'inline-block' : 'none';
            }
            
            modelSelect.disabled = false;
        }
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.OllamaIntegration.initializeInSettings();
});

// Also hook into settings modal open event if using React
if (window.SettingsModalEvents) {
    window.SettingsModalEvents.on('open', () => {
        const providerSelect = document.querySelector('#llm-provider');
        if (providerSelect?.value === 'ollama') {
            window.OllamaIntegration.refreshOllamaModels();
        }
    });
}