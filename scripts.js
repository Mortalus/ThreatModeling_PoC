// API Configuration
const API_BASE = 'http://localhost:5000/api';

// Initialize Mermaid
mermaid.initialize({ 
    startOnLoad: true,
    theme: 'dark',
    securityLevel: 'loose',
    themeVariables: {
        primaryColor: '#8b5cf6',
        primaryTextColor: '#fff',
        primaryBorderColor: '#7c3aed',
        lineColor: '#5b21b6',
        secondaryColor: '#3b82f6',
        tertiaryColor: '#10b981',
        background: '#1a1f2e',
        mainBkg: '#0f1420',
        secondBkg: '#2d3548',
        tertiaryBkg: '#374151'
    }
});

// Settings management
let currentSettings = {
    llm_provider: 'scaleway',
    llm_model: 'llama-3.3-70b-instruct',
    scw_secret_key: '',
    local_llm_endpoint: 'http://localhost:11434/api/generate',
    timeout: 5000,
    temperature: 0.2,
    max_tokens: 4096,
    enable_quality_check: true,
    enable_multi_pass: true,
    enable_mermaid: true,
    enable_llm_enrichment: true,
    mitre_enabled: true
};

function openSettings() {
    loadSettingsToUI();
    document.getElementById('settingsModal').style.display = 'block';
}

function closeSettingsModal() {
    document.getElementById('settingsModal').style.display = 'none';
}

function loadSettingsToUI() {
    console.log('Loading settings from:', `${API_BASE}/config`);
    
    fetch(`${API_BASE}/config`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new TypeError("Response was not JSON!");
            }
            return response.json();
        })
        .then(config => {
            console.log('Loaded config:', config);
            currentSettings = { ...currentSettings, ...config };
            
            // Update UI elements
            document.getElementById('llm-provider').value = currentSettings.llm_provider;
            document.getElementById('llm-model').value = currentSettings.llm_model;
            document.getElementById('scw-api-key').value = currentSettings.scw_secret_key || '';
            document.getElementById('local-endpoint').value = currentSettings.local_llm_endpoint;
            document.getElementById('timeout').value = currentSettings.timeout;
            document.getElementById('temperature').value = currentSettings.temperature;
            document.getElementById('max-tokens').value = currentSettings.max_tokens;
            
            // Update checkboxes
            document.getElementById('enable-quality-check').checked = currentSettings.enable_quality_check;
            document.getElementById('enable-multi-pass').checked = currentSettings.enable_multi_pass;
            document.getElementById('enable-mermaid').checked = currentSettings.enable_mermaid;
            document.getElementById('enable-llm-enrichment').checked = currentSettings.enable_llm_enrichment;
            document.getElementById('mitre-enabled').checked = currentSettings.mitre_enabled;
            
            // Show/hide provider-specific fields
            toggleProviderFields();
        })
        .catch(error => {
            console.error('Failed to load settings:', error);
            showNotification('Failed to load settings: ' + error.message, 'error');
        });
}

function toggleProviderFields() {
    const provider = document.getElementById('llm-provider').value;
    if (provider === 'scaleway') {
        document.getElementById('api-key-group').style.display = 'block';
        document.getElementById('local-endpoint-group').style.display = 'none';
    } else {
        document.getElementById('api-key-group').style.display = 'none';
        document.getElementById('local-endpoint-group').style.display = 'block';
    }
}

