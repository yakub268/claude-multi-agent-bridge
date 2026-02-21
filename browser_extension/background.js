/**
 * Background Service Worker
 * Manages extension state and message routing
 */

const BUS_URL = 'http://localhost:5001';

console.log('[Claude Bridge] Background service worker started');

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[Claude Bridge] Message from content script:', request);

  if (request.action === 'send') {
    // Forward to message bus
    fetch(`${BUS_URL}/api/send`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        from: 'extension',
        to: request.to,
        type: request.type,
        payload: request.payload
      })
    })
    .then(r => r.json())
    .then(data => sendResponse(data))
    .catch(err => sendResponse({status: 'error', error: err.message}));

    return true;  // Keep channel open for async response
  }
});

// Extension icon click
chrome.action.onClicked.addListener((tab) => {
  console.log('[Claude Bridge] Extension icon clicked');
});
