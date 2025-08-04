// js/constants.ts

// Wrap in IIFE to create globals
(function(window: any) {
    'use strict';

    const DEFAULT_SETTINGS: ThreatModelingConfiguration = {
        llm: {
            provider: 'scaleway',
            model: 'llama-3.1-8b-instruct',
            endpoint: 'http://localhost:11434',
            temperature: 0.7,
            maxTokens: 8192
        },
        processing: {
            timeout: 600,
            enableAsyncProcessing: true,
            maxConcurrentCalls: 3,
            detailedLlmLogging: false
        },
        debug: {
            debugMode: false,
            forceRuleBased: false,
            verboseErrorReporting: false
        },
        features: {
            enableQualityCheck: true,
            enableMultiPass: false,
            enableMermaid: true,
            enableLlmEnrichment: true,
            mitreEnabled: true,
            mitreVersion: '14.1'
        },
        directories: {
            input: './input_documents',
            output: './output'
        },
        stepSpecific: {
            step1: { 
                minTextLength: 100,
                maxTextLength: 50000,
                chunkSize: 4000,
                enableSpellCheck: true, 
                enableGrammarCheck: false
            },
            step2: { 
                maxComponents: 20, 
                enableDiagramValidation: true 
            },
            step3: { 
                minRiskScore: 0.5,
                maxComponentsToAnalyze: 50,
                similarityThreshold: 0.85,
                confidenceThreshold: 0.7
            },
            step4: { 
                confidenceThreshold: 0.7,
                enableCveEnrichment: true, 
                cvssThreshold: 7.0 
            },
            step5: { 
                maxAttackPaths: 10, 
                complexityThreshold: 5
            }
        }
    };

    const LLM_PROVIDERS: Record<string, LLMProvider> = {
        scaleway: {
            id: 'scaleway',
            name: 'Scaleway',
            requiresApiKey: true,
            models: [
                'llama-3.1-8b-instruct',
                'llama-3.1-70b-instruct',
                'mixtral-8x7b-instruct-v0.1'
            ],
            defaultModel: 'llama-3.1-8b-instruct'
        },
        ollama: {
            id: 'ollama',
            name: 'Ollama (Local)',
            requiresApiKey: false,
            models: [
                'llama2',
                'llama3',
                'mistral',
                'mixtral',
                'codellama'
            ],
            defaultModel: 'llama3',
            endpoint: 'http://localhost:11434',
            configurable: true
        },
        azure: {
            id: 'azure',
            name: 'Azure OpenAI',
            requiresApiKey: true,
            models: [
                'gpt-35-turbo',
                'gpt-4',
                'gpt-4-32k'
            ],
            defaultModel: 'gpt-35-turbo'
        },
        openai: {
            id: 'openai',
            name: 'OpenAI',
            requiresApiKey: true,
            models: [
                'gpt-3.5-turbo',
                'gpt-4',
                'gpt-4-turbo'
            ],
            defaultModel: 'gpt-3.5-turbo'
        }
    };

    const COMPLEXITY_THRESHOLDS = {
        low: 3,
        medium: 5,
        high: 8
    };

    // Export to window
    window.DEFAULT_SETTINGS = DEFAULT_SETTINGS;
    window.LLM_PROVIDERS = LLM_PROVIDERS;
    window.COMPLEXITY_THRESHOLDS = COMPLEXITY_THRESHOLDS;

    // For backward compatibility with the module pattern
    window.SettingsConstants = {
        DEFAULT_SETTINGS,
        LLM_PROVIDERS,
        COMPLEXITY_THRESHOLDS
    };

})(window);