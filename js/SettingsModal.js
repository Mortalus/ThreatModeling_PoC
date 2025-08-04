"use strict";
// js/SettingsModal.tsx
// Settings Modal React Component
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var SettingsModal = function (_a) {
    var isOpen = _a.isOpen, onClose = _a.onClose;
    var _b = React.useState(SettingsStorage.loadSettings()), config = _b[0], setConfig = _b[1];
    var _c = React.useState('llm'), activeSection = _c[0], setActiveSection = _c[1];
    var _d = React.useState(false), isSaving = _d[0], setIsSaving = _d[1];
    var _e = React.useState(null), saveMessage = _e[0], setSaveMessage = _e[1];
    var _f = React.useState([]), validationErrors = _f[0], setValidationErrors = _f[1];
    var _g = React.useState(1), activeStep = _g[0], setActiveStep = _g[1];
    // Add state for Ollama models
    var _h = React.useState([]), ollamaModels = _h[0], setOllamaModels = _h[1];
    var _j = React.useState(false), loadingOllamaModels = _j[0], setLoadingOllamaModels = _j[1];
    var _k = React.useState(null), ollamaError = _k[0], setOllamaError = _k[1];
    React.useEffect(function () {
        if (isOpen) {
            var loadedSettings = SettingsStorage.loadSettings();
            setConfig(loadedSettings);
            SettingsStorage.loadFromBackend().then(function (backendConfig) {
                if (Object.keys(backendConfig).length > 0) {
                    setConfig(function (prev) { return (__assign(__assign({}, prev), backendConfig)); });
                }
            });
        }
    }, [isOpen]);
    // Fetch Ollama models when provider changes to ollama
    React.useEffect(function () {
        if (config.llm.provider === 'ollama' && isOpen) {
            fetchOllamaModels();
        }
    }, [config.llm.provider, isOpen]);
    var fetchOllamaModels = function () { return __awaiter(void 0, void 0, void 0, function () {
        var response, data, modelNames, error_1;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    setLoadingOllamaModels(true);
                    setOllamaError(null);
                    _a.label = 1;
                case 1:
                    _a.trys.push([1, 4, 5, 6]);
                    return [4 /*yield*/, fetch('/api/ollama/models')];
                case 2:
                    response = _a.sent();
                    return [4 /*yield*/, response.json()];
                case 3:
                    data = _a.sent();
                    if (data.status === 'success') {
                        modelNames = data.models.map(function (m) { return m.name; });
                        setOllamaModels(modelNames);
                        // If current model is not in the list, select the first one
                        if (modelNames.length > 0 && !modelNames.includes(config.llm.model)) {
                            updateConfig('llm.model', modelNames[0]);
                        }
                    }
                    else {
                        setOllamaError(data.error || 'Failed to fetch models');
                        setOllamaModels([]);
                    }
                    return [3 /*break*/, 6];
                case 4:
                    error_1 = _a.sent();
                    setOllamaError('Failed to connect to Ollama');
                    setOllamaModels([]);
                    return [3 /*break*/, 6];
                case 5:
                    setLoadingOllamaModels(false);
                    return [7 /*endfinally*/];
                case 6: return [2 /*return*/];
            }
        });
    }); };
    var handleSave = function () { return __awaiter(void 0, void 0, void 0, function () {
        var errors, result, error_2;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    errors = SettingsValidator.validate(config);
                    if (errors.length > 0) {
                        setValidationErrors(errors.map(function (e) { return "".concat(e.field, ": ").concat(e.message); }));
                        setSaveMessage({ type: 'error', text: 'Please fix validation errors' });
                        return [2 /*return*/];
                    }
                    setIsSaving(true);
                    setSaveMessage(null);
                    setValidationErrors([]);
                    _a.label = 1;
                case 1:
                    _a.trys.push([1, 3, 4, 5]);
                    return [4 /*yield*/, SettingsStorage.saveSettings(config)];
                case 2:
                    result = _a.sent();
                    if (result.success) {
                        setSaveMessage({ type: 'success', text: 'Settings saved successfully!' });
                        setTimeout(function () {
                            window.location.reload();
                        }, 1500);
                    }
                    else {
                        setSaveMessage({ type: 'error', text: result.error || 'Failed to save settings' });
                    }
                    return [3 /*break*/, 5];
                case 3:
                    error_2 = _a.sent();
                    setSaveMessage({ type: 'error', text: 'An unexpected error occurred' });
                    return [3 /*break*/, 5];
                case 4:
                    setIsSaving(false);
                    return [7 /*endfinally*/];
                case 5: return [2 /*return*/];
            }
        });
    }); };
    var updateConfig = function (path, value) {
        setConfig(function (prev) {
            var newConfig = __assign({}, prev);
            var keys = path.split('.');
            var obj = newConfig;
            for (var i = 0; i < keys.length - 1; i++) {
                if (!obj[keys[i]])
                    obj[keys[i]] = {};
                obj = obj[keys[i]];
            }
            obj[keys[keys.length - 1]] = value;
            return newConfig;
        });
    };
    // Update the renderLLMSettings function
    var renderLLMSettings = function () {
        var _a;
        return (React.createElement("div", { className: "settings-section" },
            React.createElement("h3", null, "\uD83E\uDD16 LLM Configuration"),
            React.createElement("div", { className: "form-group" },
                React.createElement("label", null, "Provider"),
                React.createElement("select", { value: config.llm.provider, onChange: function (e) {
                        var provider = e.target.value;
                        var providerConfig = LLM_PROVIDERS[provider];
                        updateConfig('llm.provider', provider);
                        updateConfig('llm.model', providerConfig.defaultModel);
                        if (providerConfig.endpoint) {
                            updateConfig('llm.endpoint', providerConfig.endpoint);
                        }
                    }, className: "form-select" }, Object.values(LLM_PROVIDERS).map(function (provider) { return (React.createElement("option", { key: provider.id, value: provider.id }, provider.name)); }))),
            React.createElement("div", { className: "form-group" },
                React.createElement("label", null,
                    "Model",
                    config.llm.provider === 'ollama' && (React.createElement("button", { type: "button", className: "btn-icon-small", onClick: fetchOllamaModels, disabled: loadingOllamaModels, style: { marginLeft: '10px' }, title: "Refresh Ollama models" }, loadingOllamaModels ? '⏳' : '🔄'))),
                config.llm.provider === 'ollama' && ollamaError && (React.createElement("div", { className: "form-error" }, ollamaError)),
                React.createElement("select", { value: config.llm.model, onChange: function (e) { return updateConfig('llm.model', e.target.value); }, className: "form-select", disabled: config.llm.provider === 'ollama' && loadingOllamaModels }, config.llm.provider === 'ollama' ? (
                // For Ollama, use fetched models
                ollamaModels.length > 0 ? (ollamaModels.map(function (model) { return (React.createElement("option", { key: model, value: model }, model)); })) : (React.createElement("option", { value: "" }, loadingOllamaModels ? 'Loading models...' : 'No models available'))) : (
                // For other providers, use predefined models
                (_a = LLM_PROVIDERS[config.llm.provider]) === null || _a === void 0 ? void 0 : _a.models.map(function (model) { return (React.createElement("option", { key: model, value: model }, model)); }))),
                config.llm.provider === 'ollama' && ollamaModels.length > 0 && (React.createElement("small", { className: "form-help" },
                    "Found ",
                    ollamaModels.length,
                    " models in your Ollama instance"))),
            (config.llm.provider === 'azure' || config.llm.provider === 'ollama') && (React.createElement("div", { className: "form-group" },
                React.createElement("label", null, "Endpoint"),
                React.createElement("input", { type: "text", value: config.llm.endpoint || '', onChange: function (e) {
                        updateConfig('llm.endpoint', e.target.value);
                        // If Ollama endpoint changes, refetch models
                        if (config.llm.provider === 'ollama') {
                            fetchOllamaModels();
                        }
                    }, placeholder: config.llm.provider === 'azure' ? 'https://your-resource.openai.azure.com' : 'http://localhost:11434', className: "form-input" }),
                React.createElement("small", { className: "form-help" }, config.llm.provider === 'azure'
                    ? 'Your Azure OpenAI endpoint URL'
                    : 'Local Ollama server URL (default: http://localhost:11434)'))),
            React.createElement("div", { className: "form-row" },
                React.createElement("div", { className: "form-group" },
                    React.createElement("label", null, "Temperature"),
                    React.createElement("input", { type: "number", value: config.llm.temperature, onChange: function (e) { return updateConfig('llm.temperature', parseFloat(e.target.value)); }, min: "0", max: "2", step: "0.1", className: "form-input" }),
                    React.createElement("small", { className: "form-help" }, "Controls randomness (0-2)")),
                React.createElement("div", { className: "form-group" },
                    React.createElement("label", null, "Max Tokens"),
                    React.createElement("input", { type: "number", value: config.llm.maxTokens, onChange: function (e) { return updateConfig('llm.maxTokens', parseInt(e.target.value)); }, min: "100", max: "32000", step: "100", className: "form-input" }),
                    React.createElement("small", { className: "form-help" }, "Maximum response length")))));
    };
    var renderProcessingSettings = function () { return (React.createElement("div", { className: "settings-section" },
        React.createElement("h3", null, "\u26A1 Processing Configuration"),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null,
                React.createElement("input", { type: "checkbox", checked: config.processing.enableAsyncProcessing, onChange: function (e) { return updateConfig('processing.enableAsyncProcessing', e.target.checked); } }),
                "Enable Async Processing"),
            React.createElement("small", { className: "form-help" }, "Process multiple requests concurrently")),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null, "Max Concurrent Calls"),
            React.createElement("input", { type: "number", value: config.processing.maxConcurrentCalls, onChange: function (e) { return updateConfig('processing.maxConcurrentCalls', parseInt(e.target.value)); }, min: "1", max: "10", className: "form-input" }),
            React.createElement("small", { className: "form-help" }, "Number of simultaneous LLM calls")),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null, "Timeout (seconds)"),
            React.createElement("input", { type: "number", value: config.processing.timeout, onChange: function (e) { return updateConfig('processing.timeout', parseInt(e.target.value)); }, min: "30", max: "3600", className: "form-input" }),
            React.createElement("small", { className: "form-help" }, "Maximum time for each operation")),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null,
                React.createElement("input", { type: "checkbox", checked: config.processing.detailedLlmLogging, onChange: function (e) { return updateConfig('processing.detailedLlmLogging', e.target.checked); } }),
                "Detailed LLM Logging"),
            React.createElement("small", { className: "form-help" }, "Log all LLM requests and responses")))); };
    var renderDebugSettings = function () { return (React.createElement("div", { className: "settings-section" },
        React.createElement("h3", null, "\uD83D\uDD27 Debug Options"),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null,
                React.createElement("input", { type: "checkbox", checked: config.debug.debugMode, onChange: function (e) { return updateConfig('debug.debugMode', e.target.checked); } }),
                "Enable Debug Mode"),
            React.createElement("small", { className: "form-help" }, "Show detailed debugging information in console")),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null,
                React.createElement("input", { type: "checkbox", checked: config.debug.forceRuleBased, onChange: function (e) { return updateConfig('debug.forceRuleBased', e.target.checked); } }),
                "Force Rule-Based Processing"),
            React.createElement("small", { className: "form-help" }, "Use predefined rules instead of LLM calls (for testing/demos)")),
        React.createElement("div", { className: "form-group" },
            React.createElement("label", null,
                React.createElement("input", { type: "checkbox", checked: config.debug.verboseErrorReporting, onChange: function (e) { return updateConfig('debug.verboseErrorReporting', e.target.checked); } }),
                "Verbose Error Reporting"),
            React.createElement("small", { className: "form-help" }, "Show detailed error messages and stack traces")))); };
    var renderStepSettings = function () { return (React.createElement("div", { className: "settings-section" },
        React.createElement("h3", null, "\uD83D\uDCCB Pipeline Step Settings"),
        React.createElement("div", { className: "step-tabs" }, PIPELINE_STEPS.map(function (step) { return (React.createElement("button", { key: step.id, className: "step-tab ".concat(activeStep === step.id ? 'active' : ''), onClick: function () { return setActiveStep(step.id); } },
            step.icon,
            " ",
            step.name)); })),
        React.createElement("div", { className: "step-content" },
            React.createElement("p", null,
                "Configuration for Step ",
                activeStep)))); };
    if (!isOpen)
        return null;
    return (React.createElement("div", { className: "modal-overlay", onClick: onClose },
        React.createElement("div", { className: "modal-content enhanced-settings", onClick: function (e) { return e.stopPropagation(); } },
            React.createElement("div", { className: "modal-header" },
                React.createElement("h2", null, "\u2699\uFE0F Enhanced Settings"),
                React.createElement("button", { className: "close-button", onClick: onClose }, "\u00D7")),
            React.createElement("div", { className: "modal-body" },
                React.createElement("div", { className: "settings-tabs" },
                    React.createElement("button", { className: "settings-tab ".concat(activeSection === 'llm' ? 'active' : ''), onClick: function () { return setActiveSection('llm'); } }, "LLM"),
                    React.createElement("button", { className: "settings-tab ".concat(activeSection === 'processing' ? 'active' : ''), onClick: function () { return setActiveSection('processing'); } }, "Processing"),
                    React.createElement("button", { className: "settings-tab ".concat(activeSection === 'debug' ? 'active' : ''), onClick: function () { return setActiveSection('debug'); } }, "Debug"),
                    React.createElement("button", { className: "settings-tab ".concat(activeSection === 'features' ? 'active' : ''), onClick: function () { return setActiveSection('features'); } }, "Pipeline Steps")),
                React.createElement("div", { className: "settings-content" },
                    activeSection === 'llm' && renderLLMSettings(),
                    activeSection === 'processing' && renderProcessingSettings(),
                    activeSection === 'debug' && renderDebugSettings(),
                    activeSection === 'features' && renderStepSettings()),
                validationErrors.length > 0 && (React.createElement("div", { className: "validation-errors" },
                    React.createElement("h4", null, "Validation Errors:"),
                    React.createElement("ul", null, validationErrors.map(function (error, i) { return (React.createElement("li", { key: i }, error)); })))),
                saveMessage && (React.createElement("div", { className: "save-message ".concat(saveMessage.type) }, saveMessage.text))),
            React.createElement("div", { className: "modal-footer" },
                React.createElement("button", { className: "btn btn-primary", onClick: handleSave, disabled: isSaving }, isSaving ? 'Saving...' : '💾 Save Settings'),
                React.createElement("button", { className: "btn btn-secondary", onClick: onClose }, "Cancel")))));
};
// Export to global window object
window.SettingsModal = SettingsModal;
//# sourceMappingURL=SettingsModal.js.map