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

  // Get current running step with proper null checking
  const runningStep = useMemo(() => {
    return pipelineState.steps.find((s: PipelineStep) => s.status === 'running') || null;
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
          <ProgressDisplay step={runningStep} />
        </div>
      </div>
      
      {/* Loading Overlay */}
      {state.loading && (
        <LoadingOverlay message={state.currentOperation || 'Processing...'}>
          <div className="loading-details">
            <div className="current-step-info">
              <strong>Current Step:</strong> {currentPipelineStep?.name}
            </div>
            {runningStep && runningStep.percentage > 0 && (
              <div className="loading-progress">
                <div 
                  className="progress-bar"
                  style={{ width: `${runningStep.percentage}%` }}
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
