// PASTE THIS IN GEMINI CONSOLE - Finds the actual message selectors

console.clear();
console.log('🔍 FINDING GEMINI MESSAGE ELEMENTS...\n - find-gemini-messages.js:4');

// Test all possible message containers
console.log('1️⃣ Testing containers: - find-gemini-messages.js:7');
const containers = {
  'main': document.querySelector('main'),
  '[role="main"]': document.querySelector('[role="main"]'),
  '[role="presentation"]': document.querySelector('[role="presentation"]'),
  'chat-history attr': document.querySelector('[data-blocks-role="chat-history"]'),
};

for (const [name, el] of Object.entries(containers)) {
  console.log(`${name}: - find-gemini-messages.js:16`, el ? '✅ FOUND' : '❌ not found');
}

console.log('\n2️⃣ Searching for messages by common patterns: - find-gemini-messages.js:19');

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
  console.log(`${test.name}: ${elements.length} found - find-gemini-messages.js:39`);
  if (elements.length > 0) {
    found.push({ ...test, count: elements.length, sample: elements[0] });
  }
});

if (found.length > 0) {
  console.log('\n3️⃣ FOUND POTENTIAL SELECTORS: - find-gemini-messages.js:46');
  found.forEach(f => {
    console.log(`\n   ✅ ${f.name} (${f.count} messages) - find-gemini-messages.js:48`);
    console.log(`Selector: "${f.selector}" - find-gemini-messages.js:49`);
    console.log(`Sample text: - find-gemini-messages.js:50`, f.sample.textContent.substring(0, 100));
    console.log(`Sample HTML: - find-gemini-messages.js:51`, f.sample.outerHTML.substring(0, 200));
  });
} else {
  console.log('\n❌ No standard selectors found. Manual inspection needed. - find-gemini-messages.js:54');
  console.log('\n4️⃣ INSPECT A MESSAGE MANUALLY: - find-gemini-messages.js:55');
  console.log('1. Rightclick your first message - find-gemini-messages.js:56');
  console.log('2. Click "Inspect" - find-gemini-messages.js:57');
  console.log('3. Look for data* attributes or class names - find-gemini-messages.js:58');
  console.log('4. Share the HTML here - find-gemini-messages.js:59');
}

console.log('\n5️⃣ Looking for all data* attributes on page: - find-gemini-messages.js:62');
const allElements = document.querySelectorAll('*[data-message-role], *[data-role], *[data-testid*="message"]');
console.log(`Found ${allElements.length} elements with data attributes - find-gemini-messages.js:64`);
if (allElements.length > 0) {
  console.log('Sample: - find-gemini-messages.js:66', allElements[0]);
}
