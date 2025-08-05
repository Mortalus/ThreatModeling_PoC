#!/bin/bash

echo "🛡️ Building Full Threat Modeling App..."
echo "====================================="

# 1. Replace App.tsx with the full version
echo "Creating full App.tsx with all components..."

cat > src/App.tsx << 'EOF'
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { io, Socket } from 'socket.io-client';
import { CollapsibleSidebar } from './components/sidebar/CollapsibleSidebar';
import { StepContentDisplay } from './components/pipeline/StepContentDisplay';
import { ReviewPanel } from './components/review/ReviewPanel';
import { NotificationContainer } from './components/common/NotificationContainer';
import { ProgressDisplay } from './components/common/ProgressDisplay';
import { LoadingOverlay } from './components/common/LoadingOverlay';
import { SettingsModal } from './components/settings/SettingsModal';
import { PipelineStateProvider } from './context/PipelineStateContext';
import { NotificationProvider } from './context/NotificationContext';
import { usePipelineState } from './hooks/usePipelineState';
import { useWebSocket } from './hooks/useWebSocket';
import { useNotifications } from './hooks/useNotifications';
import { ApiService } from './services/ApiService';
import { PipelineStep, ReviewItem, ModelConfig } from './types';
import './App.css';

interface AppState {
  currentStep: number;
  loading: boolean;
  currentOperation: string;
  reviewQueue: ReviewItem[];
  showReviewPanel: boolean;
  showSettings: boolean;
  modelConfig: ModelConfig | null;
}

