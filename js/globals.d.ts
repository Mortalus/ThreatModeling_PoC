// js/globals.d.ts
// Global type declarations for the threat modeling application

// Core types
interface LLMProvider {
  id: string;
  name: string;
  requiresApiKey: boolean;
  models: string[];
  defaultModel: string;
  endpoint?: string;
  configurable?: boolean;
}

interface LLMConfiguration {
  provider: string;
  model: string;
  apiKey?: string;
  endpoint?: string;
  temperature: number;
  maxTokens: number;
}

interface ProcessingConfiguration {
  timeout: number;
  enableAsyncProcessing: boolean;
  maxConcurrentCalls: number;
  detailedLlmLogging: boolean;
}

interface DebugConfiguration {
  debugMode: boolean;
  forceRuleBased: boolean;
  verboseErrorReporting: boolean;
}

interface FeatureFlags {
  enableQualityCheck: boolean;
  enableMultiPass: boolean;
  enableMermaid: boolean;
  enableLlmEnrichment: boolean;
  mitreEnabled: boolean;
  mitreVersion: string;
}

interface StepSpecificSettings {
  step1?: {
    minTextLength: number;
    maxTextLength: number;
    chunkSize: number;
    enableSpellCheck?: boolean;
    enableGrammarCheck?: boolean;
  };
  step2?: {
    maxComponents: number;
    enableDiagramValidation?: boolean;
  };
  step3?: {
    minRiskScore: number;
    maxComponentsToAnalyze: number;
    similarityThreshold: number;
    confidenceThreshold?: number;
  };
  step4?: {
    confidenceThreshold: number;
    enableCveEnrichment?: boolean;
    cvssThreshold?: number;
  };
  step5?: {
    maxAttackPaths: number;
    complexityThreshold: number | string;
  };
}

interface ThreatModelingConfiguration {
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

interface ValidationError {
  field: string;
  message: string;
}

type SettingsSection = 'llm' | 'processing' | 'debug' | 'features' | 'directories';

// Global variable declarations
declare const CoreUtilities: {
  API_BASE: string;
  storage: any;
  debounce: any;
  throttle: any;
  [key: string]: any;
};

declare const DEFAULT_SETTINGS: ThreatModelingConfiguration;

declare const LLM_PROVIDERS: Record<string, LLMProvider>;

declare const COMPLEXITY_THRESHOLDS: Record<string, number>;

declare const PIPELINE_STEPS: Array<{
  id: number;
  name: string;
  icon: string;
}>;

declare const MITRE_VERSIONS: string[];

declare class SettingsValidator {
  static validate(config: ThreatModelingConfiguration): ValidationError[];
}

// React component props
interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}