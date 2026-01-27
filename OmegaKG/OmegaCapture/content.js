/**
 * Omega_KG Extension v2.3.4 - Zombie Script Handler
 * Change Log:
 * - Added error handling for 'Extension context invalidated'.
 * - Shows "Please Refresh Page" notification if extension was reloaded.
 * - Preserves v2.3.3 selector robustness.
 */

// --- 1. Rule Evaluation Strategies ---
const RuleStrategies = {
  class: (el, val) => el.classList.contains(val),
  closest: (el, val) => !!el.closest(val),
  attr: (el, val) => {
    const [key, value] = val.split('=');
    return el.getAttribute(key) === value;
  },
  tag: (el, val) => el.tagName.toLowerCase() === val.toLowerCase(),
  text: (el, val) => (el.textContent || '').toLowerCase().includes(val.toLowerCase())
};

// --- 2. UI & Interaction Manager ---
class OmegaUI {
  constructor(controller) {
    this.controller = controller;
    this.selectionMode = null;
    this.pickedElements = [];
    this.injectStyles();
  }

  injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
      @keyframes slideIn { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
      #omega-kg-capture-btn { position: fixed; bottom: 20px; right: 20px; width: 50px; height: 50px; border-radius: 50%; color: white; font-size: 24px; font-weight: bold; cursor: pointer; z-index: 999998; transition: transform 0.2s, box-shadow 0.3s, border 0.3s; border-style: solid; }
      #omega-kg-capture-btn.omega-initial { background: linear-gradient(135deg, #0CB577 0%, #0A9560 100%); border: 3px solid #FF7033; box-shadow: 0 4px 12px rgba(12, 181, 119, 0.4); animation: breathe 3s ease-in-out infinite; }
      #omega-kg-capture-btn.omega-persisted { background: linear-gradient(135deg, #2B956F 0%, #1F6E52 100%); border: 4px solid #FF5900; box-shadow: 0 0 20px rgba(255, 89, 0, 0.6); animation: persist-glow 2s ease-in-out infinite; }
      #omega-kg-capture-btn.omega-captured { background: linear-gradient(135deg, #0CB577 0%, #0A9560 100%); border: 3px solid #41FDFE; box-shadow: 0 0 15px rgba(65, 253, 254, 0.5); animation: breathe 3s ease-in-out infinite; }
      #omega-kg-capture-btn.omega-experimental { background: linear-gradient(135deg, #2B956F 0%, #1F6E52 100%); border: 3px solid #FF0AE6; box-shadow: 0 0 20px rgba(255, 10, 230, 0.5); animation: experimental-pulse 2.5s ease-in-out infinite; }
      #omega-kg-capture-btn.omega-capturing { animation: capture-pulse 0.8s ease-out !important; }
      #omega-kg-capture-btn.omega-disconnected { background: #666; border-color: #999; animation: none; opacity: 0.7; cursor: not-allowed; }
      #omega-kg-capture-btn:hover { transform: scale(1.1); }
      @keyframes breathe { 0%, 100% { opacity: 1; box-shadow: 0 4px 12px rgba(12, 181, 119, 0.4); } 50% { opacity: 0.85; box-shadow: 0 4px 16px rgba(12, 181, 119, 0.6); } }
      @keyframes persist-glow { 0%, 100% { box-shadow: 0 0 15px rgba(255, 89, 0, 0.4); border-color: #FF5900; } 50% { box-shadow: 0 0 30px rgba(255, 89, 0, 0.8); border-color: #FF7033; } }
      @keyframes experimental-pulse { 0%, 100% { box-shadow: 0 0 15px rgba(255, 10, 230, 0.4); } 50% { box-shadow: 0 0 25px rgba(255, 10, 230, 0.7); } }
      @keyframes capture-pulse { 0% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.2); opacity: 0.7; } 100% { transform: scale(1); opacity: 1; } }
    `;
    document.head.appendChild(style);
  }

  addButton(tier) {
    const button = document.createElement("button");
    button.id = "omega-kg-capture-btn";
    button.innerHTML = "Ω";
    button.className = tier === 2 ? "omega-experimental" : "omega-initial";
    button.title = "Capture conversation (Right-click for options)";
    
    button.addEventListener("click", (e) => {
      e.preventDefault();
      if (button.classList.contains('omega-disconnected')) {
        this.showNotification("Extension updated. Please refresh page.", "error");
        return;
      }
      if (tier <= 2) {
        this.controller.captureConversation(true);
      } else {
        this.showWebclipMenu();
      }
    });
    
    button.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      this.showContextMenu(e);
    });
    
    document.body.appendChild(button);
  }

  updateButtonState(state, title = "") {
    const button = document.getElementById("omega-kg-capture-btn");
    if (!button) return;
    
    // Safety check for zombie state
    if (state === 'disconnected') {
      button.className = 'omega-disconnected';
      button.title = "Extension context invalidated. Refresh page.";
      return;
    }

    button.classList.remove('omega-initial', 'omega-persisted', 'omega-captured', 'omega-experimental', 'omega-disconnected');
    button.classList.add(`omega-${state}`);
    if (title) button.title = title;
  }

  triggerAnimation() {
    const button = document.getElementById("omega-kg-capture-btn");
    if (!button) return;
    button.classList.add('omega-capturing');
    setTimeout(() => button.classList.remove('omega-capturing'), 800);
  }

  showNotification(message, type = "info") {
    const existing = document.getElementById("omega-kg-notification");
    if (existing) existing.remove();
    
    const notification = document.createElement("div");
    notification.id = "omega-kg-notification";
    const colors = { success: "#019387", error: "#FF7C87", info: "#3799ad", warning: "#FFB02E" };
    
    notification.style.cssText = `
      position: fixed; top: 20px; right: 20px; padding: 12px 20px;
      border-radius: 8px; background: ${colors[type] || colors.info}; color: white;
      font-family: system-ui, -apple-system, sans-serif; font-size: 14px;
      font-weight: 500; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      z-index: 999999; animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = `Ω_KG: ${message}`;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 4000);
  }

  showContextMenu(event) {
    const existing = document.getElementById("omega-context-menu");
    if (existing) existing.remove();
    
    const menu = document.createElement("div");
    menu.id = "omega-context-menu";
    const tier = this.controller.platformInfo?.tier || 3;
    
    let html = '';
    if (tier <= 2) html += '<div class="omega-menu-item" data-action="capture">📝 Capture Conversation</div>';
    html += `
      <div class="omega-menu-item" data-action="select-regions">🎯 Select Content Regions</div>
      <div class="omega-menu-item" data-action="pick-elements">👆 Pick Elements</div>
      <div class="omega-menu-item" data-action="full-page">📄 Capture Full Page</div>
    `;
    if (tier >= 2) html += '<div class="omega-menu-separator" style="height:1px;background:#ffffff33;margin:8px 0"></div><div class="omega-menu-item" data-action="debug">🔍 Debug Selectors</div>';
    
    menu.innerHTML = html;
    
    const btn = document.getElementById("omega-kg-capture-btn");
    const accent = btn ? window.getComputedStyle(btn).borderColor : '#FF7033';
    
    menu.style.cssText = `
      position: fixed; bottom: 80px; right: 20px; background: #1a1a1a;
      border: 2px solid ${accent}; border-radius: 8px; padding: 8px 0;
      z-index: 999999; box-shadow: 0 8px 24px rgba(0,0,0,0.4); min-width: 220px;
    `;
    
    menu.querySelectorAll('.omega-menu-item').forEach(item => {
      item.style.cssText = 'padding: 10px 16px; color: white; cursor: pointer; font-family: system-ui; font-size: 14px; transition: background 0.2s;';
      item.addEventListener('click', () => {
        this.handleMenuAction(item.dataset.action);
        menu.remove();
      });
      item.addEventListener('mouseenter', () => item.style.background = '#ffffff1a');
      item.addEventListener('mouseleave', () => item.style.background = 'transparent');
    });

    document.body.appendChild(menu);
    setTimeout(() => {
      const close = () => menu.remove();
      document.addEventListener('click', close, { once: true });
      document.addEventListener('contextmenu', close, { once: true });
    }, 100);
  }

  showWebclipMenu() {
    this.showNotification("Choose capture mode: Right-click button for options", "info");
    this.showContextMenu();
  }

  handleMenuAction(action) {
    switch (action) {
      case 'capture': this.controller.captureConversation(true); break;
      case 'select-regions': this.enterDragSelectMode(); break;
      case 'pick-elements': this.enterPickerMode(); break;
      case 'full-page': this.controller.captureFullPage(); break;
      case 'debug': this.controller.debugDOM(); break;
    }
  }

  // --- Interaction Modes ---
  enterDragSelectMode() {
    this.selectionMode = 'drag';
    this.showNotification("Drag to select content regions - ESC to cancel", "info");
    const overlay = document.createElement('div');
    overlay.id = 'omega-selection-overlay';
    overlay.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(43, 149, 111, 0.05); z-index: 999997; cursor: crosshair;';
    
    let box = null, startX, startY;
    const onMouseDown = (e) => {
      if (e.target !== overlay) return;
      startX = e.clientX; startY = e.clientY;
      box = document.createElement('div');
      box.style.cssText = 'position: fixed; border: 3px solid #FF0AE6; background: rgba(255, 10, 230, 0.1); z-index: 999998; pointer-events: none;';
      document.body.appendChild(box);
    };
    const onMouseMove = (e) => {
      if (!box) return;
      const w = Math.abs(e.clientX - startX), h = Math.abs(e.clientY - startY);
      box.style.left = Math.min(e.clientX, startX) + 'px';
      box.style.top = Math.min(e.clientY, startY) + 'px';
      box.style.width = w + 'px'; box.style.height = h + 'px';
    };
    const onMouseUp = () => {
      if (box) {
        const rect = box.getBoundingClientRect();
        this.controller.captureRegion(rect);
        box.remove(); box = null;
      }
    };
    const onEsc = (e) => {
      if (e.key === 'Escape') {
        overlay.remove(); if (box) box.remove();
        this.selectionMode = null;
        this.showNotification("Selection cancelled", "info");
      }
    };
    overlay.addEventListener('mousedown', onMouseDown);
    overlay.addEventListener('mousemove', onMouseMove);
    overlay.addEventListener('mouseup', onMouseUp);
    document.addEventListener('keydown', onEsc, { once: true });
    document.body.appendChild(overlay);
  }

  enterPickerMode() {
    this.selectionMode = 'picker';
    this.pickedElements = [];
    this.showNotification("Click elements to pick - Right-click when done", "info");
    const highlight = document.createElement('div');
    highlight.style.cssText = 'position: absolute; border: 3px solid #41FDFE; background: rgba(65, 253, 254, 0.1); pointer-events: none; z-index: 999998; transition: all 0.1s ease;';
    document.body.appendChild(highlight);
    const onHover = (e) => {
      const t = e.target;
      if (t.id === 'omega-kg-capture-btn' || t.closest('#omega-context-menu')) return;
      const r = t.getBoundingClientRect();
      highlight.style.left = (r.left + window.scrollX) + 'px';
      highlight.style.top = (r.top + window.scrollY) + 'px';
      highlight.style.width = r.width + 'px';
      highlight.style.height = r.height + 'px';
    };
    const onClick = (e) => {
      e.preventDefault(); e.stopPropagation();
      const t = e.target;
      if (t.id === 'omega-kg-capture-btn') return;
      this.pickedElements.push({ element: t, text: t.textContent.trim(), html: t.outerHTML.substring(0, 500) });
      t.style.outline = '2px solid #FF0AE6';
      this.showNotification(`Picked ${this.pickedElements.length} element(s)`, 'info');
    };
    const onFinish = async (e) => {
      if (e.type === 'contextmenu' || e.key === 'Escape') {
        e.preventDefault();
        document.removeEventListener('mousemove', onHover);
        document.removeEventListener('click', onClick, true);
        highlight.remove();
        if (this.pickedElements.length > 0) {
          await this.controller.capturePickedElements(this.pickedElements);
        } else {
          this.showNotification("No elements picked", "info");
        }
        this.pickedElements.forEach(i => i.element.style.outline = '');
        this.pickedElements = [];
        this.selectionMode = null;
      }
    };
    document.addEventListener('mousemove', onHover);
    document.addEventListener('click', onClick, true);
    document.addEventListener('contextmenu', onFinish, { once: true });
    document.addEventListener('keydown', onFinish, { once: true });
  }
}

