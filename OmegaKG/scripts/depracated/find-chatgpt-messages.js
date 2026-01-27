// PASTE IN CHATGPT CONSOLE

console.clear();
console.log('🔍 FINDING CHATGPT MESSAGE ELEMENTS...\n - find-chatgpt-messages.js:4');

console.log('1️⃣ Testing containers: - find-chatgpt-messages.js:6');
const containers = {
  'main': document.querySelector('main'),
  '[role="presentation"]': document.querySelector('[role="presentation"]'),
  '[role="main"]': document.querySelector('[role="main"]'),
};

for (const [name, el] of Object.entries(containers)) {
  console.log(`${name}: - find-chatgpt-messages.js:14`, el ? '✅ FOUND' : '❌ not found');
}

console.log('\n2️⃣ Testing current selectors: - find-chatgpt-messages.js:17');
console.log('[datamessageauthorrole="user"]: - find-chatgpt-messages.js:18', document.querySelectorAll('[data-message-author-role="user"]').length);
console.log('[datamessageauthorrole="assistant"]: - find-chatgpt-messages.js:19', document.querySelectorAll('[data-message-author-role="assistant"]').length);

console.log('\n3️⃣ Testing alternative selectors: - find-chatgpt-messages.js:21');
const tests = [
  '[class*="message"]',
  '[class*="user"]',
  '[class*="assistant"]',
  '[data-testid*="message"]',
  '[data-testid*="conversation"]',
  'article',
  '[role="article"]',
];

tests.forEach(sel => {
  const count = document.querySelectorAll(sel).length;
  console.log(`${sel}: ${count} found - find-chatgpt-messages.js:34`);
});

console.log('\n4️⃣ Inspect first message: - find-chatgpt-messages.js:37');
const firstArticle = document.querySelector('article');
if (firstArticle) {
  console.log('Found article element: - find-chatgpt-messages.js:40', firstArticle);
  console.log('HTML: - find-chatgpt-messages.js:41', firstArticle.outerHTML.substring(0, 300));
} else {
  console.log('❌ No article elements found - find-chatgpt-messages.js:43');
}
