// js/settings/integration.js

/**
 * Settings Integration Module
 * Connects the new modular settings system with the existing main.js
 */

import { SettingsStorage } from './storage.js';
import { DEFAULT_SETTINGS } from './constants.js';

/**
 * Initialize settings and expose global functions for backward compatibility
 */
export function initializeSettings() {
  // Load settings on startup
  const settings = SettingsStorage.loadSettings();
  
  // Apply settings to window for backward compatibility
  window.currentConfig = convertToLegacyFormat(settings);
  
  // Replace the old settings functions
  window.openSettingsModal = openEnhancedSettingsModal;
  window.closeSettingsModal = closeEnhancedSettingsModal;
  window.saveSettings = saveEnhancedSettings;
  
  // Load backend config and merge
  SettingsStorage.loadFromBackend().then(backendConfig => {
    if (Object.keys(backendConfig).length > 0) {
      window.currentConfig = { 
        ...window.currentConfig, 
        ...convertToLegacyFormat(backendConfig) 
      };
    }
  });
}

/**
 * Convert new settings format to legacy format for compatibility
 */
function convertToLegacyFormat(settings) {
  return {
    // LLM settings
    llm_provider: settings.llm?.provider || DEFAULT_SETTINGS.llm.provider,
    llm_model: settings.llm?.model || DEFAULT_SETTINGS.llm.model,
    local_llm_endpoint: settings.llm?.endpoint || DEFAULT_SETTINGS.llm.endpoint,
    temperature: settings.llm?.temperature || DEFAULT_SETTINGS.llm.temperature,
    max_tokens: settings.llm?.maxTokens || DEFAULT_SETTINGS.llm.maxTokens,
    
    // Processing settings
    timeout: settings.processing?.timeout || DEFAULT_SETTINGS.processing.timeout,
    enable_async_processing: settings.processing?.enableAsyncProcessing ?? DEFAULT_SETTINGS.processing.enableAsyncProcessing,
    max_concurrent_calls: settings.processing?.maxConcurrentCalls || DEFAULT_SETTINGS.processing.maxConcurrentCalls,
    detailed_llm_logging: settings.processing?.detailedLlmLogging ?? DEFAULT_SETTINGS.processing.detailedLlmLogging,
    
    // Debug settings
    debug_mode: settings.debug?.debugMode ?? DEFAULT_SETTINGS.debug.debugMode,
    force_rule_based: settings.debug?.forceRuleBased ?? DEFAULT_SETTINGS.debug.forceRuleBased,
    verbose_error_reporting: settings.debug?.verboseErrorReporting ?? DEFAULT_SETTINGS.debug.verboseErrorReporting,
    
    // Feature flags
    enable_quality_check: settings.features?.enableQualityCheck ?? DEFAULT_SETTINGS.features.enableQualityCheck,
    enable_multi_pass: settings.features?.enableMultiPass ?? DEFAULT_SETTINGS.features.enableMultiPass,
    enable_mermaid: settings.features?.enableMermaid ?? DEFAULT_SETTINGS.features.enableMermaid,
    enable_llm_enrichment: settings.features?.enableLlmEnrichment ?? DEFAULT_SETTINGS.features.enableLlmEnrichment,
    mitre_enabled: settings.features?.mitreEnabled ?? DEFAULT_SETTINGS.features.mitreEnabled,
    mitre_version: settings.features?.mitreVersion || DEFAULT_SETTINGS.features.mitreVersion,
    
    // Step-specific settings
    min_text_length: settings.stepSpecific?.step1?.minTextLength || DEFAULT_SETTINGS.stepSpecific.step1.minTextLength,
    max_text_length: settings.stepSpecific?.step1?.maxTextLength || DEFAULT_SETTINGS.stepSpecific.step1.maxTextLength,
    min_risk_score: settings.stepSpecific?.step3?.minRiskScore || DEFAULT_SETTINGS.stepSpecific.step3.minRiskScore,
    similarity_threshold: settings.stepSpecific?.step3?.similarityThreshold || DEFAULT_SETTINGS.stepSpecific.step3.similarityThreshold,
    max_attack_paths: settings.stepSpecific?.step5?.maxAttackPaths || DEFAULT_SETTINGS.stepSpecific.step5.maxAttackPaths,
  };
}

/**
 * Open the enhanced settings modal
 */
function openEnhancedSettingsModal() {
  // Mount React component if not already mounted
  if (!window.settingsModalMounted) {
    const container = document.createElement('div');
    container.id = 'enhanced-settings-container';
    document.body.appendChild(container);
    
    const React = window.React;
    const ReactDOM = window.ReactDOM;
    
    // Corrected path to the SettingsModal component
    import('./SettingsModal.tsx').then(({ SettingsModal }) => {
      const App = () => {
        const [isOpen, setIsOpen] = React.useState(true);
        window.setSettingsModalOpen = setIsOpen;
        
        return React.createElement(SettingsModal, {
          isOpen: isOpen,
          onClose: () => setIsOpen(false)
        });
      };
      
      ReactDOM.render(React.createElement(App), container);
      window.settingsModalMounted = true;
    });
  } else {
    window.setSettingsModalOpen(true);
  }
}

/**
 * Close the enhanced settings modal
 */
function closeEnhancedSettingsModal() {
  if (window.setSettingsModalOpen) {
    window.setSettingsModalOpen(false);
  }
}

/**
 * Save settings (for backward compatibility)
 */
async function saveEnhancedSettings() {
  // This function is now handled by the React component
  console.log('Save triggered from legacy interface');
}

/**
 * Update provider fields based on selection
 */
window.updateProviderFields = function() {
  const provider = document.getElementById('llm-provider')?.value;
  const apiKeyGroup = document.getElementById('api-key-group');
  const localEndpointGroup = document.getElementById('local-endpoint-group');
  
  if (!provider) return;
  
  // Hide all provider-specific fields first
  if (apiKeyGroup) apiKeyGroup.style.display = 'none';
  if (localEndpointGroup) localEndpointGroup.style.display = 'none';
  
  // Show relevant fields based on provider
  switch(provider) {
    case 'ollama':
      if (localEndpointGroup) localEndpointGroup.style.display = 'block';
      break;
    case 'azure':
      // Azure endpoint configuration would go here
      break;
    case 'scaleway':
      // No additional fields needed - using .env
      break;
  }
};

/**
 * Update async fields visibility
 */
window.updateAsyncFields = function() {
  const asyncEnabled = document.getElementById('enable-async-processing')?.checked;
  const concurrentGroup = document.getElementById('concurrent-calls-group');
  
  if (concurrentGroup) {
    concurrentGroup.style.display = asyncEnabled ? 'block' : 'none';
  }
};

/**
 * Update debug fields
 */
window.updateDebugFields = function() {
  const debugMode = document.getElementById('debug-mode')?.checked;
  const forceRuleBased = document.getElementById('force-rule-based')?.checked;
  
  if (debugMode && !forceRuleBased) {
    console.warn('Debug mode without force rule-based will still make LLM calls');
  }
};

// Auto-initialize when loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeSettings);
} else {
  initializeSettings();
}