function saveSettings() {
    const newSettings = {
        llm_provider: document.getElementById('llm-provider').value,
        llm_model: document.getElementById('llm-model').value,
        scw_secret_key: document.getElementById('scw-api-key').value,
        local_llm_endpoint: document.getElementById('local-endpoint').value,
        timeout: parseInt(document.getElementById('timeout').value),
        temperature: parseFloat(document.getElementById('temperature').value),
        max_tokens: parseInt(document.getElementById('max-tokens').value),
        enable_quality_check: document.getElementById('enable-quality-check').checked,
        enable_multi_pass: document.getElementById('enable-multi-pass').checked,
        enable_mermaid: document.getElementById('enable-mermaid').checked,
        enable_llm_enrichment: document.getElementById('enable-llm-enrichment').checked,
        mitre_enabled: document.getElementById('mitre-enabled').checked
    };
    
    console.log('Saving settings:', newSettings);
    
    fetch(`${API_BASE}/config`, {  // Make sure we're using the correct API_BASE
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(newSettings)
    })
    .then(response => {
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        
        // Check if response is ok
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Check content type
        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            throw new TypeError("Response was not JSON!");
        }
        
        return response.json();
    })
    .then(data => {
        console.log('Settings saved successfully:', data);
        showNotification('Settings saved successfully!', 'success');
        currentSettings = newSettings;
        closeSettingsModal();
    })
    .catch(error => {
        console.error('Settings save error:', error);
        showNotification('Failed to save settings: ' + error.message, 'error');
    });
}

// Event listeners for settings
document.addEventListener('DOMContentLoaded', function() {
    const providerSelect = document.getElementById('llm-provider');
    if (providerSelect) {
        providerSelect.addEventListener('change', toggleProviderFields);
    }
});

window.onclick = function(event) {
    const modal = document.getElementById('settingsModal');
    if (event.target === modal) {
        closeSettingsModal();
    }
}

// Notification System
const NotificationContainer = () => {
    const [notifications, setNotifications] = React.useState([]);
    
    React.useEffect(() => {
        window.showNotification = (message, type = 'info', duration = 5000) => {
            const id = Date.now();
            const notification = { id, message, type };
            
            setNotifications(prev => [...prev, notification]);
            
            setTimeout(() => {
                setNotifications(prev => prev.filter(n => n.id !== id));
            }, duration);
        };
    }, []);
    
    return (
        <div className="notification-container">
            {notifications.map(notification => (
                <div 
                    key={notification.id} 
                    className={`notification notification-${notification.type}`}
                    onClick={() => setNotifications(prev => prev.filter(n => n.id !== notification.id))}
                >
                    <span className="notification-icon">
                        {notification.type === 'success' && '✓'}
                        {notification.type === 'error' && '✗'}
                        {notification.type === 'warning' && '⚠'}
                        {notification.type === 'info' && 'ℹ'}
                    </span>
                    <span className="notification-message">{notification.message}</span>
                </div>
            ))}
        </div>
    );
};

// WebSocket Connection Status Component
const ConnectionStatus = ({ socket }) => {
    const [isConnected, setIsConnected] = React.useState(false);
    
    React.useEffect(() => {
        if (!socket) return;
        
        const onConnect = () => {
            setIsConnected(true);
            showNotification('Connected to server', 'success');
        };
        
        const onDisconnect = () => {
            setIsConnected(false);
            showNotification('Disconnected from server', 'error');
        };
        
        socket.on('connect', onConnect);
        socket.on('disconnect', onDisconnect);
        
        setIsConnected(socket.connected);
        
        return () => {
            socket.off('connect', onConnect);
            socket.off('disconnect', onDisconnect);
        };
    }, [socket]);
    
    return (
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-indicator"></span>
            <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
    );
};

// Review Queue Component
const ReviewQueue = ({ reviewItems, onReview }) => {
    const [selectedItem, setSelectedItem] = React.useState(null);
    
    if (!reviewItems || reviewItems.length === 0) {
        return (
            <div className="review-empty">
                <p>No items pending review</p>
            </div>
        );
    }
    
    return (
        <div className="review-queue">
            <h3>📋 Review Queue ({reviewItems.length} items)</h3>
            <div className="review-list">
                {reviewItems.map((item) => (
                    <div 
                        key={item.id} 
                        className={`review-item ${item.status === 'reviewed' ? 'reviewed' : 'pending'}`}
                        onClick={() => setSelectedItem(item)}
                    >
                        <div className="review-item-header">
                            <span className="review-type">{item.type}</span>
                            <span className={`confidence-badge ${item.confidence < 0.5 ? 'low' : item.confidence < 0.8 ? 'medium' : 'high'}`}>
                                {Math.round(item.confidence * 100)}% confidence
                            </span>
                        </div>
                        <div className="review-item-content">
                            <p>{item.value}</p>
                            {item.questions && item.questions[0] && (
                                <p className="review-question">{item.questions[0]}</p>
                            )}
                        </div>
                    </div>
                ))}
            </div>
            
            {selectedItem && (
                <ReviewModal 
                    item={selectedItem}
                    onClose={() => setSelectedItem(null)}
                    onSubmit={(review) => {
                        onReview(selectedItem.id, review);
                        setSelectedItem(null);
                    }}
                />
            )}
        </div>
    );
};

