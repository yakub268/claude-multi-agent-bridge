#!/usr/bin/env python3
"""
WebSocket Integration for Enhanced Collaboration Room
Bridges collaboration rooms with WebSocket server for real-time multi-Claude coordination

Usage:
    # Server side - add to server_ws.py
    from collab_ws_integration import CollabWSBridge
    bridge = CollabWSBridge()

    # Client side
    client.join_collab_room("room-id", role="coder")
    client.send_to_room("room-id", "Let's build this!")
"""
import json
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timezone
from collaboration_enhanced import (
    EnhancedCollaborationHub,
    EnhancedCollaborationRoom,
    MemberRole,
    VoteType,
    CodeLanguage
)

logger = logging.getLogger(__name__)


class CollabWSBridge:
    """
    Bridge between WebSocket server and collaboration rooms

    Features:
    - Room creation/discovery via WebSocket
    - Real-time message broadcasting to all room members
    - File transfer over WebSocket
    - Code execution results pushed instantly
    - Vote updates in real-time
    - Auto-join on first message
    """

    def __init__(self):
        self.hub = EnhancedCollaborationHub()
        self.ws_connections: Dict[str, Any] = {}  # ws -> client_id
        self.client_rooms: Dict[str, set] = {}  # client_id -> set of room_ids

    def register_ws_connection(self, ws, client_id: str):
        """Register WebSocket connection"""
        self.ws_connections[ws] = client_id
        if client_id not in self.client_rooms:
            self.client_rooms[client_id] = set()

    def unregister_ws_connection(self, ws):
        """Unregister WebSocket connection"""
        if ws in self.ws_connections:
            del self.ws_connections[ws]

    def handle_collab_message(self, ws, client_id: str, message: Dict) -> Dict:
        """
        Handle collaboration-related WebSocket message

        Message types:
        - create_room: Create new collaboration room
        - join_room: Join existing room
        - leave_room: Leave room
        - send_message: Send message to room
        - create_channel: Create sub-channel
        - upload_file: Share file
        - execute_code: Run code
        - propose_decision: Propose decision
        - vote: Vote on decision
        - get_messages: Get room messages
        - list_rooms: List all rooms
        - send_critique: Send structured critique (THINK-TANK)
        - propose_alternative: Propose alternative decision (THINK-TANK)
        - add_debate_argument: Add pro/con argument (THINK-TANK)
        - get_debate_summary: Get debate summary (THINK-TANK)
        - propose_amendment: Propose amendment to decision (THINK-TANK)
        - accept_amendment: Accept amendment (THINK-TANK)

        Args:
            ws: WebSocket connection
            client_id: Client identifier
            message: Message payload

        Returns:
            Response dictionary
        """
        action = message.get('action')

        try:
            if action == 'create_room':
                return self._create_room(client_id, message)

            elif action == 'join_room':
                return self._join_room(ws, client_id, message)

            elif action == 'leave_room':
                return self._leave_room(client_id, message)

            elif action == 'send_message':
                return self._send_message(client_id, message)

            elif action == 'create_channel':
                return self._create_channel(client_id, message)

            elif action == 'upload_file':
                return self._upload_file(client_id, message)

            elif action == 'execute_code':
                return self._execute_code(client_id, message)

            elif action == 'propose_decision':
                return self._propose_decision(client_id, message)

            elif action == 'vote':
                return self._vote(client_id, message)

            elif action == 'get_messages':
                return self._get_messages(client_id, message)

            elif action == 'list_rooms':
                return self._list_rooms()

            elif action == 'get_summary':
                return self._get_summary(message)

            # THINK-TANK FEATURES
            elif action == 'send_critique':
                return self._send_critique(client_id, message)

            elif action == 'propose_alternative':
                return self._propose_alternative(client_id, message)

            elif action == 'add_debate_argument':
                return self._add_debate_argument(client_id, message)

            elif action == 'get_debate_summary':
                return self._get_debate_summary(message)

            elif action == 'propose_amendment':
                return self._propose_amendment(client_id, message)

            elif action == 'accept_amendment':
                return self._accept_amendment(message)

            else:
                return {
                    'status': 'error',
                    'error': f'Unknown action: {action}'
                }

        except Exception as e:
            logger.error(f"Collab message error: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _create_room(self, client_id: str, message: Dict) -> Dict:
        """Create new collaboration room"""
        topic = message.get('topic', 'General Collaboration')
        room_id = self.hub.create_room(topic)

        # Auto-join creator
        room = self.hub.get_room(room_id)
        role = MemberRole[message.get('role', 'COORDINATOR').upper()]
        room.join(client_id, role)

        if client_id not in self.client_rooms:
            self.client_rooms[client_id] = set()
        self.client_rooms[client_id].add(room_id)

        return {
            'status': 'success',
            'room_id': room_id,
            'topic': topic
        }

    def _join_room(self, ws, client_id: str, message: Dict) -> Dict:
        """Join collaboration room"""
        room_id = message.get('room_id')
        room = self.hub.get_room(room_id)

        if not room:
            return {
                'status': 'error',
                'error': f'Room {room_id} not found'
            }

        role = MemberRole[message.get('role', 'PARTICIPANT').upper()]
        vote_weight = message.get('vote_weight', 1.0)

        success = room.join(client_id, role, vote_weight)

        if success:
            if client_id not in self.client_rooms:
                self.client_rooms[client_id] = set()
            self.client_rooms[client_id].add(room_id)

            # Register callback to broadcast messages
            def on_message(room_message):
                self._broadcast_to_room(room_id, {
                    'type': 'room_message',
                    'room_id': room_id,
                    'message': {
                        'id': room_message.id,
                        'from': room_message.from_client,
                        'text': room_message.text,
                        'timestamp': room_message.timestamp.isoformat(),
                        'type': room_message.type,
                        'channel': room_message.channel
                    }
                })

            room.on_message(on_message)

        return {
            'status': 'success' if success else 'already_joined',
            'room_id': room_id,
            'members': len([m for m in room.members.values() if m.active])
        }

    def _leave_room(self, client_id: str, message: Dict) -> Dict:
        """Leave collaboration room"""
        room_id = message.get('room_id')
        room = self.hub.get_room(room_id)

        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        room.leave(client_id)

        if client_id in self.client_rooms:
            self.client_rooms[client_id].discard(room_id)

        return {'status': 'success'}

    def _send_message(self, client_id: str, message: Dict) -> Dict:
        """Send message to room"""
        room_id = message.get('room_id')
        text = message.get('text')
        channel = message.get('channel', 'main')
        reply_to = message.get('reply_to')

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        room_msg = room.send_message(
            client_id,
            text,
            reply_to=reply_to,
            channel=channel
        )

        return {
            'status': 'success',
            'message_id': room_msg.id,
            'timestamp': room_msg.timestamp.isoformat()
        }

    def _create_channel(self, client_id: str, message: Dict) -> Dict:
        """Create sub-channel"""
        room_id = message.get('room_id')
        name = message.get('name')
        topic = message.get('topic', '')

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        channel_id = room.create_channel(name, topic, client_id)

        return {
            'status': 'success',
            'channel_id': channel_id
        }

    def _upload_file(self, client_id: str, message: Dict) -> Dict:
        """Upload file to room"""
        room_id = message.get('room_id')
        file_name = message.get('file_name')
        file_content_base64 = message.get('file_content')
        content_type = message.get('content_type', 'application/octet-stream')
        channel = message.get('channel', 'main')

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        # Decode base64
        import base64
        file_content = base64.b64decode(file_content_base64)

        file_id = room.upload_file(
            client_id,
            file_name,
            file_content,
            content_type,
            channel
        )

        return {
            'status': 'success',
            'file_id': file_id,
            'size': len(file_content)
        }

    def _execute_code(self, client_id: str, message: Dict) -> Dict:
        """Execute code in sandbox"""
        room_id = message.get('room_id')
        code = message.get('code')
        language = CodeLanguage[message.get('language', 'PYTHON').upper()]
        channel = message.get('channel', 'main')

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        execution = room.execute_code(client_id, code, language, channel)

        return {
            'status': 'success',
            'execution_id': execution.id,
            'output': execution.output,
            'error': execution.error,
            'exit_code': execution.exit_code,
            'execution_time_ms': execution.execution_time_ms
        }

    def _propose_decision(self, client_id: str, message: Dict) -> Dict:
        """Propose decision"""
        room_id = message.get('room_id')
        text = message.get('text')
        vote_type = VoteType[message.get('vote_type', 'SIMPLE_MAJORITY').upper()]
        required_votes = message.get('required_votes')

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        decision_id = room.propose_decision(
            client_id,
            text,
            vote_type,
            required_votes
        )

        return {
            'status': 'success',
            'decision_id': decision_id
        }

    def _vote(self, client_id: str, message: Dict) -> Dict:
        """Vote on decision"""
        room_id = message.get('room_id')
        decision_id = message.get('decision_id')
        approve = message.get('approve', True)
        veto = message.get('veto', False)

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        room.vote(decision_id, client_id, approve, veto)

        return {'status': 'success'}

    def _get_messages(self, client_id: str, message: Dict) -> Dict:
        """Get room messages"""
        room_id = message.get('room_id')
        channel = message.get('channel', 'main')
        limit = message.get('limit', 100)

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        messages = room.get_messages(channel, limit)

        return {
            'status': 'success',
            'messages': [
                {
                    'id': msg.id,
                    'from': msg.from_client,
                    'text': msg.text,
                    'timestamp': msg.timestamp.isoformat(),
                    'type': msg.type,
                    'channel': msg.channel
                }
                for msg in messages
            ]
        }

    def _list_rooms(self) -> Dict:
        """List all rooms"""
        return {
            'status': 'success',
            'rooms': self.hub.list_rooms()
        }

    def _get_summary(self, message: Dict) -> Dict:
        """Get room summary"""
        room_id = message.get('room_id')
        room = self.hub.get_room(room_id)

        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        return {
            'status': 'success',
            'summary': room.get_summary()
        }

    def _broadcast_to_room(self, room_id: str, payload: Dict):
        """Broadcast message to all members of a room"""
        room = self.hub.get_room(room_id)
        if not room:
            return

        # Find all WebSocket connections for room members
        for ws, client_id in self.ws_connections.items():
            if client_id in room.members and room.members[client_id].active:
                try:
                    ws.send(json.dumps(payload))
                except Exception as e:
                    logger.error(f"Broadcast error to {client_id}: {e}")

    # THINK-TANK ACTION HANDLERS

    def _send_critique(self, client_id: str, message: Dict) -> Dict:
        """Send structured critique"""
        room_id = message.get('room_id')
        target_message_id = message.get('target_message_id')
        critique_text = message.get('critique_text')
        severity = message.get('severity', 'suggestion')
        channel = message.get('channel', 'main')

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        critique_msg = room.send_critique(
            client_id,
            target_message_id,
            critique_text,
            severity,
            channel
        )

        return {
            'status': 'success',
            'critique_id': critique_msg.id,
            'timestamp': critique_msg.timestamp.isoformat()
        }

    def _propose_alternative(self, client_id: str, message: Dict) -> Dict:
        """Propose alternative to decision"""
        room_id = message.get('room_id')
        original_decision_id = message.get('original_decision_id')
        alternative_text = message.get('alternative_text')
        vote_type_str = message.get('vote_type')
        channel = message.get('channel', 'main')

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        # Parse vote type if provided
        vote_type = None
        if vote_type_str:
            try:
                vote_type = VoteType[vote_type_str.upper()]
            except KeyError:
                return {'status': 'error', 'error': f'Invalid vote_type: {vote_type_str}'}

        alt_id = room.propose_alternative(
            client_id,
            original_decision_id,
            alternative_text,
            vote_type,
            channel
        )

        return {
            'status': 'success',
            'alternative_id': alt_id
        }

    def _add_debate_argument(self, client_id: str, message: Dict) -> Dict:
        """Add debate argument"""
        room_id = message.get('room_id')
        decision_id = message.get('decision_id')
        position = message.get('position')  # "pro" or "con"
        argument_text = message.get('argument_text')
        evidence = message.get('evidence', [])

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        arg_id = room.add_debate_argument(
            client_id,
            decision_id,
            position,
            argument_text,
            evidence
        )

        return {
            'status': 'success',
            'argument_id': arg_id
        }

    def _get_debate_summary(self, message: Dict) -> Dict:
        """Get debate summary"""
        room_id = message.get('room_id')
        decision_id = message.get('decision_id')

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        summary = room.get_debate_summary(decision_id)

        # Convert DebateArgument objects to dicts
        return {
            'status': 'success',
            'debate': {
                'pro': [
                    {
                        'id': arg.id,
                        'from': arg.from_client,
                        'text': arg.argument_text,
                        'evidence': arg.supporting_evidence,
                        'timestamp': arg.timestamp.isoformat()
                    }
                    for arg in summary['pro']
                ],
                'con': [
                    {
                        'id': arg.id,
                        'from': arg.from_client,
                        'text': arg.argument_text,
                        'evidence': arg.supporting_evidence,
                        'timestamp': arg.timestamp.isoformat()
                    }
                    for arg in summary['con']
                ],
                'total_pro': summary['total_pro'],
                'total_con': summary['total_con']
            }
        }

    def _propose_amendment(self, client_id: str, message: Dict) -> Dict:
        """Propose amendment to decision"""
        room_id = message.get('room_id')
        decision_id = message.get('decision_id')
        amendment_text = message.get('amendment_text')

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        amend_id = room.propose_amendment(
            client_id,
            decision_id,
            amendment_text
        )

        return {
            'status': 'success',
            'amendment_id': amend_id
        }

    def _accept_amendment(self, message: Dict) -> Dict:
        """Accept amendment"""
        room_id = message.get('room_id')
        decision_id = message.get('decision_id')
        amendment_id = message.get('amendment_id')

        room = self.hub.get_room(room_id)
        if not room:
            return {'status': 'error', 'error': 'Room not found'}

        room.accept_amendment(decision_id, amendment_id)

        return {'status': 'success'}


# Example client extension
class CollabRoomClient:
    """
    Client-side helper for collaboration rooms
    Extends existing WebSocket client
    """

    def __init__(self, ws_client):
        self.ws = ws_client
        self.current_room: Optional[str] = None

    def create_room(self, topic: str, role: str = "coordinator") -> str:
        """Create and join new collaboration room"""
        response = self.ws.send_collab({
            'action': 'create_room',
            'topic': topic,
            'role': role
        })

        if response['status'] == 'success':
            self.current_room = response['room_id']
            return response['room_id']
        else:
            raise Exception(response.get('error', 'Failed to create room'))

    def join_room(self, room_id: str, role: str = "participant"):
        """Join existing room"""
        response = self.ws.send_collab({
            'action': 'join_room',
            'room_id': room_id,
            'role': role
        })

        if response['status'] == 'success':
            self.current_room = room_id

    def send(self, text: str, channel: str = "main"):
        """Send message to current room"""
        if not self.current_room:
            raise Exception("Not in a room")

        return self.ws.send_collab({
            'action': 'send_message',
            'room_id': self.current_room,
            'text': text,
            'channel': channel
        })

    def run_code(self, code: str, language: str = "python"):
        """Execute code in room"""
        if not self.current_room:
            raise Exception("Not in a room")

        return self.ws.send_collab({
            'action': 'execute_code',
            'room_id': self.current_room,
            'code': code,
            'language': language
        })

    def propose(self, text: str, vote_type: str = "simple_majority"):
        """Propose decision"""
        if not self.current_room:
            raise Exception("Not in a room")

        return self.ws.send_collab({
            'action': 'propose_decision',
            'room_id': self.current_room,
            'text': text,
            'vote_type': vote_type
        })

    def vote(self, decision_id: str, approve: bool = True):
        """Vote on decision"""
        if not self.current_room:
            raise Exception("Not in a room")

        return self.ws.send_collab({
            'action': 'vote',
            'room_id': self.current_room,
            'decision_id': decision_id,
            'approve': approve
        })


if __name__ == '__main__':
    print("=" * 80)
    print("🔗 WebSocket Collaboration Bridge - Ready")
    print("=" * 80)
    print("\nFeatures:")
    print("  ✅ Real-time room messaging")
    print("  ✅ File sharing over WebSocket")
    print("  ✅ Code execution with instant results")
    print("  ✅ Live voting and decision tracking")
    print("  ✅ Sub-channels for focused discussion")
    print("\nUsage:")
    print("  1. Integrate bridge into server_ws.py")
    print("  2. Clients use collab actions via WebSocket")
    print("  3. All room members get instant updates")
    print("\n✅ Bridge ready for integration")
