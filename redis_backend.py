#!/usr/bin/env python3
"""
Redis Backend for Distributed State

Replaces in-memory storage with Redis for multi-server deployments.
Enables horizontal scaling with multiple server instances.

Usage:
    # In server_ws.py:
    from redis_backend import RedisBackend

    backend = RedisBackend(host='localhost', port=6379)

    # Replace in-memory operations:
    # message_store.append(msg) → backend.store_message(msg)
    # list(message_store) → backend.get_messages(...)
"""
import json
import redis
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class RedisBackend:
    """
    Redis-backed storage for message bus state

    Replaces:
    - message_store (deque)
    - ws_connections (dict)
    - pending_acks (dict)
    - metrics (dict)
    """

    def __init__(self,
                 host: str = 'localhost',
                 port: int = 6379,
                 db: int = 0,
                 password: Optional[str] = None,
                 message_ttl: int = 300,  # 5 minutes
                 max_messages: int = 500):
        """
        Initialize Redis connection

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Optional password
            message_ttl: Message TTL in seconds
            max_messages: Max messages to store per client
        """
        self.message_ttl = message_ttl
        self.max_messages = max_messages

        try:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )

            # Test connection
            self.redis.ping()
            logger.info(f"✅ Connected to Redis at {host}:{port}")

        except redis.ConnectionError as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise

    # ========================================================================
    # Message Storage
    # ========================================================================

    def store_message(self, message: Dict) -> bool:
        """
        Store message in Redis

        Args:
            message: Message dict

        Returns:
            True if stored successfully
        """
        try:
            msg_id = message['id']
            to_client = message['to']

            # Store in global message list
            self.redis.lpush('messages:all', json.dumps(message))
            self.redis.ltrim('messages:all', 0, self.max_messages - 1)

            # Store in client-specific queue
            if to_client and to_client != 'all':
                self.redis.lpush(f'messages:to:{to_client}', json.dumps(message))
                self.redis.ltrim(f'messages:to:{to_client}', 0, self.max_messages - 1)

                # Set TTL
                self.redis.expire(f'messages:to:{to_client}', self.message_ttl)

            # Store message by ID
            self.redis.setex(
                f'message:{msg_id}',
                self.message_ttl,
                json.dumps(message)
            )

            return True

        except Exception as e:
            logger.error(f"Failed to store message: {e}")
            return False

    def get_messages(self,
                     to_client: Optional[str] = None,
                     since: Optional[str] = None,
                     limit: int = 100) -> List[Dict]:
        """
        Retrieve messages from Redis

        Args:
            to_client: Filter by recipient
            since: Filter by timestamp
            limit: Max messages to return

        Returns:
            List of message dicts
        """
        try:
            # Get from client-specific queue
            if to_client:
                key = f'messages:to:{to_client}'
            else:
                key = 'messages:all'

            # Get messages (newest first)
            raw_messages = self.redis.lrange(key, 0, limit - 1)

            messages = []
            for raw in raw_messages:
                msg = json.loads(raw)

                # Filter by timestamp
                if since and msg['timestamp'] <= since:
                    continue

                messages.append(msg)

            # Reverse for chronological order
            messages.reverse()

            return messages

        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []

    def get_message(self, msg_id: str) -> Optional[Dict]:
        """Get specific message by ID"""
        try:
            raw = self.redis.get(f'message:{msg_id}')
            if raw:
                return json.loads(raw)
            return None
        except Exception as e:
            logger.error(f"Failed to get message {msg_id}: {e}")
            return None

    # ========================================================================
    # Connection Tracking
    # ========================================================================

    def register_connection(self, client_id: str, connection_id: str) -> bool:
        """
        Register WebSocket connection

        Args:
            client_id: Client identifier
            connection_id: Connection identifier (unique per instance)

        Returns:
            True if registered
        """
        try:
            # Add to client's connection set
            self.redis.sadd(f'connections:{client_id}', connection_id)

            # Store connection metadata
            metadata = {
                'client_id': client_id,
                'connected_at': datetime.now(timezone.utc).isoformat(),
                'server_instance': connection_id.split('-')[0]  # Extract server ID
            }

            self.redis.setex(
                f'connection:{connection_id}',
                3600,  # 1 hour TTL
                json.dumps(metadata)
            )

            # Increment global counter
            self.redis.incr('metrics:total_connections')

            return True

        except Exception as e:
            logger.error(f"Failed to register connection: {e}")
            return False

    def unregister_connection(self, client_id: str, connection_id: str) -> bool:
        """Unregister WebSocket connection"""
        try:
            self.redis.srem(f'connections:{client_id}', connection_id)
            self.redis.delete(f'connection:{connection_id}')
            return True
        except Exception as e:
            logger.error(f"Failed to unregister connection: {e}")
            return False

    def get_active_connections(self, client_id: Optional[str] = None) -> int:
        """Get count of active connections"""
        try:
            if client_id:
                return self.redis.scard(f'connections:{client_id}')
            else:
                # Count all connections across all clients
                keys = self.redis.keys('connections:*')
                total = sum(self.redis.scard(key) for key in keys)
                return total
        except Exception as e:
            logger.error(f"Failed to count connections: {e}")
            return 0

    # ========================================================================
    # Metrics
    # ========================================================================

    def increment_metric(self, metric_name: str, amount: int = 1):
        """Increment a metric counter"""
        try:
            self.redis.incrby(f'metrics:{metric_name}', amount)
        except Exception as e:
            logger.error(f"Failed to increment metric {metric_name}: {e}")

    def set_metric(self, metric_name: str, value: any):
        """Set metric value"""
        try:
            self.redis.set(f'metrics:{metric_name}', str(value))
        except Exception as e:
            logger.error(f"Failed to set metric {metric_name}: {e}")

    def get_metric(self, metric_name: str) -> Optional[str]:
        """Get metric value"""
        try:
            return self.redis.get(f'metrics:{metric_name}')
        except Exception as e:
            logger.error(f"Failed to get metric {metric_name}: {e}")
            return None

    def get_all_metrics(self) -> Dict:
        """Get all metrics"""
        try:
            keys = self.redis.keys('metrics:*')
            metrics = {}
            for key in keys:
                metric_name = key.replace('metrics:', '')
                value = self.redis.get(key)

                # Try to convert to int
                try:
                    metrics[metric_name] = int(value)
                except ValueError:
                    metrics[metric_name] = value

            return metrics

        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {}

    # ========================================================================
    # Acknowledgments
    # ========================================================================

    def store_ack(self, msg_id: str, ack_data: Dict):
        """Store acknowledgment data"""
        try:
            self.redis.setex(
                f'ack:{msg_id}',
                self.message_ttl,
                json.dumps(ack_data)
            )
        except Exception as e:
            logger.error(f"Failed to store ack: {e}")

    def get_ack(self, msg_id: str) -> Optional[Dict]:
        """Get acknowledgment data"""
        try:
            raw = self.redis.get(f'ack:{msg_id}')
            if raw:
                return json.loads(raw)
            return None
        except Exception as e:
            logger.error(f"Failed to get ack: {e}")
            return None

    # ========================================================================
    # Cleanup
    # ========================================================================

    def cleanup_old_data(self):
        """Clean up expired data (called periodically)"""
        try:
            # Redis handles TTL automatically
            # This is a placeholder for any manual cleanup
            logger.info("Redis cleanup: TTL-based expiration active")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def close(self):
        """Close Redis connection"""
        try:
            self.redis.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Failed to close Redis: {e}")


