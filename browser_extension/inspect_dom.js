// Run this in DevTools Console to find correct message selectors
// Paste this into the console on claude.ai

console.log('=== CLAUDE MESSAGE DOM INSPECTOR ===\n');

// Find all potential message containers
const selectors = [
  '[data-testid="user-message"]',
  '[data-testid="assistant-message"]',
  '[data-testid="message"]',
  '[class*="message"]',
  '[role="article"]',
  'div[data-testid]'
];

selectors.forEach(sel => {
  const elements = document.querySelectorAll(sel);
  if (elements.length > 0) {
    console.log(`\n"${sel}" found ${elements.length} elements:`);

    // Show first 3 elements
    Array.from(elements).slice(0, 3).forEach((el, i) => {
      const text = el.textContent.trim().substring(0, 60);
      const testid = el.getAttribute('data-testid');
      const classes = el.className;

      console.log(`  [${i}] testid="${testid}"`);
      console.log(`      classes="${classes}"`);
      console.log(`      text="${text}..."`);
    });
  }
});

// Check last few messages specifically
console.log('\n\n=== LAST 5 MESSAGES ===');
const allArticles = document.querySelectorAll('[role="article"]');
Array.from(allArticles).slice(-5).forEach((msg, i) => {
  const testid = msg.getAttribute('data-testid') || msg.querySelector('[data-testid]')?.getAttribute('data-testid');
  const text = msg.textContent.trim().substring(0, 80);
  console.log(`\n[${i}] ${testid}`);
  console.log(`    "${text}..."`);
});

console.log('\n\n=== DONE ===');
console.log('Look above to identify which data-testid is for Claude responses');
