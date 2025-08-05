"use strict";
// js/storage.ts
// Storage functionality for settings - No type declarations, only implementation
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
var SettingsStorage = /** @class */ (function () {
    function SettingsStorage() {
    }
    SettingsStorage.loadSettings = function () {
        try {
            var stored = localStorage.getItem(this.STORAGE_KEY);
            if (stored) {
                var parsed = JSON.parse(stored);
                return this.deepMerge(DEFAULT_SETTINGS, parsed);
            }
        }
        catch (error) {
            console.error('Error loading settings from localStorage:', error);
        }
        return __assign({}, DEFAULT_SETTINGS);
    };
    SettingsStorage.saveSettings = function (settings) {
        return __awaiter(this, void 0, void 0, function () {
            var backendConfig, response, data, error_1;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 4, , 5]);
                        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(settings));
                        backendConfig = this.prepareBackendConfig(settings);
                        return [4 /*yield*/, fetch(this.CONFIG_ENDPOINT, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(backendConfig)
                            })];
                    case 1:
                        response = _a.sent();
                        return [4 /*yield*/, response.json()];
                    case 2:
                        data = _a.sent();
                        if (!response.ok) {
                            throw new Error(data.error || 'Failed to save settings');
                        }
                        return [4 /*yield*/, this.saveConfigFile(settings)];
                    case 3:
                        _a.sent();
                        return [2 /*return*/, { success: true }];
                    case 4:
                        error_1 = _a.sent();
                        console.error('Error saving settings:', error_1);
                        return [2 /*return*/, {
                                success: false,
                                error: error_1 instanceof Error ? error_1.message : 'Unknown error'
                            }];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    SettingsStorage.loadFromBackend = function () {
        return __awaiter(this, void 0, void 0, function () {
            var response, data, error_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 3, , 4]);
                        return [4 /*yield*/, fetch(this.CONFIG_ENDPOINT)];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) {
                            throw new Error('Failed to load backend config');
                        }
                        return [4 /*yield*/, response.json()];
                    case 2:
                        data = _a.sent();
                        return [2 /*return*/, this.parseBackendConfig(data)];
                    case 3:
                        error_2 = _a.sent();
                        console.error('Error loading from backend:', error_2);
                        return [2 /*return*/, {}];
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    SettingsStorage.saveConfigFile = function (settings) {
        return __awaiter(this, void 0, void 0, function () {
            var response, error_3;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 2, , 3]);
                        return [4 /*yield*/, fetch("".concat(CoreUtilities.API_BASE, "/save-config-file"), {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(this.prepareBackendConfig(settings))
                            })];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) {
                            throw new Error('Failed to save config file');
                        }
                        return [3 /*break*/, 3];
                    case 2:
                        error_3 = _a.sent();
                        console.error('Error saving config file:', error_3);
                        return [3 /*break*/, 3];
                    case 3: return [2 /*return*/];
                }
            });
        });
    };
    SettingsStorage.prepareBackendConfig = function (settings) {
        var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m, _o, _p, _q, _r, _s, _t, _u, _v, _w, _x, _y, _z, _0, _1, _2, _3, _4, _5, _6, _7, _8, _9;
        return {
            llm_provider: (_a = settings.llm) === null || _a === void 0 ? void 0 : _a.provider,
            llm_model: (_b = settings.llm) === null || _b === void 0 ? void 0 : _b.model,
            local_llm_endpoint: (_c = settings.llm) === null || _c === void 0 ? void 0 : _c.endpoint,
            temperature: (_d = settings.llm) === null || _d === void 0 ? void 0 : _d.temperature,
            max_tokens: (_e = settings.llm) === null || _e === void 0 ? void 0 : _e.maxTokens,
            timeout: (_f = settings.processing) === null || _f === void 0 ? void 0 : _f.timeout,
            enable_async_processing: (_g = settings.processing) === null || _g === void 0 ? void 0 : _g.enableAsyncProcessing,
            max_concurrent_calls: (_h = settings.processing) === null || _h === void 0 ? void 0 : _h.maxConcurrentCalls,
            detailed_llm_logging: (_j = settings.processing) === null || _j === void 0 ? void 0 : _j.detailedLlmLogging,
            debug_mode: (_k = settings.debug) === null || _k === void 0 ? void 0 : _k.debugMode,
            force_rule_based: (_l = settings.debug) === null || _l === void 0 ? void 0 : _l.forceRuleBased,
            verbose_error_reporting: (_m = settings.debug) === null || _m === void 0 ? void 0 : _m.verboseErrorReporting,
            enable_quality_check: (_o = settings.features) === null || _o === void 0 ? void 0 : _o.enableQualityCheck,
            enable_multi_pass: (_p = settings.features) === null || _p === void 0 ? void 0 : _p.enableMultiPass,
            enable_mermaid: (_q = settings.features) === null || _q === void 0 ? void 0 : _q.enableMermaid,
            enable_llm_enrichment: (_r = settings.features) === null || _r === void 0 ? void 0 : _r.enableLlmEnrichment,
            mitre_enabled: (_s = settings.features) === null || _s === void 0 ? void 0 : _s.mitreEnabled,
            mitre_version: (_t = settings.features) === null || _t === void 0 ? void 0 : _t.mitreVersion,
            enable_spell_check: (_v = (_u = settings.stepSpecific) === null || _u === void 0 ? void 0 : _u.step1) === null || _v === void 0 ? void 0 : _v.enableSpellCheck,
            enable_grammar_check: (_x = (_w = settings.stepSpecific) === null || _w === void 0 ? void 0 : _w.step1) === null || _x === void 0 ? void 0 : _x.enableGrammarCheck,
            max_components: (_z = (_y = settings.stepSpecific) === null || _y === void 0 ? void 0 : _y.step2) === null || _z === void 0 ? void 0 : _z.maxComponents,
            enable_diagram_validation: (_1 = (_0 = settings.stepSpecific) === null || _0 === void 0 ? void 0 : _0.step2) === null || _1 === void 0 ? void 0 : _1.enableDiagramValidation,
            confidence_threshold: (_3 = (_2 = settings.stepSpecific) === null || _2 === void 0 ? void 0 : _2.step3) === null || _3 === void 0 ? void 0 : _3.confidenceThreshold,
            similarity_threshold: (_5 = (_4 = settings.stepSpecific) === null || _4 === void 0 ? void 0 : _4.step3) === null || _5 === void 0 ? void 0 : _5.similarityThreshold,
            max_attack_paths: (_7 = (_6 = settings.stepSpecific) === null || _6 === void 0 ? void 0 : _6.step5) === null || _7 === void 0 ? void 0 : _7.maxAttackPaths,
            complexity_threshold: (_9 = (_8 = settings.stepSpecific) === null || _8 === void 0 ? void 0 : _8.step5) === null || _9 === void 0 ? void 0 : _9.complexityThreshold
        };
    };
    SettingsStorage.parseBackendConfig = function (data) {
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
    };
    SettingsStorage.deepMerge = function (target, source) {
        var _this = this;
        var output = __assign({}, target);
        if (this.isObject(target) && this.isObject(source)) {
            Object.keys(source).forEach(function (key) {
                var _a, _b;
                if (_this.isObject(source[key])) {
                    if (!(key in target)) {
                        Object.assign(output, (_a = {}, _a[key] = source[key], _a));
                    }
                    else {
                        output[key] = _this.deepMerge(target[key], source[key]);
                    }
                }
                else {
                    Object.assign(output, (_b = {}, _b[key] = source[key], _b));
                }
            });
        }
        return output;
    };
    SettingsStorage.isObject = function (item) {
        return item && typeof item === 'object' && !Array.isArray(item);
    };
    SettingsStorage.STORAGE_KEY = 'threat_modeling_settings';
    SettingsStorage.CONFIG_ENDPOINT = "".concat(CoreUtilities.API_BASE, "/config");
    return SettingsStorage;
}());
// Make it available globally
window.SettingsStorage = SettingsStorage;
//# sourceMappingURL=storage.js.map