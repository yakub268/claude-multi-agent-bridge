#!/usr/bin/env python3
"""
Simple WebSocket Server for Think-Tank Testing
Minimal server to demonstrate think-tank features without dependencies
"""
import asyncio
import websockets
import json
import logging
from datetime import datetime, timezone

# Import collaboration bridge
from collab_ws_integration import CollabWSBridge

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Collaboration bridge
collab_bridge = CollabWSBridge()


async def handle_client(websocket, path):
    """Handle WebSocket client connection"""
    client_id = None

    try:
        # Register connection
        client_id = f"client-{id(websocket)}"
        collab_bridge.register_ws_connection(websocket, client_id)
        logger.info(f"✅ Client connected: {client_id}")

        # Message loop
        async for message in websocket:
            try:
                data = json.loads(message)

                # Handle collaboration actions
                if data.get("type") == "collab":
                    response = collab_bridge.handle_collab_message(
                        websocket, data.get("from", client_id), data
                    )
                else:
                    response = {"status": "error", "error": "Unknown message type"}

                # Send response
                await websocket.send(json.dumps(response))

            except json.JSONDecodeError:
                await websocket.send(
                    json.dumps({"status": "error", "error": "Invalid JSON"})
                )
            except Exception as e:
                logger.error(f"Message error: {e}")
                await websocket.send(json.dumps({"status": "error", "error": str(e)}))

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Connection error: {e}")
    finally:
        if client_id:
            collab_bridge.unregister_ws_connection(websocket)


async def main():
    """Start WebSocket server"""
    server = await websockets.serve(
        handle_client, "localhost", 5001, ping_interval=30, ping_timeout=10
    )

    logger.info("=" * 80)
    logger.info("🚀 WebSocket Think-Tank Server Running")
    logger.info("=" * 80)
    logger.info("   URL: ws://localhost:5001")
    logger.info("   Features: Critique, Debate, Amendments, Alternatives")
    logger.info("   Press Ctrl+C to stop")
    logger.info("=" * 80)

    await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Server stopped")
