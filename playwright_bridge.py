"""
Playwright Bridge - Control browser Claude via Playwright MCP
"""

import json
import time
from code_client import CodeClient


class PlaywrightBridge:
    """
    Uses Playwright to control browser Claude
    Requires Playwright MCP server to be running
    """

    def __init__(self, code_client: CodeClient):
        self.client = code_client
        self.page_url = "https://claude.ai"

    def inject_bridge(self):
        """
        Inject message bus bridge into claude.ai page
        This should be called via Playwright MCP tools
        """
        bridge_script = """
        // Poll message bus
        let lastTimestamp = null;

        async function pollBus() {
            try {
                const params = new URLSearchParams({to: 'browser'});
                if (lastTimestamp) params.append('since', lastTimestamp);

                const response = await fetch(`http://localhost:5001/api/messages?${params}`);
                const data = await response.json();

                for (const msg of data.messages || []) {
                    lastTimestamp = msg.timestamp;
                    handleBusMessage(msg);
                }
            } catch (err) {
                console.error('[Playwright Bridge] Poll failed:', err);
            }

            setTimeout(pollBus, 1000);
        }

        function handleBusMessage(msg) {
            console.log('[Playwright Bridge] Received:', msg);

            if (msg.type === 'command' && msg.payload.action === 'run_prompt') {
                const input = document.querySelector('[contenteditable="true"]');
                if (input) {
                    input.textContent = msg.payload.text;
                    input.dispatchEvent(new Event('input', {bubbles: true}));

                    setTimeout(() => {
                        const submitBtn = document.querySelector('button[aria-label*="Send"]');
                        if (submitBtn && !submitBtn.disabled) {
                            submitBtn.click();
                        }
                    }, 100);
                }
            }
        }

        // Start polling
        pollBus();
        console.log('[Playwright Bridge] Injected and polling');
        """

        return bridge_script

    def send_prompt_to_browser(self, prompt_text: str):
        """Send prompt to browser Claude (via message bus)"""
        return self.client.send(
            to="browser",
            msg_type="command",
            payload={"action": "run_prompt", "text": prompt_text},
        )

    def wait_for_response(self, timeout: float = 30.0) -> str:
        """Wait for browser Claude response"""
        start_time = time.time()
        last_response = None

        def on_response(msg):
            nonlocal last_response
            if msg.get("from") == "browser" and msg.get("type") == "response":
                last_response = msg.get("payload", {}).get("text", "")

        self.client.on("response", on_response)

        while (time.time() - start_time) < timeout:
            self.client.poll()
            if last_response:
                return last_response
            time.sleep(0.5)

        return None


# ============= Example Usage =============

if __name__ == "__main__":
    client = CodeClient()
    bridge = PlaywrightBridge(client)

    print("📤 Sending prompt to browser Claude...")
    bridge.send_prompt_to_browser("What's the capital of France?")

    print("⏳ Waiting for response...")
    response = bridge.wait_for_response(timeout=30.0)

    if response:
        print(f"✅ Got response: {response}")
    else:
        print("❌ No response received")
