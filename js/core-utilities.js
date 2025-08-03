/* ===== CORE-UTILITIES.JS - Core Utility Functions and Constants ===== */

/**
 * Core utility functions, constants, and helper methods used throughout the application.
 * This file should be loaded first before any other JavaScript modules.
 */

(function(window) {
    'use strict';

    // ===== CONFIGURATION AND CONSTANTS =====

    const API_BASE = window.location.hostname === 'localhost' ? 
        'http://localhost:5000/api' : 
        '/api';

    const WS_BASE = window.location.hostname === 'localhost' ? 
        'http://localhost:5000' : 
        window.location.origin;

    // Application constants
    const APP_CONFIG = {
        maxFileSize: 50 * 1024 * 1024, // 50MB
        supportedFileTypes: ['.txt', '.pdf', '.doc', '.docx'],
        notificationDuration: 5000,
        progressUpdateInterval: 1000,
        autoSaveDelay: 2000,
        maxNotifications: 5
    };

    // Pipeline step configuration
    const PIPELINE_STEPS = [
        { id: 0, name: 'Document Upload', icon: '📄' },
        { id: 1, name: 'DFD Extraction', icon: '🔗' },
        { id: 2, name: 'Threat Identification', icon: '⚠️' },
        { id: 3, name: 'Threat Refinement', icon: '✨' },
        { id: 4, name: 'Attack Path Analysis', icon: '🎯' }
    ];

    // Status configurations
    const STATUS_CONFIG = {
        pending: { color: '#6b7280', icon: '⏸️' },
        running: { color: '#f59e0b', icon: '⚡' },
        completed: { color: '#10b981', icon: '✅' },
        error: { color: '#ef4444', icon: '❌' }
    };

    // ===== UTILITY FUNCTIONS =====

    /**
     * Debounce function to limit the rate of function execution
     */
    const debounce = (func, wait, immediate = false) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func.apply(this, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(this, args);
        };
    };

    /**
     * Throttle function to limit the rate of function execution
     */
    const throttle = (func, limit) => {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    };

    /**
     * Deep clone an object
     */
    const deepClone = (obj) => {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => deepClone(item));
        if (typeof obj === 'object') {
            const clonedObj = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    clonedObj[key] = deepClone(obj[key]);
                }
            }
            return clonedObj;
        }
    };

    /**
     * Generate a unique ID
     */
    const generateId = (prefix = 'id') => {
        return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    };

    /**
     * Format file size in human-readable format
     */
    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    /**
     * Format time duration in human-readable format
     */
    const formatDuration = (seconds) => {
        if (seconds < 60) return `${Math.round(seconds)}s`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    };

    /**
     * Capitalize first letter of a string
     */
    const capitalize = (str) => {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    };

    /**
     * Truncate text to specified length
     */
    const truncateText = (text, length = 100, suffix = '...') => {
        if (!text || text.length <= length) return text;
        return text.substring(0, length).trim() + suffix;
    };

    /**
     * Check if a value is empty
     */
    const isEmpty = (value) => {
        if (value == null) return true;
        if (typeof value === 'string' || Array.isArray(value)) return value.length === 0;
        if (typeof value === 'object') return Object.keys(value).length === 0;
        return false;
    };

    /**
     * Safe JSON parse with fallback
     */
    const safeJsonParse = (str, fallback = null) => {
        try {
            return JSON.parse(str);
        } catch (e) {
            console.warn('JSON parse error:', e);
            return fallback;
        }
    };

    /**
     * Safe JSON stringify with fallback
     */
    const safeJsonStringify = (obj, fallback = '{}') => {
        try {
            return JSON.stringify(obj, null, 2);
        } catch (e) {
            console.warn('JSON stringify error:', e);
            return fallback;
        }
    };

    // ===== STORAGE UTILITIES =====

    const storage = {
        get: (key, defaultValue = null) => {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (e) {
                console.warn(`Storage get error for key "${key}":`, e);
                return defaultValue;
            }
        },

        set: (key, value) => {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (e) {
                console.warn(`Storage set error for key "${key}":`, e);
                return false;
            }
        },

        remove: (key) => {
            try {
                localStorage.removeItem(key);
                return true;
            } catch (e) {
                console.warn(`Storage remove error for key "${key}":`, e);
                return false;
            }
        }
    };

    const sessionStorage = {
        get: (key, defaultValue = null) => {
            try {
                const item = window.sessionStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (e) {
                console.warn(`Session storage get error for key "${key}":`, e);
                return defaultValue;
            }
        },

        set: (key, value) => {
            try {
                window.sessionStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (e) {
                console.warn(`Session storage set error for key "${key}":`, e);
                return false;
            }
        },

        remove: (key) => {
            try {
                window.sessionStorage.removeItem(key);
                return true;
            } catch (e) {
                console.warn(`Session storage remove error for key "${key}":`, e);
                return false;
            }
        }
    };

    // ===== VALIDATION UTILITIES =====

    const validateFile = (file) => {
        const result = { valid: true, errors: [] };
        
        if (!file) {
            result.valid = false;
            result.errors.push('No file selected');
            return result;
        }
        
        if (file.size > APP_CONFIG.maxFileSize) {
            result.valid = false;
            result.errors.push(`File size (${formatFileSize(file.size)}) exceeds maximum allowed size (${formatFileSize(APP_CONFIG.maxFileSize)})`);
        }
        
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        if (!APP_CONFIG.supportedFileTypes.includes(extension)) {
            result.valid = false;
            result.errors.push(`File type "${extension}" is not supported. Supported types: ${APP_CONFIG.supportedFileTypes.join(', ')}`);
        }
        
        return result;
    };

    /**
     * Global error handler
     */
    const handleError = (error, context = 'Unknown') => {
        console.error(`Error in ${context}:`, error);
        
        let message = 'An unexpected error occurred';
        if (error?.message) {
            message = error.message;
        } else if (typeof error === 'string') {
            message = error;
        }
        
        if (window.showNotification) {
            window.showNotification(`Error: ${message}`, 'error');
        }
    };

    // ===== BROWSER DETECTION =====

    const browserSupport = {
        webSocket: typeof WebSocket !== 'undefined',
        localStorage: typeof Storage !== 'undefined',
        fileApi: typeof FileReader !== 'undefined',
        dragDrop: 'draggable' in document.createElement('div'),
        notifications: 'Notification' in window,
        serviceWorker: 'serviceWorker' in navigator,
        webWorker: typeof Worker !== 'undefined',
        intersectionObserver: 'IntersectionObserver' in window,
        resizeObserver: 'ResizeObserver' in window
    };

    const getBrowserInfo = () => {
        const userAgent = navigator.userAgent;
        const isChrome = /Chrome/.test(userAgent) && /Google Inc/.test(navigator.vendor);
        const isFirefox = /Firefox/.test(userAgent);
        const isSafari = /Safari/.test(userAgent) && /Apple Computer/.test(navigator.vendor);
        const isEdge = /Edg/.test(userAgent);
        const isMobile = /Mobi|Android/i.test(userAgent);
        
        return {
            isChrome, isFirefox, isSafari, isEdge, isMobile,
            userAgent, language: navigator.language,
            platform: navigator.platform,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine
        };
    };

    // ===== INITIALIZATION =====

    const initializeCoreUtilities = () => {
        window.addEventListener('error', (event) => {
            handleError(event.error, 'Global Error Handler');
        });
        
        window.addEventListener('unhandledrejection', (event) => {
            handleError(event.reason, 'Unhandled Promise Rejection');
        });
        
        console.log('Core Utilities initialized');
        console.log('Browser Support:', browserSupport);
    };

    // ===== EXPORTS =====

    const CoreUtilities = {
        API_BASE,
        WS_BASE,
        APP_CONFIG,
        PIPELINE_STEPS,
        STATUS_CONFIG,
        debounce,
        throttle,
        deepClone,
        generateId,
        formatFileSize,
        formatDuration,
        capitalize,
        truncateText,
        isEmpty,
        safeJsonParse,
        safeJsonStringify,
        storage,
        sessionStorage,
        validateFile,
        handleError,
        browserSupport,
        getBrowserInfo,
        initializeCoreUtilities
    };

    // Make available globally
    window.CoreUtilities = CoreUtilities;

    // Auto-initialize if DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeCoreUtilities);
    } else {
        initializeCoreUtilities();
    }

    console.log('Core Utilities loaded successfully');

})(window);