// Review Modal Component
const ReviewModal = ({ item, onClose, onSubmit }) => {
    const [decision, setDecision] = React.useState('');
    const [corrections, setCorrections] = React.useState({});
    const [comments, setComments] = React.useState('');
    const [reviewer, setReviewer] = React.useState('');
    
    const handleSubmit = () => {
        if (!decision || !reviewer) {
            showNotification('Please fill in all required fields', 'warning');
            return;
        }
        
        onSubmit({
            decision,
            corrections,
            comments,
            reviewer
        });
    };
    
    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="review-modal">
                <div className="modal-header">
                    <h3>Review Item</h3>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>
                
                <div className="modal-body">
                    <div className="review-details">
                        <p><strong>Type:</strong> {item.type}</p>
                        <p><strong>Value:</strong> {item.value}</p>
                        <p><strong>Confidence:</strong> {Math.round(item.confidence * 100)}%</p>
                    </div>
                    
                    {item.questions && (
                        <div className="review-questions">
                            <h4>Questions to Consider:</h4>
                            {item.questions.map((q, i) => (
                                <p key={i}>• {q}</p>
                            ))}
                        </div>
                    )}
                    
                    {item.attributes_needed && (
                        <div className="review-attributes">
                            <h4>Additional Information Needed:</h4>
                            {Object.entries(item.attributes_needed).map(([key, attr]) => (
                                <div key={key} className="form-group">
                                    <label>{attr.question}</label>
                                    <select 
                                        className="form-select"
                                        onChange={(e) => setCorrections({...corrections, [key]: e.target.value})}
                                    >
                                        <option value="">Select...</option>
                                        {attr.options.map(opt => (
                                            <option key={opt} value={opt}>{opt}</option>
                                        ))}
                                    </select>
                                    {attr.hint && <small className="hint">{attr.hint}</small>}
                                </div>
                            ))}
                        </div>
                    )}
                    
                    <div className="form-group">
                        <label>Decision *</label>
                        <div className="decision-buttons">
                            <button 
                                className={`decision-btn ${decision === 'approve' ? 'active approve' : ''}`}
                                onClick={() => setDecision('approve')}
                            >
                                ✅ Approve
                            </button>
                            <button 
                                className={`decision-btn ${decision === 'modify' ? 'active modify' : ''}`}
                                onClick={() => setDecision('modify')}
                            >
                                ✏️ Modify
                            </button>
                            <button 
                                className={`decision-btn ${decision === 'reject' ? 'active reject' : ''}`}
                                onClick={() => setDecision('reject')}
                            >
                                ❌ Reject
                            </button>
                        </div>
                    </div>
                    
                    <div className="form-group">
                        <label>Comments</label>
                        <textarea 
                            className="form-textarea"
                            rows={3}
                            value={comments}
                            onChange={(e) => setComments(e.target.value)}
                            placeholder="Add any additional comments..."
                        />
                    </div>
                    
                    <div className="form-group">
                        <label>Reviewer Name *</label>
                        <input 
                            type="text"
                            className="form-input"
                            value={reviewer}
                            onChange={(e) => setReviewer(e.target.value)}
                            placeholder="Your name"
                        />
                    </div>
                </div>
                
                <div className="modal-footer">
                    <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
                    <button className="btn btn-primary" onClick={handleSubmit}>Submit Review</button>
                </div>
            </div>
        </div>
    );
};

