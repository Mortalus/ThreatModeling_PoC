/* ===== MAIN.JS - Master JavaScript Import and Initialization ===== */

/**
 * THREAT MODELING DASHBOARD - JAVASCRIPT ARCHITECTURE
 * * This file orchestrates the loading and initialization of all JavaScript modules
 * for the threat modeling application. Files are loaded in dependency order to
 * ensure proper initialization and component availability.
 * * Architecture:
 * 1. Core Utilities - Essential functions, constants, and utilities
 * 2. Infrastructure - Browser detection, performance monitoring, error handling
 * 3. UI Components - Reusable React components and utilities
 * 4. Feature Components - Specific functionality components
 * 5. Application - Main app component and initialization
 * * Total estimated size: ~200KB uncompressed (~60KB compressed)
 * Performance: Optimized for progressive loading and minimal blocking
 * * ENHANCED WITH: Async processing configuration and debug mode support
 */

(function(window, document, undefined) {
    'use strict';

    // ===== LOADING CONFIGURATION =====
    
    const SCRIPT_CONFIG = {
        baseUrl: 'js/', // Base directory for legacy scripts
        version: '1.0.0',
        loadTimeout: 30000, // 30 seconds
        retryAttempts: 3,
        retryDelay: 1000 // 1 second
    };

    // Define loading order and dependencies
    const SCRIPT_MODULES = [
        {
            name: 'Core Utilities',
            file: 'core-utilities.js',
            required: true,
            exports: ['CoreUtilities'],
            description: 'Essential utility functions and constants'
        },
        {
            name: 'UI Components',
            file: 'ui-components.js',
            required: true,
            exports: ['UIComponents', 'NotificationContainer'],
            dependencies: ['CoreUtilities'],
            description: 'Reusable UI components and utilities'
        },
        {
            name: 'Sidebar Components',
            file: 'sidebar-components.js',
            required: true,
            exports: ['SidebarComponents', 'CollapsibleSidebar'],
            dependencies: ['CoreUtilities', 'UIComponents'],
            description: 'Collapsible sidebar and navigation components'
        },
        {
            name: 'Pipeline Components',
            file: 'pipeline-components.js',
            required: true,
            exports: ['PipelineComponents', 'FileUploadComponent'],
            dependencies: ['CoreUtilities', 'UIComponents'],
            description: 'Pipeline-specific components and data viewers'
        },
        {
            name: 'Review System',
            file: 'review-system.js',
            required: true,
            exports: ['ReviewSystem', 'ReviewPanel'],
            dependencies: ['CoreUtilities', 'UIComponents', 'PipelineComponents'],
            description: 'Manual review queue and decision components'
        },
        {
            name: 'Main Application',
            file: 'main-app.js',
            required: true,
            exports: ['ThreatModelingApp'],
            dependencies: ['CoreUtilities', 'UIComponents', 'SidebarComponents', 'PipelineComponents', 'ReviewSystem'],
            description: 'Main application component and initialization'
        }
    ];

    // ===== LOADING STATE MANAGEMENT =====
    
    let loadingState = {
        loaded: new Set(),
        failed: new Set(),
        loading: new Set(),
        retryCount: new Map(),
        startTime: Date.now(),
        errors: []
    };

    // ===== ENHANCED CONFIGURATION STATE =====
    
    let currentConfig = {
        llm_provider: 'scaleway',
        llm_model: 'llama-3.3-70b-instruct',
        local_llm_endpoint: 'http://localhost:11434/api/generate',
        azure_endpoint: '',
        timeout: 5000,
        temperature: 0.2,
        max_tokens: 4096,
        // New async/performance options
        enable_async_processing: true,
        max_concurrent_calls: 5,
        detailed_llm_logging: true,
        // New debug options
        debug_mode: false,
        force_rule_based: false,
        verbose_error_reporting: true,
        // Existing feature flags
        enable_quality_check: true,
        enable_multi_pass: true,
        enable_mermaid: true,
        enable_llm_enrichment: true,
        mitre_enabled: true
    };

    // Enhanced Settings System Integration
    let settingsEnhanced = false;
    let enhancedSettingsModule = null;

    // ===== UTILITY FUNCTIONS =====

    /**
     * Load the enhanced settings module
     */
    async function loadEnhancedSettingsModule() {
        try {
            // Try to load the enhanced settings modules using absolute paths
            const modules = await Promise.all([
                import('./constants.js'),
                import('./storage.js'),
                import('./validation.js'),
                import('./integration.js')
            ]);
            
            enhancedSettingsModule = {
                constants: modules[0],
                storage: modules[1],
                validation: modules[2],
                integration: modules[3]
            };
            
            // Initialize the enhanced settings
            enhancedSettingsModule.integration.initializeSettings();
            settingsEnhanced = true;
            
            console.log('✅ Enhanced settings system loaded successfully');
            return true;
        } catch (error) {
            console.warn('⚠️ Enhanced settings not available, using legacy system:', error);
            return false;
        }
    }

    /**
     * Log loading progress with timestamp
     */
    function log(message, type = 'info') {
        const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
        const prefix = type === 'error' ? '❌' : type === 'warn' ? '⚠️' : '📦';
        console.log(`[${timestamp}] ${prefix} ${message}`);
    }

    /**
     * Update loading UI
     */
    function updateLoadingUI(message, progress = 0) {
        const messageElement = document.getElementById('loading-message');
        const progressElement = document.getElementById('loading-progress');
        const detailsElement = document.getElementById('loading-details');

        if (messageElement) messageElement.textContent = message;
        if (progressElement) progressElement.style.width = `${Math.min(progress, 100)}%`;
        if (detailsElement) {
            const elapsed = ((Date.now() - loadingState.startTime) / 1000).toFixed(1);
            detailsElement.textContent = `${loadingState.loaded.size}/${SCRIPT_MODULES.length} modules loaded (${elapsed}s)`;
        }
    }

    /**
     * Remove loading UI
     */
    function removeLoadingUI() {
        const loadingElement = document.getElementById('app-loading');
        if (loadingElement) {
            loadingElement.style.opacity = '0';
            loadingElement.style.transition = 'opacity 0.3s ease';
            setTimeout(() => {
                if (loadingElement.parentNode) {
                    loadingElement.parentNode.removeChild(loadingElement);
                }
            }, 300);
        }
    }

    /**
     * Check if dependencies are satisfied
     */
    function checkDependencies(module) {
        if (!module.dependencies) return true;
        
        return module.dependencies.every(dep => {
            const depModule = SCRIPT_MODULES.find(m => m.exports.includes(dep));
            return depModule && loadingState.loaded.has(depModule.file);
        });
    }

    /**
     * Check if module exports are available
     */
    function checkExports(module) {
        return module.exports.every(exportName => {
            const exists = window[exportName] !== undefined;
            if (!exists) {
                log(`Export '${exportName}' not found for module '${module.name}'`, 'warn');
            }
            return exists;
        });
    }

    /**
     * Load a single script module
     */
    function loadScript(module) {
        return new Promise((resolve, reject) => {
            if (loadingState.loaded.has(module.file)) {
                resolve(module);
                return;
            }

            if (loadingState.loading.has(module.file)) {
                // Already loading, wait for it
                const checkInterval = setInterval(() => {
                    if (loadingState.loaded.has(module.file)) {
                        clearInterval(checkInterval);
                        resolve(module);
                    } else if (loadingState.failed.has(module.file)) {
                        clearInterval(checkInterval);
                        reject(new Error(`Module ${module.name} failed to load`));
                    }
                }, 100);
                return;
            }

            loadingState.loading.add(module.file);
            log(`Loading ${module.name}...`);

            const script = document.createElement('script');
            script.src = `${SCRIPT_CONFIG.baseUrl}${module.file}?v=${SCRIPT_CONFIG.version}`;
            script.async = true;

            const timeout = setTimeout(() => {
                cleanup();
                reject(new Error(`Timeout loading ${module.name}`));
            }, SCRIPT_CONFIG.loadTimeout);

            function cleanup() {
                clearTimeout(timeout);
                script.removeEventListener('load', onLoad);
                script.removeEventListener('error', onError);
                loadingState.loading.delete(module.file);
            }

            function onLoad() {
                cleanup();
                
                // Verify exports are available
                setTimeout(() => {
                    if (checkExports(module)) {
                        loadingState.loaded.add(module.file);
                        log(`✅ ${module.name} loaded successfully`);
                        resolve(module);
                    } else {
                        loadingState.failed.add(module.file);
                        reject(new Error(`Module ${module.name} exports not found`));
                    }
                }, 10); // Small delay to ensure exports are registered
            }

            function onError() {
                cleanup();
                loadingState.failed.add(module.file);
                reject(new Error(`Failed to load ${module.name}`));
            }

            script.addEventListener('load', onLoad);
            script.addEventListener('error', onError);
            document.head.appendChild(script);
        });
    }

    /**
     * Retry loading a module
     */
    async function retryLoad(module) {
        const retryCount = loadingState.retryCount.get(module.file) || 0;
        
        if (retryCount >= SCRIPT_CONFIG.retryAttempts) {
            throw new Error(`Max retry attempts reached for ${module.name}`);
        }

        loadingState.retryCount.set(module.file, retryCount + 1);
        loadingState.failed.delete(module.file);
        
        log(`Retrying ${module.name} (attempt ${retryCount + 1}/${SCRIPT_CONFIG.retryAttempts})...`, 'warn');
        
        await new Promise(resolve => setTimeout(resolve, SCRIPT_CONFIG.retryDelay));
        return loadScript(module);
    }

    /**
     * Load all modules in dependency order
     */
    async function loadAllModules() {
        const toLoad = [...SCRIPT_MODULES];
        const loaded = [];

        while (toLoad.length > 0) {
            // Find modules that can be loaded (dependencies satisfied)
            const readyModules = toLoad.filter(module => checkDependencies(module));
            
            if (readyModules.length === 0) {
                const remaining = toLoad.map(m => m.name).join(', ');
                throw new Error(`Dependency deadlock. Remaining: ${remaining}`);
            }

            // Load ready modules in parallel
            const promises = readyModules.map(async (module) => {
                try {
                    return await loadScript(module);
                } catch (error) {
                    if (module.required) {
                        // Try to retry required modules
                        try {
                            return await retryLoad(module);
                        } catch (retryError) {
                            throw new Error(`Required module ${module.name} failed to load: ${retryError.message}`);
                        }
                    } else {
                        log(`Optional module ${module.name} failed to load: ${error.message}`, 'warn');
                        return null; // Mark as handled
                    }
                }
            });

            const results = await Promise.allSettled(promises);
            
            // Process results
            for (let i = 0; i < results.length; i++) {
                const result = results[i];
                const module = readyModules[i];
                
                if (result.status === 'fulfilled' && result.value) {
                    loaded.push(result.value);
                    toLoad.splice(toLoad.indexOf(module), 1);
                } else if (result.status === 'rejected' && module.required) {
                    throw result.reason;
                } else {
                    // Optional module failed, remove from queue
                    toLoad.splice(toLoad.indexOf(module), 1);
                }
            }

            // Update progress
            const progress = (loaded.length / SCRIPT_MODULES.length) * 100;
            updateLoadingUI(`Loaded ${loaded.length}/${SCRIPT_MODULES.length} modules...`, progress);
        }

        return loaded;
    }

    // ===== ENHANCED CONFIGURATION FUNCTIONS =====

    function loadSettings() {
        try {
            const saved = localStorage.getItem('threat_modeling_config');
            if (saved) {
                const config = JSON.parse(saved);
                currentConfig = { ...currentConfig, ...config };
                
                // Update form fields
                updateFormFromConfig();
                console.log('✅ Loaded saved configuration');
            }
        } catch (error) {
            console.error('❌ Error loading saved configuration:', error);
        }
    }

    function updateFormFromConfig() {
        // LLM Configuration
        setFieldValue('llm-provider', currentConfig.llm_provider);
        setFieldValue('llm-model', currentConfig.llm_model);
        setFieldValue('local-endpoint', currentConfig.local_llm_endpoint);
        setFieldValue('azure-endpoint', currentConfig.azure_endpoint);
        
        // Processing Parameters
        setFieldValue('timeout', currentConfig.timeout);
        setFieldValue('temperature', currentConfig.temperature);
        setFieldValue('max-tokens', currentConfig.max_tokens);
        
        // Async/Performance Options
        setFieldValue('enable-async-processing', currentConfig.enable_async_processing);
        setFieldValue('max-concurrent-calls', currentConfig.max_concurrent_calls);
        setFieldValue('detailed-llm-logging', currentConfig.detailed_llm_logging);
        
        // Debug Options
        setFieldValue('debug-mode', currentConfig.debug_mode);
        setFieldValue('force-rule-based', currentConfig.force_rule_based);
        setFieldValue('verbose-error-reporting', currentConfig.verbose_error_reporting);
        
        // Feature Flags
        setFieldValue('enable-quality-check', currentConfig.enable_quality_check);
        setFieldValue('enable-multi-pass', currentConfig.enable_multi_pass);
        setFieldValue('enable-mermaid', currentConfig.enable_mermaid);
        setFieldValue('enable-llm-enrichment', currentConfig.enable_llm_enrichment);
        setFieldValue('mitre-enabled', currentConfig.mitre_enabled);

        // Update conditional UI elements after loading config from storage
        updateProviderFields();
        updateAsyncFields();
        updateDebugFields();
    }

    function setFieldValue(fieldId, value) {
        const field = document.getElementById(fieldId);
        if (field) {
            if (field.type === 'checkbox') {
                field.checked = Boolean(value);
            } else {
                field.value = value;
            }
        }
    }

    function getFieldValue(fieldId) {
        const field = document.getElementById(fieldId);
        if (field) {
            if (field.type === 'checkbox') {
                return field.checked;
            } else if (field.type === 'number') {
                return Number(field.value);
            } else {
                return field.value;
            }
        }
        return null;
    }

    /**
     * Enhanced provider fields update with Azure support
     */
    function updateProviderFields() {
        const provider = document.getElementById('llm-provider')?.value;
        const localEndpointGroup = document.getElementById('local-endpoint-group');
        const azureEndpointGroup = document.getElementById('azure-endpoint-group');
        
        if (!provider) return;
        
        // Hide all provider-specific fields first
        if (localEndpointGroup) localEndpointGroup.style.display = 'none';
        if (azureEndpointGroup) azureEndpointGroup.style.display = 'none';
        
        // Show relevant fields based on provider
        switch(provider) {
            case 'ollama':
                if (localEndpointGroup) localEndpointGroup.style.display = 'block';
                break;
            case 'azure':
                if (azureEndpointGroup) azureEndpointGroup.style.display = 'block';
                break;
            case 'scaleway':
                // No additional fields needed as API key is handled server-side or via env
                break;
        }
        
        // Update model dropdown
        updateModelOptions(provider);
    }

    /**
     * Update model options based on provider
     */
    function updateModelOptions(provider) {
        const modelSelect = document.getElementById('llm-model');
        if (!modelSelect) return;
        
        const models = {
            scaleway: [
                'llama-3.3-70b-instruct',
                'llama-3.1-8b-instruct',
                'llama-3.1-70b-instruct',
                'mistral-nemo-instruct-2407'
            ],
            azure: [
                'gpt-4',
                'gpt-4-turbo',
                'gpt-35-turbo',
                'gpt-4o'
            ],
            ollama: [
                'llama3.3:latest',
                'llama3.2:latest',
                'llama3.1:latest',
                'mistral:latest',
                'mixtral:latest',
                'codellama:latest',
                'phi3:latest'
            ]
        };
        
        // Clear current options
        modelSelect.innerHTML = '';
        
        // Add new options
        const providerModels = models[provider] || [];
        providerModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            modelSelect.appendChild(option);
        });
        
        // Set current or default model
        if (currentConfig.llm_provider === provider && providerModels.includes(currentConfig.llm_model)) {
            modelSelect.value = currentConfig.llm_model;
        } else if (providerModels.length > 0) {
            modelSelect.value = providerModels[0];
        }
    }

    function updateAsyncFields() {
        const asyncEnabled = getFieldValue('enable-async-processing');
        const maxConcurrentField = document.getElementById('max-concurrent-calls');
        const maxConcurrentGroup = maxConcurrentField?.closest('.form-group');
        
        if (maxConcurrentGroup) {
            maxConcurrentGroup.style.opacity = asyncEnabled ? '1' : '0.5';
            if (maxConcurrentField) maxConcurrentField.disabled = !asyncEnabled;
        }
    }

    function updateDebugFields() {
        const debugMode = getFieldValue('debug-mode');
        const forceRuleBased = getFieldValue('force-rule-based');
        
        // If force rule-based is enabled, some other options become irrelevant
        const affectedFields = ['enable-async-processing', 'max-concurrent-calls', 'detailed-llm-logging', 'enable-llm-enrichment'];
        
        affectedFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            const group = field?.closest('.form-group') || field?.closest('.checkbox-group');
            if (group) {
                group.style.opacity = forceRuleBased ? '0.5' : '1';
                if (field) {
                    field.disabled = forceRuleBased;
                }
            }
        });
        
        // Update help text based on debug mode
        const debugHelp = document.querySelector('#debug-mode + label + .form-help');
        if (debugHelp && debugMode) {
            debugHelp.style.color = '#f59e0b';
            debugHelp.style.fontWeight = '500';
        } else if (debugHelp) {
            debugHelp.style.color = '';
            debugHelp.style.fontWeight = '';
        }
    }

    function validateConfiguration(config) {
        const errors = [];
        
        // Validate numeric ranges
        if (config.timeout < 60 || config.timeout > 10000) {
            errors.push('Timeout must be between 60 and 10000 seconds');
        }
        
        if (config.temperature < 0 || config.temperature > 1) {
            errors.push('Temperature must be between 0 and 1');
        }
        
        if (config.max_tokens < 1000 || config.max_tokens > 8192) {
            errors.push('Max tokens must be between 1000 and 8192');
        }
        
        if (config.max_concurrent_calls < 1 || config.max_concurrent_calls > 20) {
            errors.push('Max concurrent calls must be between 1 and 20');
        }
        
        // Validate logical combinations
        if (config.force_rule_based && config.enable_async_processing) {
            console.warn('⚠️ Async processing is less beneficial with force rule-based mode');
        }
        
        return errors;
    }

    // Replace the saveSettings function in main.js with this version

