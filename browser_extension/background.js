/**
 * Background Service Worker
 * Manages extension lifecycle and message routing.
 * Content scripts now use SSE directly — background handles sending only.
 */

const BUS_URL = 'http://localhost:5001';

console.log('[Claude Bridge] Background service worker started');

// Forward send requests from popup or other extension pages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'send') {
    fetch(`${BUS_URL}/api/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: request.from || 'extension',
        to: request.to || 'all',
        type: request.type || 'message',
        payload: request.payload || {},
      }),
    })
      .then(r => r.json())
      .then(data => sendResponse(data))
      .catch(err => sendResponse({ status: 'error', error: err.message }));
    return true;
  }

  if (request.action === 'status') {
    fetch(`${BUS_URL}/api/status`)
      .then(r => r.json())
      .then(data => sendResponse(data))
      .catch(() => sendResponse({ status: 'offline' }));
    return true;
  }
});

// Extension icon click — open popup
chrome.action.onClicked.addListener((tab) => {
  console.log('[Claude Bridge] Extension icon clicked on tab:', tab.id);
});
