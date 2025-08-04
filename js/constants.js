// js/settings/constants.ts
export const LLM_PROVIDERS = {
    scaleway: {
        id: 'scaleway',
        name: 'Scaleway',
        models: [
            'llama-3.3-70b-instruct',
            'llama-3.1-8b-instruct',
            'llama-3.1-70b-instruct',
            'mistral-nemo-instruct-2407'
        ],
        defaultModel: 'llama-3.3-70b-instruct',
        requiresApiKey: false, // Using .env
        endpoint: 'https://api.scaleway.ai/v1'
    },
    azure: {
        id: 'azure',
        name: 'Azure OpenAI',
        models: [
            'gpt-4',
            'gpt-4-turbo',
            'gpt-35-turbo',
            'gpt-4o'
        ],
        defaultModel: 'gpt-4',
        requiresApiKey: false, // Using .env
        configurable: true // Endpoint can be configured
    },
    ollama: {
        id: 'ollama',
        name: 'Ollama (Local)',
        models: [
            'llama3.3:latest',
            'llama3.2:latest',
            'llama3.1:latest',
            'mistral:latest',
            'mixtral:latest',
            'codellama:latest',
            'phi3:latest'
        ],
        defaultModel: 'llama3.3:latest',
        requiresApiKey: false,
        endpoint: 'http://localhost:11434',
        configurable: true
    }
};
export const MITRE_VERSIONS = [
    'v13.1',
    'v13.0',
    'v12.1',
    'v12.0'
];
export const PIPELINE_STEPS = [
    {
        id: 'step1',
        name: 'Document Processing',
        description: 'Extract and process uploaded documents',
        settings: [
            'minTextLength',
            'maxTextLength',
            'chunkSize'
        ]
    },
    {
        id: 'step2',
        name: 'DFD Extraction',
        description: 'Extract Data Flow Diagrams from documents',
        settings: [
            'enableQualityCheck',
            'enableMultiPass',
            'maxComponents'
        ]
    },
    {
        id: 'step3',
        name: 'Threat Generation',
        description: 'Generate threats from DFD components',
        settings: [
            'minRiskScore',
            'maxComponentsToAnalyze',
            'similarityThreshold'
        ]
    },
    {
        id: 'step4',
        name: 'Threat Refinement',
        description: 'Refine and enhance identified threats',
        settings: [
            'enableLlmEnrichment',
            'mitreEnabled',
            'mitreVersion'
        ]
    },
    {
        id: 'step5',
        name: 'Attack Path Analysis',
        description: 'Generate attack paths and scenarios',
        settings: [
            'maxAttackPaths',
            'complexityThreshold',
            'enableMermaid'
        ]
    }
];
export const DEFAULT_SETTINGS = {
    llm: {
        provider: 'scaleway',
        model: 'llama-3.3-70b-instruct',
        temperature: 0.2,
        maxTokens: 4096
    },
    processing: {
        timeout: 5000,
        enableAsyncProcessing: true,
        maxConcurrentCalls: 5,
        detailedLlmLogging: true
    },
    debug: {
        debugMode: false,
        forceRuleBased: false,
        verboseErrorReporting: true
    },
    features: {
        enableQualityCheck: true,
        enableMultiPass: true,
        enableMermaid: true,
        enableLlmEnrichment: true,
        mitreEnabled: true,
        mitreVersion: 'v13.1'
    },
    directories: {
        input: './input_documents',
        output: './output'
    },
    stepSpecific: {
        step1: {
            minTextLength: 100,
            maxTextLength: 1000000,
            chunkSize: 4000
        },
        step2: {
            maxComponents: 20
        },
        step3: {
            minRiskScore: 3,
            maxComponentsToAnalyze: 20,
            similarityThreshold: 0.7
        },
        step4: {
            confidenceThreshold: 0.8
        },
        step5: {
            maxAttackPaths: 10,
            complexityThreshold: 0.5
        }
    }
};
