import { Socket } from 'socket.io-client';

// Pipeline Types
export interface PipelineStep {
  id: number;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  data: any;
  percentage: number;
}

export interface PipelineState {
  steps: PipelineStep[];
}

// Review System Types
export interface ReviewItem {
  id: string;
  type: 'threat' | 'dfd_component' | 'attack_path';
  status: 'pending' | 'approve' | 'reject' | 'modify';
  data: any;
  timestamp: string;
  step: number;
}

// Model Configuration Types
export interface ModelConfig {
  llm_provider: 'scaleway' | 'ollama';
  llm_model: string;
  api_key?: string;
  base_url?: string;
  max_tokens: number;
  temperature: number;
  timeout: number;
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
