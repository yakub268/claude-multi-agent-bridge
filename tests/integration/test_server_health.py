"""Integration tests for the Claude Multi-Agent Bridge server."""

import pytest
import requests
import os

BASE_URL = f"http://localhost:{os.getenv('SERVER_PORT', '5001')}"


def test_health_endpoint():
    """Server health check returns 200."""
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_status_endpoint():
    """Server status returns running state."""
    response = requests.get(f"{BASE_URL}/api/status", timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"


def test_send_and_receive_message():
    """Send a message and retrieve it."""
    payload = {
        "from": "test-sender",
        "to": "test-receiver",
        "type": "message",
        "payload": {"text": "integration test"},
    }
    send_resp = requests.post(f"{BASE_URL}/api/send", json=payload, timeout=5)
    assert send_resp.status_code == 200
    assert "message_id" in send_resp.json()

    poll_resp = requests.get(
        f"{BASE_URL}/api/messages", params={"to": "test-receiver"}, timeout=5
    )
    assert poll_resp.status_code == 200
    messages = poll_resp.json()["messages"]
    assert any(m["payload"]["text"] == "integration test" for m in messages)
