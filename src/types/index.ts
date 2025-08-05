import { Socket } from 'socket.io-client';

// Pipeline Types
export interface PipelineStep {
  id: number;  // Added id field
  name: string;
  status: 'idle' | 'running' | 'completed' | 'error' | 'pending';  // Added 'pending' status
  percentage: number;
  data?: any;
  icon?: React.ReactNode;
  description?: string;
}

export interface PipelineState {
  steps: PipelineStep[];
  currentStep?: number;
  isRunning?: boolean;
}

// Review System Types
export interface ReviewItem {
  id: string;
  type: 'threat' | 'dfd_component' | 'attack_path';
  content: any;
  timestamp: string;
  status: 'pending' | 'approved' | 'rejected';
}

// Model Configuration Types
export interface ModelConfig {
  // LLM Provider settings
  provider?: 'scaleway' | 'ollama';  // Made optional for backward compatibility
  llm_provider?: 'scaleway' | 'ollama';  // Alternative property name
  model?: string;
  llm_model?: string;  // Alternative property name
  
  // API Configuration
  api_key?: string;
  base_url?: string;
  endpoint?: string;
  
  // Model Parameters
  max_tokens?: number;
  temperature?: number;
  timeout?: number;
  
  // Processing Options
  enable_rag?: boolean;
  enable_web_search?: boolean;
  parallel_execution?: boolean;
  
  // Additional settings that might be needed
  [key: string]: any;  // Allow additional properties
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
  type: 'pipeline_update' | 'progress' | 'error' | 'complete';
  step_index?: number;
  status?: PipelineStep['status'];
  percentage?: number;
  data?: any;
  message?: string;
  error?: string;
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

// Data Viewer Types
export interface DataViewerProps {
  data: any;
  title?: string;
  viewMode?: 'formatted' | 'json';
  onViewModeChange?: (mode: 'formatted' | 'json') => void;
}

// Threat Modeling Types
export interface Threat {
  id: string;
  component_name: string;
  stride_category: string;
  threat_description: string;
  mitigation_suggestion: string;
  impact: 'Low' | 'Medium' | 'High' | 'Critical';
  likelihood: 'Low' | 'Medium' | 'High' | 'Critical';
  risk_score: 'Low' | 'Medium' | 'High' | 'Critical';
  references: string[];
  mitre_attack?: string[];
  cve_references?: string[];
}

export interface DFDComponent {
  id: string;
  name: string;
  type: 'External Entity' | 'Process' | 'Data Store' | 'Data Flow';
  description?: string;
  trust_boundary?: boolean;
  attributes?: Record<string, any>;
}

export interface AttackPath {
  id: string;
  name: string;
  description: string;
  steps: AttackStep[];
  likelihood: 'Low' | 'Medium' | 'High' | 'Critical';
  impact: 'Low' | 'Medium' | 'High' | 'Critical';
  mitigation_strategies: string[];
}

export interface AttackStep {
  step_number: number;
  technique: string;
  description: string;
  mitre_attack_id?: string;
  prerequisites: string[];
  detection_methods: string[];
}

export interface ThreatData {
  threat_id: string;
  component: string;
  threat_type: string;
  description: string;
  impact: string;
  likelihood: string;
  risk_score: number;
  mitigation: string;
  mitre_attack?: string[];
}

export interface FileUploadResponse {
  filename: string;
  filepath: string;
  content_preview: string;
  extracted_text?: string;
}