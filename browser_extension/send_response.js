// Quick script to manually extract and send last response
// Run this in DevTools console on claude.ai

(async function() {
  const BUS_URL = 'http://localhost:5001';

  // Get all messages
  const messages = document.querySelectorAll('[data-testid="user-message"]');

  // Find last Claude response
  let lastResponse = null;

  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    const paragraphs = msg.querySelectorAll('p');

    if (paragraphs.length > 0) {
      const text = Array.from(paragraphs)
        .map(p => p.textContent.trim())
        .filter(t => t && t !== 'undefined')
        .join('\n');

      if (text.length > 0 && !text.includes('Retry') && !text.includes('Edit')) {
        lastResponse = text;
        break;
      }
    }
  }

  if (lastResponse) {
    console.log('Found response:', lastResponse.substring(0, 100));

    const result = await fetch(`${BUS_URL}/api/send`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        from: 'browser',
        to: 'all',
        type: 'claude_response',
        payload: {
          response: lastResponse,
          timestamp: new Date().toISOString()
        }
      })
    });

    console.log('✅ Response sent to message bus');
    return lastResponse;
  } else {
    console.log('❌ No response found');
  }
})();
