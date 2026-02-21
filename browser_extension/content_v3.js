/**
 * Content Script V2 - CSP-safe version
 * No dynamic script injection, direct DOM manipulation
 */

const BUS_URL = 'http://localhost:5001';
const CLIENT_ID = 'browser';

console.log('[Claude Bridge] Content script loaded');

// Start from current time to ignore old queued messages
let lastTimestamp = new Date().toISOString();
let isWaitingForResponse = false;
let lastSentPrompt = null;
let lastSentResponse = null;

// Direct DOM manipulation functions (no CSP issues)
function setInputText(text) {
  const input = document.querySelector('[contenteditable="true"]');
  if (input) {
    input.textContent = text;
    input.dispatchEvent(new Event('input', {bubbles: true}));
    return true;
  }
  return false;
}

function submitInput() {
  const submitBtn = document.querySelector('button[aria-label*="Send"]');
  if (submitBtn && !submitBtn.disabled) {
    submitBtn.click();
    return true;
  }
  return false;
}

function extractLastResponse() {
  // Claude responses are in divs with class "font-claude-response"
  const responseDivs = document.querySelectorAll('.font-claude-response');

  // Get the last Claude response
  if (responseDivs.length > 0) {
    const lastResponse = responseDivs[responseDivs.length - 1];
    const paragraphs = lastResponse.querySelectorAll('p');

    if (paragraphs.length > 0) {
      const text = Array.from(paragraphs)
        .map(p => p.textContent.trim())
        .filter(t => t && t !== 'undefined' && !t.includes('Thinking'))
        .join('\n\n');

      if (text.length > 0) {
        return text;
      }
    }
  }

  return null;
}

// Poll message bus
async function pollMessages() {
  try {
    const params = new URLSearchParams({to: CLIENT_ID});
    if (lastTimestamp) {
      params.append('since', lastTimestamp);
    }

    const response = await fetch(`${BUS_URL}/api/messages?${params}`);
    const data = await response.json();

    for (const msg of data.messages || []) {
      lastTimestamp = msg.timestamp;
      handleMessage(msg);
    }
  } catch (err) {
    // Silent fail
  }

  setTimeout(pollMessages, 1000);
}

function handleMessage(msg) {
  console.log('[Claude Bridge] Received:', msg);

  if (msg.type === 'command' && msg.payload.action === 'run_prompt') {
    const text = msg.payload.text;
    lastSentPrompt = text;
    isWaitingForResponse = true;

    // Set input and submit
    if (setInputText(text)) {
      setTimeout(() => {
        submitInput();
        console.log('[Claude Bridge] Prompt submitted');
      }, 100);
    }
  }
}

// Watch for responses with MutationObserver
const observer = new MutationObserver(() => {
  if (!isWaitingForResponse) return;

  // Check if "Done" indicator appears (status element never disappears)
  const allElements = document.querySelectorAll('*');
  const hasDone = Array.from(allElements).some(el =>
    el.textContent.trim() === 'Done' && el.tagName !== 'BUTTON'
  );

  if (hasDone) {
    // Wait a bit then extract response
    setTimeout(async () => {
      const response = extractLastResponse();

      if (response && response.length > 0 && response !== lastSentResponse) {
        console.log('[Claude Bridge] Extracted response:', response.substring(0, 100) + '...');

        // Send to bus
        try {
          await fetch(`${BUS_URL}/api/send`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              from: CLIENT_ID,
              to: 'all',
              type: 'claude_response',
              payload: {
                prompt: lastSentPrompt,
                response: response,
                timestamp: new Date().toISOString()
              }
            })
          });

          console.log('[Claude Bridge] Response sent to bus');
          isWaitingForResponse = false;
          lastSentPrompt = null;
          lastSentResponse = response;
        } catch (err) {
          console.error('[Claude Bridge] Failed to send:', err);
        }
      }
    }, 1000);
  }
});

// Start observing
observer.observe(document.body, {
  childList: true,
  subtree: true
});

// Start polling
pollMessages();

console.log('[Claude Bridge] Polling started');
console.log('[Claude Bridge] Response observer active');

// Send ready signal
fetch(`${BUS_URL}/api/send`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    from: CLIENT_ID,
    to: 'all',
    type: 'browser_ready',
    payload: {
      url: window.location.href,
      timestamp: new Date().toISOString()
    }
  })
}).catch(() => {});
