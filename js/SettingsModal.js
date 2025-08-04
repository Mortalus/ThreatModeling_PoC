// js/settings/SettingsModal.tsx
import React, { useState, useEffect } from 'react';
import { LLM_PROVIDERS, PIPELINE_STEPS, MITRE_VERSIONS } from './constants.js';
import { SettingsStorage } from './storage.js';
import { SettingsValidator } from './validation.js';
export const SettingsModal = ({ isOpen, onClose }) => {
    const [config, setConfig] = useState(SettingsStorage.loadSettings());
    const [activeSection, setActiveSection] = useState('llm');
    const [isSaving, setIsSaving] = useState(false);
    const [saveMessage, setSaveMessage] = useState(null);
    const [validationErrors, setValidationErrors] = useState([]);
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
            }
            else {
                setSaveMessage({ type: 'error', text: result.error || 'Failed to save settings' });
            }
        }
        catch (error) {
            setSaveMessage({ type: 'error', text: 'An unexpected error occurred' });
        }
        finally {
            setIsSaving(false);
        }
    };
    const updateConfig = (path, value) => {
        setConfig(prev => {
            const newConfig = { ...prev };
            const keys = path.split('.');
            let obj = newConfig;
            for (let i = 0; i < keys.length - 1; i++) {
                if (!obj[keys[i]])
                    obj[keys[i]] = {};
                obj = obj[keys[i]];
            }
            obj[keys[keys.length - 1]] = value;
            return newConfig;
        });
    };
    const renderLLMSettings = () => (React.createElement("div", { className: "settings-section" },
        React.createElement("h3", null, "\uD83E\uDD16 LLM Configuration"),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null, "Provider"),
            React.createElement("select", { value: config.llm.provider, onChange: e => {
                    const provider = e.target.value;
                    const providerConfig = LLM_PROVIDERS[provider];
                    updateConfig('llm.provider', provider);
                    updateConfig('llm.model', providerConfig.defaultModel);
                    if (providerConfig.endpoint) {
                        updateConfig('llm.endpoint', providerConfig.endpoint);
                    }
                }, className: "form-select" }, Object.values(LLM_PROVIDERS).map(provider => (React.createElement("option", { key: provider.id, value: provider.id }, provider.name))))),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null, "Model"),
            React.createElement("select", { value: config.llm.model, onChange: e => updateConfig('llm.model', e.target.value), className: "form-select" }, LLM_PROVIDERS[config.llm.provider]?.models.map(model => (React.createElement("option", { key: model, value: model }, model))))),
        (config.llm.provider === 'azure' || config.llm.provider === 'ollama') && (React.createElement("div", { className: "form-group" },
            React.createElement("label", null, "Endpoint"),
            React.createElement("input", { type: "text", value: config.llm.endpoint || '', onChange: e => updateConfig('llm.endpoint', e.target.value), placeholder: config.llm.provider === 'azure' ? 'https://your-resource.openai.azure.com' : 'http://localhost:11434', className: "form-input" }),
            React.createElement("small", { className: "form-help" }, config.llm.provider === 'azure'
                ? 'Your Azure OpenAI endpoint URL'
                : 'Local Ollama server URL'))),
        React.createElement("div", { className: "form-row" },
            React.createElement("div", { className: "form-group" },
                React.createElement("label", null, "Temperature"),
                React.createElement("input", { type: "number", value: config.llm.temperature, onChange: e => updateConfig('llm.temperature', parseFloat(e.target.value)), min: "0", max: "2", step: "0.1", className: "form-input" }),
                React.createElement("small", { className: "form-help" }, "Controls randomness (0-2)")),
            React.createElement("div", { className: "form-group" },
                React.createElement("label", null, "Max Tokens"),
                React.createElement("input", { type: "number", value: config.llm.maxTokens, onChange: e => updateConfig('llm.maxTokens', parseInt(e.target.value)), min: "100", max: "32000", step: "100", className: "form-input" }),
                React.createElement("small", { className: "form-help" }, "Maximum response length")))));
    const renderProcessingSettings = () => (React.createElement("div", { className: "settings-section" },
        React.createElement("h3", null, "\u26A1 Processing Configuration"),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null,
                React.createElement("input", { type: "checkbox", checked: config.processing.enableAsyncProcessing, onChange: e => updateConfig('processing.enableAsyncProcessing', e.target.checked) }),
                "Enable Async Processing"),
            React.createElement("small", { className: "form-help" }, "Process multiple LLM calls concurrently for faster execution")),
        config.processing.enableAsyncProcessing && (React.createElement("div", { className: "form-group" },
            React.createElement("label", null, "Max Concurrent Calls"),
            React.createElement("input", { type: "number", value: config.processing.maxConcurrentCalls, onChange: e => updateConfig('processing.maxConcurrentCalls', parseInt(e.target.value)), min: "1", max: "50", className: "form-input" }),
            React.createElement("small", { className: "form-help" }, "Number of simultaneous LLM calls (1-50)"))),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null, "Timeout (seconds)"),
            React.createElement("input", { type: "number", value: config.processing.timeout / 1000, onChange: e => updateConfig('processing.timeout', parseInt(e.target.value) * 1000), min: "1", max: "300", className: "form-input" }),
            React.createElement("small", { className: "form-help" }, "Maximum time for pipeline execution")),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null,
                React.createElement("input", { type: "checkbox", checked: config.processing.detailedLlmLogging, onChange: e => updateConfig('processing.detailedLlmLogging', e.target.checked) }),
                "Detailed LLM Logging"),
            React.createElement("small", { className: "form-help" }, "Show detailed progress for each LLM call"))));
    const renderDebugSettings = () => (React.createElement("div", { className: "settings-section" },
        React.createElement("h3", null, "\uD83D\uDD27 Debug Options"),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null,
                React.createElement("input", { type: "checkbox", checked: config.debug.debugMode, onChange: e => updateConfig('debug.debugMode', e.target.checked) }),
                "Enable Debug Mode"),
            React.createElement("small", { className: "form-help" }, "Show detailed debugging information in console")),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null,
                React.createElement("input", { type: "checkbox", checked: config.debug.forceRuleBased, onChange: e => updateConfig('debug.forceRuleBased', e.target.checked) }),
                "Force Rule-Based Processing"),
            React.createElement("small", { className: "form-help" }, "Use predefined rules instead of LLM calls (for testing/demos)")),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null,
                React.createElement("input", { type: "checkbox", checked: config.debug.verboseErrorReporting, onChange: e => updateConfig('debug.verboseErrorReporting', e.target.checked) }),
                "Verbose Error Reporting"),
            React.createElement("small", { className: "form-help" }, "Show detailed error messages and stack traces"))));
    const renderStepSettings = () => (React.createElement("div", { className: "settings-section" },
        React.createElement("h3", null, "\uD83D\uDCCB Pipeline Step Settings"),
        React.createElement("div", { className: "step-tabs" }, PIPELINE_STEPS.map(step => (React.createElement("button", { key: step.id, className: `step-tab ${activeStep === step.id ? 'active' : ''}`, onClick: () => setActiveStep(step.id) }, step.name)))),
        React.createElement("div", { className: "step-content" },
            activeStep === 'step1' && (React.createElement(React.Fragment, null,
                React.createElement("h4", null, "Document Processing"),
                React.createElement("div", { className: "form-group" },
                    React.createElement("label", null, "Min Text Length"),
                    React.createElement("input", { type: "number", value: config.stepSpecific?.step1?.minTextLength || 100, onChange: e => updateConfig('stepSpecific.step1.minTextLength', parseInt(e.target.value)), min: "10", max: "10000", className: "form-input" }),
                    React.createElement("small", { className: "form-help" }, "Minimum document length to process")),
                React.createElement("div", { className: "form-group" },
                    React.createElement("label", null, "Max Text Length"),
                    React.createElement("input", { type: "number", value: config.stepSpecific?.step1?.maxTextLength || 1000000, onChange: e => updateConfig('stepSpecific.step1.maxTextLength', parseInt(e.target.value)), min: "1000", max: "10000000", className: "form-input" }),
                    React.createElement("small", { className: "form-help" }, "Maximum document length (will truncate)")))),
            activeStep === 'step2' && (React.createElement(React.Fragment, null,
                React.createElement("h4", null, "DFD Extraction"),
                React.createElement("div", { className: "form-group" },
                    React.createElement("label", null,
                        React.createElement("input", { type: "checkbox", checked: config.features.enableQualityCheck, onChange: e => updateConfig('features.enableQualityCheck', e.target.checked) }),
                        "Enable Quality Check"),
                    React.createElement("small", { className: "form-help" }, "Validate extracted DFD components")),
                React.createElement("div", { className: "form-group" },
                    React.createElement("label", null,
                        React.createElement("input", { type: "checkbox", checked: config.features.enableMultiPass, onChange: e => updateConfig('features.enableMultiPass', e.target.checked) }),
                        "Enable Multi-Pass Extraction"),
                    React.createElement("small", { className: "form-help" }, "Use multiple extraction passes for better results")))),
            activeStep === 'step3' && (React.createElement(React.Fragment, null,
                React.createElement("h4", null, "Threat Generation"),
                React.createElement("div", { className: "form-group" },
                    React.createElement("label", null, "Min Risk Score"),
                    React.createElement("input", { type: "number", value: config.stepSpecific?.step3?.minRiskScore || 3, onChange: e => updateConfig('stepSpecific.step3.minRiskScore', parseInt(e.target.value)), min: "1", max: "10", className: "form-input" }),
                    React.createElement("small", { className: "form-help" }, "Minimum risk score to include threats (1-10)")),
                React.createElement("div", { className: "form-group" },
                    React.createElement("label", null, "Similarity Threshold"),
                    React.createElement("input", { type: "number", value: config.stepSpecific?.step3?.similarityThreshold || 0.7, onChange: e => updateConfig('stepSpecific.step3.similarityThreshold', parseFloat(e.target.value)), min: "0", max: "1", step: "0.1", className: "form-input" }),
                    React.createElement("small", { className: "form-help" }, "Threshold for deduplicating similar threats")))),
            activeStep === 'step4' && (React.createElement(React.Fragment, null,
                React.createElement("h4", null, "Threat Refinement"),
                React.createElement("div", { className: "form-group" },
                    React.createElement("label", null,
                        React.createElement("input", { type: "checkbox", checked: config.features.enableLlmEnrichment, onChange: e => updateConfig('features.enableLlmEnrichment', e.target.checked) }),
                        "Enable LLM Enrichment"),
                    React.createElement("small", { className: "form-help" }, "Use LLM to enhance threat descriptions")),
                React.createElement("div", { className: "form-group" },
                    React.createElement("label", null,
                        React.createElement("input", { type: "checkbox", checked: config.features.mitreEnabled, onChange: e => updateConfig('features.mitreEnabled', e.target.checked) }),
                        "Enable MITRE ATT&CK Mapping"),
                    React.createElement("small", { className: "form-help" }, "Map threats to MITRE framework")),
                config.features.mitreEnabled && (React.createElement("div", { className: "form-group" },
                    React.createElement("label", null, "MITRE Version"),
                    React.createElement("select", { value: config.features.mitreVersion, onChange: e => updateConfig('features.mitreVersion', e.target.value), className: "form-select" }, MITRE_VERSIONS.map(version => (React.createElement("option", { key: version, value: version }, version)))))))),
            activeStep === 'step5' && (React.createElement(React.Fragment, null,
                React.createElement("h4", null, "Attack Path Analysis"),
                React.createElement("div", { className: "form-group" },
                    React.createElement("label", null,
                        React.createElement("input", { type: "checkbox", checked: config.features.enableMermaid, onChange: e => updateConfig('features.enableMermaid', e.target.checked) }),
                        "Enable Mermaid Diagrams"),
                    React.createElement("small", { className: "form-help" }, "Generate visual attack path diagrams")),
                React.createElement("div", { className: "form-group" },
                    React.createElement("label", null, "Max Attack Paths"),
                    React.createElement("input", { type: "number", value: config.stepSpecific?.step5?.maxAttackPaths || 10, onChange: e => updateConfig('stepSpecific.step5.maxAttackPaths', parseInt(e.target.value)), min: "1", max: "50", className: "form-input" }),
                    React.createElement("small", { className: "form-help" }, "Maximum number of attack paths to generate")))))));
    const [activeStep, setActiveStep] = useState('step1');
    if (!isOpen)
        return null;
    return (React.createElement("div", { className: "modal-overlay", onClick: onClose },
        React.createElement("div", { className: "modal-container", onClick: e => e.stopPropagation() },
            React.createElement("div", { className: "modal-header" },
                React.createElement("h2", null, "\u2699\uFE0F Settings"),
                React.createElement("button", { className: "modal-close", onClick: onClose }, "\u00D7")),
            React.createElement("div", { className: "modal-body" },
                React.createElement("div", { className: "settings-tabs" },
                    React.createElement("button", { className: `settings-tab ${activeSection === 'llm' ? 'active' : ''}`, onClick: () => setActiveSection('llm') }, "LLM"),
                    React.createElement("button", { className: `settings-tab ${activeSection === 'processing' ? 'active' : ''}`, onClick: () => setActiveSection('processing') }, "Processing"),
                    React.createElement("button", { className: `settings-tab ${activeSection === 'debug' ? 'active' : ''}`, onClick: () => setActiveSection('debug') }, "Debug"),
                    React.createElement("button", { className: `settings-tab ${activeSection === 'features' ? 'active' : ''}`, onClick: () => setActiveSection('features') }, "Pipeline Steps")),
                React.createElement("div", { className: "settings-content" },
                    activeSection === 'llm' && renderLLMSettings(),
                    activeSection === 'processing' && renderProcessingSettings(),
                    activeSection === 'debug' && renderDebugSettings(),
                    activeSection === 'features' && renderStepSettings()),
                validationErrors.length > 0 && (React.createElement("div", { className: "validation-errors" },
                    React.createElement("h4", null, "Validation Errors:"),
                    React.createElement("ul", null, validationErrors.map((error, i) => (React.createElement("li", { key: i }, error)))))),
                saveMessage && (React.createElement("div", { className: `save-message ${saveMessage.type}` }, saveMessage.text))),
            React.createElement("div", { className: "modal-footer" },
                React.createElement("button", { className: "btn btn-primary", onClick: handleSave, disabled: isSaving }, isSaving ? 'Saving...' : '💾 Save Settings'),
                React.createElement("button", { className: "btn btn-secondary", onClick: onClose }, "Cancel")))));
};
