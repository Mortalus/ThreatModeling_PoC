import React, { useState, useEffect } from 'react';
import { ModelConfig } from '../../types';
import './SettingsModal.css';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: ModelConfig) => void;
  currentConfig: ModelConfig | null | undefined;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onSave,
  currentConfig
}) => {
  const [config, setConfig] = useState<ModelConfig>({
    llm_provider: 'scaleway',
    llm_model: 'mixtral-8x7b-instruct',
    api_key: '',
    base_url: '',
    max_tokens: 2000,
    temperature: 0.7,
    timeout: 300
  });

  useEffect(() => {
    if (currentConfig) {
      setConfig(currentConfig);
    }
  }, [currentConfig]);

  const handleSave = () => {
    onSave(config);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Settings</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          <div className="settings-section">
            <h3>LLM Configuration</h3>
            
            <div className="form-group">
              <label htmlFor="provider">Provider</label>
              <select
                id="provider"
                value={config.llm_provider}
                onChange={(e) => setConfig({ ...config, llm_provider: e.target.value as 'scaleway' | 'ollama' })}
              >
                <option value="scaleway">Scaleway</option>
                <option value="ollama">Ollama</option>
              </select>
            </div>
            
            <div className="form-group">
              <label htmlFor="model">Model</label>
              <input
                id="model"
                type="text"
                value={config.llm_model}
                onChange={(e) => setConfig({ ...config, llm_model: e.target.value })}
              />
            </div>
            
            {config.llm_provider === 'scaleway' && (
              <div className="form-group">
                <label htmlFor="api-key">API Key</label>
                <input
                  id="api-key"
                  type="password"
                  value={config.api_key || ''}
                  onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                />
              </div>
            )}
            
            <div className="form-group">
              <label htmlFor="max-tokens">Max Tokens</label>
              <input
                id="max-tokens"
                type="number"
                value={config.max_tokens}
                onChange={(e) => setConfig({ ...config, max_tokens: parseInt(e.target.value) || 2000 })}
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="temperature">Temperature</label>
              <input
                id="temperature"
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={config.temperature}
                onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) || 0.7 })}
              />
            </div>
          </div>
        </div>
        
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSave}>Save</button>
        </div>
      </div>
    </div>
  );
};