const AppContent: React.FC = () => {
  // Core state
  const [state, setState] = useState<AppState>({
    currentStep: 0,
    loading: false,
    currentOperation: '',
    reviewQueue: [],
    showReviewPanel: false,
    showSettings: false,
    modelConfig: null
  });

  // Custom hooks
  const { pipelineState, updateStepState, updateStepData } = usePipelineState();
  const { socket, connectionStatus } = useWebSocket();
  const { showNotification } = useNotifications();

  // Computed values
  const pendingReviewCount = useMemo(() => {
    return state.reviewQueue.filter(item => item.status === 'pending').length;
  }, [state.reviewQueue]);

  const isStepAccessible = useCallback((stepIndex: number) => {
    if (stepIndex === 0) return true;
    return pipelineState.steps[stepIndex - 1].status === 'completed';
  }, [pipelineState.steps]);

  // WebSocket event handlers
  useEffect(() => {
    if (!socket) return;

    const handleProgressUpdate = (data: any) => {
      updateStepState(data.step - 1, 'running', null, data.progress);
      setState(prev => ({ ...prev, currentOperation: data.message }));
    };

    const handleStepComplete = (data: any) => {
      updateStepState(data.step - 1, 'completed', data.data, 100);
      if (data.nextStep && data.nextStep <= pipelineState.steps.length) {
        setState(prev => ({ ...prev, currentStep: data.nextStep - 1 }));
      }
      setState(prev => ({ ...prev, loading: false, currentOperation: '' }));
      showNotification(`Step ${data.step} completed successfully!`, 'success');
    };

    const handleStepError = (data: any) => {
      updateStepState(data.step - 1, 'error', null, 0);
      setState(prev => ({ ...prev, loading: false, currentOperation: '' }));
      showNotification(`Step ${data.step} failed: ${data.error}`, 'error');
    };

    socket.on('progress_update', handleProgressUpdate);
    socket.on('step_complete', handleStepComplete);
    socket.on('step_error', handleStepError);

    return () => {
      socket.off('progress_update', handleProgressUpdate);
      socket.off('step_complete', handleStepComplete);
      socket.off('step_error', handleStepError);
    };
  }, [socket, pipelineState.steps.length, updateStepState, showNotification]);

  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [configResponse, reviewResponse] = await Promise.all([
          ApiService.getModelConfig().catch(() => ({ success: false, data: null })),
          ApiService.getReviewQueue().catch(() => ({ success: false, data: [] }))
        ]);

        setState(prev => ({
          ...prev,
          modelConfig: configResponse.data || null,
          reviewQueue: reviewResponse.data || []
        }));
      } catch (error) {
        console.error('Failed to load initial data:', error);
      }
    };

    loadInitialData();
  }, []);

  // Event handlers
  const handleStepSelect = useCallback((stepIndex: number) => {
    if (!isStepAccessible(stepIndex) || state.loading) return;
    setState(prev => ({ ...prev, currentStep: stepIndex }));
  }, [isStepAccessible, state.loading]);

  const handleUpload = useCallback(async (file: File) => {
    setState(prev => ({ ...prev, loading: true, currentOperation: 'Uploading file...' }));
    
    try {
      const response = await ApiService.uploadFile(file);
      if (response.success) {
        updateStepData(0, response.data);
        updateStepState(0, 'completed', response.data, 100);
        setState(prev => ({ ...prev, currentStep: 1, loading: false, currentOperation: '' }));
        showNotification('File uploaded successfully!', 'success');
      } else {
        throw new Error(response.error || 'Upload failed');
      }
    } catch (error) {
      setState(prev => ({ ...prev, loading: false, currentOperation: '' }));
      showNotification('File upload failed', 'error');
      console.error('Upload error:', error);
    }
  }, [updateStepData, updateStepState, showNotification]);

  const runStep = useCallback(async (stepIndex: number) => {
    if (!isStepAccessible(stepIndex)) return;

    setState(prev => ({ ...prev, loading: true }));
    updateStepState(stepIndex, 'running', null, 0);

    try {
      const response = await ApiService.runPipelineStep(stepIndex + 1);
      if (response.success) {
        showNotification(`Step ${stepIndex + 1} started`, 'success');
      } else {
        throw new Error(response.error || 'Unknown error');
      }
    } catch (error) {
      setState(prev => ({ ...prev, loading: false }));
      updateStepState(stepIndex, 'error', null, 0);
      showNotification(`Failed to start step ${stepIndex + 1}`, 'error');
      console.error('Step execution error:', error);
    }
  }, [isStepAccessible, updateStepState, showNotification]);

  const handleReview = useCallback(async (
    itemId: string, 
    decision: 'approve' | 'reject' | 'modify', 
    comments?: string,
    modifications?: any
  ) => {
    try {
      await ApiService.submitReview(itemId, decision, comments, modifications);
      setState(prev => ({
        ...prev,
        reviewQueue: prev.reviewQueue.map(item =>
          item.id === itemId ? { ...item, status: decision } : item
        )
      }));
      showNotification('Review submitted successfully', 'success');
    } catch (error) {
      showNotification('Failed to submit review', 'error');
      console.error('Review submission error:', error);
    }
  }, [showNotification]);

  const openSettings = useCallback(() => {
    setState(prev => ({ ...prev, showSettings: true }));
  }, []);

  const closeSettings = useCallback(() => {
    setState(prev => ({ ...prev, showSettings: false }));
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'r' && !event.ctrlKey && !event.altKey && !event.metaKey) {
        if (pendingReviewCount > 0) {
          setState(prev => ({ ...prev, showReviewPanel: !prev.showReviewPanel }));
        }
      }
      if (event.key === 'Escape' && state.loading) {
        setState(prev => ({ ...prev, loading: false }));
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [pendingReviewCount, state.loading]);

  const currentPipelineStep = pipelineState.steps[state.currentStep];

  return (
    <div className="app-container">
      {/* Collapsible Sidebar */}
      <CollapsibleSidebar
        pipelineState={pipelineState}
        currentStep={state.currentStep}
        setCurrentStep={handleStepSelect}
        loading={state.loading}
        pendingReviewCount={pendingReviewCount}
        showReviewPanel={state.showReviewPanel}
        setShowReviewPanel={(show: boolean) => 
          setState(prev => ({ ...prev, showReviewPanel: show }))
        }
        socket={socket}
        modelConfig={state.modelConfig}
      />
      
      {/* Main Content */}
      <div className="main-content">
        {/* Top Navigation Bar */}
        <div className="topbar">
          <div className="topbar-left">
            <h1 className="topbar-title">
              🛡️ Advanced Threat Modeling Pipeline
            </h1>
            <div className="topbar-subtitle">
              Step {state.currentStep + 1} of {pipelineState.steps.length}: {currentPipelineStep?.name}
            </div>
          </div>
          
          <div className="nav-actions">
            {pendingReviewCount > 0 && (
              <button
                className="btn btn-warning btn-sm hide-mobile"
                onClick={() => setState(prev => ({ 
                  ...prev, 
                  showReviewPanel: !prev.showReviewPanel 
                }))}
                aria-label={`${pendingReviewCount} items need review`}
                title="Review Queue (Press R)"
              >
                📝 {pendingReviewCount}
              </button>
            )}
            
            <button
              className="btn btn-secondary btn-sm"
              onClick={openSettings}
              aria-label="Open settings"
              title="Settings"
            >
              ⚙️ Settings
            </button>
            
            <div className={`connection-indicator ${connectionStatus}`}>
              <span className="connection-dot" aria-hidden="true" />
              <span className="sr-only">
                Server connection: {connectionStatus}
              </span>
            </div>
          </div>
        </div>
        
        {/* Content Area */}
        <div className="content-area">
          {state.showReviewPanel ? (
            <ReviewPanel
              reviewQueue={state.reviewQueue}
              onReview={handleReview}
            />
          ) : (
            <StepContentDisplay
              step={currentPipelineStep}
              stepIndex={state.currentStep}
              pipelineState={pipelineState}
              runStep={runStep}
              loading={state.loading}
              onUpload={handleUpload}
              modelConfig={state.modelConfig}
            />
          )}
          
          {/* Progress Display */}
          <ProgressDisplay
            step={pipelineState.steps.find((s: PipelineStep) => s.status === 'running')}
          />
        </div>
      </div>
      
      {/* Loading Overlay */}
      {state.loading && (
        <LoadingOverlay message={state.currentOperation || 'Processing...'}>
          <div className="loading-details">
            <div className="current-step-info">
              <strong>Current Step:</strong> {currentPipelineStep?.name}
            </div>
            {pipelineState.steps.find((s: PipelineStep) => s.status === 'running')?.percentage > 0 && (
              <div className="loading-progress">
                <div 
                  className="progress-bar"
                  style={{ 
                    width: `${pipelineState.steps.find((s: PipelineStep) => s.status === 'running')?.percentage || 0}%` 
                  }}
                />
              </div>
            )}
            <div className="loading-hint">
              <small>You can press Escape to continue in background</small>
            </div>
          </div>
        </LoadingOverlay>
      )}

      {/* Settings Modal */}
      {state.showSettings && (
        <SettingsModal
          isOpen={state.showSettings}
          onClose={closeSettings}
          modelConfig={state.modelConfig}
          onConfigUpdate={(config: ModelConfig) => 
            setState(prev => ({ ...prev, modelConfig: config }))
          }
        />
      )}
    </div>
  );
};

