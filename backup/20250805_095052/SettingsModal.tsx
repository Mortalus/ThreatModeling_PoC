// js/SettingsModal.tsx
// Settings Modal React Component

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [config, setConfig] = React.useState<ThreatModelingConfiguration>(SettingsStorage.loadSettings());
  const [activeSection, setActiveSection] = React.useState<SettingsSection>('llm');
  const [isSaving, setIsSaving] = React.useState(false);
  const [saveMessage, setSaveMessage] = React.useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [validationErrors, setValidationErrors] = React.useState<string[]>([]);
  const [activeStep, setActiveStep] = React.useState(1);

  // Add state for Ollama models
  const [ollamaModels, setOllamaModels] = React.useState<string[]>([]);
  const [loadingOllamaModels, setLoadingOllamaModels] = React.useState(false);
  const [ollamaError, setOllamaError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (isOpen) {
      const loadedSettings = SettingsStorage.loadSettings();
      setConfig(loadedSettings);
      
      SettingsStorage.loadFromBackend().then((backendConfig: Partial<ThreatModelingConfiguration>) => {
        if (Object.keys(backendConfig).length > 0) {
          setConfig((prev: ThreatModelingConfiguration) => ({ ...prev, ...backendConfig }));
        }
      });
    }
  }, [isOpen]);

  // Fetch Ollama models when provider changes to ollama
  React.useEffect(() => {
    if (config.llm.provider === 'ollama' && isOpen) {
      fetchOllamaModels();
    }
  }, [config.llm.provider, isOpen]);

  const fetchOllamaModels = async () => {
    setLoadingOllamaModels(true);
    setOllamaError(null);
    
    try {
      const response = await fetch('/api/ollama/models');
      const data = await response.json();
      
      if (data.status === 'success') {
        const modelNames = data.models.map((m: any) => m.name);
        setOllamaModels(modelNames);
        
        // If current model is not in the list, select the first one
        if (modelNames.length > 0 && !modelNames.includes(config.llm.model)) {
          updateConfig('llm.model', modelNames[0]);
        }
      } else {
        setOllamaError(data.error || 'Failed to fetch models');
        setOllamaModels([]);
      }
    } catch (error) {
      setOllamaError('Failed to connect to Ollama');
      setOllamaModels([]);
    } finally {
      setLoadingOllamaModels(false);
    }
  };

  const handleSave = async () => {
    const errors = SettingsValidator.validate(config);
    if (errors.length > 0) {
      setValidationErrors(errors.map((e: ValidationError) => `${e.field}: ${e.message}`));
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
    setConfig((prev: ThreatModelingConfiguration) => {
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

  // Update the renderLLMSettings function
  const renderLLMSettings = () => (
    <div className="settings-section">
      <h3>🤖 LLM Configuration</h3>
      
      <div className="form-group">
        <label>Provider</label>
        <select 
          value={config.llm.provider} 
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
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
          {Object.values(LLM_PROVIDERS).map((provider: LLMProvider) => (
            <option key={provider.id} value={provider.id}>
              {provider.name}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>
          Model
          {config.llm.provider === 'ollama' && (
            <button
              type="button"
              className="btn-icon-small"
              onClick={fetchOllamaModels}
              disabled={loadingOllamaModels}
              style={{ marginLeft: '10px' }}
              title="Refresh Ollama models"
            >
              {loadingOllamaModels ? '⏳' : '🔄'}
            </button>
          )}
        </label>
        
        {config.llm.provider === 'ollama' && ollamaError && (
          <div className="form-error">{ollamaError}</div>
        )}
        
        <select 
          value={config.llm.model} 
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => updateConfig('llm.model', e.target.value)}
          className="form-select"
          disabled={config.llm.provider === 'ollama' && loadingOllamaModels}
        >
          {config.llm.provider === 'ollama' ? (
            // For Ollama, use fetched models
            ollamaModels.length > 0 ? (
              ollamaModels.map((model: string) => (
                <option key={model} value={model}>{model}</option>
              ))
            ) : (
              <option value="">
                {loadingOllamaModels ? 'Loading models...' : 'No models available'}
              </option>
            )
          ) : (
            // For other providers, use predefined models
            LLM_PROVIDERS[config.llm.provider]?.models.map((model: string) => (
              <option key={model} value={model}>{model}</option>
            ))
          )}
        </select>
        
        {config.llm.provider === 'ollama' && ollamaModels.length > 0 && (
          <small className="form-help">
            Found {ollamaModels.length} models in your Ollama instance
          </small>
        )}
      </div>

      {(config.llm.provider === 'azure' || config.llm.provider === 'ollama') && (
        <div className="form-group">
          <label>Endpoint</label>
          <input
            type="text"
            value={config.llm.endpoint || ''}
            onChange={e => {
              updateConfig('llm.endpoint', e.target.value);
              // If Ollama endpoint changes, refetch models
              if (config.llm.provider === 'ollama') {
                fetchOllamaModels();
              }
            }}
            placeholder={config.llm.provider === 'azure' ? 'https://your-resource.openai.azure.com' : 'http://localhost:11434'}
            className="form-input"
          />
          <small className="form-help">
            {config.llm.provider === 'azure' 
              ? 'Your Azure OpenAI endpoint URL'
              : 'Local Ollama server URL (default: http://localhost:11434)'}
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
        <small className="form-help">Process multiple requests concurrently</small>
      </div>

      <div className="form-group">
        <label>Max Concurrent Calls</label>
        <input
          type="number"
          value={config.processing.maxConcurrentCalls}
          onChange={e => updateConfig('processing.maxConcurrentCalls', parseInt(e.target.value))}
          min="1"
          max="10"
          className="form-input"
        />
        <small className="form-help">Number of simultaneous LLM calls</small>
      </div>

      <div className="form-group">
        <label>Timeout (seconds)</label>
        <input
          type="number"
          value={config.processing.timeout}
          onChange={e => updateConfig('processing.timeout', parseInt(e.target.value))}
          min="30"
          max="3600"
          className="form-input"
        />
        <small className="form-help">Maximum time for each operation</small>
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
        <small className="form-help">Log all LLM requests and responses</small>
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
        {PIPELINE_STEPS.map((step: any) => (
          <button
            key={step.id}
            className={`step-tab ${activeStep === step.id ? 'active' : ''}`}
            onClick={() => setActiveStep(step.id)}
          >
            {step.icon} {step.name}
          </button>
        ))}
      </div>

      <div className="step-content">
        <p>Configuration for Step {activeStep}</p>
      </div>
    </div>
  );

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content enhanced-settings" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>⚙️ Enhanced Settings</h2>
          <button className="close-button" onClick={onClose}>×</button>
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

// Export to global window object
(window as any).SettingsModal = SettingsModal;