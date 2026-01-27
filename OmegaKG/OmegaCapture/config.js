/**
 * Configuration module for Omega_KG Chrome extension
 * Centralizes all configurable settings to avoid hardcoded values
 */

const DEFAULT_CONFIG = {
    // Default server URL - can be overridden in options
    SERVER_URL: 'http://localhost:8765',
    // API endpoints (relative to SERVER_URL)
    ENDPOINTS: {
        AUTH_TOKEN: '/auth/token',
        CAPTURE: '/capture',
        HEALTH: '/health',
        LINEAR_WEBHOOK: '/webhook/linear',
    },
    // Extension settings
    EXTENSION_ID: 'Omega_KG_Capture',
    // Timeout settings (ms)
    TIMEOUTS: {
        AUTH: 5000,
        CAPTURE: 10000,
        HEALTH_CHECK: 3000,
    },
    // Validation
    VALIDATION: {
        API_KEY_MIN_LENGTH: 10,
        MAX_URL_LENGTH: 2048,
    }
};

/**
 * Configuration manager for the Chrome extension
 */
class ExtensionConfig {
    constructor() {
        this.config = { ...DEFAULT_CONFIG };
        this.listeners = new Set();
    }

    /**
     * Get the current server URL
     * @returns {Promise<string>} Server URL
     */
    async getServerUrl() {
        try {
            const data = await chrome.storage.local.get(['omega_server_url']);
            return data.omega_server_url || this.config.SERVER_URL;
        } catch (error) {
            console.warn('[Omega_KG] Failed to get server URL, using default:', error);
            return this.config.SERVER_URL;
        }
    }

    /**
     * Get full URL for an endpoint
     * @param {string} endpoint - Endpoint name from ENDPOINTS
     * @returns {Promise<string>} Full URL
     */
    async getEndpointUrl(endpoint) {
        const serverUrl = await this.getServerUrl();
        const endpointPath = this.config.ENDPOINTS[endpoint];
        if (!endpointPath) {
            throw new Error(`Unknown endpoint: ${endpoint}`);
        }
        return new URL(endpointPath, serverUrl).toString();
    }

    /**
     * Set server URL
     * @param {string} serverUrl - New server URL
     * @returns {Promise<void>}
     */
    async setServerUrl(serverUrl) {
        try {
            await chrome.storage.local.set({
                omega_server_url: serverUrl
            });
            // Notify listeners of config change
            this.notifyListeners();
            console.debug('[Omega_KG] Server URL updated:', serverUrl);
        } catch (error) {
            console.error('[Omega_KG] Failed to save server URL:', error);
            throw error;
        }
    }

    /**
     * Get all configuration
     * @returns {Promise<Object>} Complete configuration
     */
    async getConfig() {
        const serverUrl = await this.getServerUrl();
        return {
            ...this.config,
            serverUrl
        };
    }

    /**
     * Add listener for config changes
     * @param {Function} callback - Callback function
     */
    addListener(callback) {
        this.listeners.add(callback);
    }

    /**
     * Remove listener for config changes
     * @param {Function} callback - Callback function to remove
     */
    removeListener(callback) {
        this.listeners.delete(callback);
    }

    /**
     * Notify all listeners of config change
     * @private
     */
    notifyListeners() {
        this.listeners.forEach(callback => {
            try {
                callback();
            } catch (error) {
                console.error('[Omega_KG] Config listener error:', error);
            }
        });
    }

    /**
     * Validate server URL
     * @param {string} url - URL to validate
     * @returns {boolean} True if valid
     */
    validateServerUrl(url) {
        try {
            if (!url || url.length > this.config.VALIDATION.MAX_URL_LENGTH) {
                return false;
            }
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Reset to default configuration
     * @returns {Promise<void>}
     */
    async resetToDefaults() {
        try {
            await chrome.storage.local.remove(['omega_server_url']);
            this.notifyListeners();
            console.debug('[Omega_KG] Configuration reset to defaults');
        } catch (error) {
            console.error('[Omega_KG] Failed to reset configuration:', error);
            throw error;
        }
    }
}

// Create singleton instance
const config = new ExtensionConfig();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { config, DEFAULT_CONFIG };
} else if (typeof window !== 'undefined') {
    window.ExtensionConfig = config;
    window.DEFAULT_CONFIG = DEFAULT_CONFIG;
}
