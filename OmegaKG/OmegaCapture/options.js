/**
 * Options page script for Omega_KG Chrome extension
 * Handles secure storage and retrieval of bootstrap API key
 */

const STORAGE_KEYS = {
    API_KEY: 'omega_api_key',
    JWT_TOKEN: 'omega_jwt_token',
    JWT_EXPIRY: 'omega_jwt_expiry',
};

// DOM Elements
const form = document.getElementById('configForm');
const apiKeyInput = document.getElementById('apiKey');
const serverUrlInput = document.getElementById('serverUrl');
const saveBtn = document.getElementById('saveBtn');
const clearBtn = document.getElementById('clearBtn');
const statusMessage = document.getElementById('statusMessage');
const apiKeyStatus = document.getElementById('apiKeyStatus');
const serverUrlStatus = document.getElementById('serverUrlStatus');

/**
 * Initialize the options page by loading saved values
 */
async function initializeForm() {
    try {
        console.debug('[Omega_KG] Loading stored configuration...');
        const data = await chrome.storage.local.get([
            STORAGE_KEYS.API_KEY,
            'omega_server_url',
        ]);

        if (data[STORAGE_KEYS.API_KEY]) {
            apiKeyInput.value = data[STORAGE_KEYS.API_KEY];
            updateFieldStatus(apiKeyStatus, 'saved', 'API key saved ✓');
            savedApiKey = data[STORAGE_KEYS.API_KEY];
        }

        // Get current server URL from storage or use default
        const currentServerUrl = data['omega_server_url'] || 'http://localhost:8765';
        serverUrlInput.value = currentServerUrl;
        savedServerUrl = currentServerUrl;
        if (data['omega_server_url']) {
            updateFieldStatus(serverUrlStatus, 'saved', 'Server URL loaded ✓');
        }

        console.debug('[Omega_KG] Configuration loaded');
    } catch (error) {
        console.error('[Omega_KG] Failed to load configuration:', error);
        showStatus('error', `Failed to load configuration: ${error.message}`);
    }
}

/**
 * Update field status indicator
 * @param {HTMLElement} element - Status element
 * @param {string} status - Status type ('saved', 'unsaved', 'error')
 * @param {string} message - Status message
 */
function updateFieldStatus(element, status, message) {
    element.className = `field-status ${status}`;
    element.textContent = message;
}

/**
 * Display status message to user
 * @param {string} type - Message type ('success', 'error', 'info')
 * @param {string} message - Message text
 */
function showStatus(type, message) {
    statusMessage.className = `status-message ${type}`;
    statusMessage.textContent = message;
    console.debug(`[Omega_KG] Status (${type}): ${message}`);

    // Auto-hide success messages after 3 seconds
    if (type === 'success') {
        setTimeout(() => {
            statusMessage.className = 'status-message';
        }, 3000);
    }
}

/**
 * Validate API key format
 * @param {string} apiKey - API key to validate
 * @returns {boolean} True if valid
 */
function validateApiKey(apiKey) {
    return apiKey && apiKey.trim().length >= 10;
}

/**
 * Validate server URL format
 * @param {string} url - URL to validate
 * @returns {boolean} True if valid
 */
function validateServerUrl(url) {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
}

/**
 * Test connection to server
 * @param {string} apiKey - Bootstrap API key
 * @param {string} serverUrl - Server base URL
 * @returns {Promise<boolean>} True if connection successful
 */
async function testServerConnection(apiKey, serverUrl) {
    try {
        console.debug('[Omega_KG] Testing server connection...');
        const tokenUrl = new URL('/auth/token', serverUrl).toString();

        const response = await fetch(tokenUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey,
            },
        });

        if (response.ok) {
            const data = await response.json();
            if (data.access_token) {
                console.debug('[Omega_KG] Connection test passed, token received');
                // Store JWT token for later use
                await storeJwtToken(data.access_token, data.expires_in || 86400);
                return true;
            }
        }

        const errorText = await response.text();
        throw new Error(`Server returned ${response.status}: ${errorText}`);
    } catch (error) {
        console.error('[Omega_KG] Connection test failed:', error);
        throw error;
    }
}

/**
 * Store JWT token in chrome.storage.local
 * @param {string} token - JWT token
 * @param {number} expiresIn - Token expiration in seconds
 */
async function storeJwtToken(token, expiresIn) {
    const expiryTime = Date.now() + (expiresIn * 1000);
    await chrome.storage.local.set({
        [STORAGE_KEYS.JWT_TOKEN]: token,
        [STORAGE_KEYS.JWT_EXPIRY]: expiryTime,
    });
    console.debug('[Omega_KG] JWT token stored');
}

