#!/usr/bin/env python3
"""
Authentication & Authorization for Claude Multi-Agent Bridge

Features:
- API token authentication with persistent storage
- Rate limiting
- Room access control
- Input validation
"""
import time
import hashlib
import secrets
import logging
import json
import os
from typing import Dict, Optional, Set
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from pathlib import Path

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.buckets: Dict[str, list] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed"""
        now = time.time()
        minute_ago = now - 60

        # Clean old requests
        self.buckets[client_id] = [
            timestamp for timestamp in self.buckets[client_id] if timestamp > minute_ago
        ]

        # Check limit
        if len(self.buckets[client_id]) >= self.requests_per_minute:
            return False

        # Allow request
        self.buckets[client_id].append(now)
        return True


class TokenAuth:
    """API token authentication with persistent storage"""

    def __init__(self, token_file: str = "data/tokens.json"):
        """
        Initialize with persistent token storage

        Args:
            token_file: Path to JSON file for token persistence
        """
        self.token_file = token_file
        self.tokens: Dict[str, Dict] = {}
        self.revoked: Set[str] = set()

        # Ensure data directory exists
        Path(token_file).parent.mkdir(parents=True, exist_ok=True)

        # Load persisted tokens
        self._load_tokens()

    def _load_tokens(self):
        """Load tokens from disk"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r") as f:
                    data = json.load(f)
                    # Convert datetime strings back to objects
                    for token, token_data in data.get("tokens", {}).items():
                        self.tokens[token] = {
                            "client_id": token_data["client_id"],
                            "created_at": datetime.fromisoformat(
                                token_data["created_at"]
                            ),
                            "expires_at": datetime.fromisoformat(
                                token_data["expires_at"]
                            ),
                        }
                    self.revoked = set(data.get("revoked", []))
                logger.info(f"Loaded {len(self.tokens)} tokens from {self.token_file}")
            except Exception as e:
                logger.error(f"Failed to load tokens: {e}")

    def _save_tokens(self):
        """Save tokens to disk"""
        try:
            data = {
                "tokens": {
                    token: {
                        "client_id": token_data["client_id"],
                        "created_at": token_data["created_at"].isoformat(),
                        "expires_at": token_data["expires_at"].isoformat(),
                    }
                    for token, token_data in self.tokens.items()
                },
                "revoked": list(self.revoked),
            }
            with open(self.token_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")

    def generate_token(self, client_id: str, expires_hours: int = 720) -> str:
        """Generate new API token"""
        token = secrets.token_urlsafe(32)
        self.tokens[token] = {
            "client_id": client_id,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=expires_hours),
        }

        # Persist to disk
        self._save_tokens()

        logger.info(f"Generated token for {client_id}, expires in {expires_hours}h")
        return token

    def verify_token(self, token: str) -> Optional[str]:
        """Verify token and return client_id"""
        # Check if revoked
        if token in self.revoked:
            return None

        token_data = self.tokens.get(token)
        if not token_data:
            return None

        # Check expiration
        if datetime.now() > token_data["expires_at"]:
            logger.warning(f"Token expired for {token_data['client_id']}")
            return None

        return token_data["client_id"]

    def revoke_token(self, token: str) -> bool:
        """Revoke a token"""
        if token in self.tokens:
            self.revoked.add(token)
            self._save_tokens()
            logger.info(f"Revoked token for {self.tokens[token]['client_id']}")
            return True
        return False

    def cleanup_expired(self):
        """Remove expired tokens from storage"""
        now = datetime.now()
        expired = [
            token for token, data in self.tokens.items() if now > data["expires_at"]
        ]

        for token in expired:
            del self.tokens[token]
            self.revoked.discard(token)

        if expired:
            self._save_tokens()
            logger.info(f"Cleaned up {len(expired)} expired tokens")


# Test
if __name__ == "__main__":
    auth = TokenAuth()
    token = auth.generate_token("claude-code")
    print(f"Token: {token[:20]}...")
    print(f"Verify: {auth.verify_token(token)}")
