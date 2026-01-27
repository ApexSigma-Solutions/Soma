// PASTE THIS IN GEMINI CONSOLE - Finds the actual message selectors

console.clear();
console.log('🔍 FINDING GEMINI MESSAGE ELEMENTS...\n - test-gemini-selectors.js:4');

// Test all possible message containers
console.log('1️⃣ Testing containers: - test-gemini-selectors.js:7');
const containers = {
  'main': document.querySelector('main'),
  '[role="main"]': document.querySelector('[role="main"]'),
  '[role="presentation"]': document.querySelector('[role="presentation"]'),
  'chat-history attr': document.querySelector('[data-blocks-role="chat-history"]'),
};

for (const [name, el] of Object.entries(containers)) {
  console.log(`${name}: - test-gemini-selectors.js:16`, el ? '✅ FOUND' : '❌ not found');
}

console.log('\n2️⃣ Searching for messages by common patterns: - test-gemini-selectors.js:19');

// Try different message selectors
const tests = [
  { name: 'message-content class', selector: '[class*="message-content"]' },
  { name: 'user-query class', selector: '[class*="user-query"]' },
  { name: 'model-response class', selector: '[class*="model-response"]' },
  { name: 'message role attr', selector: '[data-message-role]' },
  { name: 'user role attr', selector: '[data-message-role="user"]' },
  { name: 'model role attr', selector: '[data-message-role="model"]' },
  { name: 'message-author attr', selector: '[data-message-author-role]' },
  { name: 'chat message class', selector: '[class*="chat"][class*="message"]' },
  { name: 'conversation turn', selector: '[class*="turn"]' },
  { name: 'query class', selector: '[class*="query"]' },
  { name: 'response class', selector: '[class*="response"]' },
];

const found = [];
tests.forEach(test => {
  const elements = document.querySelectorAll(test.selector);
  console.log(`${test.name}: ${elements.length} found - test-gemini-selectors.js:39`);
  if (elements.length > 0) {
    found.push({ ...test, count: elements.length, sample: elements[0] });
  }
});

if (found.length > 0) {
  console.log('\n3️⃣ FOUND POTENTIAL SELECTORS: - test-gemini-selectors.js:46');
  found.forEach(f => {
    console.log(`\n   ✅ ${f.name} (${f.count} messages) - test-gemini-selectors.js:48`);
    console.log(`Selector: "${f.selector}" - test-gemini-selectors.js:49`);
    console.log(`Sample text: - test-gemini-selectors.js:50`, f.sample.textContent.substring(0, 100));
    console.log(`Sample HTML: - test-gemini-selectors.js:51`, f.sample.outerHTML.substring(0, 200));
  });
} else {
  console.log('\n❌ No standard selectors found. Manual inspection needed. - test-gemini-selectors.js:54');
  console.log('\n4️⃣ INSPECT A MESSAGE MANUALLY: - test-gemini-selectors.js:55');
  console.log('1. Rightclick your first message - test-gemini-selectors.js:56');
  console.log('2. Click "Inspect" - test-gemini-selectors.js:57');
  console.log('3. Look for data* attributes or class names - test-gemini-selectors.js:58');
  console.log('4. Share the HTML here - test-gemini-selectors.js:59');
}

console.log('\n5️⃣ Looking for all data* attributes on page: - test-gemini-selectors.js:62');
const allElements = document.querySelectorAll('*[data-message-role], *[data-role], *[data-testid*="message"]');
console.log(`Found ${allElements.length} elements with data attributes - test-gemini-selectors.js:64`);
if (allElements.length > 0) {
  console.log('Sample: - test-gemini-selectors.js:66', allElements[0]);
}// PASTE THIS IN GEMINI'S CONSOLE TO TEST SELECTORS

console.log('🔍 Testing Gemini selectors...\n - test-gemini-selectors.js:69');

// Current selectors in content.js
const selectors = {
  container: '[role="main"]',
  userMsg: '[data-blocks-role="chat-history"] [data-blocks-role="message"][data-message-role="user"]',
  assistantMsg: '[data-blocks-role="chat-history"] [data-blocks-role="message"][data-message-role="model"]'
};

console.log('1️⃣ Testing container: - test-gemini-selectors.js:78', selectors.container);
const container = document.querySelector(selectors.container);
console.log('Found: - test-gemini-selectors.js:80', container ? '✅ YES' : '❌ NO');

console.log('\n2️⃣ Testing user messages: - test-gemini-selectors.js:82', selectors.userMsg);
const userMsgs = document.querySelectorAll(selectors.userMsg);
console.log('Count: - test-gemini-selectors.js:84', userMsgs.length);
if (userMsgs.length > 0) {
  console.log('Sample: - test-gemini-selectors.js:86', userMsgs[0].textContent.substring(0, 100));
}

console.log('\n3️⃣ Testing assistant messages: - test-gemini-selectors.js:89', selectors.assistantMsg);
const assistantMsgs = document.querySelectorAll(selectors.assistantMsg);
console.log('Count: - test-gemini-selectors.js:91', assistantMsgs.length);
if (assistantMsgs.length > 0) {
  console.log('Sample: - test-gemini-selectors.js:93', assistantMsgs[0].textContent.substring(0, 100));
}

console.log('\n4️⃣ Trying alternative selectors... - test-gemini-selectors.js:96');

// Alternative 1: Simpler message selector
const alt1 = document.querySelectorAll('[data-message-role="user"]');
console.log('[datamessagerole="user"]: - test-gemini-selectors.js:100', alt1.length, 'messages');

const alt2 = document.querySelectorAll('[data-message-role="model"]');
console.log('[datamessagerole="model"]: - test-gemini-selectors.js:103', alt2.length, 'messages');

// Alternative 2: Check chat history container
const chatHistory = document.querySelector('[data-blocks-role="chat-history"]');
console.log('Chat history container: - test-gemini-selectors.js:107', chatHistory ? '✅ Found' : '❌ Not found');

if (chatHistory) {
  const allMessages = chatHistory.querySelectorAll('[data-blocks-role="message"]');
  console.log('Total messages in history: - test-gemini-selectors.js:111', allMessages.length);
}

console.log('\n5️⃣ Inspecting DOM structure... - test-gemini-selectors.js:114');
console.log('Rightclick inspect a user message and look for: - test-gemini-selectors.js:115');
console.log('datamessagerole="user" or "model" - test-gemini-selectors.js:116');
console.log('datablocksrole attributes - test-gemini-selectors.js:117');
console.log('Parent container structure - test-gemini-selectors.js:118');