// --- 3. Main Controller ---
class ChatCapture {
  constructor() {
    this.platformInfo = null;
    this.platformConfig = null;
    this.observer = null;
    this.currentState = null;
    this.captureInProgress = false;
    this.captureTimeout = null;
    this.NOTIFICATION_INTERVAL = 20;
    this.STORAGE_PREFIX = 'omega_kg:conversation:';
    this.LEARNED_PREFIX = 'omega_kg:learned:';
    this.ui = new OmegaUI(this);
    this.saveStateDebounced = this.debounce(this.saveState.bind(this), 1000);
  }

  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => { clearTimeout(timeout); func(...args); };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  getRelativeTime(isoTimestamp) {
    if (!isoTimestamp) return 'Never';
    const now = new Date(), then = new Date(isoTimestamp);
    const diffMins = Math.floor((now - then) / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 2) return 'Yesterday';
    return then.toLocaleDateString();
  }

  async loadConfig() {
    try {
      const url = chrome.runtime.getURL('platforms.json');
      const response = await fetch(url);
      this.platformConfig = await response.json();
      console.log('[Omega_KG] Loaded platform configurations');
    } catch (error) {
      // Check for context invalidation
      if (error.message.includes('Extension context invalidated')) {
        this.handleInvalidatedContext();
        return;
      }
      console.error('[Omega_KG] Failed to load platforms.json:', error);
      this.platformConfig = {};
    }
  }

