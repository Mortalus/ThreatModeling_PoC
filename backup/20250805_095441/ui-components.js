/* ===== UI-COMPONENTS.JS - Reusable UI Components ===== */

/**
 * Reusable React UI components used throughout the application.
 * Uses React.createElement instead of JSX for browser compatibility.
 */

(function(window) {
    'use strict';

    // ===== NOTIFICATION SYSTEM =====

    /**
     * Notification container component
     */
    const NotificationContainer = () => {
        const [notifications, setNotifications] = React.useState([]);
        const maxNotifications = window.CoreUtilities?.APP_CONFIG?.maxNotifications || 5;

        // Add notification function
        const addNotification = React.useCallback((message, type = 'info', duration = 5000, actions = []) => {
            const id = window.CoreUtilities?.generateId('notification') || `notification_${Date.now()}`;
            const newNotification = {
                id, message, type, duration, actions,
                timestamp: new Date(),
                autoClose: duration > 0
            };

            setNotifications(prev => [newNotification, ...prev].slice(0, maxNotifications));

            if (duration > 0) {
                setTimeout(() => {
                    removeNotification(id);
                }, duration);
            }

            return id;
        }, [maxNotifications]);

        // Remove notification function
        const removeNotification = React.useCallback((id) => {
            setNotifications(prev => prev.filter(n => n.id !== id));
        }, []);

        // Clear all notifications
        const clearAllNotifications = React.useCallback(() => {
            setNotifications([]);
        }, []);

        // Make functions globally available
        React.useEffect(() => {
            window.showNotification = addNotification;
            window.removeNotification = removeNotification;
            window.clearAllNotifications = clearAllNotifications;
            window.addNotification = addNotification;

            return () => {
                delete window.showNotification;
                delete window.removeNotification;
                delete window.clearAllNotifications;
                delete window.addNotification;
            };
        }, [addNotification, removeNotification, clearAllNotifications]);

        // Handle keyboard shortcuts
        React.useEffect(() => {
            const handleKeyDown = (event) => {
                if (event.key === 'Escape') {
                    clearAllNotifications();
                }
            };

            document.addEventListener('keydown', handleKeyDown);
            return () => document.removeEventListener('keydown', handleKeyDown);
        }, [clearAllNotifications]);
        
        return React.createElement('div', {
            className: 'notification-container',
            role: 'region',
            'aria-label': 'Notifications',
            'aria-live': 'polite'
        }, notifications.map(notification => 
            React.createElement(NotificationItem, {
                key: notification.id,
                notification: notification,
                onRemove: removeNotification
            })
        ));
    };

    /**
     * Individual notification item component
     */
    const NotificationItem = ({ notification, onRemove }) => {
        const [isRemoving, setIsRemoving] = React.useState(false);
        const [progress, setProgress] = React.useState(100);
        const progressIntervalRef = React.useRef(null);

        // Handle progress bar for auto-dismissing notifications
        React.useEffect(() => {
            if (!notification.autoClose) return;

            const startTime = Date.now();
            const updateProgress = () => {
                const elapsed = Date.now() - startTime;
                const remaining = Math.max(0, notification.duration - elapsed);
                const progressPercent = (remaining / notification.duration) * 100;
                
                setProgress(progressPercent);
                
                if (remaining <= 0) {
                    handleRemove();
                }
            };

            progressIntervalRef.current = setInterval(updateProgress, 100);
            
            return () => {
                if (progressIntervalRef.current) {
                    clearInterval(progressIntervalRef.current);
                }
            };
        }, [notification.autoClose, notification.duration]);

        const handleRemove = React.useCallback(() => {
            setIsRemoving(true);
            setTimeout(() => {
                onRemove(notification.id);
            }, 300);
        }, [notification.id, onRemove]);

        const handleClick = React.useCallback(() => {
            if (!notification.autoClose) return;
            handleRemove();
        }, [notification.autoClose, handleRemove]);

        const handleKeyDown = React.useCallback((event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                handleRemove();
            }
        }, [handleRemove]);

        const getIcon = () => {
            switch (notification.type) {
                case 'success': return '✓';
                case 'error': return '✗';
                case 'warning': return '⚠';
                case 'info': 
                default: return 'ℹ';
            }
        };

        const notificationClasses = React.useMemo(() => {
            const classes = ['notification', `notification-${notification.type}`];
            if (isRemoving) classes.push('removing');
            if (notification.autoClose) classes.push('auto-dismiss');
            return classes.join(' ');
        }, [notification.type, isRemoving, notification.autoClose]);

        return React.createElement('div', {
            className: notificationClasses,
            onClick: handleClick,
            onKeyDown: handleKeyDown,
            role: notification.type === 'error' ? 'alert' : 'status',
            tabIndex: notification.autoClose ? 0 : -1,
            'aria-label': `${notification.type} notification: ${notification.message}`,
            style: { cursor: notification.autoClose ? 'pointer' : 'default' }
        }, [
            React.createElement('div', {
                className: 'notification-icon',
                'aria-hidden': 'true',
                key: 'icon'
            }, getIcon()),
            
            React.createElement('div', {
                className: 'notification-content',
                key: 'content'
            }, [
                React.createElement('div', {
                    className: 'notification-message',
                    key: 'message'
                }, notification.message),
                
                notification.actions && notification.actions.length > 0 && React.createElement('div', {
                    className: 'notification-actions',
                    key: 'actions'
                }, notification.actions.map((action, index) => 
                    React.createElement('button', {
                        key: index,
                        className: 'notification-action',
                        onClick: (e) => {
                            e.stopPropagation();
                            action.handler();
                            if (action.dismissOnClick !== false) {
                                handleRemove();
                            }
                        }
                    }, action.label)
                ))
            ]),
            
            React.createElement('button', {
                className: 'notification-dismiss',
                onClick: (e) => {
                    e.stopPropagation();
                    handleRemove();
                },
                'aria-label': 'Dismiss notification',
                title: 'Dismiss',
                key: 'dismiss'
            }, '×'),
            
            notification.autoClose && React.createElement('div', {
                className: 'notification-progress',
                'aria-hidden': 'true',
                key: 'progress'
            }, React.createElement('div', {
                className: 'notification-progress-bar',
                style: { width: `${progress}%` }
            }))
        ]);
    };

    // ===== LOADING COMPONENTS =====

    /**
     * Loading spinner component
     */
    const LoadingSpinner = ({ size = 'md', color = 'primary', className = '' }) => {
        const sizeClasses = {
            sm: 'w-4 h-4',
            md: 'w-6 h-6',
            lg: 'w-8 h-8',
            xl: 'w-12 h-12'
        };

        return React.createElement('div', {
            className: `loading-spinner ${sizeClasses[size]} ${className}`,
            role: 'status',
            'aria-label': 'Loading'
        }, React.createElement('span', {
            className: 'sr-only'
        }, 'Loading...'));
    };

    /**
     * Loading overlay component
     */
    const LoadingOverlay = ({ message = 'Loading...', children }) => {
        return React.createElement('div', {
            className: 'loading-overlay'
        }, React.createElement('div', {
            className: 'loading-content'
        }, [
            React.createElement(LoadingSpinner, { size: 'lg', key: 'spinner' }),
            React.createElement('p', {
                style: { marginTop: '20px', fontSize: '1.1em' },
                key: 'message'
            }, message),
            children
        ]));
    };

    // ===== PROGRESS COMPONENTS =====

    /**
     * Progress bar component
     */
    const ProgressBar = ({ 
        value = 0, 
        max = 100, 
        label = '', 
        showValue = true,
        variant = 'primary',
        size = 'md',
        animated = false 
    }) => {
        const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
        
        const progressClasses = React.useMemo(() => {
            const classes = ['progress-bar'];
            if (size !== 'md') classes.push(`progress-bar-${size}`);
            if (animated) classes.push('progress-bar-animated');
            return classes.join(' ');
        }, [size, animated]);

        const children = [
            React.createElement('div', {
                className: `progress-bar-fill progress-bar-${variant}`,
                style: { width: `${percentage}%` },
                key: 'fill'
            })
        ];

        if (showValue) {
            const textChildren = [];
            if (label) {
                textChildren.push(React.createElement('span', {
                    className: 'progress-label',
                    key: 'label'
                }, label));
            }
            textChildren.push(React.createElement('span', {
                className: 'progress-value',
                key: 'value'
            }, `${Math.round(percentage)}%`));

            children.push(React.createElement('div', {
                className: 'progress-bar-text',
                key: 'text'
            }, textChildren));
        }

        return React.createElement('div', {
            className: progressClasses,
            role: 'progressbar',
            'aria-valuenow': value,
            'aria-valuemin': 0,
            'aria-valuemax': max,
            'aria-label': label || `Progress: ${value} of ${max}`
        }, children);
    };

    /**
     * Progress display component for pipeline steps
     */
    const ProgressDisplay = ({ step }) => {
        if (!step || step.status !== 'running') return null;
        
        const children = [
            React.createElement('h4', {
                style: { color: 'var(--color-secondary)' },
                key: 'title'
            }, `Progress: ${step.percentage || 0}%`),
            React.createElement(ProgressBar, {
                value: step.percentage || 0,
                max: 100,
                variant: 'primary',
                animated: true,
                key: 'bar'
            })
        ];

        if (step.details) {
            children.push(React.createElement('p', {
                style: { marginTop: '10px', fontSize: '0.9em', color: 'var(--text-secondary)' },
                key: 'details'
            }, step.details));
        }

        return React.createElement('div', {
            className: 'progress-display'
        }, children);
    };

    // ===== MODAL COMPONENTS =====

    /**
     * Modal backdrop component
     */
    const ModalBackdrop = ({ isOpen, onClose, children }) => {
        React.useEffect(() => {
            if (isOpen) {
                document.body.style.overflow = 'hidden';
            } else {
                document.body.style.overflow = '';
            }

            return () => {
                document.body.style.overflow = '';
            };
        }, [isOpen]);

        React.useEffect(() => {
            const handleEscape = (event) => {
                if (event.key === 'Escape' && isOpen) {
                    onClose();
                }
            };

            document.addEventListener('keydown', handleEscape);
            return () => document.removeEventListener('keydown', handleEscape);
        }, [isOpen, onClose]);

        if (!isOpen) return null;

        return React.createElement('div', {
            className: 'modal',
            onClick: (e) => {
                if (e.target === e.currentTarget) {
                    onClose();
                }
            },
            role: 'dialog',
            'aria-modal': 'true'
        }, children);
    };

    /**
     * Modal component
     */
    const Modal = ({ 
        isOpen, 
        onClose, 
        title, 
        children, 
        footer,
        size = 'md',
        closeOnBackdrop = true,
        showCloseButton = true 
    }) => {
        const modalContentRef = React.useRef(null);

        React.useEffect(() => {
            if (isOpen && modalContentRef.current) {
                modalContentRef.current.focus();
            }
        }, [isOpen]);

        const sizeClasses = {
            sm: 'max-w-md',
            md: 'max-w-lg',
            lg: 'max-w-2xl',
            xl: 'max-w-4xl',
            full: 'max-w-full mx-4'
        };

        const modalChildren = [];

        if (title || showCloseButton) {
            const headerChildren = [];
            if (title) {
                headerChildren.push(React.createElement('h2', { key: 'title' }, title));
            }
            if (showCloseButton) {
                headerChildren.push(React.createElement('button', {
                    className: 'close',
                    onClick: onClose,
                    'aria-label': 'Close modal',
                    key: 'close'
                }, '×'));
            }

            modalChildren.push(React.createElement('div', {
                className: 'modal-header',
                key: 'header'
            }, headerChildren));
        }

        modalChildren.push(React.createElement('div', {
            className: 'modal-body',
            key: 'body'
        }, children));

        if (footer) {
            modalChildren.push(React.createElement('div', {
                className: 'modal-footer',
                key: 'footer'
            }, footer));
        }

        return React.createElement(ModalBackdrop, {
            isOpen: isOpen,
            onClose: closeOnBackdrop ? onClose : () => {}
        }, React.createElement('div', {
            ref: modalContentRef,
            className: `modal-content ${sizeClasses[size]}`,
            tabIndex: -1,
            role: 'document'
        }, modalChildren));
    };

    // ===== FORM COMPONENTS =====

    /**
     * Form field component
     */
    const FormField = ({ 
        label, 
        type = 'text', 
        value, 
        onChange, 
        error, 
        required = false,
        disabled = false,
        placeholder = '',
        className = '',
        children,
        ...props 
    }) => {
        const fieldId = React.useMemo(() => 
            window.CoreUtilities?.generateId('field') || `field_${Date.now()}`,
            []
        );

        const fieldChildren = [];

        if (label) {
            const labelChildren = [label];
            if (required) {
                labelChildren.push(React.createElement('span', {
                    className: 'text-error ml-1',
                    key: 'required'
                }, '*'));
            }

            fieldChildren.push(React.createElement('label', {
                htmlFor: fieldId,
                className: 'form-label',
                key: 'label'
            }, labelChildren));
        }

        let inputElement;
        const inputProps = {
            id: fieldId,
            value: value,
            onChange: onChange,
            disabled: disabled,
            placeholder: placeholder,
            'aria-invalid': error ? 'true' : 'false',
            'aria-describedby': error ? `${fieldId}-error` : undefined,
            ...props
        };

        if (type === 'textarea') {
            inputElement = React.createElement('textarea', {
                ...inputProps,
                className: 'form-textarea'
            });
        } else if (type === 'select') {
            inputElement = React.createElement('select', {
                ...inputProps,
                className: 'form-select'
            }, children);
        } else {
            inputElement = React.createElement('input', {
                ...inputProps,
                type: type,
                className: 'form-input'
            });
        }

        fieldChildren.push(inputElement);

        if (error) {
            fieldChildren.push(React.createElement('div', {
                id: `${fieldId}-error`,
                className: 'form-error',
                role: 'alert',
                key: 'error'
            }, error));
        }

        return React.createElement('div', {
            className: `form-group ${className}`
        }, fieldChildren);
    };

    // ===== BUTTON COMPONENTS =====

    /**
     * Enhanced button component
     */
    const Button = ({ 
        children, 
        variant = 'primary', 
        size = 'md', 
        loading = false, 
        disabled = false,
        icon = null,
        iconPosition = 'left',
        fullWidth = false,
        className = '',
        onClick,
        ...props 
    }) => {
        const buttonClasses = React.useMemo(() => {
            const classes = ['btn', `btn-${variant}`];
            if (size !== 'md') classes.push(`btn-${size}`);
            if (fullWidth) classes.push('btn-block');
            if (loading) classes.push('loading');
            if (className) classes.push(className);
            return classes.join(' ');
        }, [variant, size, fullWidth, loading, className]);

        const handleClick = React.useCallback((event) => {
            if (loading || disabled) {
                event.preventDefault();
                return;
            }
            if (onClick) {
                onClick(event);
            }
        }, [loading, disabled, onClick]);

        const buttonChildren = [];

        if (icon && iconPosition === 'left') {
            buttonChildren.push(React.createElement('span', {
                className: 'btn-icon',
                'aria-hidden': 'true',
                key: 'icon-left'
            }, icon));
        }

        buttonChildren.push(React.createElement('span', {
            className: loading ? 'opacity-0' : '',
            key: 'content'
        }, children));

        if (icon && iconPosition === 'right') {
            buttonChildren.push(React.createElement('span', {
                className: 'btn-icon',
                'aria-hidden': 'true',
                key: 'icon-right'
            }, icon));
        }

        return React.createElement('button', {
            className: buttonClasses,
            onClick: handleClick,
            disabled: disabled || loading,
            'aria-busy': loading,
            ...props
        }, buttonChildren);
    };

    // ===== ALERT COMPONENTS =====

    /**
     * Alert component
     */
    const Alert = ({ 
        type = 'info', 
        title, 
        children, 
        dismissible = false, 
        onDismiss,
        icon = true,
        className = '' 
    }) => {
        const [isDismissed, setIsDismissed] = React.useState(false);

        const getIcon = () => {
            if (!icon) return null;
            
            switch (type) {
                case 'success': return '✓';
                case 'error': return '✗';
                case 'warning': return '⚠';
                case 'info': 
                default: return 'ℹ';
            }
        };

        const handleDismiss = () => {
            setIsDismissed(true);
            if (onDismiss) {
                setTimeout(onDismiss, 300);
            }
        };

        if (isDismissed) return null;

        const alertChildren = [];

        if (icon) {
            alertChildren.push(React.createElement('div', {
                className: 'alert-icon',
                'aria-hidden': 'true',
                key: 'icon'
            }, getIcon()));
        }

        const contentChildren = [];
        if (title) {
            contentChildren.push(React.createElement('div', {
                className: 'alert-title',
                key: 'title'
            }, title));
        }
        contentChildren.push(React.createElement('div', {
            className: 'alert-message',
            key: 'message'
        }, children));

        alertChildren.push(React.createElement('div', {
            className: 'alert-content',
            key: 'content'
        }, contentChildren));

        if (dismissible) {
            alertChildren.push(React.createElement('button', {
                className: 'alert-dismiss',
                onClick: handleDismiss,
                'aria-label': 'Dismiss alert',
                key: 'dismiss'
            }, '×'));
        }

        return React.createElement('div', {
            className: `alert alert-${type} ${className}`,
            role: 'alert'
        }, alertChildren);
    };

    // ===== EXPORTS =====

    const UIComponents = {
        NotificationContainer,
        NotificationItem,
        LoadingSpinner,
        LoadingOverlay,
        ProgressBar,
        ProgressDisplay,
        ModalBackdrop,
        Modal,
        FormField,
        Button,
        Alert
    };

    // Make available globally
    window.UIComponents = UIComponents;
    window.NotificationContainer = NotificationContainer;
    window.ProgressDisplay = ProgressDisplay;
    window.LoadingSpinner = LoadingSpinner;
    window.LoadingOverlay = LoadingOverlay;

    console.log('UI Components loaded successfully');

})(window);