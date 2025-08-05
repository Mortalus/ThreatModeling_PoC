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
