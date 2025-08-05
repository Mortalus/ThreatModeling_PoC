/* ===== REVIEW-SYSTEM.JS - Review Queue and Decision Components ===== */

/**
 * React components for the manual review system.
 * Uses React.createElement instead of JSX for browser compatibility.
 */

(function(window) {
    'use strict';

    // ===== REVIEW PANEL COMPONENT =====

    /**
     * Main review panel component
     */
    const ReviewPanel = ({ reviewQueue, onReview }) => {
        const [filter, setFilter] = React.useState('all');
        const [sortBy, setSortBy] = React.useState('timestamp');
        const [sortOrder, setSortOrder] = React.useState('desc');

        const filteredAndSortedQueue = React.useMemo(() => {
            let filtered = reviewQueue || [];
            
            // Apply filter
            if (filter !== 'all') {
                filtered = filtered.filter(item => {
                    switch (filter) {
                        case 'pending':
                            return item.status === 'pending';
                        case 'reviewed':
                            return item.status === 'reviewed';
                        case 'high-confidence':
                            return item.confidence === 'high';
                        case 'low-confidence':
                            return item.confidence === 'low';
                        default:
                            return true;
                    }
                });
            }
            
            // Apply sorting
            filtered.sort((a, b) => {
                let aValue, bValue;
                
                switch (sortBy) {
                    case 'confidence':
                        aValue = a.confidence === 'high' ? 3 : a.confidence === 'medium' ? 2 : 1;
                        bValue = b.confidence === 'high' ? 3 : b.confidence === 'medium' ? 2 : 1;
                        break;
                    case 'type':
                        aValue = a.type || '';
                        bValue = b.type || '';
                        break;
                    case 'timestamp':
                    default:
                        aValue = new Date(a.timestamp || a.created_at || 0).getTime();
                        bValue = new Date(b.timestamp || b.created_at || 0).getTime();
                        break;
                }
                
                if (sortOrder === 'asc') {
                    return aValue > bValue ? 1 : -1;
                } else {
                    return aValue < bValue ? 1 : -1;
                }
            });
            
            return filtered;
        }, [reviewQueue, filter, sortBy, sortOrder]);

        const stats = React.useMemo(() => {
            const total = reviewQueue?.length || 0;
            const pending = reviewQueue?.filter(item => item.status === 'pending').length || 0;
            const reviewed = reviewQueue?.filter(item => item.status === 'reviewed').length || 0;
            const highConfidence = reviewQueue?.filter(item => item.confidence === 'high').length || 0;
            const lowConfidence = reviewQueue?.filter(item => item.confidence === 'low').length || 0;
            
            return { total, pending, reviewed, highConfidence, lowConfidence };
        }, [reviewQueue]);

        return React.createElement('div', {
            className: 'review-panel card'
        }, [
            React.createElement('div', {
                className: 'card-header',
                key: 'header'
            }, [
                React.createElement('h2', { key: 'title' }, '📝 Items for Manual Review'),
                React.createElement('div', {
                    className: 'review-queue-stats',
                    key: 'stats'
                }, [
                    React.createElement('div', {
                        className: 'review-stat',
                        key: 'total'
                    }, [
                        React.createElement('span', {
                            className: 'review-stat-label',
                            key: 'label'
                        }, 'Total:'),
                        React.createElement('span', {
                            className: 'review-stat-value',
                            key: 'value'
                        }, stats.total)
                    ]),
                    React.createElement('div', {
                        className: 'review-stat',
                        key: 'pending'
                    }, [
                        React.createElement('span', {
                            className: 'review-stat-label',
                            key: 'label'
                        }, 'Pending:'),
                        React.createElement('span', {
                            className: 'review-stat-value',
                            key: 'value'
                        }, stats.pending)
                    ])
                ])
            ]),
            
            React.createElement('div', {
                className: 'card-body',
                key: 'body'
            }, [
                React.createElement(ReviewControls, {
                    filter: filter,
                    setFilter: setFilter,
                    sortBy: sortBy,
                    setSortBy: setSortBy,
                    sortOrder: sortOrder,
                    setSortOrder: setSortOrder,
                    stats: stats,
                    key: 'controls'
                }),
                
                React.createElement(ReviewQueue, {
                    reviewItems: filteredAndSortedQueue,
                    onReview: onReview,
                    key: 'queue'
                })
            ])
        ]);
    };

    // ===== REVIEW CONTROLS =====

    /**
     * Controls for filtering and sorting review items
     */
    const ReviewControls = ({ 
        filter, 
        setFilter, 
        sortBy, 
        setSortBy, 
        sortOrder, 
        setSortOrder, 
        stats 
    }) => {
        return React.createElement('div', {
            className: 'review-controls'
        }, [
            React.createElement('div', {
                className: 'review-filters',
                key: 'filters'
            }, [
                React.createElement('label', {
                    htmlFor: 'review-filter',
                    key: 'label'
                }, 'Filter:'),
                React.createElement('select', {
                    id: 'review-filter',
                    value: filter,
                    onChange: (e) => setFilter(e.target.value),
                    className: 'form-select',
                    key: 'select'
                }, [
                    React.createElement('option', { value: 'all', key: 'all' }, `All Items (${stats.total})`),
                    React.createElement('option', { value: 'pending', key: 'pending' }, `Pending (${stats.pending})`),
                    React.createElement('option', { value: 'reviewed', key: 'reviewed' }, `Reviewed (${stats.reviewed})`),
                    React.createElement('option', { value: 'high-confidence', key: 'high' }, `High Confidence (${stats.highConfidence})`),
                    React.createElement('option', { value: 'low-confidence', key: 'low' }, `Low Confidence (${stats.lowConfidence})`)
                ])
            ]),
            
            React.createElement('div', {
                className: 'review-sorting',
                key: 'sorting'
            }, [
                React.createElement('label', {
                    htmlFor: 'review-sort',
                    key: 'label'
                }, 'Sort by:'),
                React.createElement('select', {
                    id: 'review-sort',
                    value: sortBy,
                    onChange: (e) => setSortBy(e.target.value),
                    className: 'form-select',
                    key: 'select'
                }, [
                    React.createElement('option', { value: 'timestamp', key: 'timestamp' }, 'Date'),
                    React.createElement('option', { value: 'confidence', key: 'confidence' }, 'Confidence'),
                    React.createElement('option', { value: 'type', key: 'type' }, 'Type')
                ]),
                
                React.createElement('button', {
                    className: 'btn btn-sm btn-secondary',
                    onClick: () => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc'),
                    'aria-label': `Sort ${sortOrder === 'asc' ? 'descending' : 'ascending'}`,
                    title: `Currently sorting ${sortOrder === 'asc' ? 'ascending' : 'descending'}`,
                    key: 'sort-order'
                }, sortOrder === 'asc' ? '↑' : '↓')
            ])
        ]);
    };

    // ===== REVIEW QUEUE =====

    /**
     * Review queue component displaying list of review items
     */
    const ReviewQueue = ({ reviewItems, onReview }) => {
        const [selectedItem, setSelectedItem] = React.useState(null);

        const handleItemClick = React.useCallback((item) => {
            if (item.status === 'reviewed') return;
            setSelectedItem(item);
        }, []);

        const handleReviewSubmit = React.useCallback(async (review) => {
            if (!selectedItem) return;
            
            try {
                await onReview(selectedItem.id, review);
                setSelectedItem(null);
                
                if (window.showNotification) {
                    window.showNotification('Review submitted successfully', 'success');
                }
            } catch (error) {
                if (window.showNotification) {
                    window.showNotification(`Failed to submit review: ${error.message}`, 'error');
                }
            }
        }, [selectedItem, onReview]);

        const handleModalClose = React.useCallback(() => {
            setSelectedItem(null);
        }, []);

        if (!reviewItems || reviewItems.length === 0) {
            return React.createElement('div', {
                className: 'review-list-empty'
            }, React.createElement('div', {
                className: 'empty-state'
            }, [
                React.createElement('span', {
                    className: 'empty-icon',
                    'aria-hidden': 'true',
                    key: 'icon'
                }, '📋'),
                React.createElement('h3', { key: 'title' }, 'No review items'),
                React.createElement('p', { key: 'description' }, 'All items have been processed or there are no items requiring review.')
            ]));
        }

        const queueChildren = [
            React.createElement('div', {
                className: 'review-list',
                role: 'list',
                key: 'list'
            }, reviewItems.map((item) => 
                React.createElement(ReviewItem, {
                    key: item.id,
                    item: item,
                    onClick: () => handleItemClick(item)
                })
            ))
        ];

        if (selectedItem) {
            queueChildren.push(React.createElement(ReviewModal, {
                item: selectedItem,
                onClose: handleModalClose,
                onSubmit: handleReviewSubmit,
                key: 'modal'
            }));
        }

        return React.createElement('div', {}, queueChildren);
    };

    // ===== REVIEW ITEM =====

    /**
     * Individual review item component
     */
    const ReviewItem = ({ item, onClick }) => {
        const handleClick = React.useCallback(() => {
            if (item.status !== 'reviewed') {
                onClick(item);
            }
        }, [item, onClick]);

        const handleKeyDown = React.useCallback((event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                handleClick();
            }
        }, [handleClick]);

        const formatTimestamp = (timestamp) => {
            if (!timestamp) return 'Unknown time';
            
            const date = new Date(timestamp);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);
            
            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;
            
            return date.toLocaleDateString();
        };

        const itemClasses = React.useMemo(() => {
            const classes = ['review-item'];
            if (item.status === 'reviewed') classes.push('reviewed');
            return classes.join(' ');
        }, [item.status]);

        const contentChildren = [];

        if (item.description) {
            contentChildren.push(React.createElement('div', {
                className: 'review-description',
                key: 'description'
            }, window.CoreUtilities?.truncateText(item.description, 150)));
        }

        if (item.question) {
            contentChildren.push(React.createElement('div', {
                className: 'review-question',
                key: 'question'
            }, [
                React.createElement('strong', { key: 'label' }, 'Question:'),
                ' ',
                item.question
            ]));
        }

        contentChildren.push(React.createElement('div', {
            className: 'review-item-footer',
            key: 'footer'
        }, [
            React.createElement('div', {
                className: 'review-timestamp',
                key: 'timestamp'
            }, formatTimestamp(item.timestamp || item.created_at)),
            React.createElement('div', {
                className: `review-status ${item.status || 'pending'}`,
                key: 'status'
            }, item.status === 'reviewed' ? '✓ Reviewed' : '⏳ Pending')
        ]));

        return React.createElement('div', {
            className: itemClasses,
            onClick: handleClick,
            onKeyDown: handleKeyDown,
            role: 'listitem button',
            tabIndex: item.status === 'reviewed' ? -1 : 0,
            'aria-label': `Review item: ${item.title || item.name || 'Unnamed item'}`,
            'aria-describedby': `item-${item.id}-details`
        }, [
            React.createElement('div', {
                className: 'review-item-header',
                key: 'header'
            }, [
                React.createElement('div', {
                    className: 'review-item-title',
                    key: 'title'
                }, item.title || item.name || 'Unnamed Item'),
                React.createElement('div', {
                    className: 'review-item-meta',
                    key: 'meta'
                }, [
                    React.createElement('span', {
                        className: `review-type ${item.type?.toLowerCase() || 'unknown'}`,
                        key: 'type'
                    }, item.type || 'Unknown'),
                    React.createElement('span', {
                        className: `confidence-badge ${item.confidence?.toLowerCase() || 'medium'}`,
                        key: 'confidence'
                    }, item.confidence || 'Medium')
                ])
            ]),
            
            React.createElement('div', {
                id: `item-${item.id}-details`,
                className: 'review-item-content',
                key: 'content'
            }, contentChildren)
        ]);
    };

    // ===== REVIEW MODAL =====

    /**
     * Modal for reviewing individual items
     */
    const ReviewModal = ({ item, onClose, onSubmit }) => {
        const [decision, setDecision] = React.useState('');
        const [comments, setComments] = React.useState('');
        const [isSubmitting, setIsSubmitting] = React.useState(false);

        const handleSubmit = React.useCallback(async (e) => {
            e.preventDefault();
            
            if (!decision) {
                if (window.showNotification) {
                    window.showNotification('Please make a decision before submitting', 'warning');
                }
                return;
            }
            
            setIsSubmitting(true);
            
            try {
                await onSubmit({
                    decision,
                    comments: comments.trim(),
                    timestamp: new Date().toISOString(),
                    reviewer: 'current_user'
                });
            } catch (error) {
                console.error('Review submission error:', error);
            } finally {
                setIsSubmitting(false);
            }
        }, [decision, comments, onSubmit]);

        const handleDecisionChange = React.useCallback((newDecision) => {
            setDecision(newDecision);
        }, []);

        return React.createElement('div', {
            className: 'modal',
            onClick: (e) => e.target === e.currentTarget && onClose()
        }, React.createElement('div', {
            className: 'review-modal',
            role: 'dialog',
            'aria-modal': 'true',
            'aria-labelledby': 'review-modal-title'
        }, [
            React.createElement('div', {
                className: 'review-modal-header',
                key: 'header'
            }, [
                React.createElement('h2', {
                    id: 'review-modal-title',
                    key: 'title'
                }, `Review Item: ${item.title || item.name || 'Unnamed Item'}`),
                React.createElement('button', {
                    className: 'close',
                    onClick: onClose,
                    'aria-label': 'Close review modal',
                    key: 'close'
                }, '×')
            ]),
            
            React.createElement('div', {
                className: 'review-modal-body',
                key: 'body'
            }, [
                React.createElement(ReviewItemDetails, {
                    item: item,
                    key: 'details'
                }),
                React.createElement(ReviewDecisionForm, {
                    decision: decision,
                    onDecisionChange: handleDecisionChange,
                    comments: comments,
                    onCommentsChange: setComments,
                    key: 'form'
                })
            ]),
            
            React.createElement('div', {
                className: 'review-modal-footer',
                key: 'footer'
            }, [
                React.createElement('button', {
                    type: 'button',
                    className: 'btn btn-secondary',
                    onClick: onClose,
                    disabled: isSubmitting,
                    key: 'cancel'
                }, 'Cancel'),
                React.createElement('button', {
                    type: 'button',
                    className: 'btn btn-primary',
                    onClick: handleSubmit,
                    disabled: !decision || isSubmitting,
                    key: 'submit'
                }, isSubmitting ? [
                    React.createElement('span', {
                        className: 'loading-spinner',
                        style: { width: '16px', height: '16px' },
                        key: 'spinner'
                    }),
                    'Submitting...'
                ] : 'Submit Review')
            ])
        ]));
    };

    // ===== REVIEW ITEM DETAILS =====

    /**
     * Detailed view of review item
     */
    const ReviewItemDetails = ({ item }) => {
        const detailsChildren = [
            React.createElement('div', {
                className: 'review-detail',
                key: 'type'
            }, [
                React.createElement('div', {
                    className: 'review-detail-label',
                    key: 'label'
                }, 'Type'),
                React.createElement('div', {
                    className: 'review-detail-value',
                    key: 'value'
                }, React.createElement('span', {
                    className: `review-type ${item.type?.toLowerCase() || 'unknown'}`
                }, item.type || 'Unknown'))
            ]),
            
            React.createElement('div', {
                className: 'review-detail',
                key: 'confidence'
            }, [
                React.createElement('div', {
                    className: 'review-detail-label',
                    key: 'label'
                }, 'Confidence'),
                React.createElement('div', {
                    className: 'review-detail-value',
                    key: 'value'
                }, React.createElement('span', {
                    className: `confidence-badge ${item.confidence?.toLowerCase() || 'medium'}`
                }, item.confidence || 'Medium'))
            ])
        ];

        if (item.severity) {
            detailsChildren.push(React.createElement('div', {
                className: 'review-detail',
                key: 'severity'
            }, [
                React.createElement('div', {
                    className: 'review-detail-label',
                    key: 'label'
                }, 'Severity'),
                React.createElement('div', {
                    className: 'review-detail-value',
                    key: 'value'
                }, React.createElement('span', {
                    className: `threat-severity ${item.severity.toLowerCase()}`
                }, item.severity))
            ]));
        }

        if (item.category) {
            detailsChildren.push(React.createElement('div', {
                className: 'review-detail',
                key: 'category'
            }, [
                React.createElement('div', {
                    className: 'review-detail-label',
                    key: 'label'
                }, 'Category'),
                React.createElement('div', {
                    className: 'review-detail-value',
                    key: 'value'
                }, item.category)
            ]));
        }

        const sectionChildren = [
            React.createElement('h3', {
                className: 'review-section-title',
                key: 'title'
            }, [
                React.createElement('span', {
                    className: 'review-section-icon',
                    'aria-hidden': 'true',
                    key: 'icon'
                }, '📋'),
                'Item Details'
            ]),
            
            React.createElement('div', {
                className: 'review-details',
                key: 'details'
            }, detailsChildren)
        ];

        if (item.description) {
            sectionChildren.push(React.createElement('div', {
                className: 'review-description-full',
                key: 'description'
            }, [
                React.createElement('h4', { key: 'title' }, 'Description'),
                React.createElement('p', { key: 'content' }, item.description)
            ]));
        }

        if (item.context) {
            sectionChildren.push(React.createElement('div', {
                className: 'review-context',
                key: 'context'
            }, [
                React.createElement('h4', { key: 'title' }, 'Context'),
                React.createElement('div', {
                    className: 'review-context-content',
                    key: 'content'
                }, typeof item.context === 'string' ?
                    React.createElement('p', {}, item.context) :
                    React.createElement('div', {
                        className: 'json-viewer'
                    }, React.createElement('pre', {
                        dangerouslySetInnerHTML: { 
                            __html: window.PipelineComponents?.highlightJSON(
                                window.CoreUtilities?.safeJsonStringify(item.context, '{}')
                            ) || JSON.stringify(item.context, null, 2)
                        }
                    }))
                )
            ]));
        }

        if (item.question) {
            sectionChildren.push(React.createElement('div', {
                className: 'review-question-section',
                key: 'question'
            }, [
                React.createElement('h4', { key: 'title' }, 'Review Question'),
                React.createElement('div', {
                    className: 'review-question-content',
                    key: 'content'
                }, item.question)
            ]));
        }

        return React.createElement('div', {
            className: 'review-section'
        }, sectionChildren);
    };

    // ===== REVIEW DECISION FORM =====

    /**
     * Form for making review decisions
     */
    const ReviewDecisionForm = ({ 
        decision, 
        onDecisionChange, 
        comments, 
        onCommentsChange 
    }) => {
        const decisions = [
            {
                value: 'approve',
                label: 'Approve',
                icon: '✓',
                description: 'Accept this item as valid and accurate'
            },
            {
                value: 'modify',
                label: 'Modify',
                icon: '✏️',
                description: 'Accept with modifications or corrections'
            },
            {
                value: 'reject',
                label: 'Reject',
                icon: '✗',
                description: 'Reject this item as invalid or incorrect'
            }
        ];

        return React.createElement('div', {
            className: 'review-section'
        }, [
            React.createElement('h3', {
                className: 'review-section-title',
                key: 'title'
            }, [
                React.createElement('span', {
                    className: 'review-section-icon',
                    'aria-hidden': 'true',
                    key: 'icon'
                }, '⚖️'),
                'Your Decision'
            ]),
            
            React.createElement('div', {
                className: 'decision-buttons',
                role: 'radiogroup',
                'aria-labelledby': 'decision-group-label',
                key: 'buttons'
            }, React.createElement('fieldset', {}, [
                React.createElement('legend', {
                    id: 'decision-group-label',
                    className: 'sr-only',
                    key: 'legend'
                }, 'Choose your review decision'),
                ...decisions.map((decisionOption) => 
                    React.createElement('button', {
                        key: decisionOption.value,
                        type: 'button',
                        className: `decision-btn ${decision === decisionOption.value ? `active ${decisionOption.value}` : ''}`,
                        onClick: () => onDecisionChange(decisionOption.value),
                        role: 'radio',
                        'aria-checked': decision === decisionOption.value,
                        'aria-describedby': `decision-${decisionOption.value}-desc`
                    }, [
                        React.createElement('div', {
                            className: 'decision-icon',
                            'aria-hidden': 'true',
                            key: 'icon'
                        }, decisionOption.icon),
                        React.createElement('div', {
                            className: 'decision-label',
                            key: 'label'
                        }, decisionOption.label),
                        React.createElement('div', {
                            id: `decision-${decisionOption.value}-desc`,
                            className: 'hint',
                            key: 'hint'
                        }, decisionOption.description)
                    ])
                )
            ])),
            
            React.createElement('div', {
                className: 'review-comments',
                key: 'comments'
            }, [
                React.createElement('label', {
                    htmlFor: 'review-comments-input',
                    key: 'label'
                }, `Comments ${decision === 'modify' || decision === 'reject' ? '(Required)' : '(Optional)'}`),
                React.createElement('textarea', {
                    id: 'review-comments-input',
                    className: 'form-textarea',
                    value: comments,
                    onChange: (e) => onCommentsChange(e.target.value),
                    placeholder: decision === 'modify' 
                        ? 'Please describe the modifications needed...'
                        : decision === 'reject'
                            ? 'Please explain why this item should be rejected...'
                            : 'Add any additional comments or notes...',
                    rows: '4',
                    required: decision === 'modify' || decision === 'reject',
                    key: 'textarea'
                })
            ])
        ]);
    };

    // ===== EXPORTS =====

    const ReviewSystem = {
        ReviewPanel,
        ReviewControls,
        ReviewQueue,
        ReviewItem,
        ReviewModal,
        ReviewItemDetails,
        ReviewDecisionForm
    };

    // Make available globally
    window.ReviewSystem = ReviewSystem;
    window.ReviewPanel = ReviewPanel;
    window.ReviewQueue = ReviewQueue;

    console.log('Review System loaded successfully');

})(window);