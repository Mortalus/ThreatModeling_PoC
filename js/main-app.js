/* ===== MAIN-APP.JS - Main Application Component ===== */

/**
 * Main React application component that orchestrates all other components.
 * Includes state management, API calls, and component coordination.
 */

// ===== MAIN APP COMPONENT =====

/**
 * Main application component
 * @returns {JSX.Element} Main app component
 */
const App = () => {
    // ===== STATE MANAGEMENT =====
    
    const [pipelineState, setPipelineState] = React.useState({
        steps: [
            { id: 0, name: 'Document Upload', status: 'pending', data: null, percentage: 0 },
            { id: 1, name: 'DFD Extraction', status: 'pending', data: null, percentage: 0 },
            { id: 2, name: 'Threat Identification', status: 'pending', data: null, percentage: 0 },
            { id: 3, name: 'Threat Refinement', status: 'pending', data: null, percentage: 0 },
            { id: 4, name: 'Attack Path Analysis', status: 'pending', data: null, percentage: 0 }
        ]
    });
    
    const [currentStep, setCurrentStep] = React.useState(0);
    const [loading, setLoading] = React.useState(false);
    const [currentOperation, setCurrentOperation] = React.useState('');
    const [reviewQueue, setReviewQueue] = React.useState([]);
    const [showReviewPanel, setShowReviewPanel] = React.useState(false);
    const [modelConfig, setModelConfig] = React.useState(null);
    const [connectionStatus, setConnectionStatus] = React.useState('disconnected');
    
    // ===== REFS AND INTERVALS =====
    
    const progressIntervalRef = React.useRef(null);
    const socket = React.useMemo(() => {
        if (typeof io !== 'undefined') {
            return io(window.CoreUtilities?.WS_BASE || window.location.origin.replace(/^http/, 'ws'));
        }
        return null;
    }, []);

    // ===== COMPUTED VALUES =====
    
    const pendingReviewCount = React.useMemo(() => {
        return reviewQueue.filter(item => item.status === 'pending').length;
    }, [reviewQueue]);

    const isStepAccessible = React.useCallback((stepIndex) => {
        if (stepIndex === 0) return true;
        return pipelineState.steps[stepIndex - 1].status === 'completed';
    }, [pipelineState.steps]);

    // ===== API FUNCTIONS =====

    /**
     * Update step state
     * @param {number} stepIndex - Index of step to update
     * @param {string} status - New status
     * @param {any} data - Step data
     * @param {number} percentage - Progress percentage
     */
    const updateStepState = React.useCallback((stepIndex, status, data = null, percentage = 0) => {
        setPipelineState(prev => ({
            ...prev,
            steps: prev.steps.map((step, index) => 
                index === stepIndex 
                    ? { ...step, status, data, percentage }
                    : step
            )
        }));
    }, []);

    /**
     * Fetch progress from API
     */
    const fetchProgress = React.useCallback(async () => {
        try {
            const response = await fetch(`${window.CoreUtilities?.API_BASE}/progress/latest`);
            if (!response.ok) return;
            
            const data = await response.json();
            
            if (data.steps) {
                setPipelineState(prev => {
                    const newSteps = prev.steps.map((s, i) => 
                        data.steps[i] ? { ...s, ...data.steps[i] } : s
                    );
                    return { ...prev, steps: newSteps };
                });

                const activeStep = data.steps.find(s => s.status === 'running');
                if (activeStep) {
                    setCurrentOperation(`${activeStep.details || 'Processing...'} (${activeStep.percentage || 0}%)`);
                }
            }
        } catch (error) {
            console.error('Progress fetch error:', error);
        }
    }, []);

    /**
     * Fetch review items from API
     */
    const fetchReviewItems = React.useCallback(async () => {
        try {
            const response = await fetch(`${window.CoreUtilities?.API_BASE}/review-items`);
            if (response.ok) {
                const data = await response.json();
                setReviewQueue(Array.isArray(data) ? data : data.items || []);
            }
        } catch (error) {
            console.error('Review items fetch error:', error);
        }
    }, []);

    /**
     * Load model configuration
     */
    const loadModelConfig = React.useCallback(async () => {
        try {
            const saved = window.CoreUtilities?.storage?.get('model-config');
            if (saved) {
                setModelConfig(saved);
            }
        } catch (error) {
            console.error('Model config load error:', error);
        }
    }, []);

    // ===== EVENT HANDLERS =====

    /**
     * Handle file upload
     * @param {File} file - Uploaded file
     * @param {Function} onProgress - Progress callback
     */
    const handleUpload = React.useCallback(async (file, onProgress) => {
        if (!file) return;

        setLoading(true);
        setCurrentOperation('Uploading file...');
        updateStepState(0, 'running', null, 0);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${window.CoreUtilities?.API_BASE}/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'Upload failed');
            }

            const data = await response.json();
            updateStepState(0, 'completed', data, 100);
            
            if (window.showNotification) {
                window.showNotification('File uploaded successfully!', 'success');
            }
            
            // Auto-advance to next step
            setCurrentStep(1);
            
        } catch (error) {
            updateStepState(0, 'error');
            if (window.showNotification) {
                window.showNotification(`Upload failed: ${error.message}`, 'error');
            }
            throw error;
        } finally {
            setLoading(false);
            setCurrentOperation('');
        }
    }, [updateStepState]);

    /**
     * Run a pipeline step
     * @param {number} stepIndex - Index of step to run
     */
    const runStep = React.useCallback(async (stepIndex) => {
    const step = pipelineState.steps[stepIndex];
    if (!step || loading) return;

    // DEBUG: Log what step is being called
    console.log('🚀 Running Step:', {
        uiStepIndex: stepIndex,
        backendStep: stepIndex + 1,
        stepName: step.name,
        previousStepStatus: stepIndex > 0 ? pipelineState.steps[stepIndex - 1].status : 'N/A'
    });

    // Check if previous step is completed
    if (stepIndex > 0 && pipelineState.steps[stepIndex - 1].status !== 'completed') {
        if (window.showNotification) {
            window.showNotification('Previous step must be completed first', 'warning');
        }
        return;
    }

    setLoading(true);
    setCurrentOperation(`Running ${step.name}...`);
    updateStepState(stepIndex, 'running', null, 0);

    try {
        const payload = {
            step: stepIndex + 1,  // Map UI steps to backend steps
            data: stepIndex > 0 ? pipelineState.steps[stepIndex - 1].data : {}
        };
        
        console.log('📡 API Call Payload:', payload);
        
        const response = await fetch(`${window.CoreUtilities?.API_BASE}/run-step`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('📡 API Response:', result);
        
        // CRITICAL: Mark step as completed with the returned data
        updateStepState(stepIndex, 'completed', result, 100);
        
        if (window.showNotification) {
            window.showNotification(`${step.name} completed successfully!`, 'success');
        }
        
        // Auto-advance to next step if available
        if (stepIndex < pipelineState.steps.length - 1) {
            setCurrentStep(stepIndex + 1);
        }
        
    } catch (error) {
        console.error('❌ Step execution error:', error);
        updateStepState(stepIndex, 'error');
        if (window.showNotification) {
            window.showNotification(`${step.name} failed: ${error.message}`, 'error');
        }
        throw error;
    } finally {
        setLoading(false);
        setCurrentOperation('');
    }
}, [pipelineState.steps, loading, updateStepState]);

    /**
     * Handle review submission
     * @param {string} itemId - Review item ID
     * @param {Object} review - Review data
     */
    const handleReview = React.useCallback(async (itemId, review) => {
        try {
            const response = await fetch(`${window.CoreUtilities?.API_BASE}/submit-review`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_id: itemId, ...review })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'Failed to submit review');
            }

            // Update local review queue
            setReviewQueue(prev => prev.map(item => 
                item.id === itemId 
                    ? { ...item, status: 'reviewed', review } 
                    : item
            ));
            
        } catch (error) {
            console.error('Review submission error:', error);
            throw error;
        }
    }, []);

    /**
     * Handle step selection
     * @param {number} stepIndex - Index of step to select
     */
    const handleStepSelect = React.useCallback((stepIndex) => {
        if (loading) return;
        
        if (!isStepAccessible(stepIndex)) {
            if (window.showNotification) {
                window.showNotification('Complete previous steps first', 'warning');
            }
            return;
        }
        
        setCurrentStep(stepIndex);
    }, [loading, isStepAccessible]);

    // ===== EFFECTS =====

    // Progress polling effect
    React.useEffect(() => {
        if (loading) {
            progressIntervalRef.current = setInterval(fetchProgress, 1000);
        } else {
            if (progressIntervalRef.current) {
                clearInterval(progressIntervalRef.current);
                progressIntervalRef.current = null;
            }
        }

        return () => {
            if (progressIntervalRef.current) {
                clearInterval(progressIntervalRef.current);
            }
        };
    }, [loading, fetchProgress]);

    // Socket connection effect
    React.useEffect(() => {
        if (!socket) return;

        const handleConnect = () => {
            setConnectionStatus('connected');
        };

        const handleDisconnect = () => {
            setConnectionStatus('disconnected');
        };

        const handleConnecting = () => {
            setConnectionStatus('connecting');
        };

        const handleProgressUpdate = (data) => {
    // DEBUG: Log all progress updates
    console.log('🔍 Progress Update Received:', {
        rawData: data,
        backendStep: data.step,
        frontendStepIndex: data.step !== undefined ? data.step - 1 : undefined,
        currentPipelineSteps: pipelineState.steps.length,
        stepNames: pipelineState.steps.map(s => s.name)
    });
    
    // Convert backend step numbers (1,2,3,4,5) to frontend step numbers (0,1,2,3,4)
    const frontendStepIndex = data.step !== undefined ? data.step - 1 : undefined;
    
    if (frontendStepIndex !== undefined && frontendStepIndex >= 0 && frontendStepIndex < pipelineState.steps.length) {
        console.log('✅ Updating step:', {
            frontendStepIndex,
            stepName: pipelineState.steps[frontendStepIndex].name,
            status: data.status || 'running',
            percentage: data.percentage || 0
        });
        
        updateStepState(frontendStepIndex, data.status || 'running', data.data, data.percentage || 0);
        
        if (data.message) {
            setCurrentOperation(data.message);
        }
    } else {
        console.log('❌ Invalid step index:', {
            frontendStepIndex,
            pipelineStepsLength: pipelineState.steps.length,
            rawStep: data.step
        });
    }
};

        const handleReviewUpdate = (data) => {
            if (data.action === 'new_item') {
                setReviewQueue(prev => [...prev, data.item]);
            } else if (data.action === 'item_reviewed') {
                setReviewQueue(prev => prev.map(item => 
                    item.id === data.item_id 
                        ? { ...item, status: 'reviewed', review: data.review }
                        : item
                ));
            }
        };

        socket.on('connect', handleConnect);
        socket.on('disconnect', handleDisconnect);
        socket.on('connecting', handleConnecting);
        socket.on('progress_update', handleProgressUpdate);
        socket.on('review_update', handleReviewUpdate);
        
        // Set initial connection state
        setConnectionStatus(socket.connected ? 'connected' : 'disconnected');
        
        return () => {
            socket.off('connect', handleConnect);
            socket.off('disconnect', handleDisconnect);
            socket.off('connecting', handleConnecting);
            socket.off('progress_update', handleProgressUpdate);
            socket.off('review_update', handleReviewUpdate);
        };
    }, [socket, pipelineState.steps.length, updateStepState]);

    // Initial data loading effect
    React.useEffect(() => {
        const initializeApp = async () => {
            try {
                await Promise.all([
                    fetchReviewItems(),
                    loadModelConfig(),
                    fetchProgress()
                ]);
            } catch (error) {
                console.error('App initialization error:', error);
                if (window.showNotification) {
                    window.showNotification('Failed to initialize application', 'error');
                }
            }
        };

        initializeApp();
    }, [fetchReviewItems, loadModelConfig, fetchProgress]);

    // Keyboard shortcuts effect
    React.useEffect(() => {
        const handleKeyDown = (event) => {
            // Prevent shortcuts when typing in inputs
            if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                return;
            }

            // Arrow key navigation
            if (event.key === 'ArrowLeft' && currentStep > 0) {
                if (isStepAccessible(currentStep - 1)) {
                    setCurrentStep(currentStep - 1);
                }
            } else if (event.key === 'ArrowRight' && currentStep < pipelineState.steps.length - 1) {
                if (isStepAccessible(currentStep + 1)) {
                    setCurrentStep(currentStep + 1);
                }
            }
            
            // Number key navigation (1-5)
            const stepNumber = parseInt(event.key);
            if (stepNumber >= 1 && stepNumber <= pipelineState.steps.length) {
                const stepIndex = stepNumber - 1;
                if (isStepAccessible(stepIndex)) {
                    setCurrentStep(stepIndex);
                }
            }
            
            // R key for review panel toggle
            if (event.key === 'r' || event.key === 'R') {
                if (pendingReviewCount > 0) {
                    setShowReviewPanel(!showReviewPanel);
                }
            }
            
            // Escape key to close review panel
            if (event.key === 'Escape' && showReviewPanel) {
                setShowReviewPanel(false);
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [currentStep, pipelineState.steps.length, isStepAccessible, pendingReviewCount, showReviewPanel]);

    // Auto-save current step to session storage
    React.useEffect(() => {
        window.CoreUtilities?.sessionStorage?.set('current-step', currentStep);
    }, [currentStep]);

    // Load saved current step on mount
    React.useEffect(() => {
        const savedStep = window.CoreUtilities?.sessionStorage?.get('current-step');
        if (savedStep !== null && savedStep >= 0 && savedStep < pipelineState.steps.length) {
            setCurrentStep(savedStep);
        }
    }, [pipelineState.steps.length]);

    // ===== SETTINGS HANDLERS =====

    const openSettings = React.useCallback(() => {
        // This would typically open a settings modal
        // For now, we'll just show a notification
        if (window.showNotification) {
            window.showNotification('Settings panel coming soon!', 'info');
        }
    }, []);

    // ===== RENDER =====

    return React.createElement('div', { className: 'app-container' },
        // Notification System
        React.createElement(window.UIComponents.NotificationContainer),
        
        // Collapsible Sidebar
        React.createElement(window.SidebarComponents.CollapsibleSidebar, {
            pipelineState: pipelineState,
            currentStep: currentStep,
            setCurrentStep: handleStepSelect,
            loading: loading,
            pendingReviewCount: pendingReviewCount,
            showReviewPanel: showReviewPanel,
            setShowReviewPanel: setShowReviewPanel,
            socket: socket,
            modelConfig: modelConfig
        }),
        
        // Main Content
        React.createElement('div', { className: 'main-content' },
            // Top Navigation Bar
            React.createElement('div', { className: 'topbar' },
                React.createElement('div', { className: 'topbar-left' },
                    React.createElement('h1', { className: 'topbar-title' },
                        'Advanced Threat Modeling Pipeline'
                    ),
                    React.createElement('div', { className: 'topbar-subtitle' },
                        `Step ${currentStep + 1} of ${pipelineState.steps.length}: ${pipelineState.steps[currentStep]?.name}`
                    )
                ),
                
                React.createElement('div', { className: 'nav-actions' },
                    pendingReviewCount > 0 && React.createElement('button', {
                        className: 'btn btn-warning btn-sm hide-mobile',
                        onClick: () => setShowReviewPanel(!showReviewPanel),
                        'aria-label': `${pendingReviewCount} items need review`,
                        title: 'Review Queue (Press R)'
                    }, `📝 ${pendingReviewCount}`),
                    
                    React.createElement('button', {
                        className: 'btn btn-secondary btn-sm',
                        onClick: openSettings,
                        'aria-label': 'Open settings',
                        title: 'Settings'
                    }, '⚙️ Settings'),
                    
                    React.createElement('div', { className: `connection-indicator ${connectionStatus}` },
                        React.createElement('span', { className: 'connection-dot', 'aria-hidden': 'true' }),
                        React.createElement('span', { className: 'sr-only' },
                            `Server connection: ${connectionStatus}`
                        )
                    )
                )
            ),
            
            // Content Area
            React.createElement('div', { className: 'content-area' },
                showReviewPanel 
                    ? React.createElement(window.ReviewSystem.ReviewPanel, {
                        reviewQueue: reviewQueue,
                        onReview: handleReview
                    })
                    : React.createElement(window.PipelineComponents.StepContentDisplay, {
                        step: pipelineState.steps[currentStep],
                        stepIndex: currentStep,
                        pipelineState: pipelineState,
                        runStep: runStep,
                        loading: loading,
                        onUpload: handleUpload,
                        modelConfig: modelConfig
                    }),
                
                // Progress Display
                React.createElement(window.UIComponents.ProgressDisplay, {
                    step: pipelineState.steps.find(s => s.status === 'running')
                })
            )
        ),
        
        // Loading Overlay
        loading && React.createElement(window.UIComponents.LoadingOverlay, {
            message: currentOperation || 'Processing...'
        },
            React.createElement('div', { className: 'loading-details' },
                React.createElement('div', { className: 'current-step-info' },
                    React.createElement('strong', null, 'Current Step:'),
                    ` ${pipelineState.steps[currentStep]?.name}`
                ),
                pipelineState.steps.find(s => s.status === 'running')?.percentage > 0 && React.createElement('div', { className: 'loading-progress' },
                    React.createElement(window.UIComponents.ProgressBar, {
                        value: pipelineState.steps.find(s => s.status === 'running')?.percentage || 0,
                        max: 100,
                        showValue: true,
                        animated: true
                    })
                ),
                React.createElement('div', { className: 'loading-hint' },
                    React.createElement('small', null, 'You can press Escape to continue in background')
                )
            )
        )
    );
};

// ===== ACCESSIBILITY UTILITIES =====

/**
 * Announce message to screen readers
 * @param {string} message - Message to announce
 */
const announceToScreenReader = (message) => {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    setTimeout(() => {
        document.body.removeChild(announcement);
    }, 1000);
};

// Make globally available
window.announceToScreenReader = announceToScreenReader;

// ===== APPLICATION INITIALIZATION =====

/**
 * Initialize the application
 */
const initializeApp = () => {
    // Check for required dependencies
    const requiredDependencies = ['React', 'ReactDOM'];
    const missingDependencies = requiredDependencies.filter(dep => !window[dep]);
    
    if (missingDependencies.length > 0) {
        console.error('Missing required dependencies:', missingDependencies);
        document.body.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #ef4444;">
                <h1>Error: Missing Dependencies</h1>
                <p>Required libraries not loaded: ${missingDependencies.join(', ')}</p>
                <p>Please ensure all required scripts are loaded before the application.</p>
            </div>
        `;
        return;
    }

    // Check browser compatibility
    if (!window.CoreUtilities?.browserSupport?.localStorage) {
        if (window.showNotification) {
            window.showNotification('LocalStorage not supported. Some features may not work properly.', 'warning');
        }
    }

    if (!window.CoreUtilities?.browserSupport?.webSocket) {
        console.warn('WebSocket not supported. Real-time updates will not work.');
    }

    // Initialize performance monitoring
    if (window.CoreUtilities?.createPerformanceObserver) {
        window.CoreUtilities.createPerformanceObserver('measure', (list) => {
            const entries = list.getEntries();
            entries.forEach(entry => {
                if (entry.duration > 100) { // Log slow operations
                    console.warn(`Slow operation detected: ${entry.name} took ${entry.duration}ms`);
                }
            });
        });
    }

    // Set up global error boundary
    window.addEventListener('unhandledrejection', (event) => {
        console.error('Unhandled promise rejection:', event.reason);
        if (window.showNotification) {
            window.showNotification('An unexpected error occurred', 'error');
        }
    });

    // Render the application
    const rootElement = document.getElementById('root');
    if (!rootElement) {
        console.error('Root element not found. Cannot render application.');
        return;
    }

    try {
        ReactDOM.render(React.createElement(App), rootElement);
        console.log('Application initialized successfully');
        
        // Announce app ready to screen readers
        setTimeout(() => {
            announceToScreenReader('Threat modeling application loaded and ready');
        }, 1000);
        
    } catch (error) {
        console.error('Failed to render application:', error);
        rootElement.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #ef4444;">
                <h1>Application Error</h1>
                <p>Failed to initialize the application.</p>
                <p>Error: ${error.message}</p>
                <button onclick="location.reload()">Reload Page</button>
            </div>
        `;
    }
};

// ===== AUTO-INITIALIZATION =====

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    // DOM is already ready
    if (document.getElementById('root')) {
        initializeApp();
    } else {
        // Wait a bit for the root element to be available
        setTimeout(initializeApp, 100);
    }
}

// ===== EXPORTS =====

// Export for potential external use
window.ThreatModelingApp = {
    App,
    initializeApp,
    announceToScreenReader
};