const App: React.FC = () => {
  return (
    <PipelineStateProvider>
      <NotificationProvider>
        <AppContent />
        <NotificationContainer />
      </NotificationProvider>
    </PipelineStateProvider>
  );
};

export default App;
EOF

# 2. Create enhanced SettingsModal component
echo "Creating SettingsModal component..."

cat > src/components/settings/SettingsModal.tsx << 'EOF'
import React, { useState, useEffect } from 'react';
import { ModelConfig } from '../../types';
import './SettingsModal.css';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  modelConfig: ModelConfig | null;
  onConfigUpdate: (config: ModelConfig) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  modelConfig,
  onConfigUpdate
}) => {
  const [config, setConfig] = useState<ModelConfig>({
    llm_provider: 'scaleway',
    llm_model: 'mixtral-8x7b-instruct',
    api_key: '',
    base_url: '',
    max_tokens: 4000,
    temperature: 0.7,
    timeout: 30000
  });

  const [activeTab, setActiveTab] = useState('llm');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (modelConfig) {
      setConfig(modelConfig);
    }
  }, [modelConfig]);

  const handleSave = async () => {
    setSaving(true);
    try {
      // In a real app, you'd save to backend
      onConfigUpdate(config);
      onClose();
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>⚙️ Settings</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          <div className="settings-tabs">
            <button
              className={`tab ${activeTab === 'llm' ? 'active' : ''}`}
              onClick={() => setActiveTab('llm')}
            >
              🤖 LLM Configuration
            </button>
            <button
              className={`tab ${activeTab === 'pipeline' ? 'active' : ''}`}
              onClick={() => setActiveTab('pipeline')}
            >
              🔄 Pipeline Settings
            </button>
          </div>

          <div className="settings-content">
            {activeTab === 'llm' && (
              <div className="settings-section">
                <div className="form-group">
                  <label htmlFor="llm-provider">LLM Provider:</label>
                  <select
                    id="llm-provider"
                    value={config.llm_provider}
                    onChange={(e) => setConfig(prev => ({
                      ...prev,
                      llm_provider: e.target.value as 'scaleway' | 'ollama'
                    }))}
                  >
                    <option value="scaleway">Scaleway</option>
                    <option value="ollama">Ollama (Local)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="llm-model">Model:</label>
                  <input
                    id="llm-model"
                    type="text"
                    value={config.llm_model}
                    onChange={(e) => setConfig(prev => ({
                      ...prev,
                      llm_model: e.target.value
                    }))}
                    placeholder="e.g., mixtral-8x7b-instruct"
                  />
                </div>

                {config.llm_provider === 'scaleway' && (
                  <div className="form-group">
                    <label htmlFor="api-key">API Key:</label>
                    <input
                      id="api-key"
                      type="password"
                      value={config.api_key || ''}
                      onChange={(e) => setConfig(prev => ({
                        ...prev,
                        api_key: e.target.value
                      }))}
                      placeholder="Enter your Scaleway API key"
                    />
                  </div>
                )}

                <div className="form-group">
                  <label htmlFor="max-tokens">Max Tokens:</label>
                  <input
                    id="max-tokens"
                    type="number"
                    value={config.max_tokens}
                    onChange={(e) => setConfig(prev => ({
                      ...prev,
                      max_tokens: parseInt(e.target.value)
                    }))}
                    min="100"
                    max="8000"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="temperature">Temperature:</label>
                  <input
                    id="temperature"
                    type="number"
                    value={config.temperature}
                    onChange={(e) => setConfig(prev => ({
                      ...prev,
                      temperature: parseFloat(e.target.value)
                    }))}
                    min="0"
                    max="1"
                    step="0.1"
                  />
                  <small>Controls randomness (0 = deterministic, 1 = very random)</small>
                </div>
              </div>
            )}

            {activeTab === 'pipeline' && (
              <div className="settings-section">
                <h3>Pipeline Configuration</h3>
                <p>Pipeline settings will be available in a future update.</p>
                <div className="form-group">
                  <label>
                    <input type="checkbox" defaultChecked />
                    Enable async processing
                  </label>
                </div>
                <div className="form-group">
                  <label>
                    <input type="checkbox" defaultChecked />
                    Auto-advance steps
                  </label>
                </div>
                <div className="form-group">
                  <label>
                    <input type="checkbox" />
                    Debug mode
                  </label>
                </div>
              </div>
            )}
          </div>
        </div>
        
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button 
            className="btn btn-primary" 
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
};
EOF

# 3. Create SettingsModal CSS
cat > src/components/settings/SettingsModal.css << 'EOF'
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050;
  backdrop-filter: blur(4px);
}

