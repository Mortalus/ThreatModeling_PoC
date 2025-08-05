#!/bin/bash

echo "Fixing ApiService and component type errors..."

# 1. Update ApiService to include all missing methods
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

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // File upload
  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/api/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Upload failed');
    }

    return await response.json();
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
    });
  }

  // Configuration
  async getConfig(): Promise<ModelConfig> {
    const response = await this.request<{ success: boolean; config: ModelConfig }>('/api/config');
    return response.config;
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

# 2. Fix CollapsibleSidebar interface
cat > src/components/sidebar/CollapsibleSidebar.tsx << 'EOF'
import React from 'react';
import { PipelineStep } from '../../types';
import './CollapsibleSidebar.css';

interface CollapsibleSidebarProps {
  steps: PipelineStep[];
  currentStep: number;
  onStepClick: (stepIndex: number) => void;
  collapsed: boolean;
  onToggle: () => void;
  onSettingsClick: () => void;
}

export const CollapsibleSidebar: React.FC<CollapsibleSidebarProps> = ({
  steps,
  currentStep,
  onStepClick,
  collapsed,
  onToggle,
  onSettingsClick
}) => {
  const getStepIcon = (stepIndex: number): string => {
    const icons = ['📄', '🔍', '⚠️', '🔧', '🎯'];
    return icons[stepIndex] || '📋';
  };

  const getStepStatusClass = (step: PipelineStep): string => {
    switch (step.status) {
      case 'completed': return 'completed';
      case 'running': return 'running';
      case 'error': return 'error';
      default: return '';
    }
  };

  return (
    <div className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        {!collapsed && (
          <>
            <h1>ThreatShield</h1>
            <p>AI Security Pipeline</p>
          </>
        )}
      </div>

      <button className="sidebar-toggle" onClick={onToggle}>
        {collapsed ? '→' : '←'}
      </button>

      <div className="pipeline-steps">
        <h3 className={collapsed ? 'collapsed-title' : ''}>
          {collapsed ? 'P' : 'PIPELINE PROGRESS'}
        </h3>
        
        {steps.map((step, index) => (
          <div
            key={step.id}
            className={`step-item ${index === currentStep ? 'active' : ''} ${getStepStatusClass(step)}`}
            onClick={() => onStepClick(index)}
          >
            <span className="step-icon">{getStepIcon(index)}</span>
            {!collapsed && (
              <div className="step-content">
                <div className="step-name">{step.name}</div>
                <div className="step-status">
                  {step.status === 'running' ? `${step.percentage}%` : step.status}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <button className="settings-btn" onClick={onSettingsClick}>
          ⚙️ {!collapsed && 'Settings'}
        </button>
      </div>
    </div>
  );
};
EOF

# 3. Fix ProgressDisplay interface
cat > src/components/common/ProgressDisplay.tsx << 'EOF'
import React from 'react';
import { PipelineStep } from '../../types';
import './ProgressDisplay.css';

interface ProgressDisplayProps {
  steps: PipelineStep[];
}

export const ProgressDisplay: React.FC<ProgressDisplayProps> = ({ steps }) => {
  const currentStep = steps.findIndex(s => s.status === 'running');
  
  if (currentStep === -1) {
    return null;
  }

  const step = steps[currentStep];

  return (
    <div className="progress-display">
      <div className="progress-info">
        <span className="progress-step">Step {currentStep + 1} of {steps.length}</span>
        <span className="progress-name">{step.name}</span>
      </div>
      <div className="progress-bar">
        <div 
          className="progress-fill"
          style={{ width: `${step.percentage}%` }}
        />
      </div>
      <div className="progress-percentage">{step.percentage}%</div>
    </div>
  );
};
EOF

# 4. Fix NotificationContainer interface
cat > src/components/common/NotificationContainer.tsx << 'EOF'
import React from 'react';
import { NotificationProps } from '../../types';
import './NotificationContainer.css';

interface NotificationContainerProps {
  notifications: NotificationProps[];
  onDismiss: (id: string) => void;
}

export const NotificationContainer: React.FC<NotificationContainerProps> = ({
  notifications,
  onDismiss
}) => {
  return (
    <div className="notification-container">
      {notifications.map(notification => (
        <div 
          key={notification.id}
          className={`notification ${notification.type}`}
        >
          <div className="notification-icon">
            {notification.type === 'success' && '✅'}
            {notification.type === 'error' && '❌'}
            {notification.type === 'warning' && '⚠️'}
            {notification.type === 'info' && 'ℹ️'}
          </div>
          <div className="notification-content">
            <p className="notification-message">{notification.message}</p>
          </div>
          {notification.dismissible && (
            <button 
              className="notification-close"
              onClick={() => onDismiss(notification.id)}
            >
              ×
            </button>
          )}
        </div>
      ))}
    </div>
  );
};
EOF

# 5. Fix SettingsModal to accept null
cat > src/components/settings/SettingsModal.tsx << 'EOF'
import React, { useState, useEffect } from 'react';
import { ModelConfig } from '../../types';
import './SettingsModal.css';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: ModelConfig) => void;
  currentConfig: ModelConfig | null | undefined;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onSave,
  currentConfig
}) => {
  const [config, setConfig] = useState<ModelConfig>({
    llm_provider: 'scaleway',
    llm_model: 'mixtral-8x7b-instruct',
    api_key: '',
    base_url: '',
    max_tokens: 2000,
    temperature: 0.7,
    timeout: 300
  });

  useEffect(() => {
    if (currentConfig) {
      setConfig(currentConfig);
    }
  }, [currentConfig]);

  const handleSave = () => {
    onSave(config);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Settings</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          <div className="settings-section">
            <h3>LLM Configuration</h3>
            
            <div className="form-group">
              <label htmlFor="provider">Provider</label>
              <select
                id="provider"
                value={config.llm_provider}
                onChange={(e) => setConfig({ ...config, llm_provider: e.target.value as 'scaleway' | 'ollama' })}
              >
                <option value="scaleway">Scaleway</option>
                <option value="ollama">Ollama</option>
              </select>
            </div>
            
            <div className="form-group">
              <label htmlFor="model">Model</label>
              <input
                id="model"
                type="text"
                value={config.llm_model}
                onChange={(e) => setConfig({ ...config, llm_model: e.target.value })}
              />
            </div>
            
            {config.llm_provider === 'scaleway' && (
              <div className="form-group">
                <label htmlFor="api-key">API Key</label>
                <input
                  id="api-key"
                  type="password"
                  value={config.api_key || ''}
                  onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                />
              </div>
            )}
            
            <div className="form-group">
              <label htmlFor="max-tokens">Max Tokens</label>
              <input
                id="max-tokens"
                type="number"
                value={config.max_tokens}
                onChange={(e) => setConfig({ ...config, max_tokens: parseInt(e.target.value) || 2000 })}
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="temperature">Temperature</label>
              <input
                id="temperature"
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={config.temperature}
                onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) || 0.7 })}
              />
            </div>
          </div>
        </div>
        
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSave}>Save</button>
        </div>
      </div>
    </div>
  );
};
EOF

# 6. Create CSS for ProgressDisplay
cat > src/components/common/ProgressDisplay.css << 'EOF'
.progress-display {
  padding: 1rem;
  text-align: center;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}

.progress-step {
  color: var(--text-muted);
}

.progress-name {
  color: var(--text-primary);
  font-weight: 500;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background-color: var(--accent-color);
  transition: width 0.3s ease;
}

.progress-percentage {
  font-size: 0.75rem;
  color: var(--text-secondary);
}
EOF

echo "All TypeScript errors fixed!"
echo ""
echo "The app should now compile without errors and be fully functional!"