// Replace the saveSettings function in main.js with this version

function saveSettings() {
    try {
        const newConfig = {
            // LLM Configuration
            llm_provider: getFieldValue('llm-provider'),
            llm_model: getFieldValue('llm-model'),
            local_llm_endpoint: getFieldValue('local-llm-endpoint'),
            temperature: parseFloat(getFieldValue('temperature')),
            max_tokens: parseInt(getFieldValue('max-tokens')),
            
            // Processing Options
            timeout: parseInt(getFieldValue('timeout')),
            enable_async_processing: getFieldValue('enable-async'),
            max_concurrent_calls: parseInt(getFieldValue('max-concurrent-calls')),
            detailed_llm_logging: getFieldValue('detailed-logging'),
            
            // Debug Options
            debug_mode: getFieldValue('debug-mode'),
            force_rule_based: getFieldValue('force-rule-based'),
            verbose_error_reporting: getFieldValue('verbose-error-reporting'),
            
            // Feature Flags
            enable_quality_check: getFieldValue('enable-quality-check'),
            enable_multi_pass: getFieldValue('enable-multi-pass'),
            enable_mermaid: getFieldValue('enable-mermaid'),
            enable_llm_enrichment: getFieldValue('enable-llm-enrichment'),
            mitre_enabled: getFieldValue('mitre-enabled')
        };
        
        // Validate configuration
        const validationErrors = validateConfiguration(newConfig);
        if (validationErrors.length > 0) {
            alert('Configuration errors:\n' + validationErrors.join('\n'));
            return;
        }
        
        // Update current config
        currentConfig = { ...currentConfig, ...newConfig };
        
        // Save to localStorage
        localStorage.setItem('threat_modeling_config', JSON.stringify(currentConfig));
        
        // Send to backend
        const apiUrl = `${window.CoreUtilities.API_BASE}/config`;
        console.log('About to fetch:', apiUrl);
        console.log('Full URL should be:', apiUrl);
        fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentConfig)
        })
        .then(response => {
            // Check if response is ok before trying to parse JSON
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Check content type
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                return response.json();
            } else {
                throw new Error("Response is not JSON");
            }
        })
        .then(data => {
            console.log('✅ Configuration saved successfully');
            showNotification('Settings saved successfully!', 'success');
            closeSettingsModal();
        })
        .catch(error => {
            console.error('❌ Error saving configuration:', error);
            // Still save locally even if backend fails
            showNotification('Settings saved locally (backend error)', 'warning');
            closeSettingsModal();
        });
        
    } catch (error) {
        console.error('❌ Error in saveSettings:', error);
        showNotification('Error saving settings: ' + error.message, 'error');
    }
}

    function showNotification(message, type = 'info') {
        const container = document.getElementById('notification-container') || document.body;
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()" style="background:none;border:none;color:inherit;font-size:1.2em;cursor:pointer;margin-left:10px;">&times;</button>
        `;
        
        container.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    function openSettingsModal() {
        if (settingsEnhanced && window.openEnhancedSettingsModal) {
            // Use enhanced settings if available
            window.openEnhancedSettingsModal();
        } else {
            // Fall back to existing modal
            const modal = document.getElementById('settingsModal');
            if (modal) {
                modal.style.display = 'flex';
                updateProviderFields();
                updateAsyncFields();
                updateDebugFields();
            }
        }
    }

    function closeSettingsModal() {
        if (settingsEnhanced && window.closeEnhancedSettingsModal) {
            // Use enhanced settings if available
            window.closeEnhancedSettingsModal();
        } else {
            // Fall back to existing modal
            const modal = document.getElementById('settingsModal');
            if (modal) {
                modal.style.display = 'none';
            }
        }
    }

    /**
     * Initialize the application after all modules are loaded
     */
    function initializeApplication() {
        updateLoadingUI('Initializing application...', 95);

        // Verify core dependencies
        const requiredGlobals = ['React', 'ReactDOM'];
        const missingGlobals = requiredGlobals.filter(name => !window[name]);
        
        if (missingGlobals.length > 0) {
            throw new Error(`Missing required global dependencies: ${missingGlobals.join(', ')}`);
        }

        // Verify our modules are available
        const requiredModules = ['CoreUtilities', 'UIComponents', 'SidebarComponents', 'PipelineComponents', 'ReviewSystem', 'ThreatModelingApp'];
        const missingModules = requiredModules.filter(name => !window[name]);
        
        if (missingModules.length > 0) {
            throw new Error(`Missing required modules: ${missingModules.join(', ')}`);
        }

        // Initialize configuration management
        loadSettings();


        // Set up event listeners for configuration
        document.addEventListener('change', function(event) {
            const fieldId = event.target.id;
            
            if (fieldId === 'llm-provider') {
                updateProviderFields();
            } else if (fieldId === 'enable-async-processing') {
                updateAsyncFields();
            } else if (fieldId === 'debug-mode' || fieldId === 'force-rule-based') {
                updateDebugFields();
            }
        });

        // Close modal when clicking outside
        document.addEventListener('click', function(event) {
            const modal = document.getElementById('settingsModal');
            if (event.target === modal) {
                closeSettingsModal();
            }
        });

        // Mount the React application
        updateLoadingUI('Mounting React application...', 98);
        
        try {
            const rootElement = document.getElementById('root');
            if (!rootElement) {
                throw new Error('Root element not found');
            }

            // Create React root and render
            const root = ReactDOM.createRoot(rootElement);
            root.render(React.createElement(window.ThreatModelingApp));
            
            log('✅ Application initialized successfully');
            
            // Remove loading UI after a brief delay
            setTimeout(() => {
                removeLoadingUI();
            }, 500);
            
        } catch (error) {
            throw new Error(`Failed to mount React application: ${error.message}`);
        }
    }

    /**
     * Handle initialization errors
     */
    function handleInitializationError(error) {
        log(`Initialization failed: ${error.message}`, 'error');
        
        // Update UI to show error
        updateLoadingUI('Initialization failed', 100);
        
        const messageElement = document.getElementById('loading-message');
        if (messageElement) {
            messageElement.textContent = `❌ ${error.message}`;
            messageElement.style.color = '#ef4444';
        }
        
        // Log detailed error for debugging
        console.error('Detailed error:', error);
        loadingState.errors.push(error);
        
        // Show retry option
        setTimeout(() => {
            const loadingElement = document.getElementById('app-loading');
            if (loadingElement) {
                const retryButton = document.createElement('button');
                retryButton.textContent = 'Retry';
                retryButton.style.cssText = 'margin-top: 20px; padding: 10px 20px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer;';
                retryButton.onclick = () => location.reload();
                loadingElement.appendChild(retryButton);
            }
        }, 1000);
    }

    // ===== MAIN INITIALIZATION =====

    /**
     * Start the application loading process
     */
    async function startApplication() {
        try {
            log('🚀 Starting Threat Modeling Dashboard...');
            
            // Load all JavaScript modules
            updateLoadingUI('Loading modules...', 10);
            await loadAllModules();
            
            // Initialize the application
            initializeApplication();
            
            const totalTime = ((Date.now() - loadingState.startTime) / 1000).toFixed(2);
            log(`✅ Application loaded successfully in ${totalTime}s`);
            
        } catch (error) {
            handleInitializationError(error);
        }
    }

    // ===== EXPOSE GLOBAL FUNCTIONS =====
    
    // Expose configuration functions globally under a single namespace
    window.ThreatModelingConfig = {
        currentConfig,
        saveSettings,
        loadSettings,
        validateConfiguration,
        showNotification,
        openSettingsModal,
        closeSettingsModal,
        updateProviderFields,
        updateAsyncFields,
        updateDebugFields
    };

    // Export loading utilities for debugging
    window.ThreatModelingLoader = {
        loadingState,
        SCRIPT_MODULES,
        SCRIPT_CONFIG,
        startApplication, // Expose the main start function
        log
    };
    
    
    // Add event listeners for settings modal buttons
    document.getElementById('open-settings-button').addEventListener('click', openSettingsModal);
    document.getElementById('close-settings-button').addEventListener('click', closeSettingsModal);
    document.getElementById('save-settings-button').addEventListener('click', saveSettings);
    document.getElementById('cancel-settings-button').addEventListener('click', closeSettingsModal);


    // ===== START APPLICATION =====
    
    // Add CSS for notifications
    const notificationCSS = `
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        display: flex;
        align-items: center;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    }

    .notification-success { background: #10b981; color: white; }
    .notification-error { background: #ef4444; color: white; }
    .notification-info { background: #3b82f6; color: white; }
    .notification-warning { background: #f59e0b; color: white; }

    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    `;

    // Inject CSS only if not already present
    if (!document.querySelector('#notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = notificationCSS;
        document.head.appendChild(style);
    }

    // Start loading when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startApplication);
    } else {
        startApplication();
    }

})(window, document);