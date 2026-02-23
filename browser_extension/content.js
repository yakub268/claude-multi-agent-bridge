/**
 * Content Script — SSE real-time version
 * Replaced HTTP polling (1s interval) with EventSource push.
 * Messages arrive instantly. CPU/network usage drops to near-zero at idle.
 */

const BUS_URL = 'http://localhost:5001';
const CLIENT_ID = 'browser';

console.log('[Claude Bridge] Content script loaded (SSE mode)');

let isWaitingForResponse = false;
let lastSentPrompt = null;
let lastSeq = 0;
let eventSource = null;

// ── DOM helpers ───────────────────────────────────────────────────────────────

function setInputText(text) {
  // Try contenteditable first (standard claude.ai)
  const input = document.querySelector('[contenteditable="true"]');
  if (input) {
    // React-compatible input dispatch
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLElement.prototype, 'textContent'
    )?.set;
    if (nativeInputValueSetter) {
      nativeInputValueSetter.call(input, text);
    } else {
      input.textContent = text;
    }
    input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
    return true;
  }
  // Fallback: textarea
  const ta = document.querySelector('textarea');
  if (ta) {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
    if (setter) setter.call(ta, text);
    ta.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  }
  return false;
}

function submitInput() {
  const btn = document.querySelector('button[aria-label*="Send"], button[data-testid*="send"]');
  if (btn && !btn.disabled) { btn.click(); return true; }
  // Fallback: Enter key
  const input = document.querySelector('[contenteditable="true"], textarea');
  if (input) {
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    return true;
  }
  return false;
}

function extractLastResponse() {
  // Current claude.ai DOM: responses in .font-claude-message or data-is-streaming=false
  const selectors = [
    '.font-claude-message',
    '.font-claude-response',
    '[data-is-streaming="false"] .prose',
    '.prose',
  ];
  for (const sel of selectors) {
    const nodes = document.querySelectorAll(sel);
    if (!nodes.length) continue;
    const last = nodes[nodes.length - 1];
    const text = last.innerText?.trim();
    if (text && text.length > 10) return text;
  }
  return null;
}

function isStreaming() {
  // Detect if Claude is still generating
  if (document.querySelector('[data-is-streaming="true"]')) return true;
  const status = [...document.querySelectorAll('[role="status"]')];
  return status.some(el => /thinking|writing|generating/i.test(el.textContent));
}

// ── Message bus ───────────────────────────────────────────────────────────────

async function sendToBus(type, payload) {
  try {
    const resp = await fetch(`${BUS_URL}/api/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: CLIENT_ID, to: 'all', type, payload }),
    });
    const data = await resp.json();
    if (data.seq) lastSeq = Math.max(lastSeq, data.seq);
  } catch (e) {
    console.warn('[Claude Bridge] Send failed:', e.message);
  }
}

function handleMessage(msg) {
  if (msg.seq) lastSeq = Math.max(lastSeq, msg.seq);

  // Only process messages targeting us
  if (msg.to !== CLIENT_ID && msg.to !== 'all') return;
  // Ignore our own messages
  if (msg.from === CLIENT_ID) return;

  console.log('[Claude Bridge] →', msg.type, msg.payload);

  if (msg.type === 'command' && msg.payload?.action === 'run_prompt') {
    const text = msg.payload.text;
    lastSentPrompt = text;
    isWaitingForResponse = true;

    if (setInputText(text)) {
      setTimeout(() => submitInput(), 150);
    }
  }

  if (msg.type === 'request' && msg.payload?.text) {
    const text = msg.payload.text;
    const requestId = msg.id;
    lastSentPrompt = text;
    isWaitingForResponse = true;
    window.__bridgeRequestId = requestId;

    if (setInputText(text)) {
      setTimeout(() => submitInput(), 150);
    }
  }
}

// ── SSE connection ────────────────────────────────────────────────────────────

function connectSSE() {
  if (eventSource) eventSource.close();

  eventSource = new EventSource(
    `${BUS_URL}/api/subscribe?client=${CLIENT_ID}&since_seq=${lastSeq}`
  );

  eventSource.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleMessage(msg);
    } catch (e) {
      // heartbeat or parse error — ignore
    }
  };

  eventSource.onerror = () => {
    console.warn('[Claude Bridge] SSE disconnected, reconnecting in 3s...');
    eventSource.close();
    setTimeout(connectSSE, 3000);
  };

  console.log('[Claude Bridge] SSE connected (since_seq=' + lastSeq + ')');
}

// ── MutationObserver: watch for Claude finishing response ─────────────────────

const observer = new MutationObserver(() => {
  if (!isWaitingForResponse) return;
  if (isStreaming()) return;

  // Debounce — wait for DOM to settle
  clearTimeout(window.__bridgeExtractTimer);
  window.__bridgeExtractTimer = setTimeout(async () => {
    if (!isWaitingForResponse) return;
    const response = extractLastResponse();
    if (response && response.length > 10) {
      isWaitingForResponse = false;
      console.log('[Claude Bridge] Response captured (' + response.length + ' chars)');

      const payload = {
        text: response,
        prompt: lastSentPrompt,
        url: window.location.href,
      };

      // If this was a request/reply, include reply_to
      if (window.__bridgeRequestId) {
        payload.reply_to = window.__bridgeRequestId;
        payload.request_id = window.__bridgeRequestId;
        window.__bridgeRequestId = null;
      }

      await sendToBus('response', payload);
    }
  }, 800);
});

observer.observe(document.body, {
  childList: true,
  subtree: true,
  characterData: true,
});

// ── Boot ──────────────────────────────────────────────────────────────────────

// Small delay to let the page fully load
setTimeout(connectSSE, 500);

// Announce presence
setTimeout(() => sendToBus('status', { client: CLIENT_ID, ready: true, transport: 'SSE' }), 1000);
