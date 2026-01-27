// PASTE IN CHATGPT - Find actual messages

console.clear();
console.log('🔍 FINDING CHATGPT MESSAGES (NEW DOM)...\n - find-chatgpt-turns.js:4');

// The thread container
const thread = document.querySelector('#thread');
if (!thread) {
  console.error('❌ No #thread element - find-chatgpt-turns.js:9');
} else {
  console.log('✅ Found #thread container\n - find-chatgpt-turns.js:11');

  // Look for common message patterns in new ChatGPT
  console.log('Testing selectors:\n - find-chatgpt-turns.js:14');

  const tests = {
    'Turn containers': '[data-testid^="conversation-turn"]',
    'Message blocks': '[class*="group/conversation-turn"]',
    'Agent turns': '[data-message-author-role]',
    'Any data-testid': '[data-testid]',
  };

  for (const [name, selector] of Object.entries(tests)) {
    const elements = thread.querySelectorAll(selector);
    console.log(`${name} (${selector}): - find-chatgpt-turns.js:25`);
    console.log(`Found: ${elements.length} - find-chatgpt-turns.js:26`);
    if (elements.length > 0) {
      const first = elements[0];
      console.log(`First element classes: - find-chatgpt-turns.js:29`, first.className);
      console.log(`First element data*: - find-chatgpt-turns.js:30`, Array.from(first.attributes).filter(a => a.name.startsWith('data-')).map(a => `${a.name}="${a.value}"`).join(', '));
      console.log(`Text preview: - find-chatgpt-turns.js:31`, first.textContent.substring(0, 100));
    }
    console.log('');
  }

  // Deep search - find all elements with data-testid
  console.log('All datatestid attributes found:\n - find-chatgpt-turns.js:37');
  const allTestIds = Array.from(thread.querySelectorAll('[data-testid]'))
    .map(el => el.getAttribute('data-testid'))
    .filter((v, i, a) => a.indexOf(v) === i); // unique
  allTestIds.forEach(id => console.log(`${id} - find-chatgpt-turns.js:41`));

  // Look for text that looks like your messages
  console.log('\n\nSearching for your actual message text... - find-chatgpt-turns.js:44');
  console.log('(Type some text from your first message below): - find-chatgpt-turns.js:45');
  console.log('\nwindow.findText = (searchText) => { - find-chatgpt-turns.js:46');
  console.log('const all = Array.from(document.querySelectorAll("*")); - find-chatgpt-turns.js:47');
  console.log('const matches = all.filter(el => el.textContent.includes(searchText) && el.children.length < 5); - find-chatgpt-turns.js:48');
  console.log('matches.forEach(el => { - find-chatgpt-turns.js:49');
  console.log('console.log("Match:", el.tagName, el.className); - find-chatgpt-turns.js:50');
  console.log('console.log("HTML:", el.outerHTML.substring(0, 300)); - find-chatgpt-turns.js:51');
  console.log('}); - find-chatgpt-turns.js:52');
  console.log('}; - find-chatgpt-turns.js:53');
  console.log('\n// Example: findText("your message text here") - find-chatgpt-turns.js:54');
}