  async detectPlatform() {
    if (!this.platformConfig) await this.loadConfig();
    const hostname = window.location.hostname;
    const url = window.location.href;

    for (const [key, config] of Object.entries(this.platformConfig)) {
      const hostMatch = config.hostnames.some(h => hostname.includes(h));
      const urlMatch = config.urlContains ? url.includes(config.urlContains) : true;
      if (hostMatch && urlMatch) return { tier: 1, platform: key, name: key };
    }

    const learned = await this.checkLearnedSelectors(hostname, url);
    if (learned) return { tier: 1.5, platform: 'learned', name: hostname, selectors: learned.selectors };

    const confidence = this.detectChatPattern();
    if (confidence >= 0.6) return { tier: 2, platform: 'experimental', name: hostname, confidence };

    return { tier: 3, platform: 'webclip', name: hostname };
  }

  detectChatPattern() {
    const signals = {
      hasMessageContainers: document.querySelectorAll('[class*="message" i], [role="article"]').length > 2,
      hasInputField: !!document.querySelector('textarea[placeholder*="message" i], input[placeholder*="chat" i]'),
      hasAlternatingBlocks: !!this.detectAlternatingPattern(),
      hasTimestamps: document.querySelectorAll('time, [class*="time" i]').length > 2,
    };
    return Object.values(signals).reduce((acc, val) => acc + (val ? 0.25 : 0), 0);
  }