.modal-content {
  background-color: var(--bg-surface, #1e293b);
  border-radius: 12px;
  border: 1px solid var(--border-color, #334155);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.settings-modal {
  max-width: 700px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-color, #334155);
  background-color: var(--bg-secondary, #0f172a);
}

.modal-header h2 {
  margin: 0;
  color: var(--text-primary, #f8fafc);
  font-size: 1.5rem;
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  color: var(--text-muted, #94a3b8);
  font-size: 2rem;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.modal-close:hover {
  background-color: var(--bg-tertiary, #334155);
  color: var(--text-primary, #f8fafc);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.settings-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color, #334155);
  background-color: var(--bg-secondary, #0f172a);
}

.settings-tabs .tab {
  background: none;
  border: none;
  padding: 1rem 1.5rem;
  color: var(--text-muted, #94a3b8);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
  font-size: 0.875rem;
  font-weight: 500;
}

.settings-tabs .tab:hover {
  color: var(--text-secondary, #cbd5e1);
  background-color: var(--bg-tertiary, #334155);
}

.settings-tabs .tab.active {
  color: var(--accent-color, #3b82f6);
  border-bottom-color: var(--accent-color, #3b82f6);
  background-color: var(--bg-surface, #1e293b);
}

.settings-content {
  padding: 1.5rem;
}

.settings-section h3 {
  margin: 0 0 1rem 0;
  color: var(--text-primary, #f8fafc);
  font-size: 1.125rem;
  font-weight: 600;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-primary, #f8fafc);
  font-weight: 500;
  font-size: 0.875rem;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--border-color, #334155);
  border-radius: 6px;
  background-color: var(--bg-primary, #0a0e1a);
  color: var(--text-primary, #f8fafc);
  font-size: 0.875rem;
  transition: border-color 0.2s ease;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--accent-color, #3b82f6);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-group small {
  display: block;
  margin-top: 0.5rem;
  color: var(--text-muted, #94a3b8);
  font-size: 0.75rem;
}

.form-group label input[type="checkbox"] {
  width: auto;
  margin-right: 0.5rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.5rem;
  border-top: 1px solid var(--border-color, #334155);
  background-color: var(--bg-secondary, #0f172a);
}

.btn {
  padding: 0.75rem 1.5rem;
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: var(--accent-color, #3b82f6);
  color: white;
  border-color: var(--accent-color, #3b82f6);
}

.btn-primary:hover:not(:disabled) {
  background-color: #2563eb;
  border-color: #2563eb;
}

.btn-secondary {
  background-color: var(--bg-tertiary, #334155);
  color: var(--text-primary, #f8fafc);
  border-color: var(--border-color, #334155);
}

.btn-secondary:hover {
  background-color: var(--border-light, #475569);
  border-color: var(--border-light, #475569);
}

.btn-warning {
  background-color: var(--warning-color, #f59e0b);
  color: white;
  border-color: var(--warning-color, #f59e0b);
}

.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
}
EOF

echo "✅ Created full App.tsx with all components"
echo "✅ Created SettingsModal component"
echo "✅ Added comprehensive styling"
echo ""
echo "🚀 Your threat modeling app is now ready!"
echo ""
echo "Features added:"
echo "• Complete pipeline workflow (5 steps)"
echo "• File upload with drag & drop"
echo "• Real-time progress tracking via WebSocket"
echo "• Review system for AI-generated results"
echo "• Collapsible sidebar with pipeline status"
echo "• Settings modal for LLM configuration"
echo "• Notification system"
echo "• Loading states and error handling"
echo ""
echo "Try uploading a document and running the pipeline!"
