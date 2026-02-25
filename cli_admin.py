#!/usr/bin/env python3
"""
CLI Admin Tool for Multi-Agent Bridge
Manage and monitor the system from command line
"""
import requests
import json
import argparse
from typing import Optional
from datetime import datetime
import sys


class BridgeAdmin:
    """
    Command-line administration tool

    Commands:
    - status: Show server status
    - messages: List recent messages
    - clients: List connected clients
    - send: Send a test message
    - health: Check health status
    - metrics: Show metrics
    - clear: Clear message queue
    - restart: Restart specific client
    """

    def __init__(self, server_url: str = "http://localhost:5001"):
        self.server_url = server_url.rstrip('/')

    def _request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request to server"""
        url = f"{self.server_url}{endpoint}"

        try:
            response = requests.request(method, url, timeout=10, **kwargs)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError:
            print(f"❌ Error: Cannot connect to server at {self.server_url}")
            print("   Make sure the server is running:")
            print("   python server_ws.py")
            sys.exit(1)

        except requests.exceptions.Timeout:
            print("❌ Error: Request timeout")
            sys.exit(1)

        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            sys.exit(1)

    def status(self):
        """Show server status"""
        data = self._request('GET', '/api/status')

        print("\n" + "="*70)
        print("🖥️  SERVER STATUS")
        print("="*70)
        print(f"Status: {'🟢 ONLINE' if data.get('status') == 'running' else '🔴 OFFLINE'}")
        print(f"Uptime: {self._format_uptime(data.get('uptime', 0))}")
        print(f"Total Messages: {data.get('total_messages', 0):,}")
        print(f"Queue Size: {data.get('queue_size', 0)}")
        print("="*70 + "\n")

    def messages(self, limit: int = 20, to: Optional[str] = None, from_: Optional[str] = None):
        """List recent messages"""
        params = {'limit': limit}
        if to:
            params['to'] = to
        if from_:
            params['from'] = from_

        data = self._request('GET', '/api/messages', params=params)
        messages = data.get('messages', [])

        print("\n" + "="*70)
        print(f"📨 RECENT MESSAGES ({len(messages)})")
        print("="*70)

        if not messages:
            print("No messages found\n")
            return

        for msg in messages:
            timestamp = self._format_timestamp(msg.get('timestamp'))
            from_client = msg.get('from', '?')
            to_client = msg.get('to', '?')
            msg_type = msg.get('type', '?')

            print(f"\n[{timestamp}] {from_client} → {to_client}")
            print(f"Type: {msg_type}")

            payload = msg.get('payload', {})
            if isinstance(payload, dict):
                if 'text' in payload:
                    text = payload['text']
                    preview = text[:100] + '...' if len(text) > 100 else text
                    print(f"Text: {preview}")
                elif 'response' in payload:
                    resp = payload['response']
                    preview = resp[:100] + '...' if len(resp) > 100 else resp
                    print(f"Response: {preview}")

        print("\n" + "="*70 + "\n")

    def clients(self):
        """List connected clients"""
        # Try streaming endpoint first
        try:
            data = self._request('GET', '/stream/clients')
            clients = data.get('clients', [])

            print("\n" + "="*70)
            print(f"👥 CONNECTED CLIENTS ({len(clients)})")
            print("="*70)

            if not clients:
                print("No clients connected\n")
                return

            for client in clients:
                client_id = client.get('client_id', '?')
                connected_at = self._format_timestamp(client.get('connected_at', ''))
                subscriptions = client.get('subscriptions', [])
                queue_size = client.get('queue_size', 0)

                print(f"\n🔹 {client_id}")
                print(f"   Connected: {connected_at}")
                print(f"   Queue: {queue_size} messages")
                if subscriptions:
                    print(f"   Subscribed: {', '.join(subscriptions)}")

            print("\n" + "="*70 + "\n")

        except Exception:
            print("\n" + "="*70)
            print("👥 CONNECTED CLIENTS")
            print("="*70)
            print("Client tracking not available (requires SSE module)\n")

    def send(self, to: str, msg_type: str = 'test', text: str = 'Test message'):
        """Send test message"""
        payload = {
            'from': 'admin',
            'to': to,
            'type': msg_type,
            'payload': {'text': text},
            'timestamp': datetime.now().isoformat()
        }

        data = self._request('POST', '/api/send', json=payload)

        print(f"\n✅ Message sent to '{to}'")
        print(f"   Type: {msg_type}")
        print(f"   Text: {text[:100]}...")
        print()

    def health(self):
        """Check health status"""
        try:
            data = self._request('GET', '/health/status')

            print("\n" + "="*70)
            print("🏥 HEALTH STATUS")
            print("="*70)

            overall = data.get('status', 'unknown')
            emoji = {'healthy': '🟢', 'degraded': '🟡', 'unhealthy': '🔴'}.get(overall, '⚪')

            print(f"Overall: {emoji} {overall.upper()}")

            # Liveness checks
            liveness = data.get('liveness', {})
            print(f"\nLiveness: {liveness.get('status', '?').upper()}")
            for name, result in liveness.get('checks', {}).items():
                status = '✅' if result.get('passed') else '❌'
                print(f"  {status} {name}: {result.get('message', '?')}")

            # Readiness checks
            readiness = data.get('readiness', {})
            print(f"\nReadiness: {readiness.get('status', '?').upper()}")
            for name, result in readiness.get('checks', {}).items():
                status = '✅' if result.get('passed') else '❌'
                print(f"  {status} {name}: {result.get('message', '?')}")

            print("\n" + "="*70 + "\n")

        except Exception:
            print("\n❌ Health check not available (requires health_checks module)\n")

    def metrics(self):
        """Show metrics summary"""
        try:
            # Get Prometheus metrics and parse
            response = requests.get(f"{self.server_url}/metrics", timeout=5)
            text = response.text

            print("\n" + "="*70)
            print("📊 METRICS SUMMARY")
            print("="*70)

            # Parse key metrics
            for line in text.split('\n'):
                if line.startswith('#') or not line.strip():
                    continue

                # Extract metric name and value
                parts = line.split()
                if len(parts) >= 2:
                    metric = parts[0]
                    value = parts[-1]

                    # Show important metrics
                    if any(key in metric for key in ['total', 'count', 'rate', 'percent']):
                        print(f"{metric}: {value}")

            print("\n" + "="*70 + "\n")

        except Exception:
            print("\n❌ Metrics not available (requires enhanced_metrics module)\n")

    def clear(self):
        """Clear message queue"""
        confirm = input("⚠️  Clear all messages? This cannot be undone. [y/N]: ")

        if confirm.lower() != 'y':
            print("Cancelled\n")
            return

        try:
            self._request('POST', '/admin/emergency/clear')
            print("\n✅ Message queue cleared\n")
        except Exception:
            print("\n❌ Clear not available (requires admin API)\n")

    def restart(self, client_id: str):
        """Restart specific client connection"""
        confirm = input(f"⚠️  Disconnect client '{client_id}'? [y/N]: ")

        if confirm.lower() != 'y':
            print("Cancelled\n")
            return

        try:
            self._request('DELETE', f'/admin/connections/{client_id}')
            print(f"\n✅ Client '{client_id}' disconnected (will auto-reconnect)\n")
        except Exception:
            print("\n❌ Restart not available (requires admin API)\n")

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def _format_timestamp(self, ts: str) -> str:
        """Format timestamp"""
        if not ts:
            return "?"

        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return ts


def main():
    parser = argparse.ArgumentParser(
        description='Multi-Agent Bridge CLI Admin Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show server status
  python cli_admin.py status

  # List recent messages
  python cli_admin.py messages --limit 50

  # List messages to specific client
  python cli_admin.py messages --to browser

  # List connected clients
  python cli_admin.py clients

  # Send test message
  python cli_admin.py send browser --text "Hello from admin"

  # Check health
  python cli_admin.py health

  # View metrics
  python cli_admin.py metrics

  # Clear message queue (dangerous!)
  python cli_admin.py clear

  # Restart client connection
  python cli_admin.py restart desktop

  # Custom server URL
  python cli_admin.py --server http://192.168.1.100:5001 status
        """
    )

    parser.add_argument('--server', type=str, default='http://localhost:5001',
                       help='Server URL (default: http://localhost:5001)')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # status command
    subparsers.add_parser('status', help='Show server status')

    # messages command
    msg_parser = subparsers.add_parser('messages', help='List recent messages')
    msg_parser.add_argument('--limit', type=int, default=20, help='Number of messages')
    msg_parser.add_argument('--to', type=str, help='Filter by recipient')
    msg_parser.add_argument('--from', dest='from_', type=str, help='Filter by sender')

    # clients command
    subparsers.add_parser('clients', help='List connected clients')

    # send command
    send_parser = subparsers.add_parser('send', help='Send test message')
    send_parser.add_argument('to', type=str, help='Recipient client ID')
    send_parser.add_argument('--type', type=str, default='test', help='Message type')
    send_parser.add_argument('--text', type=str, default='Test message', help='Message text')

    # health command
    subparsers.add_parser('health', help='Check health status')

    # metrics command
    subparsers.add_parser('metrics', help='Show metrics summary')

    # clear command
    subparsers.add_parser('clear', help='Clear message queue (dangerous!)')

    # restart command
    restart_parser = subparsers.add_parser('restart', help='Restart client connection')
    restart_parser.add_argument('client_id', type=str, help='Client ID to restart')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    admin = BridgeAdmin(server_url=args.server)

    # Execute command
    if args.command == 'status':
        admin.status()

    elif args.command == 'messages':
        admin.messages(limit=args.limit, to=args.to, from_=args.from_)

    elif args.command == 'clients':
        admin.clients()

    elif args.command == 'send':
        admin.send(to=args.to, msg_type=args.type, text=args.text)

    elif args.command == 'health':
        admin.health()

    elif args.command == 'metrics':
        admin.metrics()

    elif args.command == 'clear':
        admin.clear()

    elif args.command == 'restart':
        admin.restart(args.client_id)


if __name__ == '__main__':
    main()
