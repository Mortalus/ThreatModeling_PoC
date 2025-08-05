#!/bin/bash

echo "Fixing runtime errors..."

# 1. Fix notification duplicate keys by using a better ID generator
cat > src/App.tsx << 'EOF'
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { CollapsibleSidebar } from './components/sidebar/CollapsibleSidebar';
import { StepContentDisplay } from './components/pipeline/StepContentDisplay';
import { ReviewPanel } from './components/review/ReviewPanel';
import { NotificationContainer } from './components/common/NotificationContainer';
import { ProgressDisplay } from './components/common/ProgressDisplay';
import { LoadingOverlay } from './components/common/LoadingOverlay';
import { SettingsModal } from './components/settings/SettingsModal';
import { ApiService } from './services/ApiService';
import { PipelineStep, ReviewItem, ModelConfig, NotificationProps } from './types';
import './App.css';
import './css/main.css';

// Initialize steps with proper structure
const initialSteps: PipelineStep[] = [
  { id: 0, name: 'Document Upload', status: 'idle', data: null, percentage: 0 },
  { id: 1, name: 'DFD Extraction', status: 'idle', data: null, percentage: 0 },
  { id: 2, name: 'Threat Identification', status: 'idle', data: null, percentage: 0 },
  { id: 3, name: 'Threat Refinement', status: 'idle', data: null, percentage: 0 },
  { id: 4, name: 'Attack Path Analysis', status: 'idle', data: null, percentage: 0 }
];

// Unique ID generator
let notificationCounter = 0;
const generateNotificationId = (): string => {
  notificationCounter += 1;
  return `notification-${Date.now()}-${notificationCounter}-${Math.random().toString(36).substr(2, 9)}`;
};

