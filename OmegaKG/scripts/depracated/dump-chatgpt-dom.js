// PASTE IN CHATGPT CONSOLE - Shows actual DOM structure

console.clear();
console.log('🔍 DUMPING CHATGPT DOM STRUCTURE...\n - dump-chatgpt-dom.js:4');

// Find the main chat container
const main = document.querySelector('main');
if (!main) {
  console.error('❌ NO MAIN ELEMENT FOUND - dump-chatgpt-dom.js:9');
} else {
  console.log('✅ Found main element - dump-chatgpt-dom.js:11');

  // Get all direct children
  const children = Array.from(main.children);
  console.log(`\n📦 Main has ${children.length} direct children:\n - dump-chatgpt-dom.js:15`);

  children.forEach((child, i) => {
    console.log(`Child ${i}: - dump-chatgpt-dom.js:18`);
    console.log('Tag: - dump-chatgpt-dom.js:19', child.tagName);
    console.log('Classes: - dump-chatgpt-dom.js:20', child.className);
    console.log('ID: - dump-chatgpt-dom.js:21', child.id);
    console.log('Data attrs: - dump-chatgpt-dom.js:22', Array.from(child.attributes).filter(a => a.name.startsWith('data-')).map(a => `${a.name}="${a.value}"`).join(', '));
    console.log('Has text content: - dump-chatgpt-dom.js:23', child.textContent.length > 0);
    if (child.textContent.length > 0 && child.textContent.length < 200) {
      console.log('Sample text: - dump-chatgpt-dom.js:25', child.textContent.substring(0, 100));
    }
    console.log('');
  });

  // Look for anything with text content that might be messages
  console.log('\n🔍 Searching for elements with substantial text...\n - dump-chatgpt-dom.js:31');
  const allDivs = main.querySelectorAll('div');
  const textElements = Array.from(allDivs).filter(el => {
    const text = el.textContent.trim();
    return text.length > 20 && text.length < 5000 && el.children.length < 10;
  }).slice(0, 5); // First 5

  console.log(`Found ${textElements.length} potential message elements:\n - dump-chatgpt-dom.js:38`);
  textElements.forEach((el, i) => {
    console.log(`Element ${i}: - dump-chatgpt-dom.js:40`);
    console.log('Classes: - dump-chatgpt-dom.js:41', el.className);
    console.log('Data attrs: - dump-chatgpt-dom.js:42', Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => `${a.name}="${a.value}"`).join(', '));
    console.log('Text preview: - dump-chatgpt-dom.js:43', el.textContent.substring(0, 100));
    console.log('HTML: - dump-chatgpt-dom.js:44', el.outerHTML.substring(0, 300));
    console.log('');
  });
}

// Also check if extension is even loaded
console.log('\n🔌 Extension check: - dump-chatgpt-dom.js:50');
console.log('Omega button exists: - dump-chatgpt-dom.js:51', !!document.querySelector('div[style*="Omega"]') || !!document.querySelector('div:contains("Ω")'));
console.log('Extension console messages: - dump-chatgpt-dom.js:52', 'Check above for [Omega_KG] logs');
