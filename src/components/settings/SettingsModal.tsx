import React, { useState, useEffect } from 'react';
import { ModelConfig } from '../../types';
import './SettingsModal.css';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  modelConfig: ModelConfig | null;
  onConfigUpdate: (config: ModelConfig) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  modelConfig,
  onConfigUpdate
}) => {
  const [config, setConfig] = useState<ModelConfig>({
    llm_provider: 'scaleway',
    llm_model: 'mixtral-8x7b-instruct',
    api_key: '',
    base_url: '',
    max_tokens: 4000,
    temperature: 0.7,
    timeout: 30000
  });

  const [activeTab, setActiveTab] = useState('llm');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (modelConfig) {
      setConfig(modelConfig);
    }
  }, [modelConfig]);

  const handleSave = async () => {
    setSaving(true);
    try {
      // In a real app, you'd save to backend
      onConfigUpdate(config);
      onClose();
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>⚙️ Settings</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          <div className="settings-tabs">
            <button
              className={`tab ${activeTab === 'llm' ? 'active' : ''}`}
              onClick={() => setActiveTab('llm')}
            >
              🤖 LLM Configuration
            </button>
            <button
              className={`tab ${activeTab === 'pipeline' ? 'active' : ''}`}
              onClick={() => setActiveTab('pipeline')}
            >
              🔄 Pipeline Settings
            </button>
          </div>

          <div className="settings-content">
            {activeTab === 'llm' && (
              <div className="settings-section">
                <div className="form-group">
                  <label htmlFor="llm-provider">LLM Provider:</label>
                  <select
                    id="llm-provider"
                    value={config.llm_provider}
                    onChange={(e) => setConfig(prev => ({
                      ...prev,
                      llm_provider: e.target.value as 'scaleway' | 'ollama'
                    }))}
                  >
                    <option value="scaleway">Scaleway</option>
                    <option value="ollama">Ollama (Local)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="llm-model">Model:</label>
                  <input
                    id="llm-model"
                    type="text"
                    value={config.llm_model}
                    onChange={(e) => setConfig(prev => ({
                      ...prev,
                      llm_model: e.target.value
                    }))}
                    placeholder="e.g., mixtral-8x7b-instruct"
                  />
                </div>

                {config.llm_provider === 'scaleway' && (
                  <div className="form-group">
                    <label htmlFor="api-key">API Key:</label>
                    <input
                      id="api-key"
                      type="password"
                      value={config.api_key || ''}
                      onChange={(e) => setConfig(prev => ({
                        ...prev,
                        api_key: e.target.value
                      }))}
                      placeholder="Enter your Scaleway API key"
                    />
                  </div>
                )}

                <div className="form-group">
                  <label htmlFor="max-tokens">Max Tokens:</label>
                  <input
                    id="max-tokens"
                    type="number"
                    value={config.max_tokens}
                    onChange={(e) => setConfig(prev => ({
                      ...prev,
                      max_tokens: parseInt(e.target.value)
                    }))}
                    min="100"
                    max="8000"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="temperature">Temperature:</label>
                  <input
                    id="temperature"
                    type="number"
                    value={config.temperature}
                    onChange={(e) => setConfig(prev => ({
                      ...prev,
                      temperature: parseFloat(e.target.value)
                    }))}
                    min="0"
                    max="1"
                    step="0.1"
                  />
                  <small>Controls randomness (0 = deterministic, 1 = very random)</small>
                </div>
              </div>
            )}

            {activeTab === 'pipeline' && (
              <div className="settings-section">
                <h3>Pipeline Configuration</h3>
                <p>Pipeline settings will be available in a future update.</p>
                <div className="form-group">
                  <label>
                    <input type="checkbox" defaultChecked />
                    Enable async processing
                  </label>
                </div>
                <div className="form-group">
                  <label>
                    <input type="checkbox" defaultChecked />
                    Auto-advance steps
                  </label>
                </div>
                <div className="form-group">
                  <label>
                    <input type="checkbox" />
                    Debug mode
                  </label>
                </div>
              </div>
            )}
          </div>
        </div>
        
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button 
            className="btn btn-primary" 
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
};
