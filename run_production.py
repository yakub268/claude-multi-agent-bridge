#!/usr/bin/env python3
"""
Production server launcher (Windows-compatible)
Uses waitress for production WSGI serving
"""
import sys
import logging

logger = logging.getLogger(__name__)

def main():
    print("=" * 80)
    print("🚀 CLAUDE MULTI-AGENT BRIDGE - Production Server")
    print("=" * 80)
    print()

    try:
        from waitress import serve
        from server_ws import app

        print("Server Configuration:")
        print("  Host: 0.0.0.0")
        print("  Port: 5001")
        print("  Mode: Production (Waitress)")
        print("  WebSocket: Enabled")
        print("  Collaboration: Enabled")
        print()
        print("Starting server...")
        print("=" * 80)
        print()

        # Serve with waitress
        serve(
            app,
            host='0.0.0.0',
            port=5001,
            threads=8,  # Thread pool size
            channel_timeout=120,
            cleanup_interval=30,
            send_bytes=65536
        )

    except ImportError:
        print()
        print("ERROR: waitress not installed")
        print()
        print("Install with:")
        print("  pip install waitress")
        print()
        print("Or use development server:")
        print("  python server_ws.py")
        print()
        sys.exit(1)

    except KeyboardInterrupt:
        print()
        print("Server stopped by user")
        sys.exit(0)

    except Exception as e:
        print()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
