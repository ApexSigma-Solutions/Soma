// Background service worker - sends to localhost server
// Manifest V3 service workers go inactive - this is NORMAL Chrome behavior
// The extension will wake up when messages arrive or alarms fire

const STORAGE_KEYS = {
    API_KEY: 'omega_api_key',
    JWT_TOKEN: 'omega_jwt_token',
    JWT_EXPIRY: 'omega_jwt_expiry',
};

const DEFAULT_SERVER_URL = 'http://localhost:8765';

/**
 * Retrieve the configured server URL from Chrome local storage, falling back to the default if not set.
 * @returns {Promise<string>} The stored server URL, or DEFAULT_SERVER_URL if none is configured or an error occurs.
 */
async function getServerUrl() {
    try {
        const data = await chrome.storage.local.get(['omega_server_url']);
        return data['omega_server_url'] || DEFAULT_SERVER_URL;
    } catch (error) {
        console.warn('[Omega_KG] Failed to get server URL:', error);
        return DEFAULT_SERVER_URL;
    }
}

/**
 * Constructs the full URL for a named API endpoint.
 * @param {string} endpoint - One of: `AUTH_TOKEN`, `CAPTURE`, `HEALTH`, `LINEAR_WEBHOOK`.
 * @returns {string} The full URL string for the given endpoint.
 */
async function getEndpointUrl(endpoint) {
    const endpoints = {
        AUTH_TOKEN: '/v1/capture/auth/token',
        CAPTURE: '/v1/capture/capture',
        HEALTH: '/v1/health',
        LINEAR_WEBHOOK: '/v1/webhooks/linear',
    };

    const serverUrl = await getServerUrl();
    const endpointPath = endpoints[endpoint];
    if (!endpointPath) {
        throw new Error(`Unknown endpoint: ${endpoint}`);
    }
    return new URL(endpointPath, serverUrl).toString();
}

// Token cache (short-term cache to avoid excessive /auth/token calls)
let cachedJwtToken = null;
let cachedJwtExpiry = 0;

/**
 * Return a valid JWT token, preferring the in-memory cache, then stored token, and refreshing when necessary.
 *
 * Updates the in-memory cache (and persists token/expiry when refreshed) as a side effect.
 * @returns {string|null} `string` JWT token if available, `null` otherwise.
 */
async function getValidJwtToken() {
  try {
    // Check if cached token is still valid (with 60-second buffer)
    const now = Date.now();
    if (cachedJwtToken && cachedJwtExpiry > (now + 60000)) {
      console.debug('[Omega_KG] Using cached JWT token');
      return cachedJwtToken;
    }

    // Try to load from storage first
    const storedData = await chrome.storage.local.get([
      STORAGE_KEYS.JWT_TOKEN,
      STORAGE_KEYS.JWT_EXPIRY,
    ]);

    const storedToken = storedData[STORAGE_KEYS.JWT_TOKEN];
    const storedExpiry = storedData[STORAGE_KEYS.JWT_EXPIRY];

    if (storedToken && storedExpiry && storedExpiry > (now + 60000)) {
      console.debug('[Omega_KG] Using stored JWT token from storage');
      cachedJwtToken = storedToken;
      cachedJwtExpiry = storedExpiry;
      return storedToken;
    }

    // Token expired or not available - need to refresh
    console.debug('[Omega_KG] JWT token expired or missing, refreshing...');
    return await refreshJwtToken();
  } catch (error) {
    console.error('[Omega_KG] Failed to get valid JWT token:', error);
    return null;
  }
}

/**
 * Refreshes the JWT token using the stored bootstrap API key.
 *
 * On success caches the token and its expiry in memory and persists both to chrome.storage.local.
 * @returns {string|null} The new JWT token if refreshed successfully, `null` otherwise.
 */