// File Upload Component
const FileUploadComponent = ({ onUpload, loading }) => {
    const [dragActive, setDragActive] = React.useState(false);
    
    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };
    
    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            onUpload(e.dataTransfer.files[0]);
        }
    };
    
    const handleChange = (e) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            onUpload(e.target.files[0]);
        }
    };
    
    return (
        <div 
            className={`upload-area ${dragActive ? 'dragging' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => !loading && document.getElementById('file-input').click()}
        >
            <input 
                id="file-input"
                type="file"
                style={{display: 'none'}}
                onChange={handleChange}
                accept=".txt,.pdf,.doc,.docx"
                disabled={loading}
            />
            <div style={{fontSize: '3em', marginBottom: '20px'}}>
                {loading ? '⏳' : '📁'}
            </div>
            <div style={{fontSize: '1.2em', marginBottom: '10px', fontWeight: '600'}}>
                {loading ? 'Processing...' : 'Drop files here or click to browse'}
            </div>
            <div style={{fontSize: '0.95em', color: '#9ca3af', marginBottom: '20px'}}>
                Supports TXT, PDF, DOC, DOCX files
            </div>
            <div style={{fontSize: '0.85em', color: '#6b7280'}}>
                Maximum file size: 50MB
            </div>
        </div>
    );
};

// Pipeline Step Component
const PipelineStep = ({ step, index, active, onClick }) => {
    const icons = ['📄', '🔗', '⚠️', '✨', '🎯'];
    
    return (
        <div 
            className={`pipeline-step ${active ? 'active' : ''} ${step.status}`}
            onClick={onClick}
        >
            <div className="step-title">
                <span>{icons[index]}</span>
                <span>{step.name}</span>
            </div>
            <div className="step-status" style={{fontSize: '0.85em', color: '#9ca3af'}}>
                {step.status === 'pending' && 'Ready to run'}
                {step.status === 'running' && 'Processing...'}
                {step.status === 'completed' && 'Completed'}
                {step.status === 'error' && 'Failed'}
            </div>
        </div>
    );
};

// JSON Highlighter
const highlightJSON = (obj) => {
    const json = JSON.stringify(obj, null, 2);
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, 
        function (match) {
            let cls = 'json-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                } else {
                    cls = 'json-string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'json-boolean';
            } else if (/null/.test(match)) {
                cls = 'json-null';
            }
            return '<span class="' + cls + '">' + match + '</span>';
        });
};

// Main App Component
const App = () => {
    const [pipelineState, setPipelineState] = React.useState({
        steps: [
            { id: 0, name: 'Document Upload', status: 'pending', data: null },
            { id: 1, name: 'DFD Extraction', status: 'pending', data: null },
            { id: 2, name: 'Threat Identification', status: 'pending', data: null },
            { id: 3, name: 'Threat Refinement', status: 'pending', data: null },
            { id: 4, name: 'Attack Path Analysis', status: 'pending', data: null }
        ]
    });
    
    const [currentStep, setCurrentStep] = React.useState(0);
    const [loading, setLoading] = React.useState(false);
    const [currentOperation, setCurrentOperation] = React.useState('');
    const [reviewQueue, setReviewQueue] = React.useState({});
    const [showReviewPanel, setShowReviewPanel] = React.useState(false);
    
    // Initialize WebSocket connection
    const socket = React.useMemo(() => io(API_BASE.replace('/api', '')), []);
    
    // Fetch review items
    const fetchReviewItems = async () => {
        try {
            const response = await fetch(`${API_BASE}/review-items`);
            if (response.ok) {
                const data = await response.json();
                setReviewQueue(data);
            }
        } catch (error) {
            console.error('Failed to fetch review items:', error);
        }
    };
    
    // Handle review submission
    const handleReview = async (itemId, review) => {
        try {
            const response = await fetch(`${API_BASE}/submit-review`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_id: itemId, ...review })
            });
            
            if (response.ok) {
                showNotification('Review submitted successfully', 'success');
                fetchReviewItems();
            }
        } catch (error) {
            showNotification('Failed to submit review', 'error');
        }
    };
    
    // WebSocket event handlers
    React.useEffect(() => {
        socket.on('pipeline_update', (data) => {
            if (data.step_outputs) {
                // Update step data
            }
        });
        
        socket.on('review_update', (data) => {
            fetchReviewItems();
        });
        
        socket.on('progress_update', (data) => {
            if (data.step !== undefined) {
                // Update progress for specific step
            }
        });
        
        return () => {
            socket.disconnect();
        };
    }, [socket]);
    
    // Load review items when steps complete
    React.useEffect(() => {
        const hasCompletedSteps = pipelineState.steps.some(s => s.status === 'completed');
        if (hasCompletedSteps) {
            fetchReviewItems();
        }
    }, [pipelineState.steps]);
    
    // Calculate total pending reviews
    const pendingReviewCount = React.useMemo(() => {
        return Array.isArray(reviewQueue) ? 
            reviewQueue.filter(item => item.status === 'pending').length : 0;
    }, [reviewQueue]);
    
    const updateStepStatus = (index, status, data = null) => {
        setPipelineState(prev => {
            const newSteps = [...prev.steps];
            newSteps[index] = { ...newSteps[index], status, data };
            return { ...prev, steps: newSteps };
        });
    };
    
    const handleUpload = async (file) => {
        setLoading(true);
        setCurrentOperation('Uploading document...');
        updateStepStatus(0, 'running');
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${API_BASE}/upload`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Upload failed');
            }
            
            updateStepStatus(0, 'completed', data);
            setLoading(false);
            setCurrentOperation('');
            showNotification('Document uploaded successfully!', 'success');
            
        } catch (error) {
            console.error('Upload error:', error);
            updateStepStatus(0, 'error');
            setLoading(false);
            setCurrentOperation('');
            showNotification(`Upload failed: ${error.message}`, 'error');
        }
    };
    
    const runStep = async (stepIndex) => {
        const step = pipelineState.steps[stepIndex];
        setLoading(true);
        updateStepStatus(stepIndex, 'running');
        
        const stepDescriptions = {
            1: 'Extracting DFD components from document...',
            2: 'Generating threats using STRIDE methodology...',
            3: 'Refining threats and removing duplicates...',
            4: 'Analyzing attack paths and scenarios...'
        };
        
        setCurrentOperation(stepDescriptions[stepIndex] || `Running ${step.name}...`);

        try {
            // CRITICAL FIX: Map frontend step indices to backend step numbers
            // Frontend: 0=Upload, 1=DFD, 2=Threats, 3=Refine, 4=Attack
            // Backend:  1=Upload, 2=DFD, 3=Threats, 4=Refine, 5=Attack
            
            // Since upload (index 0) is handled separately, we only handle indices 1-4
            // which map to backend steps 2-5
            const backendStepNumber = stepIndex + 1;  // 1->2, 2->3, 3->4, 4->5
            
            console.log(`Running ${step.name} (frontend index ${stepIndex} -> backend step ${backendStepNumber})`);
            
            const response = await fetch(`${API_BASE}/run-step`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    step: backendStepNumber,  // Send the mapped step number
                    input: stepIndex > 0 ? pipelineState.steps[stepIndex - 1]?.data : {}
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Step failed');
            }
            
            // Validate we got the expected response type
            if (stepIndex === 1) {  // DFD Extraction
                if (!data.dfd && !data.error) {
                    console.error('Expected DFD data but got:', data);
                    throw new Error('Invalid response - this looks like upload data, not DFD extraction');
                }
            }
            
            updateStepStatus(stepIndex, 'completed', data);
            setLoading(false);
            setCurrentOperation('');
            showNotification(`${step.name} completed successfully!`, 'success');
            
        } catch (error) {
            updateStepStatus(stepIndex, 'error');
            setLoading(false);
            setCurrentOperation('');
            showNotification(`Step failed: ${error.message}`, 'error');
        }
    };
    
    const resetPipeline = () => {
        if (loading) {
            showNotification('Cannot reset while a step is running', 'warning');
            return;
        }
        
        setPipelineState(prev => ({
            ...prev,
            steps: prev.steps.map(step => ({ ...step, status: 'pending', data: null }))
        }));
        setCurrentStep(0);
        showNotification('Pipeline reset successfully', 'success');
    };
    
    const runPipeline = async () => {
        // Check if upload is complete
        if (pipelineState.steps[0].status !== 'completed') {
            showNotification('Please upload a document first', 'warning');
            return;
        }
        
        // Run steps 1-4 (DFD, Threats, Refinement, Attack Paths)
        for (let i = 1; i < pipelineState.steps.length; i++) {
            await runStep(i);
            // Stop if any step fails
            if (pipelineState.steps[i].status === 'error') {
                break;
            }
        }
    };
    
    return (
        <div className="app-container">
            <NotificationContainer />
            
            <div className="sidebar">
                <div className="sidebar-header">
                    <h1>🛡️ Threat Modeling Pipeline</h1>
                    <p>AI-Powered Security Analysis</p>
                    <ConnectionStatus socket={socket} />
                </div>
                
                <div className="pipeline-steps">
                    {pipelineState.steps.map((step, index) => (
                        <PipelineStep
                            key={step.id}
                            step={step}
                            index={index}
                            active={currentStep === index}
                            onClick={() => setCurrentStep(index)}
                        />
                    ))}
                </div>
                
                {pendingReviewCount > 0 && (
                    <div className="review-button-container">
                        <button 
                            className="btn btn-warning btn-block"
                            onClick={() => setShowReviewPanel(!showReviewPanel)}
                        >
                            📋 Review Queue ({pendingReviewCount})
                        </button>
                    </div>
                )}
            </div>
            
            <div className="main-content">
                <div className="topbar">
                    <h2>{pipelineState.steps[currentStep].name}</h2>
                    <div className="nav-actions">
                        <button className="btn btn-secondary" onClick={openSettings}>
                            ⚙️ Settings
                        </button>
                        <button className="btn btn-secondary" onClick={resetPipeline}>
                            🔄 Reset Pipeline
                        </button>
                        <button className="btn btn-primary" onClick={runPipeline}>
                            ▶️ Run Pipeline
                        </button>
                    </div>
                </div>
                
                <div className="content-area">
                    {showReviewPanel && (
                        <ReviewQueue 
                            reviewItems={Array.isArray(reviewQueue) ? reviewQueue : []}
                            onReview={handleReview}
                        />
                    )}
                    
                    <StepContentDisplay 
                        step={pipelineState.steps[currentStep]}
                        stepIndex={currentStep}
                        currentStep={currentStep}
                        pipelineState={pipelineState}
                        runStep={runStep}
                        loading={loading}
                        onUpload={handleUpload}
                    />
                </div>
            </div>
            
            {loading && (
                <div className="loading-overlay">
                    <div style={{textAlign: 'center'}}>
                        <div className="loading-spinner"></div>
                        <p style={{marginTop: '20px', fontSize: '1.1em'}}>{currentOperation}</p>
                    </div>
                </div>
            )}
        </div>
    );
};

