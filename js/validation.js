"use strict";
// js/validation.ts
// Validation for the settings system
(function (window) {
    'use strict';
    var SettingsValidator = /** @class */ (function () {
        function SettingsValidator() {
        }
        /**
         * Validate the entire configuration
         */
        SettingsValidator.validateConfiguration = function (config) {
            var errors = [];
            // Validate LLM settings
            this.validateLLMSettings(config.llm, errors);
            // Validate processing settings
            this.validateProcessingSettings(config.processing, errors);
            // Validate debug settings
            this.validateDebugSettings(config.debug, errors);
            // Validate feature flags
            this.validateFeatureFlags(config.features, errors);
            // Validate step-specific settings
            if (config.stepSpecific) {
                this.validateStepSpecificSettings(config.stepSpecific, errors);
            }
            return {
                valid: errors.length === 0,
                errors: errors
            };
        };
        /**
         * Validate LLM settings
         */
        SettingsValidator.validateLLMSettings = function (llm, errors) {
            if (!llm) {
                errors.push({ field: 'llm', message: 'LLM configuration is required' });
                return;
            }
            // Provider validation
            if (!llm.provider) {
                errors.push({ field: 'llm.provider', message: 'LLM provider is required' });
            }
            else if (!LLM_PROVIDERS || !LLM_PROVIDERS[llm.provider]) {
                errors.push({ field: 'llm.provider', message: "Invalid LLM provider: ".concat(llm.provider) });
            }
            // Model validation
            if (!llm.model) {
                errors.push({ field: 'llm.model', message: 'LLM model is required' });
            }
            else if (llm.provider && LLM_PROVIDERS && LLM_PROVIDERS[llm.provider]) {
                var provider = LLM_PROVIDERS[llm.provider];
                if (!provider.models.includes(llm.model)) {
                    errors.push({
                        field: 'llm.model',
                        message: "Invalid model \"".concat(llm.model, "\" for provider \"").concat(llm.provider, "\"")
                    });
                }
            }
            // Temperature validation
            if (typeof llm.temperature !== 'number' || llm.temperature < 0 || llm.temperature > 2) {
                errors.push({
                    field: 'llm.temperature',
                    message: 'Temperature must be a number between 0 and 2'
                });
            }
            // Max tokens validation
            if (typeof llm.maxTokens !== 'number' || llm.maxTokens < 1 || llm.maxTokens > 100000) {
                errors.push({
                    field: 'llm.maxTokens',
                    message: 'Max tokens must be a number between 1 and 100000'
                });
            }
            // Endpoint validation for Ollama
            if (llm.provider === 'ollama' && !llm.endpoint) {
                errors.push({
                    field: 'llm.endpoint',
                    message: 'Endpoint is required for Ollama provider'
                });
            }
        };
        /**
         * Validate processing settings
         */
        SettingsValidator.validateProcessingSettings = function (processing, errors) {
            if (!processing) {
                errors.push({ field: 'processing', message: 'Processing configuration is required' });
                return;
            }
            // Timeout validation
            if (typeof processing.timeout !== 'number' || processing.timeout < 10 || processing.timeout > 3600) {
                errors.push({
                    field: 'processing.timeout',
                    message: 'Timeout must be a number between 10 and 3600 seconds'
                });
            }
            // Max concurrent calls validation
            if (typeof processing.maxConcurrentCalls !== 'number' ||
                processing.maxConcurrentCalls < 1 ||
                processing.maxConcurrentCalls > 10) {
                errors.push({
                    field: 'processing.maxConcurrentCalls',
                    message: 'Max concurrent calls must be a number between 1 and 10'
                });
            }
            // Boolean validations
            if (typeof processing.enableAsyncProcessing !== 'boolean') {
                errors.push({
                    field: 'processing.enableAsyncProcessing',
                    message: 'Enable async processing must be a boolean'
                });
            }
            if (typeof processing.detailedLlmLogging !== 'boolean') {
                errors.push({
                    field: 'processing.detailedLlmLogging',
                    message: 'Detailed LLM logging must be a boolean'
                });
            }
        };
        /**
         * Validate debug settings
         */
        SettingsValidator.validateDebugSettings = function (debug, errors) {
            if (!debug) {
                errors.push({ field: 'debug', message: 'Debug configuration is required' });
                return;
            }
            var booleanFields = ['debugMode', 'forceRuleBased', 'verboseErrorReporting'];
            booleanFields.forEach(function (field) {
                if (typeof debug[field] !== 'boolean') {
                    errors.push({
                        field: "debug.".concat(field),
                        message: "".concat(field, " must be a boolean")
                    });
                }
            });
        };
        /**
         * Validate feature flags
         */
        SettingsValidator.validateFeatureFlags = function (features, errors) {
            if (!features) {
                errors.push({ field: 'features', message: 'Features configuration is required' });
                return;
            }
            var booleanFields = [
                'enableQualityCheck', 'enableMultiPass', 'enableMermaid',
                'enableLlmEnrichment', 'mitreEnabled'
            ];
            booleanFields.forEach(function (field) {
                if (typeof features[field] !== 'boolean') {
                    errors.push({
                        field: "features.".concat(field),
                        message: "".concat(field, " must be a boolean")
                    });
                }
            });
            // Validate MITRE version
            if (features.mitreEnabled && !features.mitreVersion) {
                errors.push({
                    field: 'features.mitreVersion',
                    message: 'MITRE version is required when MITRE is enabled'
                });
            }
        };
        /**
         * Validate step-specific settings
         */
        SettingsValidator.validateStepSpecificSettings = function (stepSpecific, errors) {
            var _a, _b;
            // Validate step 1
            if (stepSpecific.step1) {
                var step1 = stepSpecific.step1;
                if (step1.minTextLength && step1.maxTextLength) {
                    if (step1.minTextLength >= step1.maxTextLength) {
                        errors.push({
                            field: 'stepSpecific.step1',
                            message: 'Min text length must be less than max text length'
                        });
                    }
                }
            }
            // Validate step 2
            if ((_a = stepSpecific.step2) === null || _a === void 0 ? void 0 : _a.maxComponents) {
                if (typeof stepSpecific.step2.maxComponents !== 'number' ||
                    stepSpecific.step2.maxComponents < 1 ||
                    stepSpecific.step2.maxComponents > 100) {
                    errors.push({
                        field: 'stepSpecific.step2.maxComponents',
                        message: 'Max components must be a number between 1 and 100'
                    });
                }
            }
            // Validate step 3
            if (stepSpecific.step3) {
                var step3 = stepSpecific.step3;
                if (step3.confidenceThreshold !== undefined) {
                    if (typeof step3.confidenceThreshold !== 'number' ||
                        step3.confidenceThreshold < 0 ||
                        step3.confidenceThreshold > 1) {
                        errors.push({
                            field: 'stepSpecific.step3.confidenceThreshold',
                            message: 'Confidence threshold must be a number between 0 and 1'
                        });
                    }
                }
                if (step3.similarityThreshold !== undefined) {
                    if (typeof step3.similarityThreshold !== 'number' ||
                        step3.similarityThreshold < 0 ||
                        step3.similarityThreshold > 1) {
                        errors.push({
                            field: 'stepSpecific.step3.similarityThreshold',
                            message: 'Similarity threshold must be a number between 0 and 1'
                        });
                    }
                }
            }
            // Validate step 5
            if ((_b = stepSpecific.step5) === null || _b === void 0 ? void 0 : _b.complexityThreshold) {
                if (typeof stepSpecific.step5.complexityThreshold === 'string') {
                    var validComplexities = ['low', 'medium', 'high'];
                    if (!validComplexities.includes(stepSpecific.step5.complexityThreshold)) {
                        errors.push({
                            field: 'stepSpecific.step5.complexityThreshold',
                            message: 'Complexity threshold must be one of: low, medium, high'
                        });
                    }
                }
                else if (typeof stepSpecific.step5.complexityThreshold === 'number') {
                    if (stepSpecific.step5.complexityThreshold < 1 ||
                        stepSpecific.step5.complexityThreshold > 10) {
                        errors.push({
                            field: 'stepSpecific.step5.complexityThreshold',
                            message: 'Complexity threshold must be a number between 1 and 10'
                        });
                    }
                }
            }
        };
        return SettingsValidator;
    }());
    // Export to window
    window.SettingsValidator = SettingsValidator;
})(window);
//# sourceMappingURL=validation.js.map