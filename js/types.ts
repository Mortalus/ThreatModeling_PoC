// js/settings/types.ts

export interface LLMProvider {
  id: string;
  name: string;
  requiresApiKey: boolean;
  models: string[];
  defaultModel: string;
  endpoint?: string;
  configurable?: boolean;
}

export interface LLMProvider {
  id: string;
  name: string;
  requiresApiKey: boolean;
  models: string[];
  defaultModel: string;
  endpoint?: string;
  configurable?: boolean;
}

export interface LLMConfiguration {
  provider: string;
  model: string;
  apiKey?: string;
  endpoint?: string;
  temperature: number;
  maxTokens: number;
}

export interface ProcessingConfiguration {
  timeout: number;
  enableAsyncProcessing: boolean;
  maxConcurrentCalls: number;
  detailedLlmLogging: boolean;
}

export interface DebugConfiguration {
  debugMode: boolean;
  forceRuleBased: boolean;
  verboseErrorReporting: boolean;
}

export interface FeatureFlags {
  enableQualityCheck: boolean;
  enableMultiPass: boolean;
  enableMermaid: boolean;
  enableLlmEnrichment: boolean;
  mitreEnabled: boolean;
  mitreVersion: string;
}

export interface StepSpecificSettings {
  step1?: {
    minTextLength: number;
    maxTextLength: number;
    chunkSize: number;
  };
  step2?: {
    maxComponents: number;
  };
  step3?: {
    minRiskScore: number;
    maxComponentsToAnalyze: number;
    similarityThreshold: number;
  };
  step4?: {
    confidenceThreshold: number;
  };
  step5?: {
    maxAttackPaths: number;
    complexityThreshold: number;
  };
}

export interface ThreatModelingConfiguration {
  llm: LLMConfiguration;
  processing: ProcessingConfiguration;
  debug: DebugConfiguration;
  features: FeatureFlags;
  directories: {
    input: string;
    output: string;
  };
  stepSpecific?: StepSpecificSettings;
}

export interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: ThreatModelingConfiguration) => Promise<void>;
  currentConfig: ThreatModelingConfiguration;
}

export interface ValidationError {
  field: string;
  message: string;
}

export type SettingsSection = 'llm' | 'processing' | 'debug' | 'features' | 'directories';