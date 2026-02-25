#!/usr/bin/env python3
"""
Batch Operations for Multi-Agent Bridge
Send to multiple recipients, bulk operations, compression
"""
import gzip
import json
import base64
from typing import List, Dict, Optional
from datetime import datetime, timezone


class BatchOperations:
    """
    Batch messaging operations

    Features:
    - Send to multiple recipients
    - Broadcast to all clients
    - Bulk message sending
    - Message compression (gzip)
    - Deduplication
    - Transaction-like batching
    """

    def __init__(self, send_function: callable):
        """
        Initialize batch operations

        Args:
            send_function: Function to send individual message
                          Should accept (to, type, payload) -> bool
        """
        self.send = send_function
        self.stats = {
            'total_sent': 0,
            'total_failed': 0,
            'bytes_sent': 0,
            'bytes_compressed': 0
        }

    def send_to_many(self,
                     recipients: List[str],
                     msg_type: str,
                     payload: Dict,
                     require_all: bool = False) -> Dict:
        """
        Send same message to multiple recipients

        Args:
            recipients: List of client IDs
            msg_type: Message type
            payload: Message payload
            require_all: If True, fails if any send fails

        Returns:
            {
                'sent': ['client1', 'client2'],
                'failed': ['client3'],
                'success_rate': 0.67
            }
        """
        sent = []
        failed = []

        for recipient in recipients:
            try:
                success = self.send(recipient, msg_type, payload)
                if success:
                    sent.append(recipient)
                    self.stats['total_sent'] += 1
                else:
                    failed.append(recipient)
                    self.stats['total_failed'] += 1

                    if require_all:
                        # Rollback not implemented - would need transactional support
                        break

            except Exception as e:
                failed.append(recipient)
                self.stats['total_failed'] += 1

        return {
            'sent': sent,
            'failed': failed,
            'total': len(recipients),
            'success_rate': len(sent) / len(recipients) if recipients else 0
        }

    def broadcast(self,
                  msg_type: str,
                  payload: Dict,
                  exclude: Optional[List[str]] = None) -> Dict:
        """
        Broadcast to all connected clients

        Args:
            msg_type: Message type
            payload: Message payload
            exclude: List of client IDs to exclude

        Returns:
            Delivery report
        """
        # This would integrate with connection tracker to get all clients
        # For now, simplified version
        all_clients = ['code', 'browser', 'desktop']  # Placeholder

        if exclude:
            all_clients = [c for c in all_clients if c not in exclude]

        return self.send_to_many(all_clients, msg_type, payload)

    def send_compressed(self,
                        to: str,
                        msg_type: str,
                        payload: Dict,
                        compression_threshold: int = 1024) -> bool:
        """
        Send message with compression if payload is large

        Args:
            to: Recipient client ID
            msg_type: Message type
            payload: Message payload
            compression_threshold: Compress if payload > N bytes

        Returns:
            True if sent successfully
        """
        # Serialize payload
        payload_json = json.dumps(payload)
        payload_bytes = payload_json.encode('utf-8')
        original_size = len(payload_bytes)

        self.stats['bytes_sent'] += original_size

        # Compress if over threshold
        if original_size > compression_threshold:
            compressed = gzip.compress(payload_bytes)
            compressed_b64 = base64.b64encode(compressed).decode('ascii')

            self.stats['bytes_compressed'] += len(compressed)

            # Send compressed
            compressed_payload = {
                '_compressed': True,
                '_original_size': original_size,
                '_data': compressed_b64
            }

            return self.send(to, msg_type, compressed_payload)

        else:
            # Send uncompressed
            return self.send(to, msg_type, payload)

    def decompress_payload(self, payload: Dict) -> Dict:
        """
        Decompress payload if compressed

        Args:
            payload: Potentially compressed payload

        Returns:
            Decompressed payload
        """
        if payload.get('_compressed'):
            compressed_b64 = payload['_data']
            compressed = base64.b64decode(compressed_b64)
            decompressed = gzip.decompress(compressed)
            return json.loads(decompressed.decode('utf-8'))

        return payload

    def send_batch(self, messages: List[Dict]) -> Dict:
        """
        Send multiple messages in batch

        Args:
            messages: List of {to, type, payload} dicts

        Returns:
            Batch result summary
        """
        results = {
            'sent': 0,
            'failed': 0,
            'total': len(messages),
            'details': []
        }

        for msg in messages:
            try:
                success = self.send(
                    msg['to'],
                    msg['type'],
                    msg['payload']
                )

                if success:
                    results['sent'] += 1
                    results['details'].append({
                        'to': msg['to'],
                        'status': 'success'
                    })
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'to': msg['to'],
                        'status': 'failed'
                    })

            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'to': msg['to'],
                    'status': 'error',
                    'error': str(e)
                })

        return results

    def deduplicate_and_send(self,
                            messages: List[Dict],
                            key_func: callable = None) -> Dict:
        """
        Remove duplicate messages before sending

        Args:
            messages: List of messages
            key_func: Function to generate dedup key
                     Default: lambda msg: (msg['to'], msg['type'])

        Returns:
            Send results
        """
        if key_func is None:
            key_func = lambda msg: (msg['to'], msg['type'])

        # Deduplicate
        seen = set()
        unique_messages = []

        for msg in messages:
            key = key_func(msg)
            if key not in seen:
                seen.add(key)
                unique_messages.append(msg)

        duplicates_removed = len(messages) - len(unique_messages)

        result = self.send_batch(unique_messages)
        result['duplicates_removed'] = duplicates_removed

        return result

    def get_stats(self) -> Dict:
        """Get batch operation statistics"""
        compression_ratio = 0
        if self.stats['bytes_sent'] > 0:
            compression_ratio = self.stats['bytes_compressed'] / self.stats['bytes_sent']

        return {
            **self.stats,
            'compression_ratio': compression_ratio,
            'compression_savings_bytes': self.stats['bytes_sent'] - self.stats['bytes_compressed']
        }