  detectAlternatingPattern() {
    const containers = document.querySelectorAll('div[class*="chat" i], div[class*="conversation" i], main, [role="main"]');
    for (const container of containers) {
      const children = Array.from(container.children).filter(el => el.textContent.trim().length > 20);
      if (children.length < 4) continue;
      const patterns = children.map(el => Array.from(el.classList).sort().join('|'));
      const unique = new Set(patterns);
      if (unique.size >= 2 && unique.size <= 4) return container;
    }
    return null;
  }

  extractMessages() {
    let config = null;
    if (this.platformInfo.tier === 1.5) config = this.platformInfo.selectors;
    else if (this.platformInfo.tier === 1) config = this.platformConfig[this.platformInfo.platform];

    let elements = [];
    if (config && config.messages) {
      // Try selectors individually with error handling for each
      for (const selector of config.messages) {
        try {
          const matches = Array.from(document.querySelectorAll(selector));
          elements.push(...matches);
        } catch (e) {
          console.warn(`[Omega_KG] Invalid selector "${selector}":`, e.message);
        }
      }
      // Remove duplicates while preserving order
      elements = Array.from(new Set(elements));
    }

    if (elements.length === 0) {
      if (config) console.warn('[Omega_KG] Specific selectors failed, trying generic');
      return this.extractGeneric();
    }

    return elements.map((el, index) => {
      try {
        if (!el.textContent) return null;
        const isUser = config.isUser.some(rule => {
          const [type, val] = rule.includes(':') ? rule.split(/:(.*)/) : [null, null];
          return type && RuleStrategies[type] ? RuleStrategies[type](el, val) : false;
        });
        let content = el.textContent;
        for (const rule of config.getText) {
          if (rule === 'textContent') break;
          if (rule.startsWith('selector:')) {
            const target = el.querySelector(rule.substring(9));
            if (target && target.textContent) { content = target.textContent; break; }
          }
        }
        return {
          role: isUser ? "user" : "assistant",
          content: this.cleanText(content),
          timestamp: new Date().toISOString(),
          index
        };
      } catch (e) { return null; }
    }).filter(m => m && m.content.length > 0);
  }

  extractGeneric() {
    const container = this.detectAlternatingPattern() || document.querySelector('main');
    if (!container) return [];
    const children = Array.from(container.children).filter(el => el.textContent.trim().length > 20);
    return children.map((el, index) => ({
      role: index % 2 === 0 ? "user" : "assistant",
      content: this.cleanText(el.textContent),
      timestamp: new Date().toISOString(),
      index
    }));
  }

