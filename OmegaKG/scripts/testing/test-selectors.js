// Omega_KG Selector Test - Paste this in browser DevTools Console
// Tests if DOM selectors still work on current page

(function() {
    console.clear();
    console.log('%c🔍 OMEGA_KG SELECTOR DIAGNOSTIC', 'font-size: 20px; font-weight: bold; color: #00ff00;');
    console.log('%c════════════════════════════════════════════════════', 'color: #00ff00;');

    // Detect platform
    const hostname = window.location.hostname;
    const pathname = window.location.pathname;

    let platform = 'unknown';
    if (hostname.includes('claude.ai')) platform = 'claude';
    if (hostname.includes('openai.com')) platform = 'chatgpt';
    if (hostname.includes('gemini.google.com')) platform = 'gemini';
    if (hostname.includes('perplexity.ai')) platform = 'perplexity';
    if (hostname.includes('github.com') && pathname.includes('/copilot/')) platform = 'github_copilot';
    if (hostname.includes('chat.qwen.ai')) platform = 'qwen';
    if (hostname.includes('copilot.microsoft.com') || hostname.includes('copilot.com')) platform = 'microsoft_copilot';

    console.log(`%c📍 Platform: ${platform}`, 'font-size: 16px; color: cyan;');
    console.log(`%c🌐 URL: ${window.location.href}`, 'color: gray;');

    // Selectors from content.js
    const selectors = {
        claude: {
            container: '[data-testid="conversation"]',
            userMsg: '[data-is-streaming="false"] .font-claude-message:has(> div[data-is-streaming="false"])',
            assistantMsg: '[data-testid="message-content"]'
        },
        chatgpt: {
            container: '[role="presentation"]',
            userMsg: '[data-message-author-role="user"]',
            assistantMsg: '[data-message-author-role="assistant"]'
        },
        gemini: {
            container: '[role="main"]',
            userMsg: '[data-blocks-role="chat-history"] [data-blocks-role="message"][data-message-role="user"]',
            assistantMsg: '[data-blocks-role="chat-history"] [data-blocks-role="message"][data-message-role="model"]'
        },
        perplexity: {
            container: '[class*="thread"]',
            userMsg: '[class*="question"]',
            assistantMsg: '[class*="answer"]'
        },
        github_copilot: {
            container: '[class*="TaskChat-module"]',
            userMsg: '.UserInitialMessage-module__container--j2mCV',
            assistantMsg: '.markdown-body.MarkdownRenderer-module__container--dNKcF:not(.UserInitialMessage-module__markdown--adqIo)'
        },
        qwen: {
            container: '[class*="content"]',
            userMsg: '[class*="user"]',
            assistantMsg: '[class*="bot"]'
        },
        microsoft_copilot: {
            container: '[class*="conversation"]',
            userMsg: '[class*="user-message"]',
            assistantMsg: '[class*="assistant-message"]'
        }
    };

    if (platform === 'unknown') {
        console.log('%c❌ Platform not recognized! This site is not supported.', 'color: red; font-size: 14px;');
        return;
    }

    const config = selectors[platform];
    console.log('\n%c🎯 Testing Selectors...', 'font-size: 14px; color: yellow;');

    // Test container
    const container = document.querySelector(config.container);
    if (container) {
        console.log(`%c✅ Container: "${config.container}"`, 'color: green;');
        console.log('   Found:', container);
    } else {
        console.log(`%c❌ Container NOT found: "${config.container}"`, 'color: red; font-weight: bold;');
        console.log(`%c   🔎 Searching for similar elements...`, 'color: orange;');

        // Try to find alternatives
        const mains = document.querySelectorAll('main, [role="main"], [class*="main"]');
        console.log(`   Found ${mains.length} potential main containers:`, mains);
    }

    // Test user messages
    if (container) {
        const userMsgs = container.querySelectorAll(config.userMsg);
        if (userMsgs.length > 0) {
            console.log(`%c✅ User Messages: "${config.userMsg}"`, 'color: green;');
            console.log(`   Found ${userMsgs.length} user messages`);
            console.log('   Sample:', userMsgs[0]);
            console.log('   Text preview:', userMsgs[0].textContent.substring(0, 100));
        } else {
            console.log(`%c❌ User Messages NOT found: "${config.userMsg}"`, 'color: red; font-weight: bold;');

            // Try alternatives
            const alternatives = container.querySelectorAll('[class*="user"], [data-role="user"], [role="user"]');
            console.log(`   🔎 Found ${alternatives.length} potential user message elements:`, alternatives);
        }

        // Test assistant messages
        const assistantMsgs = container.querySelectorAll(config.assistantMsg);
        if (assistantMsgs.length > 0) {
            console.log(`%c✅ Assistant Messages: "${config.assistantMsg}"`, 'color: green;');
            console.log(`   Found ${assistantMsgs.length} assistant messages`);
            console.log('   Sample:', assistantMsgs[0]);
            console.log('   Text preview:', assistantMsgs[0].textContent.substring(0, 100));
        } else {
            console.log(`%c❌ Assistant Messages NOT found: "${config.assistantMsg}"`, 'color: red; font-weight: bold;');

            // Try alternatives
            const alternatives = container.querySelectorAll('[class*="assistant"], [class*="bot"], [class*="model"], [data-role="assistant"]');
            console.log(`   🔎 Found ${alternatives.length} potential assistant message elements:`, alternatives);
        }
    }

    // Summary
    console.log('\n%c════════════════════════════════════════════════════', 'color: #00ff00;');
    console.log('%c📊 DIAGNOSTIC SUMMARY', 'font-size: 16px; font-weight: bold; color: cyan;');

    if (container && container.querySelectorAll(config.userMsg).length > 0) {
        console.log('%c✅ SELECTORS WORKING - Extension should capture successfully', 'color: green; font-size: 14px; font-weight: bold;');
    } else {
        console.log('%c❌ SELECTORS BROKEN - DOM structure has changed!', 'color: red; font-size: 14px; font-weight: bold;');
        console.log('%c   Platform updated their HTML structure. Selectors need updating.', 'color: orange;');
        console.log('%c   Action needed: Update selectors in content.js', 'color: yellow;');
    }

    console.log('%c════════════════════════════════════════════════════', 'color: #00ff00;');

    // Return diagnostic object for further inspection
    return {
        platform,
        container: container || null,
        userMessages: container ? container.querySelectorAll(config.userMsg) : [],
        assistantMessages: container ? container.querySelectorAll(config.assistantMsg) : [],
        selectors: config
    };
})();