// Step Content Display Component (placeholder - add your specific step content here)
const StepContentDisplay = ({ step, stepIndex, currentStep, pipelineState, runStep, loading, onUpload }) => {
    if (stepIndex !== currentStep) return null;
    
    // Add your specific step content rendering logic here
    if (stepIndex === 0 && step.status === 'pending') {
        return <FileUploadComponent onUpload={onUpload} loading={loading} />;
    }
    
    return (
        <div className="card">
            <div className="card-header">
                <h2>{step.name}</h2>
                <span className={`tag tag-${step.status === 'completed' ? 'success' : 'info'}`}>
                    {step.status}
                </span>
            </div>
            {step.data && (
                <div className="json-viewer">
                    <pre dangerouslySetInnerHTML={{__html: highlightJSON(step.data)}} />
                </div>
            )}
            {step.status === 'pending' && stepIndex > 0 && (
                <button 
                    className="btn btn-primary" 
                    onClick={() => runStep(stepIndex)}
                    disabled={loading || (stepIndex > 0 && pipelineState.steps[stepIndex - 1].status !== 'completed')}
                >
                    Run {step.name}
                </button>
            )}
        </div>
    );
};

// Model configurations per provider
const MODEL_OPTIONS = {
    scaleway: [
        { id: 'llama-3.3-70b-instruct', name: 'Llama 3.3 70B Instruct', description: 'Best for complex analysis' },
        { id: 'llama-3.1-8b-instruct', name: 'Llama 3.1 8B Instruct', description: 'Faster, good for simple tasks' },
        { id: 'mistral-7b-instruct', name: 'Mistral 7B Instruct', description: 'Efficient general purpose' },
        { id: 'mixtral-8x7b-instruct', name: 'Mixtral 8x7B Instruct', description: 'High quality, balanced' },
        { id: 'qwen-2.5-72b-instruct', name: 'Qwen 2.5 72B', description: 'Excellent for technical content' }
    ],
    ollama: [
        { id: 'llama3.3:latest', name: 'Llama 3.3', description: 'Latest Llama model' },
        { id: 'llama3.1:latest', name: 'Llama 3.1', description: 'Stable version' },
        { id: 'mistral:latest', name: 'Mistral', description: 'Fast and efficient' },
        { id: 'mixtral:latest', name: 'Mixtral', description: 'MoE architecture' },
        { id: 'qwen2.5:latest', name: 'Qwen 2.5', description: 'Good for technical analysis' },
        { id: 'deepseek-coder:latest', name: 'DeepSeek Coder', description: 'Optimized for code analysis' },
        { id: 'phi3:latest', name: 'Phi-3', description: 'Small but capable' }
    ]
};