  cleanText(text) {
    return text.replace(/\s+/g, " ").replace(/Copy code/g, "").replace(/\d+\/\d+/g, "").trim();
  }

  async captureConversation(manualTrigger = false) {
    if (this.captureInProgress) return false;
    this.captureInProgress = true;

    try {
      const messages = this.extractMessages();
      if (!this.validateCapture(messages, manualTrigger)) return false;

      const payload = this.preparePayload(messages);
      const response = await chrome.runtime.sendMessage({
        type: "CAPTURE_CONVERSATION",
        data: payload
      });

      if (response?.success) {
        await this.handleCaptureSuccess(messages, manualTrigger);
        return true;
      } else {
        throw new Error(response?.error || "Unknown server error");
      }
    } catch (error) {
      // HANDLE ZOMBIE SCRIPT
      if (error.message.includes('Extension context invalidated')) {
        this.handleInvalidatedContext();
        return false;
      }
      
      console.error("[Omega_KG] Capture Error:", error);
      if (manualTrigger) this.ui.showNotification("Capture failed: " + error.message, "error");
      return false;
    } finally {
      this.captureInProgress = false;
    }
  }

  handleInvalidatedContext() {
    console.error("[Omega_KG] EXTENSION CONTEXT INVALIDATED. Script is orphaned.");
    this.ui.showNotification("Extension updated. Please refresh the page.", "error");
    this.ui.updateButtonState('disconnected');
    if (this.observer) this.observer.disconnect(); // Stop trying to capture
  }

  validateCapture(messages, manualTrigger) {
    if (messages.length === 0) {
      if (manualTrigger) this.ui.showNotification("No messages found", "info");
      return false;
    }
    const delta = messages.length - (this.currentState?.message_count_at_last_capture || 0);
    if (delta < -5 && this.currentState?.message_count_at_last_capture > 0) {
      console.warn('[Omega_KG] Significant message count drop detected.');
      this.ui.showNotification("Message count anomaly detected", "info");
    }
    if (delta === 0 && !manualTrigger) return false;
    return true;
  }

  preparePayload(messages) {
    let platformName = this.platformInfo.name;
    if (platformName === 'webclip' && messages.length > 0) {
      platformName = `${window.location.hostname} (Generic)`;
    }
    return {
      platform: platformName,
      tier: this.platformInfo.tier,
      url: window.location.href,
      title: document.title,
      messages: messages.map(m => ({ role: m.role, content: m.content, timestamp: m.timestamp })),
      captured_at: new Date().toISOString()
    };
  }

  async handleCaptureSuccess(messages, manualTrigger) {
    const now = new Date().toISOString();
    const isFirst = !this.currentState.first_captured_at;
    this.currentState.last_captured_at = now;
    if (isFirst) this.currentState.first_captured_at = now;
    this.currentState.message_count_at_last_capture = messages.length;
    await this.saveStateDebounced();
    this.ui.triggerAnimation();
    const sinceLastNotify = messages.length - (this.currentState.message_count_at_last_notification || 0);
    if (isFirst || manualTrigger || sinceLastNotify >= this.NOTIFICATION_INTERVAL) {
      const msg = isFirst ? "Conversation captured!" : manualTrigger ? "Conversation updated!" : `Auto-saved (+${sinceLastNotify} messages)`;
      this.ui.showNotification(msg, "success");
      this.currentState.message_count_at_last_notification = messages.length;
      await this.saveState();
    }
    if (isFirst && this.platformInfo.tier <= 2) {
      this.ui.updateButtonState('persisted', `Saved: ${this.getRelativeTime(now)}`);
    }
  }

  startObserving() {
    if (this.platformInfo.tier >= 3) return;
    const target = document.body; 
    this.observer = new MutationObserver(() => {
      clearTimeout(this.captureTimeout);
      this.captureTimeout = setTimeout(() => {
        if (this.platformInfo.tier <= 2) this.captureConversation(false);
      }, 2000);
    });
    this.observer.observe(target, { childList: true, subtree: true });
    console.log('[Omega_KG] DOM observation started');
  }

