#!/usr/bin/env python3
"""
Authentication & Authorization for Claude Multi-Agent Bridge

Features:
- API token authentication
- Rate limiting  
- Room access control
- Input validation
"""
import time
import hashlib
import secrets
import logging
from typing import Dict, Optional, Set
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify

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
            timestamp for timestamp in self.buckets[client_id]
            if timestamp > minute_ago
        ]

        # Check limit
        if len(self.buckets[client_id]) >= self.requests_per_minute:
            return False

        # Allow request
        self.buckets[client_id].append(now)
        return True


class TokenAuth:
    """API token authentication"""

    def __init__(self):
        self.tokens: Dict[str, Dict] = {}

    def generate_token(self, client_id: str, expires_hours: int = 720) -> str:
        """Generate new API token"""
        token = secrets.token_urlsafe(32)
        self.tokens[token] = {
            'client_id': client_id,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(hours=expires_hours)
        }
        return token

    def verify_token(self, token: str) -> Optional[str]:
        """Verify token and return client_id"""
        token_data = self.tokens.get(token)
        if not token_data:
            return None
        if datetime.now() > token_data['expires_at']:
            return None
        return token_data['client_id']


# Test
if __name__ == '__main__':
    auth = TokenAuth()
    token = auth.generate_token("claude-code")
    print(f"Token: {token[:20]}...")
    print(f"Verify: {auth.verify_token(token)}")