# Migration helper
def migrate_to_redis(message_store, backend: RedisBackend):
    """
    Migrate existing in-memory messages to Redis

    Args:
        message_store: Existing deque of messages
        backend: RedisBackend instance
    """
    logger.info(f"Migrating {len(message_store)} messages to Redis...")

    count = 0
    for msg in message_store:
        if backend.store_message(msg):
            count += 1

    logger.info(f"✅ Migrated {count}/{len(message_store)} messages")


# Example usage
if __name__ == '__main__':
    print("=" * 80)
    print("🔴 REDIS BACKEND - Test")
    print("=" * 80)
    print()

    try:
        backend = RedisBackend(host='localhost', port=6379)

        # Test message storage
        test_msg = {
            'id': 'msg-test-123',
            'from': 'test-client-1',
            'to': 'test-client-2',
            'text': 'Hello Redis!',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        print("Storing test message...")
        backend.store_message(test_msg)

        print("Retrieving messages...")
        messages = backend.get_messages(to_client='test-client-2')
        print(f"Found {len(messages)} messages")

        print("Testing metrics...")
        backend.increment_metric('test_counter', 5)
        metrics = backend.get_all_metrics()
        print(f"Metrics: {metrics}")

        print()
        print("✅ Redis backend test complete!")

        backend.close()

    except Exception as e:
        print(f"❌ Test failed: {e}")
        print()
        print("Make sure Redis is running:")
        print("  docker run -d -p 6379:6379 redis:7-alpine")