// Step-specific model recommendations
const STEP_MODEL_RECOMMENDATIONS = {
    1: { // DFD Extraction
        preferred: ['qwen-2.5-72b-instruct', 'llama-3.3-70b-instruct'],
        reason: 'Complex document understanding required'
    },
    2: { // Threat Identification
        preferred: ['llama-3.3-70b-instruct', 'mixtral-8x7b-instruct'],
        reason: 'Security expertise and STRIDE methodology'
    },
    3: { // Threat Refinement
        preferred: ['mixtral-8x7b-instruct', 'llama-3.1-8b-instruct'],
        reason: 'Pattern matching and deduplication'
    },
    4: { // Attack Path Analysis
        preferred: ['llama-3.3-70b-instruct', 'qwen-2.5-72b-instruct'],
        reason: 'Complex reasoning and path analysis'
    }
};

// Model Selection Modal Component
const ModelSelectionModal = ({ isOpen, onClose, stepIndex, currentConfig, onSelect }) => {
    const [selectedProvider, setSelectedProvider] = React.useState(currentConfig.provider || 'scaleway');
    const [selectedModel, setSelectedModel] = React.useState(currentConfig.model || '');
    const [showAdvanced, setShowAdvanced] = React.useState(false);
    const [customParams, setCustomParams] = React.useState({
        temperature: currentConfig.temperature || 0.2,
        max_tokens: currentConfig.max_tokens || 4096,
        top_p: currentConfig.top_p || 0.95
    });
    
    const recommendations = STEP_MODEL_RECOMMENDATIONS[stepIndex] || {};
    const models = MODEL_OPTIONS[selectedProvider] || [];
    
    const handleConfirm = () => {
        if (!selectedModel) {
            showNotification('Please select a model', 'warning');
            return;
        }
        
        onSelect({
            provider: selectedProvider,
            model: selectedModel,
            ...customParams
        });
        onClose();
    };
    
    if (!isOpen) return null;
    
    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="model-selection-modal">
                <div className="modal-header">
                    <h3>🤖 Select Model for Step {stepIndex}</h3>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>
                
                <div className="modal-body">
                    {/* Provider Selection */}
                    <div className="provider-tabs">
                        <button 
                            className={`provider-tab ${selectedProvider === 'scaleway' ? 'active' : ''}`}
                            onClick={() => {
                                setSelectedProvider('scaleway');
                                setSelectedModel('');
                            }}
                        >
                            <span className="provider-icon">☁️</span>
                            Scaleway (Cloud)
                        </button>
                        <button 
                            className={`provider-tab ${selectedProvider === 'ollama' ? 'active' : ''}`}
                            onClick={() => {
                                setSelectedProvider('ollama');
                                setSelectedModel('');
                            }}
                        >
                            <span className="provider-icon">🖥️</span>
                            Ollama (Local)
                        </button>
                    </div>
                    
                    {/* Model Recommendation */}
                    {recommendations.preferred && (
                        <div className="recommendation-box">
                            <p className="recommendation-title">💡 Recommended for this step:</p>
                            <p className="recommendation-reason">{recommendations.reason}</p>
                        </div>
                    )}
                    
                    {/* Model List */}
                    <div className="model-list">
                        {models.map(model => {
                            const isRecommended = recommendations.preferred?.includes(model.id);
                            return (
                                <div 
                                    key={model.id}
                                    className={`model-option ${selectedModel === model.id ? 'selected' : ''} ${isRecommended ? 'recommended' : ''}`}
                                    onClick={() => setSelectedModel(model.id)}
                                >
                                    <div className="model-info">
                                        <div className="model-name">
                                            {model.name}
                                            {isRecommended && <span className="recommended-badge">⭐ Recommended</span>}
                                        </div>
                                        <div className="model-description">{model.description}</div>
                                    </div>
                                    <div className="model-select-indicator">
                                        {selectedModel === model.id ? '✓' : '○'}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                    
                    {/* Advanced Parameters */}
                    <div className="advanced-section">
                        <button 
                            className="advanced-toggle"
                            onClick={() => setShowAdvanced(!showAdvanced)}
                        >
                            {showAdvanced ? '▼' : '▶'} Advanced Parameters
                        </button>
                        
                        {showAdvanced && (
                            <div className="advanced-params">
                                <div className="param-group">
                                    <label>Temperature (0-1)</label>
                                    <input 
                                        type="number"
                                        className="param-input"
                                        value={customParams.temperature}
                                        onChange={(e) => setCustomParams({...customParams, temperature: parseFloat(e.target.value)})}
                                        min="0"
                                        max="1"
                                        step="0.1"
                                    />
                                    <small>Higher = more creative, lower = more focused</small>
                                </div>
                                
                                <div className="param-group">
                                    <label>Max Tokens</label>
                                    <input 
                                        type="number"
                                        className="param-input"
                                        value={customParams.max_tokens}
                                        onChange={(e) => setCustomParams({...customParams, max_tokens: parseInt(e.target.value)})}
                                        min="1000"
                                        max="8192"
                                        step="100"
                                    />
                                    <small>Maximum response length</small>
                                </div>
                                
                                <div className="param-group">
                                    <label>Top P (0-1)</label>
                                    <input 
                                        type="number"
                                        className="param-input"
                                        value={customParams.top_p}
                                        onChange={(e) => setCustomParams({...customParams, top_p: parseFloat(e.target.value)})}
                                        min="0"
                                        max="1"
                                        step="0.05"
                                    />
                                    <small>Nucleus sampling threshold</small>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
                
                <div className="modal-footer">
                    <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
                    <button className="btn btn-primary" onClick={handleConfirm} disabled={!selectedModel}>
                        Use Selected Model
                    </button>
                </div>
            </div>
        </div>
    );
};

// Update PipelineStep component to show model info
const PipelineStepEnhanced = ({ step, index, active, onClick, modelConfig }) => {
    const icons = ['📄', '🔗', '⚠️', '✨', '🎯'];
    
    return (
        <div 
            className={`pipeline-step ${active ? 'active' : ''} ${step.status}`}
            onClick={onClick}
        >
            <div className="step-title">
                <span>{icons[index]}</span>
                <span>{step.name}</span>
            </div>
            <div className="step-status" style={{fontSize: '0.85em', color: '#9ca3af'}}>
                {step.status === 'pending' && 'Ready to run'}
                {step.status === 'running' && 'Processing...'}
                {step.status === 'completed' && 'Completed'}
                {step.status === 'error' && 'Failed'}
            </div>
            {modelConfig && index > 0 && (
                <div className="step-model-info">
                    <span className="model-badge">
                        {modelConfig.provider === 'ollama' ? '🖥️' : '☁️'} 
                        {modelConfig.model?.split(':')[0] || 'Default'}
                    </span>
                </div>
            )}
        </div>
    );
};

// Render the app
ReactDOM.render(<App />, document.getElementById('root'));