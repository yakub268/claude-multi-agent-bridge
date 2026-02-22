#!/usr/bin/env python3
"""
Authentication & Authorization for Multi-Agent Bridge
API key management, rate limiting, permissions
"""
import hashlib
import secrets
import time
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Set
from functools import wraps
from flask import request, jsonify


class AuthManager:
    """
    Manages API keys, permissions, and rate limiting

    Features:
    - API key generation and validation
    - Per-key rate limiting
    - Permission levels (read, write, admin)
    - Key expiration
    - Usage tracking
    """

    def __init__(self, keys_file: str = "api_keys.json"):
        self.keys_file = Path(keys_file)
        self.keys = {}  # key_hash -> {metadata}
        self.rate_limits = {}  # key_hash -> {count, reset_time}
        self.usage_stats = {}  # key_hash -> {requests, messages, errors}

        self._load_keys()

    def _load_keys(self):
        """Load API keys from file"""
        if self.keys_file.exists():
            try:
                with open(self.keys_file) as f:
                    self.keys = json.load(f)
            except Exception as e:
                print(f"⚠️  Error loading keys: {e}")

    def _save_keys(self):
        """Save API keys to file"""
        try:
            with open(self.keys_file, 'w') as f:
                json.dump(self.keys, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving keys: {e}")

    def generate_key(self, client_id: str, permissions: Set[str] = None,
                     rate_limit: int = 1000, expires_days: int = None) -> str:
        """
        Generate new API key

        Args:
            client_id: Client identifier
            permissions: Set of permissions (read, write, admin)
            rate_limit: Requests per hour
            expires_days: Days until expiration (None = never)

        Returns:
            API key (format: cb_xxx...)
        """
        # Generate random key
        raw_key = f"cb_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()

        # Store metadata
        self.keys[key_hash] = {
            'client_id': client_id,
            'permissions': list(permissions or {'read', 'write'}),
            'rate_limit': rate_limit,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expires_at': expires_at,
            'active': True
        }

        self.usage_stats[key_hash] = {
            'requests': 0,
            'messages': 0,
            'errors': 0,
            'first_used': None,
            'last_used': None
        }

        self._save_keys()
        return raw_key

    def validate_key(self, api_key: str) -> Optional[Dict]:
        """
        Validate API key and return metadata

        Returns:
            Key metadata if valid, None if invalid
        """
        if not api_key or not api_key.startswith('cb_'):
            return None

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        if key_hash not in self.keys:
            return None

        key_data = self.keys[key_hash]

        # Check if active
        if not key_data.get('active', True):
            return None

        # Check expiration
        if key_data.get('expires_at'):
            expires = datetime.fromisoformat(key_data['expires_at'])
            if datetime.now(timezone.utc) > expires:
                return None

        # Check rate limit
        if not self._check_rate_limit(key_hash, key_data['rate_limit']):
            return None

        # Update usage
        self._update_usage(key_hash)

        return key_data

    def _check_rate_limit(self, key_hash: str, limit: int) -> bool:
        """Check if request is within rate limit"""
        now = time.time()

        if key_hash not in self.rate_limits:
            self.rate_limits[key_hash] = {
                'count': 0,
                'reset_time': now + 3600  # 1 hour window
            }

        rate_data = self.rate_limits[key_hash]

        # Reset if window expired
        if now > rate_data['reset_time']:
            rate_data['count'] = 0
            rate_data['reset_time'] = now + 3600

        # Check limit
        if rate_data['count'] >= limit:
            return False

        rate_data['count'] += 1
        return True

    def _update_usage(self, key_hash: str):
        """Update usage statistics"""
        if key_hash not in self.usage_stats:
            self.usage_stats[key_hash] = {
                'requests': 0,
                'messages': 0,
                'errors': 0,
                'first_used': None,
                'last_used': None
            }

        stats = self.usage_stats[key_hash]
        stats['requests'] += 1

        now = datetime.now(timezone.utc).isoformat()
        if not stats['first_used']:
            stats['first_used'] = now
        stats['last_used'] = now

    def has_permission(self, api_key: str, permission: str) -> bool:
        """Check if API key has specific permission"""
        key_data = self.validate_key(api_key)
        if not key_data:
            return False

        return permission in key_data.get('permissions', [])

    def revoke_key(self, api_key: str) -> bool:
        """Revoke an API key"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        if key_hash in self.keys:
            self.keys[key_hash]['active'] = False
            self._save_keys()
            return True

        return False

    def get_stats(self, api_key: str) -> Optional[Dict]:
        """Get usage statistics for an API key"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        if key_hash in self.usage_stats:
            return {
                **self.usage_stats[key_hash],
                'rate_limit': self.keys[key_hash].get('rate_limit'),
                'current_usage': self.rate_limits.get(key_hash, {}).get('count', 0)
            }

        return None


# ============================================================================
# Flask Decorators
# ============================================================================

def require_auth(auth_manager: AuthManager):
    """Decorator to require API key authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get API key from header
            api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')

            if api_key and api_key.startswith('Bearer '):
                api_key = api_key[7:]  # Remove 'Bearer ' prefix

            # Validate
            key_data = auth_manager.validate_key(api_key)

            if not key_data:
                return jsonify({'error': 'Invalid or expired API key'}), 401

            # Attach to request
            request.api_key_data = key_data

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_permission(auth_manager: AuthManager, permission: str):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')

            if api_key and api_key.startswith('Bearer '):
                api_key = api_key[7:]

            if not auth_manager.has_permission(api_key, permission):
                return jsonify({'error': f'Permission denied: {permission} required'}), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == '__main__':
    # Create auth manager
    auth = AuthManager(keys_file='test_keys.json')

    # Generate keys
    admin_key = auth.generate_key(
        client_id='admin',
        permissions={'read', 'write', 'admin'},
        rate_limit=10000
    )

    user_key = auth.generate_key(
        client_id='user1',
        permissions={'read', 'write'},
        rate_limit=1000,
        expires_days=30
    )

    readonly_key = auth.generate_key(
        client_id='monitor',
        permissions={'read'},
        rate_limit=5000
    )

    print("Generated API Keys:")
    print(f"\n🔑 Admin Key:    {admin_key}")
    print(f"🔑 User Key:     {user_key}")
    print(f"🔑 ReadOnly Key: {readonly_key}")

    # Test validation
    print(f"\n✅ Admin key valid: {auth.validate_key(admin_key) is not None}")
    print(f"✅ Has admin perm: {auth.has_permission(admin_key, 'admin')}")
    print(f"❌ User has admin: {auth.has_permission(user_key, 'admin')}")

    # Test rate limiting
    print(f"\nTesting rate limits...")
    for i in range(5):
        if auth.validate_key(user_key):
            print(f"  Request {i+1}: ✅")
        else:
            print(f"  Request {i+1}: ❌ Rate limited")

    # Get stats
    stats = auth.get_stats(user_key)
    print(f"\nUsage stats: {stats}")
