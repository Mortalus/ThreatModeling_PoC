/* ===== PIPELINE-COMPONENTS.JS - Pipeline-Specific Components ===== */

/**
 * React components specific to the threat modeling pipeline functionality.
 * Uses React.createElement instead of JSX for browser compatibility.
 */

(function(window) {
    'use strict';

    // ===== FILE UPLOAD COMPONENT =====

    /**
     * File upload component with drag and drop support
     */
    const FileUploadComponent = ({ onUpload, loading, accept = window.CoreUtilities?.APP_CONFIG?.supportedFileTypes?.join(',') || '.txt,.pdf,.doc,.docx' }) => {
        const [dragActive, setDragActive] = React.useState(false);
        const [uploadProgress, setUploadProgress] = React.useState(0);
        const [uploadError, setUploadError] = React.useState(null);
        const fileInputRef = React.useRef(null);

        // Handle drag events
        const handleDrag = React.useCallback((e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (e.type === "dragenter" || e.type === "dragover") {
                setDragActive(true);
            } else if (e.type === "dragleave") {
                setDragActive(false);
            }
        }, []);

        // Handle drop event
        const handleDrop = React.useCallback((e) => {
            e.preventDefault();
            e.stopPropagation();
            setDragActive(false);
            setUploadError(null);
            
            if (loading) return;
            
            const files = e.dataTransfer?.files;
            if (files?.[0]) {
                handleFileSelection(files[0]);
            }
        }, [loading]);

        // Handle file input change
        const handleChange = React.useCallback((e) => {
            e.preventDefault();
            setUploadError(null);
            
            if (loading) return;
            
            const files = e.target?.files;
            if (files?.[0]) {
                handleFileSelection(files[0]);
            }
        }, [loading]);

        // Process selected file
        const handleFileSelection = React.useCallback(async (file) => {
            const validation = window.CoreUtilities?.validateFile(file);
            
            if (!validation?.valid) {
                setUploadError(validation?.errors?.join(', ') || 'Invalid file');
                return;
            }

            try {
                setUploadProgress(0);
                await onUpload(file, setUploadProgress);
                setUploadProgress(100);
                
                if (fileInputRef.current) {
                    fileInputRef.current.value = '';
                }
            } catch (error) {
                setUploadError(error.message || 'Upload failed');
                setUploadProgress(0);
            }
        }, [onUpload]);

        // Handle click to open file dialog
        const handleClick = React.useCallback(() => {
            if (!loading && fileInputRef.current) {
                fileInputRef.current.click();
            }
        }, [loading]);

        // Handle keyboard interaction
        const handleKeyDown = React.useCallback((event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                handleClick();
            }
        }, [handleClick]);

        const uploadAreaClasses = React.useMemo(() => {
            const classes = ['upload-area'];
            if (dragActive) classes.push('dragging');
            if (loading) classes.push('uploading');
            if (uploadError) classes.push('error');
            return classes.join(' ');
        }, [dragActive, loading, uploadError]);

        const uploadChildren = [
            React.createElement('input', {
                ref: fileInputRef,
                id: 'file-input',
                type: 'file',
                style: { display: 'none' },
                onChange: handleChange,
                accept: accept,
                disabled: loading,
                'aria-hidden': 'true',
                key: 'input'
            }),
            
            React.createElement('div', {
                className: 'upload-icon',
                'aria-hidden': 'true',
                key: 'icon'
            }, loading ? '⏳' : uploadError ? '❌' : '📁'),
            
            React.createElement('div', {
                className: 'upload-title',
                key: 'title'
            }, loading ? 'Processing...' : uploadError ? 'Upload Failed' : 'Drop files here or click to browse'),
            
            React.createElement('div', {
                id: 'upload-instructions',
                className: 'upload-description',
                key: 'description'
            }, uploadError ? 
                React.createElement('span', {
                    className: 'upload-error'
                }, uploadError) :
                [
                    React.createElement('div', { key: 'types' }, 'Supports TXT, PDF, DOC, DOCX files'),
                    React.createElement('div', { key: 'size' }, 
                        `Maximum file size: ${window.CoreUtilities?.formatFileSize(window.CoreUtilities?.APP_CONFIG?.maxFileSize || 52428800)}`
                    )
                ]
            )
        ];

        if (loading && uploadProgress > 0) {
            uploadChildren.push(React.createElement('div', {
                className: 'upload-progress',
                key: 'progress'
            }, [
                React.createElement('div', {
                    className: 'upload-progress-bar',
                    style: { width: `${uploadProgress}%` },
                    key: 'bar'
                }),
                React.createElement('div', {
                    className: 'upload-progress-text',
                    key: 'text'
                }, `${uploadProgress}%`)
            ]));
        }

        return React.createElement('div', {
            className: uploadAreaClasses,
            onDragEnter: handleDrag,
            onDragLeave: handleDrag,
            onDragOver: handleDrag,
            onDrop: handleDrop,
            onClick: handleClick,
            onKeyDown: handleKeyDown,
            role: 'button',
            tabIndex: loading ? -1 : 0,
            'aria-label': 'Upload file area',
            'aria-describedby': 'upload-instructions'
        }, uploadChildren);
    };

    // ===== STEP CONTENT DISPLAY =====

    /**
     * Component to display content for each pipeline step
     */
    const StepContentDisplay = ({ 
        step, 
        stepIndex, 
        pipelineState, 
        runStep, 
        loading, 
        onUpload,
        modelConfig 
    }) => {
        // Handle file upload step
        if (stepIndex === 0 && step.status === 'pending') {
            return React.createElement('div', {
                className: 'card'
            }, [
                React.createElement('div', {
                    className: 'card-header',
                    key: 'header'
                }, [
                    React.createElement('h2', { key: 'title' }, [
                        '📄 ',
                        step.name
                    ]),
                    React.createElement('span', {
                        className: `tag tag-${step.status}`,
                        key: 'tag'
                    }, window.CoreUtilities?.capitalize(step.status) || step.status)
                ]),
                React.createElement('div', {
                    className: 'card-body',
                    key: 'body'
                }, React.createElement(FileUploadComponent, {
                    onUpload: onUpload,
                    loading: loading
                }))
            ]);
        }

        const cardChildren = [
            React.createElement('div', {
                className: 'card-header',
                key: 'header'
            }, [
                React.createElement('h2', { key: 'title' }, [
                    React.createElement('span', {
                        'aria-hidden': 'true',
                        key: 'icon'
                    }, window.CoreUtilities?.PIPELINE_STEPS?.[stepIndex]?.icon || '📋'),
                    step.name
                ]),
                React.createElement('span', {
                    className: `tag tag-${step.status}`,
                    key: 'tag'
                }, window.CoreUtilities?.capitalize(step.status) || step.status)
            ])
        ];

        const bodyChildren = [];

        // Display step data if available
        if (step.data) {
            bodyChildren.push(React.createElement('div', {
                className: 'step-data-section',
                key: 'data'
            }, [
                React.createElement('h3', { key: 'title' }, 'Results'),
                React.createElement(StepDataViewer, {
                    data: step.data,
                    stepType: step.name,
                    key: 'viewer'
                })
            ]));
        }

        // Display model information
        if (modelConfig && stepIndex > 0) {
            bodyChildren.push(React.createElement('div', {
                className: 'step-model-section',
                key: 'model'
            }, [
                React.createElement('h4', { key: 'title' }, 'Model Configuration'),
                React.createElement('div', {
                    className: 'model-info',
                    key: 'info'
                }, [
                    React.createElement('span', {
                        className: 'model-provider',
                        key: 'provider'
                    }, modelConfig.provider === 'ollama' ? '🖥️ Local' : '☁️ Cloud'),
                    React.createElement('span', {
                        className: 'model-name',
                        key: 'name'
                    }, modelConfig.model?.split(/[:\/]/).pop() || 'Default')
                ])
            ]));
        }

        // Action buttons based on step status
        bodyChildren.push(React.createElement(StepActions, {
            step: step,
            stepIndex: stepIndex,
            pipelineState: pipelineState,
            runStep: runStep,
            loading: loading,
            key: 'actions'
        }));

        cardChildren.push(React.createElement('div', {
            className: 'card-body',
            key: 'body'
        }, bodyChildren));

        return React.createElement('div', {
            className: 'card'
        }, cardChildren);
    };

    // ===== STEP DATA VIEWER =====

    /**
     * Component to display step data in appropriate format
     */
    const StepDataViewer = ({ data, stepType }) => {
        const [viewMode, setViewMode] = React.useState('formatted');
        const [expandedItems, setExpandedItems] = React.useState(new Set());

        if (!data) return null;

        const toggleExpanded = (itemId) => {
            setExpandedItems(prev => {
                const newSet = new Set(prev);
                if (newSet.has(itemId)) {
                    newSet.delete(itemId);
                } else {
                    newSet.add(itemId);
                }
                return newSet;
            });
        };

        const renderFormattedData = () => {
            if (stepType?.toLowerCase().includes('threat')) {
                return React.createElement(ThreatDataViewer, {
                    data: data,
                    expandedItems: expandedItems,
                    onToggleExpanded: toggleExpanded
                });
            }
            
            if (stepType?.toLowerCase().includes('dfd')) {
                return React.createElement(DFDDataViewer, { data: data });
            }
            
            if (stepType?.toLowerCase().includes('attack')) {
                return React.createElement(AttackPathViewer, {
                    data: data,
                    expandedItems: expandedItems,
                    onToggleExpanded: toggleExpanded
                });
            }
            
            return React.createElement(GenericDataViewer, { data: data });
        };

        return React.createElement('div', {
            className: 'step-data-viewer'
        }, [
            React.createElement('div', {
                className: 'data-viewer-controls',
                key: 'controls'
            }, React.createElement('div', {
                className: 'view-mode-tabs'
            }, [
                React.createElement('button', {
                    className: `tab ${viewMode === 'formatted' ? 'active' : ''}`,
                    onClick: () => setViewMode('formatted'),
                    key: 'formatted'
                }, '📊 Formatted'),
                React.createElement('button', {
                    className: `tab ${viewMode === 'json' ? 'active' : ''}`,
                    onClick: () => setViewMode('json'),
                    key: 'json'
                }, '📝 Raw JSON')
            ])),
            
            React.createElement('div', {
                className: 'data-viewer-content',
                key: 'content'
            }, viewMode === 'formatted' ? 
                renderFormattedData() :
                React.createElement('div', {
                    className: 'json-viewer'
                }, React.createElement('pre', {
                    dangerouslySetInnerHTML: { 
                        __html: highlightJSON(window.CoreUtilities?.safeJsonStringify(data, '{}'))
                    }
                }))
            )
        ]);
    };

    // ===== GENERIC DATA VIEWER =====

    /**
     * Generic data viewer for unknown data types
     */
    const GenericDataViewer = ({ data }) => {
        if (Array.isArray(data)) {
            return React.createElement('div', {
                className: 'generic-list'
            }, data.map((item, index) => 
                React.createElement('div', {
                    key: index,
                    className: 'generic-item'
                }, typeof item === 'object' ? 
                    React.createElement('div', {
                        className: 'json-viewer'
                    }, React.createElement('pre', {
                        dangerouslySetInnerHTML: { 
                            __html: highlightJSON(window.CoreUtilities?.safeJsonStringify(item, '{}'))
                        }
                    })) :
                    React.createElement('div', {}, String(item))
                )
            ));
        }
        
        if (typeof data === 'object') {
            return React.createElement('div', {
                className: 'json-viewer'
            }, React.createElement('pre', {
                dangerouslySetInnerHTML: { 
                    __html: highlightJSON(window.CoreUtilities?.safeJsonStringify(data, '{}'))
                }
            }));
        }
        
        return React.createElement('div', {
            className: 'generic-text'
        }, String(data));
    };

    // ===== THREAT DATA VIEWER =====

    /**
     * Specialized viewer for threat data
     */
    const ThreatDataViewer = ({ data, expandedItems, onToggleExpanded }) => {
        const threats = Array.isArray(data) ? data : data?.threats || [];
        
        if (threats.length === 0) {
            return React.createElement('div', {
                className: 'no-data-message'
            }, [
                React.createElement('span', {
                    'aria-hidden': 'true',
                    key: 'icon'
                }, '🔍'),
                React.createElement('p', { key: 'text' }, 'No threats identified in this step.')
            ]);
        }

        return React.createElement('div', {
            className: 'threats-list'
        }, threats.map((threat, index) => {
            const threatId = threat.id || `threat-${index}`;
            const isExpanded = expandedItems.has(threatId);
            
            const threatChildren = [
                React.createElement('div', {
                    className: 'threat-header',
                    key: 'header'
                }, [
                    React.createElement('button', {
                        className: 'threat-toggle',
                        onClick: () => onToggleExpanded(threatId),
                        'aria-expanded': isExpanded,
                        'aria-label': `${isExpanded ? 'Collapse' : 'Expand'} threat details`,
                        key: 'toggle'
                    }, React.createElement('span', {
                        className: 'toggle-icon',
                        'aria-hidden': 'true'
                    }, isExpanded ? '▼' : '▶')),
                    
                    React.createElement('div', {
                        className: 'threat-title-section',
                        key: 'title-section'
                    }, [
                        React.createElement('h4', {
                            className: 'threat-title',
                            key: 'title'
                        }, threat.title || threat.name || `Threat ${index + 1}`),
                        React.createElement('div', {
                            className: 'threat-meta',
                            key: 'meta'
                        }, [
                            React.createElement('span', {
                                className: `threat-severity ${threat.severity?.toLowerCase() || 'medium'}`,
                                key: 'severity'
                            }, threat.severity || 'Medium'),
                            threat.category && React.createElement('span', {
                                className: 'threat-category',
                                key: 'category'
                            }, threat.category)
                        ])
                    ])
                ])
            ];

            if (isExpanded) {
                const detailChildren = [];

                if (threat.description) {
                    detailChildren.push(React.createElement('div', {
                        className: 'threat-section',
                        key: 'description'
                    }, [
                        React.createElement('h5', { key: 'title' }, 'Description'),
                        React.createElement('p', { key: 'content' }, threat.description)
                    ]));
                }

                if (threat.impact) {
                    detailChildren.push(React.createElement('div', {
                        className: 'threat-section',
                        key: 'impact'
                    }, [
                        React.createElement('h5', { key: 'title' }, 'Impact'),
                        React.createElement('p', { key: 'content' }, threat.impact)
                    ]));
                }

                if (threat.mitigation) {
                    detailChildren.push(React.createElement('div', {
                        className: 'threat-section',
                        key: 'mitigation'
                    }, [
                        React.createElement('h5', { key: 'title' }, 'Mitigation'),
                        React.createElement('p', { key: 'content' }, threat.mitigation)
                    ]));
                }

                if (threat.assets && threat.assets.length > 0) {
                    detailChildren.push(React.createElement('div', {
                        className: 'threat-section',
                        key: 'assets'
                    }, [
                        React.createElement('h5', { key: 'title' }, 'Affected Assets'),
                        React.createElement('ul', {
                            className: 'threat-assets',
                            key: 'list'
                        }, threat.assets.map((asset, idx) => 
                            React.createElement('li', { key: idx }, asset)
                        ))
                    ]));
                }

                threatChildren.push(React.createElement('div', {
                    className: 'threat-details',
                    key: 'details'
                }, detailChildren));
            }

            return React.createElement('div', {
                key: threatId,
                className: `threat-item ${threat.severity?.toLowerCase() || 'medium'}`
            }, threatChildren);
        }));
    };

    // ===== DFD DATA VIEWER =====

    /**
     * Specialized viewer for DFD (Data Flow Diagram) data
     */
    const DFDDataViewer = ({ data }) => {
        const entities = data?.entities || [];
        const processes = data?.processes || [];
        const dataStores = data?.dataStores || [];
        const dataFlows = data?.dataFlows || [];

        const summaryChildren = [
            React.createElement('div', {
                className: 'summary-stats',
                key: 'stats'
            }, [
                React.createElement('div', {
                    className: 'stat-item',
                    key: 'entities'
                }, [
                    React.createElement('span', {
                        className: 'stat-icon',
                        'aria-hidden': 'true',
                        key: 'icon'
                    }, '👤'),
                    React.createElement('span', {
                        className: 'stat-label',
                        key: 'label'
                    }, 'Entities'),
                    React.createElement('span', {
                        className: 'stat-value',
                        key: 'value'
                    }, entities.length)
                ]),
                React.createElement('div', {
                    className: 'stat-item',
                    key: 'processes'
                }, [
                    React.createElement('span', {
                        className: 'stat-icon',
                        'aria-hidden': 'true',
                        key: 'icon'
                    }, '⚙️'),
                    React.createElement('span', {
                        className: 'stat-label',
                        key: 'label'
                    }, 'Processes'),
                    React.createElement('span', {
                        className: 'stat-value',
                        key: 'value'
                    }, processes.length)
                ]),
                React.createElement('div', {
                    className: 'stat-item',
                    key: 'datastores'
                }, [
                    React.createElement('span', {
                        className: 'stat-icon',
                        'aria-hidden': 'true',
                        key: 'icon'
                    }, '💾'),
                    React.createElement('span', {
                        className: 'stat-label',
                        key: 'label'
                    }, 'Data Stores'),
                    React.createElement('span', {
                        className: 'stat-value',
                        key: 'value'
                    }, dataStores.length)
                ]),
                React.createElement('div', {
                    className: 'stat-item',
                    key: 'dataflows'
                }, [
                    React.createElement('span', {
                        className: 'stat-icon',
                        'aria-hidden': 'true',
                        key: 'icon'
                    }, '🔗'),
                    React.createElement('span', {
                        className: 'stat-label',
                        key: 'label'
                    }, 'Data Flows'),
                    React.createElement('span', {
                        className: 'stat-value',
                        key: 'value'
                    }, dataFlows.length)
                ])
            ])
        ];

        const sectionsChildren = [];

        if (entities.length > 0) {
            sectionsChildren.push(React.createElement(DFDSection, {
                title: 'External Entities',
                items: entities,
                icon: '👤',
                key: 'entities'
            }));
        }

        if (processes.length > 0) {
            sectionsChildren.push(React.createElement(DFDSection, {
                title: 'Processes',
                items: processes,
                icon: '⚙️',
                key: 'processes'
            }));
        }

        if (dataStores.length > 0) {
            sectionsChildren.push(React.createElement(DFDSection, {
                title: 'Data Stores',
                items: dataStores,
                icon: '💾',
                key: 'datastores'
            }));
        }

        if (dataFlows.length > 0) {
            sectionsChildren.push(React.createElement(DFDSection, {
                title: 'Data Flows',
                items: dataFlows,
                icon: '🔗',
                key: 'dataflows'
            }));
        }

        return React.createElement('div', {
            className: 'dfd-viewer'
        }, [
            React.createElement('div', {
                className: 'dfd-summary',
                key: 'summary'
            }, summaryChildren),
            React.createElement('div', {
                className: 'dfd-sections',
                key: 'sections'
            }, sectionsChildren)
        ]);
    };

    /**
     * DFD section component
     */
    const DFDSection = ({ title, items, icon }) => {
        return React.createElement('div', {
            className: 'dfd-section'
        }, [
            React.createElement('h4', {
                className: 'dfd-section-title',
                key: 'title'
            }, [
                React.createElement('span', {
                    'aria-hidden': 'true',
                    key: 'icon'
                }, icon),
                title
            ]),
            React.createElement('div', {
                className: 'dfd-items',
                key: 'items'
            }, items.map((item, index) => {
                const itemChildren = [
                    React.createElement('div', {
                        className: 'dfd-item-name',
                        key: 'name'
                    }, item.name || item.title || `Item ${index + 1}`)
                ];

                if (item.description) {
                    itemChildren.push(React.createElement('div', {
                        className: 'dfd-item-description',
                        key: 'description'
                    }, item.description));
                }

                if (item.type) {
                    itemChildren.push(React.createElement('div', {
                        className: 'dfd-item-type',
                        key: 'type'
                    }, `Type: ${item.type}`));
                }

                return React.createElement('div', {
                    key: index,
                    className: 'dfd-item'
                }, itemChildren);
            }))
        ]);
    };

    // ===== ATTACK PATH VIEWER =====

    /**
     * Specialized viewer for attack path data
     */
    const AttackPathViewer = ({ data, expandedItems, onToggleExpanded }) => {
        const attackPaths = Array.isArray(data) ? data : data?.attackPaths || data?.paths || [];
        
        if (attackPaths.length === 0) {
            return React.createElement('div', {
                className: 'no-data-message'
            }, [
                React.createElement('span', {
                    'aria-hidden': 'true',
                    key: 'icon'
                }, '🛡️'),
                React.createElement('p', { key: 'text' }, 'No attack paths identified in this analysis.')
            ]);
        }

        return React.createElement('div', {
            className: 'attack-paths-list'
        }, attackPaths.map((path, index) => {
            const pathId = path.id || `path-${index}`;
            const isExpanded = expandedItems.has(pathId);
            
            // Similar structure to ThreatDataViewer but for attack paths
            // Implementation would be similar but with attack path specific fields
            return React.createElement('div', {
                key: pathId,
                className: 'attack-path-item'
            }, `Attack Path ${index + 1}: ${path.name || 'Unnamed'}`);
        }));
    };

    // ===== STEP ACTIONS =====

    /**
     * Component for step-specific action buttons
     */
    const StepActions = ({ step, stepIndex, pipelineState, runStep, loading }) => {
        const canRunStep = React.useMemo(() => {
            if (loading || stepIndex === 0) return false;
            if (stepIndex > 0 && pipelineState.steps[stepIndex - 1].status !== 'completed') return false;
            return true;
        }, [loading, stepIndex, pipelineState.steps]);

        if (step.status === 'pending' && stepIndex > 0) {
            return React.createElement('div', {
                className: 'step-actions'
            }, React.createElement('button', {
                className: 'btn btn-primary',
                onClick: () => runStep(stepIndex),
                disabled: !canRunStep,
                'aria-label': `Run ${step.name} step`
            }, [
                React.createElement('span', {
                    'aria-hidden': 'true',
                    key: 'icon'
                }, '▶️'),
                `Run ${step.name}`
            ]));
        }
        
        if (step.status === 'error') {
            return React.createElement('div', {
                className: 'step-actions'
            }, React.createElement('div', {
                className: 'error-box'
            }, [
                React.createElement('p', { key: 'message' }, [
                    React.createElement('span', {
                        'aria-hidden': 'true',
                        key: 'icon'
                    }, '❌'),
                    'This step failed to execute. Check the console for details.'
                ]),
                React.createElement('button', {
                    className: 'btn btn-secondary',
                    onClick: () => runStep(stepIndex),
                    disabled: !canRunStep,
                    'aria-label': `Retry ${step.name} step`,
                    key: 'retry'
                }, [
                    React.createElement('span', {
                        'aria-hidden': 'true',
                        key: 'icon'
                    }, '🔄'),
                    `Retry ${step.name}`
                ])
            ]));
        }
        
        if (step.status === 'completed') {
            return React.createElement('div', {
                className: 'step-actions'
            }, [
                React.createElement('div', {
                    className: 'success-message',
                    key: 'success'
                }, [
                    React.createElement('span', {
                        'aria-hidden': 'true',
                        key: 'icon'
                    }, '✅'),
                    React.createElement('span', { key: 'text' }, 'Step completed successfully!')
                ]),
                React.createElement('button', {
                    className: 'btn btn-secondary btn-sm',
                    onClick: () => runStep(stepIndex),
                    disabled: !canRunStep,
                    'aria-label': `Re-run ${step.name} step`,
                    key: 'rerun'
                }, [
                    React.createElement('span', {
                        'aria-hidden': 'true',
                        key: 'icon'
                    }, '🔄'),
                    'Re-run'
                ])
            ]);
        }
        
        return null;
    };

    // ===== JSON HIGHLIGHTING UTILITY =====

    /**
     * Highlight JSON syntax for better readability
     */
    const highlightJSON = (json) => {
        if (!json) return '';
        
        return json.replace(
            /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, 
            (match) => {
                let cls = 'json-number';
                if (/^"/.test(match)) {
                    cls = /:$/.test(match) ? 'json-key' : 'json-string';
                } else if (/true|false/.test(match)) {
                    cls = 'json-boolean';
                } else if (/null/.test(match)) {
                    cls = 'json-null';
                }
                return `<span class="${cls}">${match}</span>`;
            }
        );
    };

    // ===== EXPORTS =====

    const PipelineComponents = {
        FileUploadComponent,
        StepContentDisplay,
        StepDataViewer,
        ThreatDataViewer,
        DFDDataViewer,
        AttackPathViewer,
        GenericDataViewer,
        StepActions,
        highlightJSON
    };

    // Make available globally
    window.PipelineComponents = PipelineComponents;
    window.FileUploadComponent = FileUploadComponent;
    window.StepContentDisplay = StepContentDisplay;
    window.highlightJSON = highlightJSON;

    console.log('Pipeline Components loaded successfully');

})(window);