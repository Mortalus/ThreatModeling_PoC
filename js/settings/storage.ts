// js/settings/storage.ts

import { ThreatModelingConfiguration } from './types.js';
import { DEFAULT_SETTINGS } from './constants.js';

export class SettingsStorage {
  private static readonly STORAGE_KEY = 'threat_modeling_settings';
  private static readonly CONFIG_ENDPOINT = '/api/config';

  /**
   * Load settings from localStorage and merge with defaults
   */
  static loadSettings(): ThreatModelingConfiguration {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Deep merge with defaults to ensure all fields exist
        return this.deepMerge(DEFAULT_SETTINGS, parsed);
      }
    } catch (error) {
      console.error('Error loading settings from localStorage:', error);
    }
    return { ...DEFAULT_SETTINGS };
  }

  /**
   * Save settings to localStorage and backend
   */
  static async saveSettings(settings: ThreatModelingConfiguration): Promise<{ success: boolean; error?: string }> {
    try {
      // Save to localStorage
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(settings));

      // Prepare backend config
      const backendConfig = this.prepareBackendConfig(settings);

      // Save to backend
      const response = await fetch(this.CONFIG_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(backendConfig)
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to save settings');
      }

      // Also save to a config file for persistence
      await this.saveConfigFile(settings);

      return { success: true };
    } catch (error) {
      console.error('Error saving settings:', error);
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      };
    }
  }

  /**
   * Load settings from backend
   */
  static async loadFromBackend(): Promise<Partial<ThreatModelingConfiguration>> {
    try {
      const response = await fetch(this.CONFIG_ENDPOINT);
      if (!response.ok) {
        throw new Error('Failed to load backend config');
      }
      const data = await response.json();
      return this.parseBackendConfig(data);
    } catch (error) {
      console.error('Error loading from backend:', error);
      return {};
    }
  }

  /**
   * Save configuration to a file (via backend endpoint)
   */
  private static async saveConfigFile(settings: ThreatModelingConfiguration): Promise<void> {
    try {
      const configData = {
        ...this.prepareBackendConfig(settings),
        saved_at: new Date().toISOString(),
        version: '1.0'
      };

      await fetch('/api/config/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(configData)
      });
    } catch (error) {
      console.error('Error saving config file:', error);
      // Non-critical error, don't throw
    }
  }

  /**
   * Convert frontend settings to backend format
   */
  private static prepareBackendConfig(settings: ThreatModelingConfiguration): any {
    return {
      // LLM settings
      llm_provider: settings.llm.provider,
      llm_model: settings.llm.model,
      temperature: settings.llm.temperature,
      max_tokens: settings.llm.maxTokens,
      
      // Processing settings
      timeout: settings.processing.timeout,
      enable_async_processing: settings.processing.enableAsyncProcessing,
      max_concurrent_calls: settings.processing.maxConcurrentCalls,
      detailed_llm_logging: settings.processing.detailedLlmLogging,
      
      // Debug settings
      debug_mode: settings.debug.debugMode,
      force_rule_based: settings.debug.forceRuleBased,
      verbose_error_reporting: settings.debug.verboseErrorReporting,
      
      // Feature flags
      enable_quality_check: settings.features.enableQualityCheck,
      enable_multi_pass: settings.features.enableMultiPass,
      enable_mermaid: settings.features.enableMermaid,
      enable_llm_enrichment: settings.features.enableLlmEnrichment,
      mitre_enabled: settings.features.mitreEnabled,
      mitre_version: settings.features.mitreVersion,
      
      // Step-specific settings
      min_text_length: settings.stepSpecific?.step1?.minTextLength,
      max_text_length: settings.stepSpecific?.step1?.maxTextLength,
      chunk_size: settings.stepSpecific?.step1?.chunkSize,
      min_risk_score: settings.stepSpecific?.step3?.minRiskScore,
      max_components_to_analyze: settings.stepSpecific?.step3?.maxComponentsToAnalyze,
      similarity_threshold: settings.stepSpecific?.step3?.similarityThreshold,
      max_attack_paths: settings.stepSpecific?.step5?.maxAttackPaths,
      complexity_threshold: settings.stepSpecific?.step5?.complexityThreshold
    };
  }

  /**
   * Parse backend config to frontend format
   */
  private static parseBackendConfig(data: any): Partial<ThreatModelingConfiguration> {
    return {
      llm: {
        provider: data.llm_provider,
        model: data.llm_model,
        temperature: data.temperature,
        maxTokens: data.max_tokens
      },
      processing: {
        timeout: data.timeout,
        enableAsyncProcessing: data.enable_async_processing,
        maxConcurrentCalls: data.max_concurrent_calls,
        detailedLlmLogging: data.detailed_llm_logging
      },
      features: {
        enableQualityCheck: data.enable_quality_check,
        enableMultiPass: data.enable_multi_pass,
        enableMermaid: data.enable_mermaid,
        enableLlmEnrichment: data.enable_llm_enrichment,
        mitreEnabled: data.mitre_enabled,
        mitreVersion: data.mitre_version
      }
    };
  }

  /**
   * Deep merge utility
   */
  private static deepMerge(target: any, source: any): any {
    const output = { ...target };
    
    if (this.isObject(target) && this.isObject(source)) {
      Object.keys(source).forEach(key => {
        if (this.isObject(source[key])) {
          if (!(key in target)) {
            Object.assign(output, { [key]: source[key] });
          } else {
            output[key] = this.deepMerge(target[key], source[key]);
          }
        } else {
          Object.assign(output, { [key]: source[key] });
        }
      });
    }
    
    return output;
  }

  private static isObject(item: any): boolean {
    return item && typeof item === 'object' && !Array.isArray(item);
  }
}