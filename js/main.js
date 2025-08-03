/* ===== MAIN.JS - Master JavaScript Import and Initialization ===== */

/**
 * THREAT MODELING DASHBOARD - JAVASCRIPT ARCHITECTURE
 * 
 * This file orchestrates the loading and initialization of all JavaScript modules
 * for the threat modeling application. Files are loaded in dependency order to
 * ensure proper initialization and component availability.
 * 
 * Architecture:
 * 1. Core Utilities - Essential functions, constants, and utilities
 * 2. Infrastructure - Browser detection, performance monitoring, error handling
 * 3. UI Components - Reusable React components and utilities
 * 4. Feature Components - Specific functionality components
 * 5. Application - Main app component and initialization
 * 
 * Total estimated size: ~200KB uncompressed (~60KB compressed)
 * Performance: Optimized for progressive loading and minimal blocking
 */

(function(window, document, undefined) {
    'use strict';

    // ===== LOADING CONFIGURATION =====
    
    const SCRIPT_CONFIG = {
        baseUrl: 'js/', // Empty string since all files are in the same js/ directory
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

    // ===== UTILITY FUNCTIONS =====

    /**
     * Log loading progress with timestamp
     */
    function log(message, type = 'info') {
        const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
        const prefix = `[${timestamp}] [ThreatModeling]`;
        
        switch (type) {
            case 'error':
                console.error(`${prefix} ❌ ${message}`);
                break;
            case 'warn':
                console.warn(`${prefix} ⚠️ ${message}`);
                break;
            case 'success':
                console.log(`${prefix} ✅ ${message}`);
                break;
            case 'info':
            default:
                console.log(`${prefix} ℹ️ ${message}`);
                break;
        }
    }

    /**
     * Show loading progress in UI
     */
    function updateLoadingUI(message, progress = 0) {
        let loadingElement = document.getElementById('app-loading');
        
        if (!loadingElement) {
            loadingElement = document.createElement('div');
            loadingElement.id = 'app-loading';
            loadingElement.innerHTML = `
                <div style="
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(135deg, #0a0e1a 0%, #1a1f2e 100%);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    color: #e0e0e0;
                ">
                    <div style="text-align: center; max-width: 400px; padding: 40px;">
                        <div style="
                            width: 60px;
                            height: 60px;
                            border: 4px solid #2d3548;
                            border-top: 4px solid #8b5cf6;
                            border-radius: 50%;
                            animation: spin 1s linear infinite;
                            margin: 0 auto 30px;
                        "></div>
                        <h2 style="
                            font-size: 1.5em;
                            margin-bottom: 10px;
                            background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
                            -webkit-background-clip: text;
                            background-clip: text;
                            -webkit-text-fill-color: transparent;
                        ">🛡️ Advanced Threat Modeling</h2>
                        <div id="loading-message" style="
                            font-size: 1em;
                            margin-bottom: 20px;
                            min-height: 1.2em;
                        ">Initializing...</div>
                        <div style="
                            width: 100%;
                            height: 4px;
                            background: #2d3548;
                            border-radius: 2px;
                            overflow: hidden;
                        ">
                            <div id="loading-progress" style="
                                height: 100%;
                                background: linear-gradient(90deg, #8b5cf6 0%, #3b82f6 100%);
                                width: 0%;
                                transition: width 0.3s ease;
                            "></div>
                        </div>
                        <div id="loading-details" style="
                            font-size: 0.8em;
                            color: #9ca3af;
                            margin-top: 15px;
                            min-height: 1em;
                        "></div>
                    </div>
                </div>
                <style>
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                </style>
            `;
            document.body.appendChild(loadingElement);
        }

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
            const fullPath = SCRIPT_CONFIG.baseUrl + module.file;
            log(`Loading ${module.name} from: ${fullPath}`);
            updateLoadingUI(`Loading ${module.name}...`, (loadingState.loaded.size / SCRIPT_MODULES.length) * 100);

            const script = document.createElement('script');
            script.src = fullPath;
            script.async = true;
            script.defer = true;

            const timeout = setTimeout(() => {
                cleanup();
                handleError(new Error(`Timeout loading ${module.name} from ${fullPath}`));
            }, SCRIPT_CONFIG.loadTimeout);

            function cleanup() {
                clearTimeout(timeout);
                loadingState.loading.delete(module.file);
                if (script.parentNode) {
                    script.parentNode.removeChild(script);
                }
            }

            function handleError(error) {
                cleanup();
                loadingState.failed.add(module.file);
                loadingState.errors.push({ module: module.name, error: error.message });
                log(`Failed to load ${module.name}: ${error.message}`, 'error');
                reject(error);
            }

            function handleSuccess() {
                cleanup();
                
                // Small delay to ensure script has executed
                setTimeout(() => {
                    // Verify exports are available
                    if (!checkExports(module)) {
                        handleError(new Error(`Exports not available for ${module.name}`));
                        return;
                    }

                    loadingState.loaded.add(module.file);
                    loadingState.loading.delete(module.file);
                    log(`Successfully loaded ${module.name}`, 'success');
                    resolve(module);
                }, 50);
            }

            script.onload = handleSuccess;
            script.onerror = (event) => {
                log(`Script error for ${module.name}: ${event.message || 'Unknown error'}`, 'error');
                handleError(new Error(`Script load error: ${event.message || 'Failed to load script'}`));
            };

            document.head.appendChild(script);
        });
    }

    /**
     * Retry loading a failed module
     */
    async function retryLoad(module) {
        const retryCount = loadingState.retryCount.get(module.file) || 0;
        
        if (retryCount >= SCRIPT_CONFIG.retryAttempts) {
            throw new Error(`Max retry attempts reached for ${module.name}`);
        }

        loadingState.retryCount.set(module.file, retryCount + 1);
        loadingState.failed.delete(module.file);
        
        log(`Retrying ${module.name} (attempt ${retryCount + 1}/${SCRIPT_CONFIG.retryAttempts})`, 'warn');
        
        await new Promise(resolve => setTimeout(resolve, SCRIPT_CONFIG.retryDelay));
        return loadScript(module);
    }

    /**
     * Load modules in dependency order
     */
    async function loadModules() {
        const toLoad = [...SCRIPT_MODULES];
        const loaded = [];

        updateLoadingUI('Checking dependencies...', 0);

        while (toLoad.length > 0) {
            const readyModules = toLoad.filter(module => checkDependencies(module));
            
            if (readyModules.length === 0) {
                const remaining = toLoad.map(m => m.name).join(', ');
                throw new Error(`Circular dependency detected or missing dependencies. Remaining: ${remaining}`);
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
        const requiredModules = ['CoreUtilities', 'UIComponents', 'SidebarComponents', 'PipelineComponents', 'ReviewSystem'];
        const missingModules = requiredModules.filter(name => !window[name]);
        
        if (missingModules.length > 0) {
            throw new Error(`Missing required modules: ${missingModules.join(', ')}`);
        }

        log('All modules loaded successfully', 'success');
        updateLoadingUI('Starting application...', 100);

        // Initialize core utilities first
        if (window.CoreUtilities && window.CoreUtilities.initializeCoreUtilities) {
            window.CoreUtilities.initializeCoreUtilities();
        }

        // Initialize the main application
        setTimeout(() => {
            removeLoadingUI();
            
            if (window.ThreatModelingApp && window.ThreatModelingApp.initializeApp) {
                window.ThreatModelingApp.initializeApp();
            } else {
                log('ThreatModelingApp not available, falling back to manual initialization', 'warn');
                // Fallback initialization code could go here
            }
        }, 300);
    }

    /**
     * Handle loading errors
     */
    function handleLoadingError(error) {
        log(`Application loading failed: ${error.message}`, 'error');
        
        const errorDetails = loadingState.errors.length > 0 
            ? `\n\nDetails:\n${loadingState.errors.map(e => `- ${e.module}: ${e.error}`).join('\n')}`
            : '';

        const errorHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(135deg, #1a0000 0%, #2d0000 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                color: #ff6b6b;
                padding: 20px;
            ">
                <div style="text-align: center; max-width: 600px;">
                    <div style="font-size: 4em; margin-bottom: 20px;">❌</div>
                    <h1 style="font-size: 2em; margin-bottom: 15px; color: #ff4757;">Application Load Error</h1>
                    <p style="font-size: 1.1em; margin-bottom: 20px; line-height: 1.5;">
                        Failed to load the threat modeling application.
                    </p>
                    <details style="text-align: left; background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                        <summary style="cursor: pointer; font-weight: bold;">Technical Details</summary>
                        <pre style="margin-top: 10px; font-size: 0.9em; color: #ffcccc;">${error.message}${errorDetails}</pre>
                    </details>
                    <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                        <button onclick="location.reload()" style="
                            padding: 12px 24px;
                            background: #ff4757;
                            color: white;
                            border: none;
                            border-radius: 6px;
                            cursor: pointer;
                            font-size: 1em;
                            font-weight: 600;
                        ">Reload Page</button>
                        <button onclick="localStorage.clear(); location.reload()" style="
                            padding: 12px 24px;
                            background: #ffa502;
                            color: white;
                            border: none;
                            border-radius: 6px;
                            cursor: pointer;
                            font-size: 1em;
                            font-weight: 600;
                        ">Clear Cache & Reload</button>
                    </div>
                </div>
            </div>
        `;

        document.body.innerHTML = errorHTML;
    }

    // ===== MAIN LOADING PROCESS =====

    /**
     * Main application loading function
     */
    async function loadApplication() {
        try {
            log('Starting application loading process...', 'info');
            log(`Loading ${SCRIPT_MODULES.length} modules...`, 'info');

            const loadedModules = await loadModules();
            
            log(`Successfully loaded ${loadedModules.length} modules`, 'success');
            
            await initializeApplication();
            
            const totalTime = ((Date.now() - loadingState.startTime) / 1000).toFixed(2);
            log(`Application loaded successfully in ${totalTime}s`, 'success');
            
        } catch (error) {
            handleLoadingError(error);
        }
    }

    // ===== AUTO-START =====

    // Start loading when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadApplication);
    } else {
        // DOM is already ready
        loadApplication();
    }

    // ===== GLOBAL EXPORTS =====

    // Export loading utilities for debugging
    window.ThreatModelingLoader = {
        loadingState,
        SCRIPT_MODULES,
        SCRIPT_CONFIG,
        loadApplication,
        log
    };

})(window, document);