  async captureRegion(rect) {
    const elements = document.elementsFromPoint(rect.left + rect.width/2, rect.top + rect.height/2);
    const content = elements
      .filter(el => el.textContent.trim().length > 20 && el.id !== 'omega-selection-overlay')
      .map(el => ({ tag: el.tagName, text: el.textContent.trim().substring(0, 1000) }));
    if (content.length === 0) return this.ui.showNotification("No content found", "info");
    await this.sendWebclip({ type: 'region', content, rect });
  }

  async capturePickedElements(items) {
    await this.sendWebclip({ type: 'picked_elements', content: items.map(i => ({ text: i.text, html: i.html })), count: items.length });
  }

  async captureFullPage() {
    this.ui.showNotification("Capturing full page...", "info");
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, 
      { acceptNode: n => n.textContent.trim().length > 20 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT });
    const nodes = [];
    let node;
    while(node = walker.nextNode()) nodes.push(node.textContent.trim());
    await this.sendWebclip({ type: 'full_page', content: nodes.join('\n\n'), word_count: nodes.length });
  }

  async sendWebclip(data) {
    const payload = {
      platform: 'webclip', tier: 3,
      url: window.location.href, title: document.title,
      webclip: data, captured_at: new Date().toISOString()
    };
    try {
      const res = await chrome.runtime.sendMessage({ type: "CAPTURE_CONVERSATION", data: payload });
      if (res?.success) {
        this.ui.showNotification("Webclip captured!", "success");
        this.ui.updateButtonState('captured');
        setTimeout(() => this.ui.updateButtonState('initial'), 2000);
      } else {
        throw new Error(res?.error);
      }
    } catch (e) {
      if (e.message.includes('Extension context invalidated')) {
        this.handleInvalidatedContext();
        return;
      }
      this.ui.showNotification("Webclip failed", "error");
    }
  }

  async checkLearnedSelectors(hostname, url) {
    try {
      const pathPattern = this.extractPathPattern(url);
      const keys = [`${this.LEARNED_PREFIX}${hostname}:domain`, `${this.LEARNED_PREFIX}${hostname}${pathPattern}`];
      const stored = await chrome.storage.local.get(keys);
      return stored[keys[0]] || stored[keys[1]] || null;
    } catch { return null; }
  }

  extractPathPattern(url) {
    const parts = new URL(url).pathname.split('/').filter(Boolean);
    return parts.length > 0 ? `/${parts[0]}` : '';
  }

  async initializeState() {
    const key = this.STORAGE_PREFIX + window.location.href;
    try {
      const stored = await chrome.storage.local.get(key);
      if (stored[key]) {
        this.currentState = { ...stored[key], session_state: 'continuing' };
        this.ui.updateButtonState('persisted', `Last saved: ${this.getRelativeTime(this.currentState.last_captured_at)}`);
      } else {
        this.currentState = { url: window.location.href, session_state: 'new', message_count_at_last_capture: 0 };
        this.ui.updateButtonState(this.platformInfo.tier === 2 ? 'experimental' : 'initial');
      }
    } catch (e) {
      this.currentState = { url: window.location.href, session_state: 'new' };
    }
  }

  async saveState() {
    if (!this.currentState) return;
    const key = this.STORAGE_PREFIX + this.currentState.url;
    await chrome.storage.local.set({ [key]: this.currentState });
  }

  debugDOM() {
    console.log("=== Debug ===", {
      platform: this.platformInfo,
      state: this.currentState,
      config: this.platformConfig
    });
    this.ui.showNotification("Debug info logged to console", "info");
  }
}

// --- Initialization ---
(async () => {
  const capture = new ChatCapture();
  window.captureInstance = capture;
  capture.platformInfo = await capture.detectPlatform();
  console.log(`[Omega_KG] Initialized: ${capture.platformInfo.name} (Tier ${capture.platformInfo.tier})`);
  await capture.initializeState();
  capture.ui.addButton(capture.platformInfo.tier);
  if (capture.platformInfo.tier <= 2) {
    capture.startObserving();
  }
})();

// --- Listeners ---
window.addEventListener("load", () => setTimeout(() => {
  if (window.captureInstance?.platformInfo?.tier <= 2) window.captureInstance.captureConversation(false);
}, 3000));

document.addEventListener("visibilitychange", () => {
  if (document.hidden && window.captureInstance?.platformInfo?.tier <= 2) window.captureInstance.captureConversation(false);
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'TRIGGER_CAPTURE') {
    (async () => {
      const cap = window.captureInstance;
      if (cap) {
        const success = await cap.captureConversation(true);
        sendResponse({ success });
      } else {
        sendResponse({ success: false, error: "Not initialized" });
      }
    })();
    return true;
  }
});