/* ===== SIDEBAR-COMPONENTS.JS - Collapsible Sidebar Components ===== */

/**
 * React components for the collapsible sidebar functionality.
 * Uses React.createElement instead of JSX for browser compatibility.
 */

(function(window) {
    'use strict';

    // ===== CUSTOM HOOKS =====

    /**
     * Custom hook for managing sidebar collapse state with persistence
     */
    const useSidebarState = () => {
        const [isCollapsed, setIsCollapsed] = React.useState(() => {
            const saved = window.CoreUtilities?.sessionStorage?.get('sidebar-collapsed');
            return saved !== null ? saved : false;
        });

        const toggleSidebar = React.useCallback(() => {
            setIsCollapsed(prev => {
                const newState = !prev;
                window.CoreUtilities?.sessionStorage?.set('sidebar-collapsed', newState);
                
                window.dispatchEvent(new CustomEvent('sidebarToggle', { 
                    detail: { isCollapsed: newState } 
                }));
                
                return newState;
            });
        }, []);

        // Keyboard shortcut for toggle (Ctrl/Cmd + B)
        React.useEffect(() => {
            const handleKeyDown = (event) => {
                if ((event.ctrlKey || event.metaKey) && event.key === 'b') {
                    event.preventDefault();
                    toggleSidebar();
                }
            };

            document.addEventListener('keydown', handleKeyDown);
            return () => document.removeEventListener('keydown', handleKeyDown);
        }, [toggleSidebar]);

        return { isCollapsed, toggleSidebar };
    };

    /**
     * Custom hook for responsive sidebar behavior
     */
    const useResponsiveSidebar = () => {
        const [isMobile, setIsMobile] = React.useState(window.innerWidth < 768);
        const [isTablet, setIsTablet] = React.useState(
            window.innerWidth >= 768 && window.innerWidth < 1024
        );

        React.useEffect(() => {
            const handleResize = window.CoreUtilities?.throttle(() => {
                const width = window.innerWidth;
                setIsMobile(width < 768);
                setIsTablet(width >= 768 && width < 1024);
            }, 250);

            window.addEventListener('resize', handleResize);
            return () => window.removeEventListener('resize', handleResize);
        }, []);

        return { isMobile, isTablet };
    };

    /**
     * Custom hook for managing sidebar animations
     */
    const useSidebarAnimations = (isCollapsed) => {
        const [isAnimating, setIsAnimating] = React.useState(false);
        const animationTimeoutRef = React.useRef(null);

        React.useEffect(() => {
            setIsAnimating(true);
            
            if (animationTimeoutRef.current) {
                clearTimeout(animationTimeoutRef.current);
            }
            
            animationTimeoutRef.current = setTimeout(() => {
                setIsAnimating(false);
            }, 400);

            return () => {
                if (animationTimeoutRef.current) {
                    clearTimeout(animationTimeoutRef.current);
                }
            };
        }, [isCollapsed]);

        return { isAnimating };
    };

    // ===== MAIN SIDEBAR COMPONENT =====

    /**
     * Main collapsible sidebar component
     */
    const CollapsibleSidebar = ({ 
        children, 
        pipelineState, 
        currentStep, 
        setCurrentStep, 
        loading, 
        pendingReviewCount = 0, 
        showReviewPanel, 
        setShowReviewPanel, 
        socket,
        modelConfig 
    }) => {
        const { isCollapsed, toggleSidebar } = useSidebarState();
        const { isMobile, isTablet } = useResponsiveSidebar();
        const { isAnimating } = useSidebarAnimations(isCollapsed);
        const sidebarRef = React.useRef(null);

        // Handle click outside on mobile to close sidebar
        React.useEffect(() => {
            if (!isMobile || isCollapsed) return;

            const handleClickOutside = (event) => {
                if (sidebarRef.current && !sidebarRef.current.contains(event.target)) {
                    toggleSidebar();
                }
            };

            document.addEventListener('mousedown', handleClickOutside);
            return () => document.removeEventListener('mousedown', handleClickOutside);
        }, [isMobile, isCollapsed, toggleSidebar]);

        // Handle escape key on mobile
        React.useEffect(() => {
            if (!isMobile) return;

            const handleEscape = (event) => {
                if (event.key === 'Escape' && !isCollapsed) {
                    toggleSidebar();
                }
            };

            document.addEventListener('keydown', handleEscape);
            return () => document.removeEventListener('keydown', handleEscape);
        }, [isMobile, isCollapsed, toggleSidebar]);

        const sidebarClasses = React.useMemo(() => {
            const classes = ['sidebar'];
            if (isCollapsed) classes.push('collapsed');
            if (isAnimating) classes.push('animating');
            if (isMobile) classes.push('mobile');
            if (isTablet) classes.push('tablet');
            return classes.join(' ');
        }, [isCollapsed, isAnimating, isMobile, isTablet]);

        const sidebarChildren = [
            React.createElement('button', {
                className: 'sidebar-toggle',
                onClick: toggleSidebar,
                'aria-label': isCollapsed ? 'Expand sidebar' : 'Collapse sidebar',
                title: `${isCollapsed ? 'Expand' : 'Collapse'} Progress Panel (Ctrl+B)`,
                type: 'button',
                key: 'toggle'
            }, React.createElement('span', {
                className: 'sidebar-toggle-icon',
                'aria-hidden': 'true'
            }, isCollapsed ? '▶' : '◀')),

            React.createElement('div', {
                className: 'sidebar-content',
                key: 'content'
            }, isCollapsed ? [
                React.createElement('div', {
                    className: 'sidebar-collapsed-content',
                    key: 'collapsed'
                }, [
                    React.createElement('div', {
                        className: 'collapsed-steps',
                        role: 'list',
                        key: 'steps'
                    }, pipelineState.steps.map((step, index) => 
                        React.createElement(CollapsedStepIndicator, {
                            key: step.id,
                            step: step,
                            index: index,
                            active: index === currentStep,
                            onClick: () => !loading && setCurrentStep(index)
                        })
                    )),
                    
                    pendingReviewCount > 0 && React.createElement('div', {
                        className: 'collapsed-review-indicator',
                        key: 'review'
                    }, React.createElement('button', {
                        className: 'btn btn-icon btn-primary',
                        onClick: () => setShowReviewPanel(!showReviewPanel),
                        title: `${pendingReviewCount} items pending review`,
                        'aria-label': `Review queue with ${pendingReviewCount} pending items`
                    }, [
                        '📝',
                        React.createElement('span', {
                            className: 'review-count-badge',
                            'aria-hidden': 'true',
                            key: 'badge'
                        }, pendingReviewCount)
                    ])),

                    React.createElement('div', {
                        className: 'collapsed-connection-status',
                        key: 'connection'
                    }, React.createElement(ConnectionStatusCollapsed, { socket: socket }))
                ])
            ] : [
                React.createElement('div', {
                    className: 'sidebar-header',
                    key: 'header'
                }, [
                    React.createElement('h1', { key: 'title' }, '🛡️ Advanced Threat Modeling'),
                    React.createElement('p', { key: 'subtitle' }, 'AI-Powered Security Analysis')
                ]),
                
                React.createElement('div', {
                    className: 'pipeline-steps',
                    role: 'list',
                    key: 'steps'
                }, pipelineState.steps.map((step, index) => 
                    React.createElement(EnhancedPipelineStep, {
                        key: step.id,
                        step: step,
                        index: index,
                        active: index === currentStep,
                        onClick: () => !loading && setCurrentStep(index),
                        isCollapsed: false,
                        modelConfig: modelConfig
                    })
                )),
                
                pendingReviewCount > 0 && React.createElement('div', {
                    className: 'review-button-container',
                    key: 'review'
                }, React.createElement('button', {
                    className: 'btn btn-primary btn-block',
                    onClick: () => setShowReviewPanel(!showReviewPanel),
                    'aria-label': `Review queue with ${pendingReviewCount} pending items`
                }, `📝 Review Queue (${pendingReviewCount})`)),
                
                React.createElement(ConnectionStatus, { socket: socket, key: 'connection' })
            ])
        ];

        return React.createElement('div', {
            ref: sidebarRef,
            className: sidebarClasses,
            role: 'navigation',
            'aria-label': 'Pipeline Progress Navigation',
            'aria-expanded': !isCollapsed
        }, sidebarChildren);
    };

    // ===== ENHANCED PIPELINE STEP COMPONENT =====

    /**
     * Enhanced pipeline step component that adapts to collapsed/expanded states
     */
    const EnhancedPipelineStep = ({ 
        step, 
        index, 
        active, 
        onClick, 
        isCollapsed, 
        modelConfig 
    }) => {
        const icons = window.CoreUtilities?.PIPELINE_STEPS?.map(s => s.icon) || 
                     ['📄', '🔗', '⚠️', '✨', '🎯'];
        
        const stepClasses = React.useMemo(() => {
            const classes = ['pipeline-step'];
            if (active) classes.push('active');
            classes.push(step.status);
            if (isCollapsed) classes.push('collapsed-step');
            return classes.join(' ');
        }, [active, step.status, isCollapsed]);

        const handleClick = React.useCallback(() => {
            onClick();
            
            if (window.announceToScreenReader) {
                window.announceToScreenReader(`Switched to ${step.name} step`);
            }
        }, [onClick, step.name]);

        const handleKeyDown = React.useCallback((event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                handleClick();
            }
        }, [handleClick]);

        const stepChildren = [];

        if (step.status === 'running' && step.percentage > 0) {
            stepChildren.push(React.createElement('div', {
                className: 'step-progress-bar-container',
                'aria-hidden': 'true',
                key: 'progress'
            }, React.createElement('div', {
                className: 'step-progress-bar',
                style: { width: `${step.percentage}%` }
            })));
        }

        const contentChildren = [
            React.createElement('div', {
                className: 'step-title',
                key: 'title'
            }, [
                React.createElement('span', {
                    className: 'step-icon',
                    'aria-hidden': 'true',
                    key: 'icon'
                }, icons[index]),
                !isCollapsed && React.createElement('span', {
                    className: 'step-name',
                    key: 'name'
                }, step.name)
            ])
        ];

        if (!isCollapsed) {
            contentChildren.push(React.createElement('div', {
                className: 'step-status',
                'aria-live': 'polite',
                key: 'status'
            }, step.status === 'running' ? 
                `${step.percentage || 0}%` : 
                window.CoreUtilities?.capitalize(step.status)
            ));

            if (modelConfig && index > 0) {
                contentChildren.push(React.createElement('div', {
                    className: 'step-model-info',
                    key: 'model'
                }, React.createElement('span', {
                    className: 'model-badge'
                }, [
                    React.createElement('span', {
                        'aria-hidden': 'true',
                        key: 'provider-icon'
                    }, modelConfig.provider === 'ollama' ? '🖥️' : '☁️'),
                    React.createElement('span', {
                        className: 'sr-only',
                        key: 'provider-text'
                    }, modelConfig.provider === 'ollama' ? 'Local model' : 'Cloud model'),
                    modelConfig.model?.split(/[:\/]/).pop() || 'Default'
                ])));
            }
        }

        stepChildren.push(React.createElement('div', {
            className: 'step-content',
            key: 'content'
        }, contentChildren));

        return React.createElement('div', {
            className: stepClasses,
            onClick: handleClick,
            onKeyDown: handleKeyDown,
            role: 'listitem button',
            tabIndex: 0,
            'aria-current': active ? 'step' : undefined,
            'aria-label': `${step.name} - ${step.status}${step.percentage ? ` (${step.percentage}%)` : ''}`,
            title: isCollapsed ? `${step.name} - ${step.status}` : undefined
        }, stepChildren);
    };

    // ===== COLLAPSED STEP INDICATOR =====

    /**
     * Compact step indicator for collapsed sidebar
     */
    const CollapsedStepIndicator = ({ step, index, active, onClick }) => {
        const icons = window.CoreUtilities?.PIPELINE_STEPS?.map(s => s.icon) || 
                     ['📄', '🔗', '⚠️', '✨', '🎯'];
        
        const indicatorClasses = React.useMemo(() => {
            const classes = ['collapsed-step-indicator'];
            if (active) classes.push('active');
            classes.push(step.status);
            return classes.join(' ');
        }, [active, step.status]);

        const handleClick = React.useCallback(() => {
            onClick();
            
            if (window.announceToScreenReader) {
                window.announceToScreenReader(`Switched to ${step.name} step`);
            }
        }, [onClick, step.name]);

        const handleKeyDown = React.useCallback((event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                handleClick();
            }
        }, [handleClick]);

        const indicatorChildren = [
            React.createElement('span', {
                className: 'collapsed-step-icon',
                'aria-hidden': 'true',
                key: 'icon'
            }, icons[index])
        ];

        if (step.status === 'running' && step.percentage > 0) {
            indicatorChildren.push(React.createElement('div', {
                className: 'collapsed-progress-ring',
                'aria-hidden': 'true',
                key: 'progress'
            }, React.createElement('svg', {
                width: '40',
                height: '40',
                className: 'progress-ring'
            }, [
                React.createElement('circle', {
                    cx: '20',
                    cy: '20',
                    r: '16',
                    fill: 'transparent',
                    stroke: 'var(--border-primary)',
                    strokeWidth: '2',
                    key: 'bg'
                }),
                React.createElement('circle', {
                    cx: '20',
                    cy: '20',
                    r: '16',
                    fill: 'transparent',
                    stroke: 'var(--color-primary)',
                    strokeWidth: '2',
                    strokeDasharray: `${2 * Math.PI * 16}`,
                    strokeDashoffset: `${2 * Math.PI * 16 * (1 - (step.percentage || 0) / 100)}`,
                    transform: 'rotate(-90 20 20)',
                    className: 'progress-circle',
                    key: 'progress'
                })
            ])));
        }

        if (step.status === 'completed') {
            indicatorChildren.push(React.createElement('div', {
                className: 'status-indicator completed',
                'aria-hidden': 'true',
                key: 'completed'
            }, '✓'));
        }

        if (step.status === 'error') {
            indicatorChildren.push(React.createElement('div', {
                className: 'status-indicator error',
                'aria-hidden': 'true',
                key: 'error'
            }, '✗'));
        }

        return React.createElement('div', {
            className: indicatorClasses,
            onClick: handleClick,
            onKeyDown: handleKeyDown,
            role: 'button',
            tabIndex: 0,
            'aria-label': `${step.name} - ${step.status}${step.percentage ? ` (${step.percentage}%)` : ''}`,
            title: `${step.name} - ${step.status}${step.percentage ? ` (${step.percentage}%)` : ''}`
        }, indicatorChildren);
    };

    // ===== CONNECTION STATUS COMPONENTS =====

    /**
     * Connection status component for expanded sidebar
     */
    const ConnectionStatus = ({ socket }) => {
        const [connectionState, setConnectionState] = React.useState({
            isConnected: false,
            isConnecting: false,
            lastConnected: null,
            retryCount: 0
        });

        React.useEffect(() => {
            if (!socket) return;
            
            const handleConnect = () => {
                setConnectionState(prev => ({
                    ...prev,
                    isConnected: true,
                    isConnecting: false,
                    lastConnected: new Date(),
                    retryCount: 0
                }));
                
                if (window.showNotification) {
                    window.showNotification('Connected to server', 'success', 3000);
                }
            };

            const handleDisconnect = () => {
                setConnectionState(prev => ({
                    ...prev,
                    isConnected: false,
                    isConnecting: false
                }));
                
                if (window.showNotification) {
                    window.showNotification('Disconnected from server', 'error', 5000);
                }
            };

            const handleConnecting = () => {
                setConnectionState(prev => ({
                    ...prev,
                    isConnecting: true,
                    retryCount: prev.retryCount + 1
                }));
            };
            
            socket.on('connect', handleConnect);
            socket.on('disconnect', handleDisconnect);
            socket.on('connecting', handleConnecting);
            
            setConnectionState(prev => ({
                ...prev,
                isConnected: socket.connected,
                isConnecting: socket.connecting || false
            }));
            
            return () => {
                socket.off('connect', handleConnect);
                socket.off('disconnect', handleDisconnect);
                socket.off('connecting', handleConnecting);
            };
        }, [socket]);

        const getStatusText = () => {
            if (connectionState.isConnecting) return 'Connecting...';
            if (connectionState.isConnected) return 'Connected';
            return 'Disconnected';
        };

        const getStatusClass = () => {
            if (connectionState.isConnecting) return 'connecting';
            if (connectionState.isConnected) return 'connected';
            return 'disconnected';
        };

        const statusChildren = [
            React.createElement('span', {
                className: 'status-indicator',
                'aria-hidden': 'true',
                key: 'indicator'
            }),
            React.createElement('span', { key: 'text' }, getStatusText())
        ];

        if (connectionState.retryCount > 0 && !connectionState.isConnected) {
            statusChildren.push(React.createElement('span', {
                className: 'retry-count',
                key: 'retry'
            }, `(Retry ${connectionState.retryCount})`));
        }
        
        return React.createElement('div', {
            className: `connection-status ${getStatusClass()}`,
            role: 'status',
            'aria-live': 'polite',
            'aria-label': `Server connection status: ${getStatusText()}`
        }, statusChildren);
    };

    /**
     * Collapsed connection status component
     */
    const ConnectionStatusCollapsed = ({ socket }) => {
        const [isConnected, setIsConnected] = React.useState(false);
        
        React.useEffect(() => {
            if (!socket) return;
            
            const handleConnect = () => setIsConnected(true);
            const handleDisconnect = () => setIsConnected(false);
            
            socket.on('connect', handleConnect);
            socket.on('disconnect', handleDisconnect);
            setIsConnected(socket.connected);
            
            return () => {
                socket.off('connect', handleConnect);
                socket.off('disconnect', handleDisconnect);
            };
        }, [socket]);
        
        return React.createElement('div', {
            className: `status-indicator ${isConnected ? 'connected' : 'disconnected'}`,
            title: `Server: ${isConnected ? 'Connected' : 'Disconnected'}`,
            'aria-label': `Server connection: ${isConnected ? 'Connected' : 'Disconnected'}`,
            role: 'status'
        });
    };

    // ===== EXPORTS =====

    const SidebarComponents = {
        useSidebarState,
        useResponsiveSidebar,
        useSidebarAnimations,
        CollapsibleSidebar,
        EnhancedPipelineStep,
        CollapsedStepIndicator,
        ConnectionStatus,
        ConnectionStatusCollapsed
    };

    // Make available globally
    window.SidebarComponents = SidebarComponents;
    window.CollapsibleSidebar = CollapsibleSidebar;
    window.EnhancedPipelineStep = EnhancedPipelineStep;
    window.useSidebarState = useSidebarState;

    console.log('Sidebar Components loaded successfully');

})(window);