# ============================================================================
# Compression Utilities
# ============================================================================

def compress_message(message: Dict) -> Dict:
    """Compress a message payload"""
    payload_json = json.dumps(message['payload'])
    payload_bytes = payload_json.encode('utf-8')

    compressed = gzip.compress(payload_bytes)
    compressed_b64 = base64.b64encode(compressed).decode('ascii')

    return {
        **message,
        'payload': {
            '_compressed': True,
            '_original_size': len(payload_bytes),
            '_data': compressed_b64
        }
    }


def decompress_message(message: Dict) -> Dict:
    """Decompress a message payload"""
    if message['payload'].get('_compressed'):
        compressed_b64 = message['payload']['_data']
        compressed = base64.b64decode(compressed_b64)
        decompressed = gzip.decompress(compressed)
        payload = json.loads(decompressed.decode('utf-8'))

        return {
            **message,
            'payload': payload
        }

    return message


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == '__main__':
    print("="*70)
    print("📦 Batch Operations Test")
    print("="*70)

    # Mock send function
    def mock_send(to, msg_type, payload):
        print(f"   → Sending {msg_type} to {to}")
        return True

    batch = BatchOperations(mock_send)

    # Test: Send to many
    print("\n1️⃣ Send to Multiple Recipients")
    result = batch.send_to_many(
        recipients=['browser', 'desktop', 'mobile'],
        msg_type='notification',
        payload={'text': 'Update available'}
    )
    print(f"   Result: {result['sent']} sent, {result['failed']} failed")

    # Test: Broadcast
    print("\n2️⃣ Broadcast to All")
    result = batch.broadcast(
        msg_type='alert',
        payload={'message': 'System maintenance in 10 minutes'}
    )
    print(f"   Broadcasted to {len(result['sent'])} clients")

    # Test: Compression
    print("\n3️⃣ Compression Test")
    large_payload = {'data': 'x' * 2000}  # 2KB payload

    print(f"   Original size: {len(json.dumps(large_payload))} bytes")

    batch.send_compressed(
        'browser',
        'data',
        large_payload,
        compression_threshold=1024
    )

    stats = batch.get_stats()
    print(f"   Compressed size: {stats['bytes_compressed']} bytes")
    print(f"   Savings: {stats['compression_savings_bytes']} bytes")

    # Test: Batch send
    print("\n4️⃣ Batch Send")
    messages = [
        {'to': 'browser', 'type': 'msg1', 'payload': {'a': 1}},
        {'to': 'desktop', 'type': 'msg2', 'payload': {'b': 2}},
        {'to': 'mobile', 'type': 'msg3', 'payload': {'c': 3}}
    ]

    result = batch.send_batch(messages)
    print(f"   Sent {result['sent']}/{result['total']} messages")

    # Test: Deduplication
    print("\n5️⃣ Deduplication")
    messages_with_dupes = [
        {'to': 'browser', 'type': 'update', 'payload': {}},
        {'to': 'browser', 'type': 'update', 'payload': {}},  # Duplicate
        {'to': 'desktop', 'type': 'update', 'payload': {}},
    ]

    result = batch.deduplicate_and_send(messages_with_dupes)
    print(f"   Removed {result['duplicates_removed']} duplicates")
    print(f"   Sent {result['sent']} unique messages")

    # Final stats
    print("\n📊 Total Stats:")
    for key, value in batch.get_stats().items():
        print(f"   {key}: {value}")
