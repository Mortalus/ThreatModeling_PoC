// js/settings/validation.ts

import { ThreatModelingConfiguration, ValidationError } from './types.js';
import { LLM_PROVIDERS } from './constants.js';

export class SettingsValidator {
  /**
   * Validate the entire configuration
   */
  static validate(config: ThreatModelingConfiguration): ValidationError[] {
    const errors: ValidationError[] = [];

    // Validate LLM settings
    errors.push(...this.validateLLMSettings(config.llm));

    // Validate processing settings
    errors.push(...this.validateProcessingSettings(config.processing));

    // Validate debug settings
    errors.push(...this.validateDebugSettings(config.debug, config));

    // Validate step-specific settings
    errors.push(...this.validateStepSettings(config.stepSpecific));

    return errors;
  }

  /**
   * Validate LLM configuration
   */
  private static validateLLMSettings(llm: ThreatModelingConfiguration['llm']): ValidationError[] {
    const errors: ValidationError[] = [];

    // Validate provider
    if (!llm.provider || !LLM_PROVIDERS[llm.provider]) {
      errors.push({
        field: 'llm.provider',
        message: 'Invalid LLM provider selected'
      });
    }

    // Validate model
    if (llm.provider && LLM_PROVIDERS[llm.provider]) {
      const provider = LLM_PROVIDERS[llm.provider];
      if (!provider.models.includes(llm.model)) {
        errors.push({
          field: 'llm.model',
          message: `Invalid model for ${provider.name}`
        });
      }
    }

    // Validate temperature
    if (llm.temperature < 0 || llm.temperature > 2) {
      errors.push({
        field: 'llm.temperature',
        message: 'Temperature must be between 0 and 2'
      });
    }

    // Validate max tokens
    if (llm.maxTokens < 100 || llm.maxTokens > 32000) {
      errors.push({
        field: 'llm.maxTokens',
        message: 'Max tokens must be between 100 and 32000'
      });
    }

    // Validate Azure endpoint if Azure is selected
    if (llm.provider === 'azure' && llm.endpoint) {
      if (!this.isValidUrl(llm.endpoint)) {
        errors.push({
          field: 'llm.endpoint',
          message: 'Invalid Azure endpoint URL'
        });
      }
    }

    // Validate Ollama endpoint if Ollama is selected
    if (llm.provider === 'ollama' && llm.endpoint) {
      if (!this.isValidUrl(llm.endpoint)) {
        errors.push({
          field: 'llm.endpoint',
          message: 'Invalid Ollama endpoint URL'
        });
      }
    }

    return errors;
  }

  /**
   * Validate processing settings
   */
  private static validateProcessingSettings(processing: ThreatModelingConfiguration['processing']): ValidationError[] {
    const errors: ValidationError[] = [];

    // Validate timeout
    if (processing.timeout < 1000 || processing.timeout > 300000) {
      errors.push({
        field: 'processing.timeout',
        message: 'Timeout must be between 1 and 300 seconds'
      });
    }

    // Validate concurrent calls
    if (processing.maxConcurrentCalls < 1 || processing.maxConcurrentCalls > 50) {
      errors.push({
        field: 'processing.maxConcurrentCalls',
        message: 'Max concurrent calls must be between 1 and 50'
      });
    }

    return errors;
  }

  /**
   * Validate debug settings with context
   */
  private static validateDebugSettings(
    debug: ThreatModelingConfiguration['debug'], 
    config: ThreatModelingConfiguration
  ): ValidationError[] {
    const errors: ValidationError[] = [];

    // Warn about debug mode implications
    if (debug.debugMode && !debug.forceRuleBased) {
      // This is just a warning, not an error
      console.warn('Debug mode enabled without force rule-based. LLM calls will still be made.');
    }

    // Check for conflicting settings
    if (debug.forceRuleBased && config.processing.enableAsyncProcessing) {
      console.warn('Async processing has limited benefits with force rule-based mode enabled.');
    }

    return errors;
  }

  /**
   * Validate step-specific settings
   */
  private static validateStepSettings(stepSettings: any): ValidationError[] {
    const errors: ValidationError[] = [];

    if (!stepSettings) return errors;

    // Step 1 validation
    if (stepSettings.step1) {
      const { minTextLength, maxTextLength, chunkSize } = stepSettings.step1;
      
      if (minTextLength && (minTextLength < 10 || minTextLength > 10000)) {
        errors.push({
          field: 'step1.minTextLength',
          message: 'Min text length must be between 10 and 10,000'
        });
      }

      if (maxTextLength && (maxTextLength < 1000 || maxTextLength > 10000000)) {
        errors.push({
          field: 'step1.maxTextLength',
          message: 'Max text length must be between 1,000 and 10,000,000'
        });
      }

      if (minTextLength && maxTextLength && minTextLength >= maxTextLength) {
        errors.push({
          field: 'step1.textLength',
          message: 'Min text length must be less than max text length'
        });
      }

      if (chunkSize && (chunkSize < 500 || chunkSize > 10000)) {
        errors.push({
          field: 'step1.chunkSize',
          message: 'Chunk size must be between 500 and 10,000'
        });
      }
    }

    // Step 3 validation
    if (stepSettings.step3) {
      const { minRiskScore, similarityThreshold } = stepSettings.step3;
      
      if (minRiskScore && (minRiskScore < 1 || minRiskScore > 10)) {
        errors.push({
          field: 'step3.minRiskScore',
          message: 'Min risk score must be between 1 and 10'
        });
      }

      if (similarityThreshold && (similarityThreshold < 0 || similarityThreshold > 1)) {
        errors.push({
          field: 'step3.similarityThreshold',
          message: 'Similarity threshold must be between 0 and 1'
        });
      }
    }

    // Step 5 validation
    if (stepSettings.step5) {
      const { maxAttackPaths, complexityThreshold } = stepSettings.step5;
      
      if (maxAttackPaths && (maxAttackPaths < 1 || maxAttackPaths > 50)) {
        errors.push({
          field: 'step5.maxAttackPaths',
          message: 'Max attack paths must be between 1 and 50'
        });
      }

      if (complexityThreshold && (complexityThreshold < 0 || complexityThreshold > 1)) {
        errors.push({
          field: 'step5.complexityThreshold',
          message: 'Complexity threshold must be between 0 and 1'
        });
      }
    }

    return errors;
  }

  /**
   * Check if a string is a valid URL
   */
  private static isValidUrl(url: string): boolean {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get validation summary
   */
  static getValidationSummary(errors: ValidationError[]): string {
    if (errors.length === 0) {
      return 'Configuration is valid';
    }

    return `Found ${errors.length} validation error${errors.length > 1 ? 's' : ''}:\n` +
      errors.map(e => `• ${e.field}: ${e.message}`).join('\n');
  }
}