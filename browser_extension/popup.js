const BUS_URL = 'http://localhost:5001';

const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const log = document.getElementById('log');

// Check bus status
async function checkStatus() {
  try {
    const response = await fetch(`${BUS_URL}/api/status`);
    const data = await response.json();

    if (data.status === 'running') {
      statusDot.classList.add('connected');
      statusText.textContent = `Connected (${data.message_count} messages)`;
    } else {
      statusDot.classList.remove('connected');
      statusText.textContent = 'Bus not responding';
    }
  } catch (err) {
    statusDot.classList.remove('connected');
    statusText.textContent = 'Bus offline';
  }
}

// Load recent messages
async function loadMessages() {
  try {
    const response = await fetch(`${BUS_URL}/api/messages`);
    const data = await response.json();

    log.innerHTML = '';
    for (const msg of (data.messages || []).slice(-10)) {
      const entry = document.createElement('div');
      entry.className = 'log-entry';
      entry.textContent = `[${msg.from}→${msg.to}] ${msg.type}`;
      log.appendChild(entry);
    }
  } catch (err) {
    log.textContent = 'Failed to load messages';
  }
}

// Send test message
document.getElementById('testBtn').addEventListener('click', async () => {
  try {
    await fetch(`${BUS_URL}/api/send`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        from: 'extension',
        to: 'code',
        type: 'test',
        payload: {message: 'Hello from extension!'}
      })
    });

    loadMessages();
  } catch (err) {
    alert('Failed to send message. Is the bus running?');
  }
});

// Clear messages
document.getElementById('clearBtn').addEventListener('click', () => {
  log.innerHTML = '';
});

// Initialize
checkStatus();
loadMessages();

// Auto-refresh every 2 seconds
setInterval(() => {
  checkStatus();
  loadMessages();
}, 2000);
