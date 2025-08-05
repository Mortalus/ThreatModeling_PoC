// src/components/settings/SettingsModal.tsx

import React, { useState, useEffect } from 'react';
import { ModelConfig } from '../../types';
import './SettingsModal.css';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: ModelConfig) => void;
  currentConfig?: ModelConfig;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onSave,
  currentConfig
}) => {
  const [config, setConfig] = useState<ModelConfig>({
    llm_provider: currentConfig?.llm_provider || currentConfig?.provider || 'scaleway',
    llm_model: currentConfig?.llm_model || currentConfig?.model || 'mixtral-8x7b-instruct',
    api_key: currentConfig?.api_key || '',
    base_url: currentConfig?.base_url || '',
    max_tokens: currentConfig?.max_tokens || 2000,
    temperature: currentConfig?.temperature || 0.7,
    timeout: currentConfig?.timeout || 300,
    enable_rag: currentConfig?.enable_rag || false,
    enable_web_search: currentConfig?.enable_web_search || false,
    parallel_execution: currentConfig?.parallel_execution || false
  });

  const [activeTab, setActiveTab] = useState<'llm' | 'processing' | 'debug'>('llm');

  useEffect(() => {
    if (currentConfig) {
      setConfig({
        llm_provider: currentConfig.llm_provider || currentConfig.provider || 'scaleway',
        llm_model: currentConfig.llm_model || currentConfig.model || 'mixtral-8x7b-instruct',
        api_key: currentConfig.api_key || '',
        base_url: currentConfig.base_url || '',
        max_tokens: currentConfig.max_tokens || 2000,
        temperature: currentConfig.temperature || 0.7,
        timeout: currentConfig.timeout || 300,
        enable_rag: currentConfig.enable_rag || false,
        enable_web_search: currentConfig.enable_web_search || false,
        parallel_execution: currentConfig.parallel_execution || false
      });
    }
  }, [currentConfig]);

  const handleSave = () => {
    // Normalize the config to support both property names
    const normalizedConfig: ModelConfig = {
      ...config,
      provider: config.llm_provider,
      model: config.llm_model
    };
    onSave(normalizedConfig);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>⚙️ Settings</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="settings-tabs">
          <button
            className={`tab ${activeTab === 'llm' ? 'active' : ''}`}
            onClick={() => setActiveTab('llm')}
          >
            🤖 LLM Configuration
          </button>
          <button
            className={`tab ${activeTab === 'processing' ? 'active' : ''}`}
            onClick={() => setActiveTab('processing')}
          >
            ⚡ Processing Options
          </button>
          <button
            className={`tab ${activeTab === 'debug' ? 'active' : ''}`}
            onClick={() => setActiveTab('debug')}
          >
            🐛 Debug Settings
          </button>
        </div>

        <div className="modal-body">
          {activeTab === 'llm' && (
            <div className="settings-section">
              <h3>LLM Configuration</h3>
              
              <div className="form-group">
                <label htmlFor="llm-provider">Provider:</label>
                <select
                  id="llm-provider"
                  value={config.llm_provider}
                  onChange={(e) => setConfig(prev => ({
                    ...prev,
                    llm_provider: e.target.value as 'scaleway' | 'ollama',
                    provider: e.target.value as 'scaleway' | 'ollama'
                  }))}
                  className="form-control"
                >
                  <option value="scaleway">☁️ Scaleway (Cloud)</option>
                  <option value="ollama">🖥️ Ollama (Local)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="llm-model">Model:</label>
                <input
                  id="llm-model"
                  type="text"
                  value={config.llm_model || ''}
                  onChange={(e) => setConfig(prev => ({
                    ...prev,
                    llm_model: e.target.value,
                    model: e.target.value
                  }))}
                  className="form-control"
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
                    className="form-control"
                    placeholder="Enter your Scaleway API key"
                  />
                </div>
              )}

              <div className="form-group">
                <label htmlFor="max-tokens">Max Tokens:</label>
                <input
                  id="max-tokens"
                  type="number"
                  value={config.max_tokens || 2000}
                  onChange={(e) => setConfig(prev => ({
                    ...prev,
                    max_tokens: parseInt(e.target.value) || 2000
                  }))}
                  className="form-control"
                  min="100"
                  max="8000"
                />
              </div>

              <div className="form-group">
                <label htmlFor="temperature">Temperature:</label>
                <input
                  id="temperature"
                  type="number"
                  value={config.temperature || 0.7}
                  onChange={(e) => setConfig(prev => ({
                    ...prev,
                    temperature: parseFloat(e.target.value) || 0.7
                  }))}
                  className="form-control"
                  min="0"
                  max="2"
                  step="0.1"
                />
              </div>
            </div>
          )}

          {activeTab === 'processing' && (
            <div className="settings-section">
              <h3>Processing Options</h3>
              
              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={config.enable_rag || false}
                    onChange={(e) => setConfig(prev => ({
                      ...prev,
                      enable_rag: e.target.checked
                    }))}
                  />
                  <span>Enable RAG (Retrieval-Augmented Generation)</span>
                </label>
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={config.enable_web_search || false}
                    onChange={(e) => setConfig(prev => ({
                      ...prev,
                      enable_web_search: e.target.checked
                    }))}
                  />
                  <span>Enable Web Search Enhancement</span>
                </label>
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={config.parallel_execution || false}
                    onChange={(e) => setConfig(prev => ({
                      ...prev,
                      parallel_execution: e.target.checked
                    }))}
                  />
                  <span>Enable Parallel Execution</span>
                </label>
              </div>

              <div className="form-group">
                <label htmlFor="timeout">Timeout (seconds):</label>
                <input
                  id="timeout"
                  type="number"
                  value={config.timeout || 300}
                  onChange={(e) => setConfig(prev => ({
                    ...prev,
                    timeout: parseInt(e.target.value) || 300
                  }))}
                  className="form-control"
                  min="30"
                  max="600"
                />
              </div>
            </div>
          )}

          {activeTab === 'debug' && (
            <div className="settings-section">
              <h3>Debug Settings</h3>
              <p className="info-text">
                Debug options will be available in future updates.
              </p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSave}>
            💾 Save Settings
          </button>
        </div>
      </div>
    </div>
  );
};