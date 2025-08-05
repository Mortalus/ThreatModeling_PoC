// js/storage.ts
// Storage functionality for settings - No type declarations, only implementation

class SettingsStorage {
    private static readonly STORAGE_KEY = 'threat_modeling_settings';
    private static readonly CONFIG_ENDPOINT = `${CoreUtilities.API_BASE}/config`;

    static loadSettings(): ThreatModelingConfiguration {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            if (stored) {
                const parsed = JSON.parse(stored);
                return this.deepMerge(DEFAULT_SETTINGS, parsed);
            }
        } catch (error) {
            console.error('Error loading settings from localStorage:', error);
        }
        return { ...DEFAULT_SETTINGS };
    }

    static async saveSettings(settings: ThreatModelingConfiguration): Promise<{ success: boolean; error?: string }> {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(settings));
            const backendConfig = this.prepareBackendConfig(settings);

            const response = await fetch(this.CONFIG_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(backendConfig)
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to save settings');
            }

            await this.saveConfigFile(settings);
            return { success: true };
        } catch (error) {
            console.error('Error saving settings:', error);
            return { 
                success: false, 
                error: error instanceof Error ? error.message : 'Unknown error'
            };
        }
    }

    static async loadFromBackend(): Promise<Partial<ThreatModelingConfiguration>> {
        try {
            const response = await fetch(this.CONFIG_ENDPOINT);
            if (!response.ok) {
                throw new Error('Failed to load backend config');
            }
            
            const data = await response.json();
            return this.parseBackendConfig(data);
        } catch (error) {
            console.error('Error loading from backend:', error);
            return {};
        }
    }

    private static async saveConfigFile(settings: ThreatModelingConfiguration): Promise<void> {
        try {
            const response = await fetch(`${CoreUtilities.API_BASE}/save-config-file`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.prepareBackendConfig(settings))
            });
            
            if (!response.ok) {
                throw new Error('Failed to save config file');
            }
        } catch (error) {
            console.error('Error saving config file:', error);
        }
    }

    private static prepareBackendConfig(settings: ThreatModelingConfiguration): any {
        return {
            llm_provider: settings.llm?.provider,
            llm_model: settings.llm?.model,
            local_llm_endpoint: settings.llm?.endpoint,
            temperature: settings.llm?.temperature,
            max_tokens: settings.llm?.maxTokens,
            
            timeout: settings.processing?.timeout,
            enable_async_processing: settings.processing?.enableAsyncProcessing,
            max_concurrent_calls: settings.processing?.maxConcurrentCalls,
            detailed_llm_logging: settings.processing?.detailedLlmLogging,
            
            debug_mode: settings.debug?.debugMode,
            force_rule_based: settings.debug?.forceRuleBased,
            verbose_error_reporting: settings.debug?.verboseErrorReporting,
            
            enable_quality_check: settings.features?.enableQualityCheck,
            enable_multi_pass: settings.features?.enableMultiPass,
            enable_mermaid: settings.features?.enableMermaid,
            enable_llm_enrichment: settings.features?.enableLlmEnrichment,
            mitre_enabled: settings.features?.mitreEnabled,
            mitre_version: settings.features?.mitreVersion,
            
            enable_spell_check: settings.stepSpecific?.step1?.enableSpellCheck,
            enable_grammar_check: settings.stepSpecific?.step1?.enableGrammarCheck,
            max_components: settings.stepSpecific?.step2?.maxComponents,
            enable_diagram_validation: settings.stepSpecific?.step2?.enableDiagramValidation,
            confidence_threshold: settings.stepSpecific?.step3?.confidenceThreshold,
            similarity_threshold: settings.stepSpecific?.step3?.similarityThreshold,
            max_attack_paths: settings.stepSpecific?.step5?.maxAttackPaths,
            complexity_threshold: settings.stepSpecific?.step5?.complexityThreshold
        };
    }

    private static parseBackendConfig(data: any): Partial<ThreatModelingConfiguration> {
        return {
            llm: {
                provider: data.llm_provider,
                model: data.llm_model,
                temperature: data.temperature,
                maxTokens: data.max_tokens,
                endpoint: data.local_llm_endpoint
            },
            processing: {
                timeout: data.timeout,
                enableAsyncProcessing: data.enable_async_processing,
                maxConcurrentCalls: data.max_concurrent_calls,
                detailedLlmLogging: data.detailed_llm_logging
            },
            features: {
                enableQualityCheck: data.enable_quality_check,
                enableMultiPass: data.enable_multi_pass,
                enableMermaid: data.enable_mermaid,
                enableLlmEnrichment: data.enable_llm_enrichment,
                mitreEnabled: data.mitre_enabled,
                mitreVersion: data.mitre_version
            }
        };
    }

    private static deepMerge(target: any, source: any): any {
        const output = { ...target };
        if (this.isObject(target) && this.isObject(source)) {
            Object.keys(source).forEach(key => {
                if (this.isObject(source[key])) {
                    if (!(key in target)) {
                        Object.assign(output, { [key]: source[key] });
                    } else {
                        output[key] = this.deepMerge(target[key], source[key]);
                    }
                } else {
                    Object.assign(output, { [key]: source[key] });
                }
            });
        }
        return output;
    }

    private static isObject(item: any): boolean {
        return item && typeof item === 'object' && !Array.isArray(item);
    }
}

// Make it available globally
(window as any).SettingsStorage = SettingsStorage;