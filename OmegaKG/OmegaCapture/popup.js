/**
 * Popup script for Omega_KG Chrome extension
 * Handles capture button interaction and debug mode toggle
 */

const STORAGE_KEYS = {
    API_KEY: 'omega_api_key',
    LAST_CAPTURE: 'omega_last_capture',
};

// DOM Elements
const statusDiv = document.getElementById('status');
const captureBtn = document.getElementById('captureBtn');
const logoHeader = document.getElementById('logoHeader');
const debugPanel = document.getElementById('debugPanel');
const configLink = document.getElementById('configLink');

let debugMode = false;

/**
 * Set the popup status text and apply a visual state class.
 * @param {string} message - Text to display in the status area.
 * @param {'success'|'error'|'info'} [type='info'] - Visual state to apply: 'success', 'error', or 'info'.
 */
function updateStatus(message, type = 'info') {
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
}

/**
 * Populate the debug panel with stored configuration and server health.
 *
 * Reads the API key, server URL, and last capture timestamp from chrome.storage.local,
 * updates the debug panel DOM elements (API key status, server URL, last capture) and
 * performs a GET to the server's /health endpoint to set the server status.
 * Any errors encountered while loading debug information are caught and logged to the console.
 */
async function loadDebugInfo() {
    try {
        const data = await chrome.storage.local.get([
            STORAGE_KEYS.API_KEY,
            'omega_server_url',
            STORAGE_KEYS.LAST_CAPTURE,
        ]);

        const apiKey = data[STORAGE_KEYS.API_KEY];
        const serverUrl = data['omega_server_url'] || 'http://localhost:8765';
        const lastCapture = data[STORAGE_KEYS.LAST_CAPTURE] || 'Never';

        // Update debug panel
        document.getElementById('debugApiKey').textContent = apiKey ? '✓ Configured' : '✗ Not configured';
        document.getElementById('debugServer').textContent = serverUrl;
        document.getElementById('debugLastCapture').textContent = lastCapture;

        // Test server health
        try {
            const healthUrl = new URL('/health', serverUrl).toString();
            const response = await fetch(healthUrl, { method: 'GET' });
            if (response.ok) {
                document.getElementById('debugServerStatus').textContent = '✓ Online';
            } else {
                document.getElementById('debugServerStatus').textContent = '✗ Error';
            }
        } catch {
            document.getElementById('debugServerStatus').textContent = '✗ Offline';
        }
    } catch (error) {
        console.error('[Omega_KG] Error loading debug info:', error);
    }
}

/**
 * Update the popup UI to reflect whether an API key is configured.
 *
 * Reads the stored API key and sets the status message, enables or disables
 * the capture button, and updates the button text to indicate required action.
 */
async function checkConfiguration() {
    const data = await chrome.storage.local.get(STORAGE_KEYS.API_KEY);
    const isConfigured = !!data[STORAGE_KEYS.API_KEY];

    if (!isConfigured) {
        updateStatus('⚠️ API Key not configured. Click "Configure API Key" to set up.', 'error');
        captureBtn.disabled = true;
        captureBtn.textContent = '🔒 Configure First';
    } else {
        updateStatus('Ready to capture conversations.');
        captureBtn.disabled = false;
        captureBtn.textContent = '📸 Capture Conversation';
    }
}

/**
 * Initiates a conversation capture from the active tab, updates UI status, and stores the capture timestamp.
 *
 * On success, saves the capture time to local storage under STORAGE_KEYS.LAST_CAPTURE and updates the debug panel if visible.
 * On failure or error, updates the status element with an error message and re-enables the capture button.
 */
async function captureConversation() {
    updateStatus('⏳ Capturing...', 'info');
    captureBtn.disabled = true;

    try {
        // Send message to content script to capture
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        // Execute capture in content script
        const response = await chrome.tabs.sendMessage(tab.id, {
            type: 'TRIGGER_CAPTURE',
        });

        if (response?.success) {
            // Update last capture timestamp
            const now = new Date().toLocaleString();
            await chrome.storage.local.set({ [STORAGE_KEYS.LAST_CAPTURE]: now });

            updateStatus('✅ Conversation captured successfully!', 'success');

            // Update debug panel if visible
            if (debugMode) {
                document.getElementById('debugLastCapture').textContent = now;
            }
        } else {
            updateStatus('❌ Capture failed: ' + (response?.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('[Omega_KG] Capture error:', error);
        updateStatus('❌ Error: ' + error.message, 'error');
    } finally {
        captureBtn.disabled = false;
    }
}

/**
 * Toggle the debug panel visibility and load debug information when enabling it.
 *
 * Flips the `debugMode` flag, adds or removes the panel's `show` class, and calls `loadDebugInfo` when the panel is shown.
 */
function toggleDebugMode() {
    debugMode = !debugMode;
    if (debugMode) {
        debugPanel.classList.add('show');
        loadDebugInfo();
    } else {
        debugPanel.classList.remove('show');
    }
}

/**
 * Open extension options page
 */
function openOptions() {
    chrome.runtime.openOptionsPage();
}

// Event listeners
captureBtn.addEventListener('click', captureConversation);

logoHeader.addEventListener('click', (e) => {
    e.preventDefault();
    captureConversation();
});

logoHeader.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    toggleDebugMode();
});

configLink.addEventListener('click', openOptions);

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkConfiguration();
    console.debug('[Omega_KG] Popup initialized');
});

console.debug('[Omega_KG] Popup script loaded');