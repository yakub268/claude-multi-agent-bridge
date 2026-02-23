"""
Claude Multi-Agent Bridge — MCP Server

Exposes the bridge message bus as MCP tools so ANY MCP-compatible client
(Claude Desktop, Cursor, VS Code Copilot, etc.) can communicate with
Browser Claude and Desktop Claude without touching the API.

Usage — add to claude_desktop_config.json or .cursor/mcp.json:
{
  "mcpServers": {
    "claude-bridge": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": { "BRIDGE_URL": "http://localhost:5001" }
    }
  }
}

Or via uvx (no install):
  uvx --from claude-multi-agent-bridge bridge-mcp
"""

import json
import os
import sys
import queue
import threading
import time
from typing import Any

import requests

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
except ImportError:
    print(
        "mcp package not found. Install with: pip install mcp",
        file=sys.stderr
    )
    sys.exit(1)

BRIDGE_URL = os.environ.get("BRIDGE_URL", "http://localhost:5001")
DEFAULT_TIMEOUT = int(os.environ.get("BRIDGE_TIMEOUT", "30"))

server = Server("claude-bridge")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _send(to: str, msg_type: str, payload: dict, from_c: str = "mcp") -> dict:
    resp = requests.post(
        f"{BRIDGE_URL}/api/send",
        json={"from": from_c, "to": to, "type": msg_type, "payload": payload},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()


def _wait_for_reply(msg_id: str, timeout: int = DEFAULT_TIMEOUT) -> dict | None:
    """
    Poll /api/messages until we see a reply referencing msg_id,
    or until timeout. Returns the reply message or None.
    """
    deadline = time.time() + timeout
    seen: set[str] = set()
    while time.time() < deadline:
        try:
            resp = requests.get(
                f"{BRIDGE_URL}/api/messages",
                params={"to": "mcp"},
                timeout=5,
            )
            messages = resp.json().get("messages", [])
            for m in messages:
                if m["id"] in seen:
                    continue
                seen.add(m["id"])
                payload = m.get("payload", {})
                if payload.get("reply_to") == msg_id or payload.get("request_id") == msg_id:
                    return m
        except Exception:
            pass
        time.sleep(0.5)
    return None


# ── Tool definitions ──────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="bridge_send",
            description=(
                "Send a message to a Claude instance via the bridge. "
                "Targets: 'browser' (claude.ai tab), 'desktop' (Claude Desktop), 'all' (broadcast). "
                "Does not wait for a reply — use bridge_ask for request/response."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "enum": ["browser", "desktop", "all"],
                        "description": "Target Claude instance",
                    },
                    "message": {
                        "type": "string",
                        "description": "Text to send",
                    },
                    "type": {
                        "type": "string",
                        "default": "message",
                        "description": "Message type tag (e.g. 'task', 'message', 'result')",
                    },
                },
                "required": ["to", "message"],
            },
        ),
        types.Tool(
            name="bridge_ask",
            description=(
                "Send a message to a Claude instance and WAIT for its reply. "
                "Use this when you need Browser Claude to search the web or perform a task "
                "and return results. Blocks until reply received or timeout."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "enum": ["browser", "desktop"],
                        "description": "Target Claude instance",
                    },
                    "message": {
                        "type": "string",
                        "description": "Question or task for the target Claude",
                    },
                    "timeout": {
                        "type": "integer",
                        "default": DEFAULT_TIMEOUT,
                        "description": "Seconds to wait for reply",
                    },
                },
                "required": ["to", "message"],
            },
        ),
        types.Tool(
            name="bridge_broadcast",
            description="Broadcast a message to ALL connected Claude instances simultaneously.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "type": {"type": "string", "default": "broadcast"},
                },
                "required": ["message"],
            },
        ),
        types.Tool(
            name="bridge_messages",
            description=(
                "Retrieve recent messages from the bridge bus. "
                "Useful for checking what other Claude instances have said."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "since": {
                        "type": "string",
                        "description": "ISO timestamp — only return messages after this time",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "description": "Max messages to return",
                    },
                },
            },
        ),
        types.Tool(
            name="bridge_search",
            description=(
                "Full-text search across all bridge messages (FTS5). "
                "Find past agent conversations about a topic."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search terms"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="bridge_status",
            description="Check if the bridge server is running and see connected clients.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    try:
        if name == "bridge_send":
            result = _send(
                to=arguments["to"],
                msg_type=arguments.get("type", "message"),
                payload={"text": arguments["message"]},
            )
            return [types.TextContent(
                type="text",
                text=f"✅ Sent to {arguments['to']} (id: {result.get('message_id')})"
            )]

        elif name == "bridge_ask":
            sent = _send(
                to=arguments["to"],
                msg_type="request",
                payload={
                    "text": arguments["message"],
                    "reply_to": "mcp",
                    "awaiting_reply": True,
                },
            )
            msg_id = sent.get("message_id")
            timeout = arguments.get("timeout", DEFAULT_TIMEOUT)
            reply = _wait_for_reply(msg_id, timeout=timeout)
            if reply:
                payload = reply.get("payload", {})
                text = payload.get("text") or payload.get("response") or json.dumps(payload)
                return [types.TextContent(type="text", text=text)]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"⏱️ No reply from {arguments['to']} within {timeout}s. "
                         f"Message was delivered (id: {msg_id})."
                )]

        elif name == "bridge_broadcast":
            result = _send(
                to="all",
                msg_type=arguments.get("type", "broadcast"),
                payload={"text": arguments["message"]},
            )
            return [types.TextContent(
                type="text",
                text=f"📡 Broadcast sent (id: {result.get('message_id')})"
            )]

        elif name == "bridge_messages":
            params = {}
            if arguments.get("since"):
                params["since"] = arguments["since"]
            resp = requests.get(f"{BRIDGE_URL}/api/messages", params=params, timeout=5)
            messages = resp.json().get("messages", [])
            limit = arguments.get("limit", 20)
            messages = messages[-limit:]
            if not messages:
                return [types.TextContent(type="text", text="No messages found.")]
            lines = []
            for m in messages:
                payload_text = m.get("payload", {}).get("text", json.dumps(m["payload"]))
                lines.append(f"[{m['timestamp']}] {m['from']} → {m['to']} ({m['type']}): {payload_text}")
            return [types.TextContent(type="text", text="\n".join(lines))]

        elif name == "bridge_search":
            resp = requests.get(
                f"{BRIDGE_URL}/api/search",
                params={"q": arguments["query"], "limit": arguments.get("limit", 10)},
                timeout=5,
            )
            results = resp.json().get("results", [])
            if not results:
                return [types.TextContent(type="text", text=f"No messages found for: {arguments['query']}")]
            lines = []
            for m in results:
                payload_text = m.get("payload", {}).get("text", json.dumps(m["payload"]))
                lines.append(f"[{m['timestamp']}] {m['from']} → {m['to']}: {payload_text}")
            return [types.TextContent(type="text", text="\n".join(lines))]

        elif name == "bridge_status":
            resp = requests.get(f"{BRIDGE_URL}/api/status", timeout=5)
            data = resp.json()
            return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except requests.ConnectionError:
        return [types.TextContent(
            type="text",
            text=(
                f"❌ Cannot connect to bridge at {BRIDGE_URL}. "
                "Start the server: python server.py"
            )
        )]
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error: {e}")]


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