async function refreshJwtToken() {
  try {
    // Get bootstrap API key from storage
    const storedData = await chrome.storage.local.get(STORAGE_KEYS.API_KEY);
    const apiKey = storedData[STORAGE_KEYS.API_KEY];

    if (!apiKey) {
      console.warn('[Omega_KG] No bootstrap API key configured - cannot refresh token');
      return null;
    }

    // Call /auth/token endpoint
    const authUrl = await getEndpointUrl('AUTH_TOKEN');
    const response = await fetch(authUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Token refresh failed (${response.status}): ${errorText}`);
    }

    const data = await response.json();
    const token = data.access_token;
    const expiresIn = data.expires_in || 86400; // Default 24 hours
    const expiry = Date.now() + (expiresIn * 1000);

    // Cache the token
    cachedJwtToken = token;
    cachedJwtExpiry = expiry;

    // Also store in chrome.storage.local for persistence across service worker reloads
    await chrome.storage.local.set({
      [STORAGE_KEYS.JWT_TOKEN]: token,
      [STORAGE_KEYS.JWT_EXPIRY]: expiry,
    });

    console.debug('[Omega_KG] JWT token refreshed successfully');
    return token;
  } catch (error) {
    console.error('[Omega_KG] JWT token refresh failed:', error);
    return null;
  }
}

// Listen for configuration updates from options.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'CONFIG_UPDATED') {
    console.debug('[Omega_KG] Configuration updated, clearing cached JWT token');
    cachedJwtToken = null;
    cachedJwtExpiry = 0;
  }
});

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log(
    "[Omega_KG] Service worker received message:",
    message.type,
  );

  if (message.type === "CAPTURE_CONVERSATION") {
    saveToLocalhost(message.data)
      .then((response) => {
        console.log(
          "[Omega_KG] ✅ Captured successfully:",
          response,
        );
        sendResponse({ success: true, response });
      })
      .catch((error) => {
        console.error(
          "[Omega_KG] ❌ Capture failed:",
          error,
        );
        sendResponse({ success: false, error: error.message });
      });

    return true; // Keep channel open for async response
  }

  if (message.type === "PING") {
    console.log("[Omega_KG] Service worker is alive - background.js:36");
    sendResponse({ alive: true, timestamp: new Date().toISOString() });
    return true;
  }
});

/**
 * Save conversation data to the configured localhost capture endpoint.
 *
 * Sends the provided conversation payload to the server using a JWT Bearer token
 * (the token is fetched or refreshed from the configured bootstrap API key as needed).
 * @param {Object} data - Conversation payload to send; typically includes fields such as `platform`, `messages`, and `url`.
 * @returns {Object} The parsed JSON response from the capture server.
 * @throws {Error} If no JWT is available, the network request fails, or the server responds with a non-OK status.
 */
async function saveToLocalhost(data) {
  console.log(
    "[Omega_KG] Attempting to save to localhost...",
    {
      platform: data.platform,
      messageCount: data.messages?.length,
      url: data.url,
    },
  );

  try {
    // Get valid JWT token (will refresh if necessary)
    const jwtToken = await getValidJwtToken();

    if (!jwtToken) {
      throw new Error(
        'No JWT token available. Please configure API key in extension options.'
      );
    }

    const response = await fetch(await getEndpointUrl('CAPTURE'), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${jwtToken}`,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Server returned ${response.status}: ${errorText}`);
    }

    const result = await response.json();
    console.log("[Omega_KG] Server response:", result);
    return result;
  } catch (error) {
    console.error(
      "[Omega_KG] ❌ Server error:",
      error.message,
    );
    throw error;
  }
}

// Periodic health check (ensures server is running)
chrome.alarms.create("health-check", { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "health-check") {
    try {
      const healthUrl = await getEndpointUrl('HEALTH');
      const response = await fetch(healthUrl, {
        method: 'GET',
        signal: AbortSignal.timeout(5000), // 5 second timeout
      });

      // Only access response properties if fetch succeeded
      // Validate response status before parsing JSON
      // response.ok is true only for 2xx status codes
      if (!response.ok) {
        // Handle client errors (4xx) and server errors (5xx) separately
        if (response.status >= 400 && response.status < 500) {
          const errorText = await response.text().catch(() => 'Unknown client error');
          console.warn(
            `[Omega_KG] Server health check failed (client error ${response.status}):`,
            errorText
          );
          return;
        } else if (response.status >= 500) {
          const errorText = await response.text().catch(() => 'Unknown server error');
          console.error(
            `[Omega_KG] Server health check failed (server error ${response.status}):`,
            errorText
          );
          return;
        } else {
          // Handle 1xx (informational) and 3xx (redirect) responses
          // These are unexpected for a health check endpoint
          console.warn(
            `[Omega_KG] Server health check returned unexpected status ${response.status} (informational/redirect)`
          );
          return;
        }
      }

      // Parse JSON only if response is OK (2xx status)
      const data = await response.json();
      console.log(
        "[Omega_KG] Server status:",
        data.status,
      );
    } catch (error) {
      // Check for timeout/abort errors FIRST (before any response access)
      // These occur when fetch() throws before a response is received
      if (error.name === 'AbortError' || error.name === 'TimeoutError') {
        console.warn("[Omega_KG] Server health check timed out");
        return;
      }

      // Check for network errors (no response received)
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        console.warn("[Omega_KG] Server offline - network error:", error.message);
        return;
      }

      // Other errors
      console.warn("[Omega_KG] Server health check error:", error.message);
    }
  }
});
