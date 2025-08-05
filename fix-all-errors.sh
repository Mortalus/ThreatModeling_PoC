#!/bin/bash

echo "Fixing all remaining errors in the Threat Modeling App..."

# 1. Check if base.css exists, if not create it
echo "Checking for base.css..."
if [ ! -f "src/css/base.css" ]; then
    echo "Creating base.css..."
    cat > src/css/base.css << 'EOF'
/* Base styles for the threat modeling app */
:root {
  /* Color scheme */
  --bg-primary: #0a0e1a;
  --bg-secondary: #1e293b;
  --bg-surface: #1e293b;
  --bg-overlay: rgba(0, 0, 0, 0.5);
  
  --text-primary: #f8fafc;
  --text-secondary: #cbd5e1;
  --text-muted: #64748b;
  
  --accent-color: #3b82f6;
  --success-color: #10b981;
  --error-color: #ef4444;
  --warning-color: #f59e0b;
  --info-color: #06b6d4;
  
  --border-color: #334155;
  
  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  
  /* Border radius */
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  
  /* Z-index */
  --z-modal: 1000;
  --z-dropdown: 100;
  --z-sticky: 50;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: var(--bg-primary);
  color: var(--text-primary);
}

/* Button base styles */
.btn {
  padding: var(--spacing-sm) var(--spacing-md);
  border: none;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-primary {
  background-color: var(--accent-color);
  color: white;
}

.btn-primary:hover {
  background-color: #2563eb;
}

.btn-secondary {
  background-color: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background-color: #334155;
}

.btn-success {
  background-color: var(--success-color);
  color: white;
}

.btn-success:hover {
  background-color: #059669;
}

.btn-error {
  background-color: var(--error-color);
  color: white;
}

.btn-error:hover {
  background-color: #dc2626;
}

/* Input styles */
input[type="text"],
input[type="number"],
input[type="password"],
textarea,
select {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 0.875rem;
  transition: all 0.2s ease;
}

input:focus,
textarea:focus,
select:focus {
  outline: none;
  border-color: var(--accent-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Utility classes */
.text-center { text-align: center; }
.text-left { text-align: left; }
.text-right { text-align: right; }

.mt-1 { margin-top: var(--spacing-xs); }
.mt-2 { margin-top: var(--spacing-sm); }
.mt-3 { margin-top: var(--spacing-md); }
.mt-4 { margin-top: var(--spacing-lg); }
.mt-5 { margin-top: var(--spacing-xl); }

.mb-1 { margin-bottom: var(--spacing-xs); }
.mb-2 { margin-bottom: var(--spacing-sm); }
.mb-3 { margin-bottom: var(--spacing-md); }
.mb-4 { margin-bottom: var(--spacing-lg); }
.mb-5 { margin-bottom: var(--spacing-xl); }

.p-1 { padding: var(--spacing-xs); }
.p-2 { padding: var(--spacing-sm); }
.p-3 { padding: var(--spacing-md); }
.p-4 { padding: var(--spacing-lg); }
.p-5 { padding: var(--spacing-xl); }
EOF
fi

# 2. Update the types to fix ModelConfig and PipelineStep issues
echo "Updating types/index.ts to fix all type errors..."
cat > src/types/index.ts << 'EOF'
import { Socket } from 'socket.io-client';

// Pipeline Types
export interface PipelineStep {
  id: number;
  name: string;
  status: 'idle' | 'pending' | 'running' | 'completed' | 'error';
  data: any;
  percentage: number;
}

export interface PipelineState {
  steps: PipelineStep[];
  currentStep?: number;
  isRunning?: boolean;
}

// Specific data types for ReviewItem
export interface ThreatData {
  component_name: string;
  stride_category: string;
  threat_description: string;
  mitigation_suggestion: string;
  risk_score?: 'Low' | 'Medium' | 'High' | 'Critical';
}

export interface DFDComponentData {
  name: string;
  type: string;
  description?: string;
}

// Review System Types
export interface ReviewItem {
  id: string;
  type: 'threat' | 'dfd_component' | 'attack_path';
  status: 'pending' | 'approved' | 'rejected';
  data: ThreatData | DFDComponentData | any;
  timestamp: string;
  step: number;
}

// Model Configuration Types - Extended with all properties
export interface ModelConfig {
  // Core LLM settings
  llm_provider: 'scaleway' | 'ollama';
  llm_model: string;
  
  // Alternative property names for compatibility
  provider?: 'scaleway' | 'ollama';
  model?: string;
  
  // API Configuration
  api_key?: string;
  base_url?: string;
  
  // Model Parameters
  max_tokens: number;
  temperature: number;
  timeout: number;
  
  // Feature flags
  enable_rag?: boolean;
  enable_web_search?: boolean;
  parallel_execution?: boolean;
  
  // Allow additional properties
  [key: string]: any;
}

// Notification Types
export interface NotificationProps {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
  dismissible?: boolean;
}

// API Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface UploadResponse {
  filename: string;
  size: number;
  content_preview: string;
  file_type: string;
}

export interface ProgressData {
  step: number;
  current: number;
  total: number;
  progress: number;
  message: string;
  details?: string;
  timestamp: string;
}

// WebSocket Types
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export interface ConnectionStatus {
  status: 'connected' | 'disconnected' | 'connecting' | 'error';
  lastConnected?: Date;
  reconnectAttempts?: number;
}

// File Upload Types
export interface FileUploadProps {
  onUpload: (file: File) => void;
  acceptedTypes?: string[];
  maxSize?: number;
  multiple?: boolean;
  disabled?: boolean;
  dragAndDrop?: boolean;
}

export interface UploadedFile {
  file: File;
  preview?: string;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  progress?: number;
  error?: string;
}

// UI Component Types
export interface LoadingOverlayProps {
  message: string;
  children?: React.ReactNode;
}
EOF

# 3. Update PipelineStateContext to use 'idle' status
echo "Updating PipelineStateContext.tsx..."
sed -i.bak "s/status: 'pending' | 'running' | 'completed' | 'error'/status: 'idle' | 'pending' | 'running' | 'completed' | 'error'/g" src/context/PipelineStateContext.tsx

# 4. If the SettingsModal has issues, let's check if it exists
if [ -f "src/components/settings/SettingsModal.tsx" ]; then
    echo "SettingsModal.tsx exists, TypeScript should now recognize the extended ModelConfig type"
else
    echo "Creating a basic SettingsModal.tsx..."
    mkdir -p src/components/settings
    cat > src/components/settings/SettingsModal.tsx << 'EOF'
import React, { useState, useEffect } from 'react';
import { ModelConfig } from '../../types';
import './SettingsModal.css';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: ModelConfig) => void;
  currentConfig: ModelConfig | null;
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

    # Create SettingsModal.css
    cat > src/components/settings/SettingsModal.css << 'EOF'
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background-color: var(--bg-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.close-button {
  background: none;
  border: none;
  font-size: 2rem;
  cursor: pointer;
  color: var(--text-secondary);
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  transition: all 0.2s ease;
}

.close-button:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.modal-body {
  flex: 1;
  padding: var(--spacing-lg);
  overflow-y: auto;
}

.settings-section {
  margin-bottom: var(--spacing-xl);
}

.settings-section h3 {
  margin-bottom: var(--spacing-md);
  font-size: 1.125rem;
  color: var(--text-primary);
}

.form-group {
  margin-bottom: var(--spacing-md);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.modal-footer {
  padding: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
}
EOF
fi

echo "All errors should be fixed now!"
echo ""
echo "Summary of fixes:"
echo "1. Created base.css file"
echo "2. Updated types to include all necessary properties"
echo "3. Added 'idle' status to PipelineStep type"
echo "4. Extended ModelConfig interface to support all properties"
echo ""
echo "Run 'npm start' to start the application!"