/**
 * Save configuration
 */
async function saveConfiguration() {
    const apiKey = apiKeyInput.value.trim();
    const serverUrl = serverUrlInput.value.trim();

    // Validate inputs
    if (!validateApiKey(apiKey)) {
        updateFieldStatus(apiKeyStatus, 'error', 'API key too short (min 10 chars)');
        showStatus('error', 'Please enter a valid API key');
        return;
    }

    if (!validateServerUrl(serverUrl)) {
        updateFieldStatus(serverUrlStatus, 'error', 'Invalid URL format');
        showStatus('error', 'Please enter a valid server URL');
        return;
    }

    // Disable save button during test
    saveBtn.disabled = true;
    showStatus('info', 'Testing server connection...');

    try {
        // Test connection to server
        await testServerConnection(apiKey, serverUrl);

        // Save API key to chrome.storage.local
        await chrome.storage.local.set({
            [STORAGE_KEYS.API_KEY]: apiKey,
            'omega_server_url': serverUrl,
        });

        // Update saved values for synchronous comparison
        savedApiKey = apiKey;
        savedServerUrl = serverUrl;

        console.debug('[Omega_KG] Configuration saved successfully');
        updateFieldStatus(apiKeyStatus, 'saved', 'API key saved ✓');
        updateFieldStatus(serverUrlStatus, 'saved', 'Server URL saved ✓');
        showStatus('success', '✓ Configuration saved and verified!');

        // Notify background script of new configuration
        try {
            await chrome.runtime.sendMessage({
                type: 'CONFIG_UPDATED',
                config: { apiKey, serverUrl },
            });
            console.debug('[Omega_KG] Background script notified');
        } catch (err) {
            console.debug('[Omega_KG] Could not notify background (may be inactive)');
        }
    } catch (error) {
        console.error('[Omega_KG] Save failed:', error);
        updateFieldStatus(apiKeyStatus, 'error', 'Connection failed');
        showStatus('error', `Failed: ${error.message}`);
    } finally {
        saveBtn.disabled = false;
    }
}

/**
 * Clear all configuration
 */
async function clearConfiguration() {
    if (!confirm('Are you sure you want to clear all configuration?')) {
        return;
    }

    try {
        await chrome.storage.local.remove([
            STORAGE_KEYS.API_KEY,
            'omega_server_url',
            STORAGE_KEYS.JWT_TOKEN,
            STORAGE_KEYS.JWT_EXPIRY,
        ]);

        apiKeyInput.value = '';
        serverUrlInput.value = 'http://localhost:8765';
        savedApiKey = '';
        savedServerUrl = 'http://localhost:8765';
        apiKeyStatus.className = 'field-status';
        apiKeyStatus.textContent = '';
        serverUrlStatus.className = 'field-status';
        serverUrlStatus.textContent = '';

        showStatus('info', '✓ Configuration cleared');
        console.debug('[Omega_KG] Configuration cleared');
    } catch (error) {
        console.error('[Omega_KG] Clear failed:', error);
        showStatus('error', `Failed to clear: ${error.message}`);
    }
}

// Saved values for synchronous comparison (avoid race conditions)
let savedApiKey = '';
let savedServerUrl = 'http://localhost:8765';

/**
 * Mark form as having unsaved changes
 * Uses strict equality comparison to detect changes, including when saved values are cleared
 * Synchronous version to avoid race conditions with async storage reads
 */
function markUnsaved() {
    // Get current input values
    const currentApiKey = apiKeyInput.value.trim();
    const currentServerUrl = serverUrlInput.value.trim();

    // Strict equality comparison for API key (detects both changes and clearing)
    if (currentApiKey !== savedApiKey) {
        updateFieldStatus(apiKeyStatus, 'unsaved', 'Changes not saved');
    } else {
        // Reset to saved state if values match
        updateFieldStatus(apiKeyStatus, 'saved', 'API key saved ✓');
    }

    // Strict equality comparison for server URL
    if (currentServerUrl !== savedServerUrl) {
        updateFieldStatus(serverUrlStatus, 'unsaved', 'Changes not saved');
    } else {
        // Reset to saved state if values match
        updateFieldStatus(serverUrlStatus, 'saved', 'Server URL saved ✓');
    }
}

// Event listeners
form.addEventListener('submit', (e) => {
    e.preventDefault();
    saveConfiguration();
});

clearBtn.addEventListener('click', clearConfiguration);

apiKeyInput.addEventListener('change', markUnsaved);
serverUrlInput.addEventListener('change', markUnsaved);

// Initialize on page load
document.addEventListener('DOMContentLoaded', initializeForm);

console.debug('[Omega_KG] Options page loaded');