function App() {
  // Core state
  const [currentStep, setCurrentStep] = useState(0);
  const [steps, setSteps] = useState<PipelineStep[]>(initialSteps);
  const [loading, setLoading] = useState(false);
  const [currentOperation, setCurrentOperation] = useState('');
  const [reviewQueue, setReviewQueue] = useState<ReviewItem[]>([]);
  const [showReviewPanel, setShowReviewPanel] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [modelConfig, setModelConfig] = useState<ModelConfig | null>(null);
  const [notifications, setNotifications] = useState<NotificationProps[]>([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const socketRef = useRef<Socket | null>(null);

  // Initialize WebSocket connection
  useEffect(() => {
    // Use proper Socket.IO connection options
    socketRef.current = io('http://localhost:5000', {
      transports: ['websocket', 'polling'], // Allow fallback to polling
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socketRef.current.on('connect', () => {
      console.log('WebSocket connected');
      addNotification('success', 'Connected to server');
    });

    socketRef.current.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      if (reason === 'io server disconnect') {
        // Server disconnected, try to reconnect
        socketRef.current?.connect();
      }
    });

    socketRef.current.on('connect_error', (error) => {
      console.log('Connection error:', error.message);
      // Don't show error notification on initial connection attempts
    });

    socketRef.current.on('pipeline_update', (data) => {
      console.log('Pipeline update:', data);
      if (data.step_index !== undefined && data.status) {
        updateStepStatus(data.step_index, data.status, data.percentage || 0, data.data);
      }
    });

    socketRef.current.on('progress', (data) => {
      console.log('Progress update:', data);
      if (data.step !== undefined) {
        const percentage = Math.round((data.current / data.total) * 100);
        updateStepProgress(data.step - 1, percentage);
      }
    });

    // Load initial config
    loadConfig();

    return () => {
      socketRef.current?.disconnect();
    };
  }, []);

  // Load model configuration
  const loadConfig = async () => {
    try {
      const config = await ApiService.getConfig();
      setModelConfig(config);
    } catch (error) {
      console.error('Failed to load config:', error);
      // Don't show error notification if backend is not ready yet
    }
  };

  // Add notification with unique ID
  const addNotification = useCallback((type: NotificationProps['type'], message: string) => {
    const id = generateNotificationId();
    setNotifications(prev => [...prev, { id, type, message, duration: 5000, dismissible: true }]);
    
    // Auto-remove notification after duration
    setTimeout(() => {
      removeNotification(id);
    }, 5000);
  }, []);

  // Remove notification
  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  // Update step status
  const updateStepStatus = (stepIndex: number, status: PipelineStep['status'], percentage: number, data?: any) => {
    setSteps(prev => prev.map((step, idx) => 
      idx === stepIndex ? { ...step, status, percentage, data } : step
    ));

    if (status === 'completed') {
      addNotification('success', `${steps[stepIndex].name} completed successfully`);
      
      // Handle special cases for certain steps
      if (stepIndex === 2) { // Threat Generation
        // Add threats to review queue
        if (data?.threats) {
          const newReviewItems: ReviewItem[] = data.threats.map((threat: any, index: number) => ({
            id: `threat-${Date.now()}-${index}-${Math.random().toString(36).substr(2, 9)}`,
            type: 'threat' as const,
            status: 'pending' as const,
            data: threat,
            timestamp: new Date().toISOString(),
            step: stepIndex + 1
          }));
          setReviewQueue(prev => [...prev, ...newReviewItems]);
        }
      }
    } else if (status === 'error') {
      addNotification('error', `${steps[stepIndex].name} failed`);
    }
  };

  // Update step progress
  const updateStepProgress = (stepIndex: number, percentage: number) => {
    setSteps(prev => prev.map((step, idx) => 
      idx === stepIndex ? { ...step, percentage } : step
    ));
  };

  // Handle file upload
  const handleFileUpload = async (file: File) => {
    try {
      setLoading(true);
      setCurrentOperation('Uploading file...');
      
      const response = await ApiService.uploadFile(file);
      
      // Update first step as completed
      updateStepStatus(0, 'completed', 100, response);
      
      addNotification('success', 'File uploaded successfully');
      
      // Enable the next step
      setCurrentStep(1);
      
      // Reset loading state
      setLoading(false);
      setCurrentOperation('');
    } catch (error: any) {
      console.error('Upload error:', error);
      addNotification('error', error.message || 'Failed to upload file');
      setLoading(false);
      setCurrentOperation('');
    }
  };

  // Run specific pipeline step
  const runStep = async (stepIndex: number) => {
    // Validate that previous steps are completed
    if (stepIndex > 0) {
      const previousStep = steps[stepIndex - 1];
      if (previousStep.status !== 'completed') {
        addNotification('warning', `Please complete ${previousStep.name} first`);
        return;
      }
    }

    try {
      setLoading(true);
      setCurrentOperation(`Running ${steps[stepIndex].name}...`);
      
      // Update step status to running
      updateStepStatus(stepIndex, 'running', 0);
      
      // Call appropriate API endpoint based on step
      let response;
      switch (stepIndex) {
        case 1: // DFD Extraction
          response = await ApiService.runPipelineStep('extract_dfd');
          break;
        case 2: // Threat Generation
          response = await ApiService.runPipelineStep('generate_threats');
          break;
        case 3: // Threat Refinement
          response = await ApiService.runPipelineStep('refine_threats');
          break;
        case 4: // Attack Path Analysis
          response = await ApiService.runPipelineStep('analyze_attack_paths');
          break;
        default:
          throw new Error('Invalid step index');
      }
      
      if (response.success) {
        // The WebSocket will handle the actual status updates
        addNotification('info', `${steps[stepIndex].name} started`);
      } else {
        throw new Error(response.error || 'Step execution failed');
      }
      
    } catch (error: any) {
      console.error('Step execution error:', error);
      updateStepStatus(stepIndex, 'error', 0);
      
      // Provide more helpful error messages
      let errorMessage = `Failed to run ${steps[stepIndex].name}`;
      if (error.message.includes('400')) {
        errorMessage += ': Please make sure the previous step completed successfully and generated the required data.';
      } else if (error.message.includes('500')) {
        errorMessage += ': Server error. Please check the backend logs.';
      } else {
        errorMessage += `: ${error.message}`;
      }
      
      addNotification('error', errorMessage);
    } finally {
      setLoading(false);
      setCurrentOperation('');
    }
  };

  // Handle the "Start Threat Analysis" button
  const handleStartAnalysis = () => {
    if (steps[0].status === 'completed') {
      // Start from step 1 (DFD Extraction)
      runStep(1);
    } else {
      addNotification('warning', 'Please upload a document first');
    }
  };

  // Handle review decisions
  const handleReview = async (itemId: string, decision: 'approve' | 'reject' | 'modify', comments?: string, modifications?: any) => {
    try {
      await ApiService.reviewItem(itemId, decision, comments, modifications);
      
      setReviewQueue(prev => prev.map(item => 
        item.id === itemId 
          ? { ...item, status: decision === 'approve' ? 'approved' : 'rejected' }
          : item
      ));
      
      addNotification('success', `Item ${decision}d successfully`);
    } catch (error: any) {
      console.error('Review error:', error);
      addNotification('error', 'Failed to submit review');
    }
  };

  // Handle settings save
  const handleSaveSettings = async (config: ModelConfig) => {
    try {
      await ApiService.updateConfig(config);
      setModelConfig(config);
      setShowSettings(false);
      addNotification('success', 'Settings saved successfully');
    } catch (error: any) {
      console.error('Settings save error:', error);
      addNotification('error', 'Failed to save settings');
    }
  };

  const currentStepData = steps[currentStep];

  return (
    <div className="App">
      <CollapsibleSidebar
        steps={steps}
        currentStep={currentStep}
        onStepClick={setCurrentStep}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        onSettingsClick={() => setShowSettings(true)}
      />
      
      <div className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <div className="content-wrapper">
          <StepContentDisplay
            step={currentStepData}
            stepIndex={currentStep}
            pipelineState={{ steps }}
            runStep={runStep}
            loading={loading}
            onUpload={handleFileUpload}
            modelConfig={modelConfig}
            onStartAnalysis={handleStartAnalysis}
          />
          
          {showReviewPanel && (
            <ReviewPanel
              reviewQueue={reviewQueue}
              onReview={handleReview}
            />
          )}
        </div>
      </div>
      
      {loading && (
        <LoadingOverlay message={currentOperation}>
          <ProgressDisplay steps={steps} />
        </LoadingOverlay>
      )}
      
      {showSettings && (
        <SettingsModal
          isOpen={showSettings}
          onClose={() => setShowSettings(false)}
          onSave={handleSaveSettings}
          currentConfig={modelConfig}
        />
      )}
      
      <NotificationContainer
        notifications={notifications}
        onDismiss={removeNotification}
      />
    </div>
  );
}

export default App;
EOF

# 2. Update ApiService to handle errors better
cat > src/services/ApiService.ts << 'EOF'
import { ApiResponse, UploadResponse, ModelConfig } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

class ApiServiceClass {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        // Extract error message from response
        const errorMessage = data.error || data.message || `HTTP error! status: ${response.status}`;
        throw new Error(errorMessage);
      }

      return data;
    } catch (error: any) {
      // If it's a network error or parsing error
      if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
        throw new Error('Cannot connect to server. Please make sure the backend is running on port 5000.');
      }
      throw error;
    }
  }

  // File upload
  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${this.baseUrl}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || data.message || 'Upload failed');
      }

      return data;
    } catch (error: any) {
      if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
        throw new Error('Cannot connect to server. Please make sure the backend is running.');
      }
      throw error;
    }
  }

  // Pipeline operations
  async runPipelineStep(stepName: string): Promise<ApiResponse> {
    // Map step names to step numbers for the backend
    const stepMap: { [key: string]: number } = {
      'extract_dfd': 2,
      'generate_threats': 3,
      'refine_threats': 4,
      'analyze_attack_paths': 5
    };

    const stepNumber = stepMap[stepName] || 2;

    return this.request<ApiResponse>(`/api/run-step/${stepNumber}`, {
      method: 'POST',
      body: JSON.stringify({}), // Send empty body to avoid 400 errors
    });
  }

  // Configuration
  async getConfig(): Promise<ModelConfig> {
    try {
      const response = await this.request<{ success: boolean; config: ModelConfig }>('/api/config');
      return response.config;
    } catch (error) {
      // Return default config if backend is not ready
      console.log('Using default config');
      return {
        llm_provider: 'scaleway',
        llm_model: 'mixtral-8x7b-instruct',
        api_key: '',
        base_url: '',
        max_tokens: 2000,
        temperature: 0.7,
        timeout: 300
      };
    }
  }

  async updateConfig(config: ModelConfig): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/config', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  // Review operations
  async reviewItem(
    itemId: string,
    decision: 'approve' | 'reject' | 'modify',
    comments?: string,
    modifications?: any
  ): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/review', {
      method: 'POST',
      body: JSON.stringify({
        item_id: itemId,
        decision,
        comments,
        modifications,
      }),
    });
  }

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/api/health');
  }
}

export const ApiService = new ApiServiceClass();
EOF

echo "Runtime errors fixed!"
echo ""
echo "Changes made:"
echo "1. Fixed duplicate notification IDs with better unique ID generator"
echo "2. Improved WebSocket connection handling with fallback to polling"
echo "3. Better error handling and user-friendly error messages"
echo "4. Added auto-removal of notifications after 5 seconds"
echo "5. Fixed API requests to include empty body for POST requests"
echo ""
echo "Make sure your Flask backend is running on port 5000!"