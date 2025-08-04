// js/settings/SettingsModal.tsx

import React, { useState, useEffect } from 'react';
import { ThreatModelingConfiguration, SettingsSection } from './types.js';
import { LLM_PROVIDERS, PIPELINE_STEPS, MITRE_VERSIONS } from './constants.js';
import { SettingsStorage } from './storage.js';
import { SettingsValidator } from './validation.js';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [config, setConfig] = useState<ThreatModelingConfiguration>(SettingsStorage.loadSettings());
  const [activeSection, setActiveSection] = useState<SettingsSection>('llm');
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  useEffect(() => {
    if (isOpen) {
      // Load latest settings when modal opens
      const loadedSettings = SettingsStorage.loadSettings();
      setConfig(loadedSettings);
      
      // Also fetch from backend to sync
      SettingsStorage.loadFromBackend().then(backendConfig => {
        if (Object.keys(backendConfig).length > 0) {
          setConfig(prev => ({ ...prev, ...backendConfig }));
        }
      });
    }
  }, [isOpen]);

  const handleSave = async () => {
    // Validate settings
    const errors = SettingsValidator.validate(config);
    if (errors.length > 0) {
      setValidationErrors(errors.map(e => `${e.field}: ${e.message}`));
      setSaveMessage({ type: 'error', text: 'Please fix validation errors' });
      return;
    }

    setIsSaving(true);
    setSaveMessage(null);
    setValidationErrors([]);

    try {
      const result = await SettingsStorage.saveSettings(config);
      
      if (result.success) {
        setSaveMessage({ type: 'success', text: 'Settings saved successfully!' });
        
        // Reload the page to apply new settings
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        setSaveMessage({ type: 'error', text: result.error || 'Failed to save settings' });
      }
    } catch (error) {
      setSaveMessage({ type: 'error', text: 'An unexpected error occurred' });
    } finally {
      setIsSaving(false);
    }
  };

  const updateConfig = (path: string, value: any) => {
    setConfig(prev => {
      const newConfig = { ...prev };
      const keys = path.split('.');
      let obj: any = newConfig;
      
      for (let i = 0; i < keys.length - 1; i++) {
        if (!obj[keys[i]]) obj[keys[i]] = {};
        obj = obj[keys[i]];
      }
      
      obj[keys[keys.length - 1]] = value;
      return newConfig;
    });
  };

  const renderLLMSettings = () => (
    <div className="settings-section">
      <h3>🤖 LLM Configuration</h3>
      
      <div className="form-group">
        <label>Provider</label>
        <select 
          value={config.llm.provider} 
          onChange={e => {
            const provider = e.target.value;
            const providerConfig = LLM_PROVIDERS[provider];
            updateConfig('llm.provider', provider);
            updateConfig('llm.model', providerConfig.defaultModel);
            if (providerConfig.endpoint) {
              updateConfig('llm.endpoint', providerConfig.endpoint);
            }
          }}
          className="form-select"
        >
          {Object.values(LLM_PROVIDERS).map(provider => (
            <option key={provider.id} value={provider.id}>
              {provider.name}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Model</label>
        <select 
          value={config.llm.model} 
          onChange={e => updateConfig('llm.model', e.target.value)}
          className="form-select"
        >
          {LLM_PROVIDERS[config.llm.provider]?.models.map(model => (
            <option key={model} value={model}>{model}</option>
          ))}
        </select>
      </div>

      {(config.llm.provider === 'azure' || config.llm.provider === 'ollama') && (
        <div className="form-group">
          <label>Endpoint</label>
          <input
            type="text"
            value={config.llm.endpoint || ''}
            onChange={e => updateConfig('llm.endpoint', e.target.value)}
            placeholder={config.llm.provider === 'azure' ? 'https://your-resource.openai.azure.com' : 'http://localhost:11434'}
            className="form-input"
          />
          <small className="form-help">
            {config.llm.provider === 'azure' 
              ? 'Your Azure OpenAI endpoint URL'
              : 'Local Ollama server URL'}
          </small>
        </div>
      )}

      <div className="form-row">
        <div className="form-group">
          <label>Temperature</label>
          <input
            type="number"
            value={config.llm.temperature}
            onChange={e => updateConfig('llm.temperature', parseFloat(e.target.value))}
            min="0"
            max="2"
            step="0.1"
            className="form-input"
          />
          <small className="form-help">Controls randomness (0-2)</small>
        </div>

        <div className="form-group">
          <label>Max Tokens</label>
          <input
            type="number"
            value={config.llm.maxTokens}
            onChange={e => updateConfig('llm.maxTokens', parseInt(e.target.value))}
            min="100"
            max="32000"
            step="100"
            className="form-input"
          />
          <small className="form-help">Maximum response length</small>
        </div>
      </div>
    </div>
  );

  const renderProcessingSettings = () => (
    <div className="settings-section">
      <h3>⚡ Processing Configuration</h3>
      
      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={config.processing.enableAsyncProcessing}
            onChange={e => updateConfig('processing.enableAsyncProcessing', e.target.checked)}
          />
          Enable Async Processing
        </label>
        <small className="form-help">Process multiple LLM calls concurrently for faster execution</small>
      </div>

      {config.processing.enableAsyncProcessing && (
        <div className="form-group">
          <label>Max Concurrent Calls</label>
          <input
            type="number"
            value={config.processing.maxConcurrentCalls}
            onChange={e => updateConfig('processing.maxConcurrentCalls', parseInt(e.target.value))}
            min="1"
            max="50"
            className="form-input"
          />
          <small className="form-help">Number of simultaneous LLM calls (1-50)</small>
        </div>
      )}

      <div className="form-group">
        <label>Timeout (seconds)</label>
        <input
          type="number"
          value={config.processing.timeout / 1000}
          onChange={e => updateConfig('processing.timeout', parseInt(e.target.value) * 1000)}
          min="1"
          max="300"
          className="form-input"
        />
        <small className="form-help">Maximum time for pipeline execution</small>
      </div>

      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={config.processing.detailedLlmLogging}
            onChange={e => updateConfig('processing.detailedLlmLogging', e.target.checked)}
          />
          Detailed LLM Logging
        </label>
        <small className="form-help">Show detailed progress for each LLM call</small>
      </div>
    </div>
  );

  const renderDebugSettings = () => (
    <div className="settings-section">
      <h3>🔧 Debug Options</h3>
      
      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={config.debug.debugMode}
            onChange={e => updateConfig('debug.debugMode', e.target.checked)}
          />
          Enable Debug Mode
        </label>
        <small className="form-help">Show detailed debugging information in console</small>
      </div>

      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={config.debug.forceRuleBased}
            onChange={e => updateConfig('debug.forceRuleBased', e.target.checked)}
          />
          Force Rule-Based Processing
        </label>
        <small className="form-help">
          Use predefined rules instead of LLM calls (for testing/demos)
        </small>
      </div>

      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={config.debug.verboseErrorReporting}
            onChange={e => updateConfig('debug.verboseErrorReporting', e.target.checked)}
          />
          Verbose Error Reporting
        </label>
        <small className="form-help">Show detailed error messages and stack traces</small>
      </div>
    </div>
  );

  const renderStepSettings = () => (
    <div className="settings-section">
      <h3>📋 Pipeline Step Settings</h3>
      
      <div className="step-tabs">
        {PIPELINE_STEPS.map(step => (
          <button
            key={step.id}
            className={`step-tab ${activeStep === step.id ? 'active' : ''}`}
            onClick={() => setActiveStep(step.id)}
          >
            {step.name}
          </button>
        ))}
      </div>

      <div className="step-content">
        {activeStep === 'step1' && (
          <>
            <h4>Document Processing</h4>
            <div className="form-group">
              <label>Min Text Length</label>
              <input
                type="number"
                value={config.stepSpecific?.step1?.minTextLength || 100}
                onChange={e => updateConfig('stepSpecific.step1.minTextLength', parseInt(e.target.value))}
                min="10"
                max="10000"
                className="form-input"
              />
              <small className="form-help">Minimum document length to process</small>
            </div>

            <div className="form-group">
              <label>Max Text Length</label>
              <input
                type="number"
                value={config.stepSpecific?.step1?.maxTextLength || 1000000}
                onChange={e => updateConfig('stepSpecific.step1.maxTextLength', parseInt(e.target.value))}
                min="1000"
                max="10000000"
                className="form-input"
              />
              <small className="form-help">Maximum document length (will truncate)</small>
            </div>
          </>
        )}

        {activeStep === 'step2' && (
          <>
            <h4>DFD Extraction</h4>
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={config.features.enableQualityCheck}
                  onChange={e => updateConfig('features.enableQualityCheck', e.target.checked)}
                />
                Enable Quality Check
              </label>
              <small className="form-help">Validate extracted DFD components</small>
            </div>

            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={config.features.enableMultiPass}
                  onChange={e => updateConfig('features.enableMultiPass', e.target.checked)}
                />
                Enable Multi-Pass Extraction
              </label>
              <small className="form-help">Use multiple extraction passes for better results</small>
            </div>
          </>
        )}

        {activeStep === 'step3' && (
          <>
            <h4>Threat Generation</h4>
            <div className="form-group">
              <label>Min Risk Score</label>
              <input
                type="number"
                value={config.stepSpecific?.step3?.minRiskScore || 3}
                onChange={e => updateConfig('stepSpecific.step3.minRiskScore', parseInt(e.target.value))}
                min="1"
                max="10"
                className="form-input"
              />
              <small className="form-help">Minimum risk score to include threats (1-10)</small>
            </div>

            <div className="form-group">
              <label>Similarity Threshold</label>
              <input
                type="number"
                value={config.stepSpecific?.step3?.similarityThreshold || 0.7}
                onChange={e => updateConfig('stepSpecific.step3.similarityThreshold', parseFloat(e.target.value))}
                min="0"
                max="1"
                step="0.1"
                className="form-input"
              />
              <small className="form-help">Threshold for deduplicating similar threats</small>
            </div>
          </>
        )}

        {activeStep === 'step4' && (
          <>
            <h4>Threat Refinement</h4>
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={config.features.enableLlmEnrichment}
                  onChange={e => updateConfig('features.enableLlmEnrichment', e.target.checked)}
                />
                Enable LLM Enrichment
              </label>
              <small className="form-help">Use LLM to enhance threat descriptions</small>
            </div>

            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={config.features.mitreEnabled}
                  onChange={e => updateConfig('features.mitreEnabled', e.target.checked)}
                />
                Enable MITRE ATT&CK Mapping
              </label>
              <small className="form-help">Map threats to MITRE framework</small>
            </div>

            {config.features.mitreEnabled && (
              <div className="form-group">
                <label>MITRE Version</label>
                <select
                  value={config.features.mitreVersion}
                  onChange={e => updateConfig('features.mitreVersion', e.target.value)}
                  className="form-select"
                >
                  {MITRE_VERSIONS.map(version => (
                    <option key={version} value={version}>{version}</option>
                  ))}
                </select>
              </div>
            )}
          </>
        )}

        {activeStep === 'step5' && (
          <>
            <h4>Attack Path Analysis</h4>
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={config.features.enableMermaid}
                  onChange={e => updateConfig('features.enableMermaid', e.target.checked)}
                />
                Enable Mermaid Diagrams
              </label>
              <small className="form-help">Generate visual attack path diagrams</small>
            </div>

            <div className="form-group">
              <label>Max Attack Paths</label>
              <input
                type="number"
                value={config.stepSpecific?.step5?.maxAttackPaths || 10}
                onChange={e => updateConfig('stepSpecific.step5.maxAttackPaths', parseInt(e.target.value))}
                min="1"
                max="50"
                className="form-input"
              />
              <small className="form-help">Maximum number of attack paths to generate</small>
            </div>
          </>
        )}
      </div>
    </div>
  );

  const [activeStep, setActiveStep] = useState('step1');

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>⚙️ Settings</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <div className="settings-tabs">
            <button 
              className={`settings-tab ${activeSection === 'llm' ? 'active' : ''}`}
              onClick={() => setActiveSection('llm')}
            >
              LLM
            </button>
            <button 
              className={`settings-tab ${activeSection === 'processing' ? 'active' : ''}`}
              onClick={() => setActiveSection('processing')}
            >
              Processing
            </button>
            <button 
              className={`settings-tab ${activeSection === 'debug' ? 'active' : ''}`}
              onClick={() => setActiveSection('debug')}
            >
              Debug
            </button>
            <button 
              className={`settings-tab ${activeSection === 'features' ? 'active' : ''}`}
              onClick={() => setActiveSection('features')}
            >
              Pipeline Steps
            </button>
          </div>

          <div className="settings-content">
            {activeSection === 'llm' && renderLLMSettings()}
            {activeSection === 'processing' && renderProcessingSettings()}
            {activeSection === 'debug' && renderDebugSettings()}
            {activeSection === 'features' && renderStepSettings()}
          </div>

          {validationErrors.length > 0 && (
            <div className="validation-errors">
              <h4>Validation Errors:</h4>
              <ul>
                {validationErrors.map((error, i) => (
                  <li key={i}>{error}</li>
                ))}
              </ul>
            </div>
          )}

          {saveMessage && (
            <div className={`save-message ${saveMessage.type}`}>
              {saveMessage.text}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button 
            className="btn btn-primary" 
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? 'Saving...' : '💾 Save Settings'}
          </button>
          <button 
            className="btn btn-secondary" 
            onClick={onClose}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};