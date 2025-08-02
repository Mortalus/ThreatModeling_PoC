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

// --- Settings Management (Vanilla JS) ---

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
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
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
            
            toggleProviderFields();
        })
        .catch(error => {
            console.error('Failed to load settings:', error);
            if (window.showNotification) {
                showNotification('Failed to load settings: ' + error.message, 'error');
            }
        });
}

function toggleProviderFields() {
    const provider = document.getElementById('llm-provider').value;
    const apiKeyGroup = document.getElementById('api-key-group');
    const localEndpointGroup = document.getElementById('local-endpoint-group');
    
    if (provider === 'scaleway') {
        if (apiKeyGroup) apiKeyGroup.style.display = 'block';
        if (localEndpointGroup) localEndpointGroup.style.display = 'none';
    } else {
        if (apiKeyGroup) apiKeyGroup.style.display = 'none';
        if (localEndpointGroup) localEndpointGroup.style.display = 'block';
    }
}

function saveSettings() {
    const newSettings = {
        llm_provider: document.getElementById('llm-provider').value,
        llm_model: document.getElementById('llm-model').value,
        scw_secret_key: document.getElementById('scw-api-key').value,
        local_llm_endpoint: document.getElementById('local-endpoint').value,
        timeout: parseInt(document.getElementById('timeout').value, 10),
        temperature: parseFloat(document.getElementById('temperature').value),
        max_tokens: parseInt(document.getElementById('max-tokens').value, 10),
        enable_quality_check: document.getElementById('enable-quality-check').checked,
        enable_multi_pass: document.getElementById('enable-multi-pass').checked,
        enable_mermaid: document.getElementById('enable-mermaid').checked,
        enable_llm_enrichment: document.getElementById('enable-llm-enrichment').checked,
        mitre_enabled: document.getElementById('mitre-enabled').checked
    };
    
    console.log('Saving settings:', newSettings);
    
    fetch(`${API_BASE}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSettings)
    })
    .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
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

// Global Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    const providerSelect = document.getElementById('llm-provider');
    if (providerSelect) {
        providerSelect.addEventListener('change', toggleProviderFields);
    }
});

window.onclick = (event) => {
    const modal = document.getElementById('settingsModal');
    if (event.target === modal) {
        closeSettingsModal();
    }
};

// --- Helper Functions ---

const highlightJSON = (obj) => {
    if (obj === null || obj === undefined) return '';
    const json = JSON.stringify(obj, null, 2);
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, 
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
        });
};


// --- React Components ---

const NotificationContainer = () => {
    const [notifications, setNotifications] = React.useState([]);
    
    React.useEffect(() => {
        window.showNotification = (message, type = 'info', duration = 5000) => {
            const id = Date.now();
            setNotifications(prev => [...prev, { id, message, type }]);
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
        onSubmit({ decision, corrections, comments, reviewer });
    };
    
    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="review-modal">
                <div className="modal-header">
                    <h3>Review Item</h3>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>
                <div className="modal-body">
                     {/* Form content from original script */}
                </div>
                <div className="modal-footer">
                    <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
                    <button className="btn btn-primary" onClick={handleSubmit}>Submit Review</button>
                </div>
            </div>
        </div>
    );
};

const ReviewQueue = ({ reviewItems, onReview }) => {
    const [selectedItem, setSelectedItem] = React.useState(null);
    
    if (!reviewItems || reviewItems.length === 0) {
        return <div className="review-empty"><p>No items pending review</p></div>;
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
                        {/* Item content from original script */}
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

// FIX: Added the missing ReviewPanel component
const ReviewPanel = ({ reviewQueue, onReview }) => (
    <div className="review-panel card">
        <div className="card-header">
            <h2>Items for Manual Review</h2>
        </div>
        <div className="card-body">
            <ReviewQueue reviewItems={reviewQueue} onReview={onReview} />
        </div>
    </div>
);

const FileUploadComponent = ({ onUpload, loading }) => {
    const [dragActive, setDragActive] = React.useState(false);
    
    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
        else if (e.type === "dragleave") setDragActive(false);
    };
    
    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files?.[0]) onUpload(e.dataTransfer.files[0]);
    };
    
    const handleChange = (e) => {
        e.preventDefault();
        if (e.target.files?.[0]) onUpload(e.target.files[0]);
    };
    
    return (
        <div 
            className={`upload-area ${dragActive ? 'dragging' : ''}`}
            onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}
            onClick={() => !loading && document.getElementById('file-input').click()}
        >
            <input id="file-input" type="file" style={{display: 'none'}} onChange={handleChange} accept=".txt,.pdf,.doc,.docx" disabled={loading} />
            <div style={{fontSize: '3em', marginBottom: '20px'}}>{loading ? '⏳' : '📁'}</div>
            <div style={{fontSize: '1.2em', marginBottom: '10px', fontWeight: '600'}}>{loading ? 'Processing...' : 'Drop files here or click to browse'}</div>
            <div style={{fontSize: '0.95em', color: '#9ca3af', marginBottom: '20px'}}>Supports TXT, PDF, DOC, DOCX files</div>
            <div style={{fontSize: '0.85em', color: '#6b7280'}}>Maximum file size: 50MB</div>
        </div>
    );
};

// FIX: Consolidated and enhanced PipelineStep component
const PipelineStep = ({ step, index, active, onClick, modelConfig }) => {
    const icons = ['📄', '🔗', '⚠️', '✨', '🎯'];
    
    return (
        <div 
            className={`pipeline-step ${active ? 'active' : ''} ${step.status}`}
            onClick={onClick}
            style={{ position: 'relative' }}
        >
            {step.status === 'running' && step.percentage > 0 && (
                <div className="step-progress-bar-container">
                    <div className="step-progress-bar" style={{ width: `${step.percentage}%` }} />
                </div>
            )}
            <div className="step-title">
                <span>{icons[index]}</span>
                <span>{step.name}</span>
            </div>
            <div className="step-status">
                {step.status === 'running' && `${step.percentage || 0}%`}
                {step.status !== 'running' && step.status}
            </div>
            {modelConfig && index > 0 && (
                <div className="step-model-info">
                    <span className="model-badge">
                        {modelConfig.provider === 'ollama' ? '🖥️' : '☁️'} 
                        {modelConfig.model?.split(/[:\/]/).pop() || 'Default'}
                    </span>
                </div>
            )}
        </div>
    );
};

// FIX: Moved ProgressDisplay outside of App component
const ProgressDisplay = ({ step }) => {
    if (!step || step.status !== 'running') return null;
    
    return (
        <div className="progress-display">
            <h4 style={{ color: '#3b82f6' }}>Progress: {step.percentage || 0}%</h4>
            <div className="progress-bar-container">
                <div className="progress-bar" style={{ width: `${step.percentage || 0}%` }} />
            </div>
            {step.details && <p>{step.details}</p>}
        </div>
    );
};

// FIX: Moved StepContentDisplay outside of App component
const StepContentDisplay = ({ step, stepIndex, pipelineState, runStep, loading, onUpload }) => {
    if (stepIndex === 0 && step.status === 'pending') {
        return <FileUploadComponent onUpload={onUpload} loading={loading} />;
    }
    
    return (
        <div className="card">
            <div className="card-header">
                <h2>{step.name}</h2>
                <span className={`tag tag-${step.status}`}>{step.status}</span>
            </div>
            {step.data && (
                <div className="json-viewer">
                    <pre dangerouslySetInnerHTML={{ __html: highlightJSON(step.data) }} />
                </div>
            )}
            {step.status === 'pending' && stepIndex > 0 && (
                <button 
                    className="btn btn-primary" 
                    onClick={() => runStep(stepIndex)}
                    disabled={loading || pipelineState.steps[stepIndex - 1].status !== 'completed'}
                >
                    Run {step.name}
                </button>
            )}
             {step.status === 'error' && (
                <div className="error-box">
                    <p>This step failed to execute. Check the console for details.</p>
                     <button 
                        className="btn btn-secondary" 
                        onClick={() => runStep(stepIndex)}
                        disabled={loading || pipelineState.steps[stepIndex - 1].status !== 'completed'}
                    >
                        Retry {step.name}
                    </button>
                </div>
            )}
        </div>
    );
};

// --- Main App Component ---

const App = () => {
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
    
    const progressIntervalRef = React.useRef(null);
    const socket = React.useMemo(() => io(API_BASE.replace('/api', '')), []);

    const fetchProgress = async () => {
        try {
            const response = await fetch(`${API_BASE}/progress/latest`);
            if (!response.ok) return;
            const data = await response.json();
            
            if (data.steps) {
                setPipelineState(prev => {
                    const newSteps = prev.steps.map((s, i) => data.steps[i] ? { ...s, ...data.steps[i] } : s);
                    return { ...prev, steps: newSteps };
                });

                const activeStep = data.steps.find(s => s.status === 'running');
                if (activeStep) {
                    setCurrentOperation(`${activeStep.details || 'Processing...'} (${activeStep.percentage}%)`);
                }
            }
        } catch (error) {
            console.error('Progress fetch error:', error);
        }
    };

    React.useEffect(() => {
        if (loading) {
            progressIntervalRef.current = setInterval(fetchProgress, 1000);
        } else {
            clearInterval(progressIntervalRef.current);
        }
        return () => clearInterval(progressIntervalRef.current);
    }, [loading]);

    const fetchReviewItems = async () => {
        try {
            const response = await fetch(`${API_BASE}/review-items`);
            if (response.ok) {
                const data = await response.json();
                setReviewQueue(Array.isArray(data) ? data : []);
            }
        } catch (error) {
            console.error('Failed to fetch review items:', error);
        }
    };
    
    React.useEffect(() => {
        loadSettingsToUI();
        
        socket.on('review_update', fetchReviewItems);
        return () => {
            socket.off('review_update', fetchReviewItems);
            socket.disconnect();
        };
    }, [socket]);
    
    const pendingReviewCount = React.useMemo(() => {
        return reviewQueue.filter(item => item.status === 'pending').length;
    }, [reviewQueue]);
    
    const updateStepState = (index, status, data = null) => {
        setPipelineState(prev => {
            const newSteps = [...prev.steps];
            newSteps[index] = { ...newSteps[index], status, data: data ?? newSteps[index].data };
            if(status === 'error' || status === 'completed') newSteps[index].percentage = 100;
            if(status === 'pending') newSteps[index].percentage = 0;
            return { ...prev, steps: newSteps };
        });
    };

    const handleUpload = async (file) => {
        setLoading(true);
        setCurrentOperation('Uploading document...');
        updateStepState(0, 'running');
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Upload failed');
            
            updateStepState(0, 'completed', data);
            setCurrentStep(1);
            showNotification('Document uploaded successfully!', 'success');
        } catch (error) {
            updateStepState(0, 'error');
            showNotification(`Upload failed: ${error.message}`, 'error');
        } finally {
            setLoading(false);
            setCurrentOperation('');
        }
    };

    const runStep = async (stepIndex) => {
        const step = pipelineState.steps[stepIndex];
        setLoading(true);
        updateStepState(stepIndex, 'running');
        
        try {
            const response = await fetch(`${API_BASE}/run-step`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    step: stepIndex + 1,
                    input: stepIndex > 0 ? pipelineState.steps[stepIndex - 1].data : null
                })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Step execution failed');
            
            updateStepState(stepIndex, 'completed', data);
            if (stepIndex < pipelineState.steps.length - 1) {
              setCurrentStep(stepIndex + 1);
            }
            showNotification(`${step.name} completed successfully!`, 'success');
            fetchReviewItems();
        } catch (error) {
            updateStepState(stepIndex, 'error');
            showNotification(`${step.name} failed: ${error.message}`, 'error');
        } finally {
            setLoading(false);
            setCurrentOperation('');
        }
    };
    
     const handleReview = async (itemId, review) => {
        try {
            const response = await fetch(`${API_BASE}/submit-review`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_id: itemId, ...review })
            });
            if (!response.ok) throw new Error('Failed to submit');

            showNotification('Review submitted successfully', 'success');
            fetchReviewItems();
        } catch (error) {
            showNotification('Failed to submit review', 'error');
        }
    };

    return (
        <div className="app-container">
            <NotificationContainer />
            <div className="sidebar">
                <div className="sidebar-header">
                    <h1>🛡️ Advanced Threat Modeling</h1>
                    <p>AI-Powered Security Analysis</p>
                </div>
                <div className="pipeline-steps">
                    {pipelineState.steps.map((step, index) => (
                        <PipelineStep
                            key={step.id}
                            step={step}
                            index={index}
                            active={index === currentStep}
                            onClick={() => !loading && setCurrentStep(index)}
                        />
                    ))}
                </div>
                {pendingReviewCount > 0 && (
                    <div className="review-button-container">
                        <button className="btn btn-primary btn-block" onClick={() => setShowReviewPanel(!showReviewPanel)}>
                            📝 Review Queue ({pendingReviewCount})
                        </button>
                    </div>
                )}
                 <ConnectionStatus socket={socket} />
            </div>
            
            <div className="main-content">
                <div className="topbar">
                    <button className="btn btn-secondary" onClick={openSettings}>⚙️ Settings</button>
                </div>
                <div className="content-area">
                    {showReviewPanel ? (
                        <ReviewPanel reviewQueue={reviewQueue} onReview={handleReview} />
                    ) : (
                        <StepContentDisplay 
                            step={pipelineState.steps[currentStep]}
                            stepIndex={currentStep}
                            pipelineState={pipelineState}
                            runStep={runStep}
                            loading={loading}
                            onUpload={handleUpload}
                        />
                    )}
                    <ProgressDisplay step={pipelineState.steps.find(s => s.status === 'running')} />
                </div>
            </div>
            
            {loading && (
                <div className="loading-overlay">
                    <div style={{textAlign: 'center'}}>
                        <div className="loading-spinner"></div>
                        <p style={{marginTop: '20px', fontSize: '1.1em'}}>{currentOperation || 'Processing...'}</p>
                    </div>
                </div>
            )}
        </div>
    );
};

// --- Render App ---
ReactDOM.render(<App />, document.getElementById('root'));