#!/usr/bin/env python3
"""
Enhanced WebSocket Client with Collaboration Support
Extends code_client_ws.py with collaboration room features

New features:
- Join/create collaboration rooms
- Enhanced voting (consensus, veto, weighted)
- Sub-channels
- File sharing
- Code execution
- Kanban board integration
"""
import json
import base64
from typing import Optional, Dict, List, Callable
from code_client_ws import CodeClientWS


class CodeClientCollab(CodeClientWS):
    """
    WebSocket client with collaboration room support

    Extends base WebSocket client with:
    - Room creation/joining
    - Voting and decisions
    - File upload/download
    - Code execution
    - Channel management
    """

    def __init__(self, client_id: str, server_url: str = 'ws://localhost:5001'):
        super().__init__(client_id, server_url)
        self.current_room: Optional[str] = None
        self.room_handlers: Dict[str, List[Callable]] = {}

    # ========================================================================
    # Room Management
    # ========================================================================

    def create_room(self, topic: str, role: str = "coordinator") -> str:
        """
        Create new collaboration room

        Args:
            topic: Room topic
            role: Your role (coordinator, researcher, coder, reviewer, etc.)

        Returns:
            Room ID
        """
        response = self._send_collab({
            'action': 'create_room',
            'topic': topic,
            'role': role
        })

        if response['status'] == 'success':
            self.current_room = response['room_id']
            return response['room_id']
        else:
            raise Exception(response.get('error', 'Failed to create room'))

    def join_room(self, room_id: str, role: str = "participant", vote_weight: float = 1.0):
        """
        Join existing collaboration room

        Args:
            room_id: Room ID
            role: Your role
            vote_weight: Vote weight (for weighted voting)

        Returns:
            Success status
        """
        response = self._send_collab({
            'action': 'join_room',
            'room_id': room_id,
            'role': role,
            'vote_weight': vote_weight
        })

        if response['status'] == 'success':
            self.current_room = room_id
            return True
        else:
            raise Exception(response.get('error', 'Failed to join room'))

    def leave_room(self, room_id: Optional[str] = None):
        """Leave collaboration room"""
        room_id = room_id or self.current_room
        if not room_id:
            raise Exception("Not in a room")

        response = self._send_collab({
            'action': 'leave_room',
            'room_id': room_id
        })

        if room_id == self.current_room:
            self.current_room = None

    def list_rooms(self) -> List[Dict]:
        """List all collaboration rooms"""
        response = self._send_collab({
            'action': 'list_rooms'
        })

        if response['status'] == 'success':
            return response['rooms']
        else:
            return []

    def get_summary(self, room_id: Optional[str] = None) -> Dict:
        """Get room summary"""
        room_id = room_id or self.current_room
        if not room_id:
            raise Exception("Not in a room")

        response = self._send_collab({
            'action': 'get_summary',
            'room_id': room_id
        })

        if response['status'] == 'success':
            return response['summary']
        else:
            raise Exception(response.get('error', 'Failed to get summary'))

    # ========================================================================
    # Messaging
    # ========================================================================

    def send_to_room(self, text: str, channel: str = "main", reply_to: Optional[str] = None):
        """
        Send message to room

        Args:
            text: Message text
            channel: Target channel
            reply_to: Optional message ID to reply to
        """
        if not self.current_room:
            raise Exception("Not in a room")

        response = self._send_collab({
            'action': 'send_message',
            'room_id': self.current_room,
            'text': text,
            'channel': channel,
            'reply_to': reply_to
        })

        if response['status'] != 'success':
            raise Exception(response.get('error', 'Failed to send message'))

    def get_messages(self, channel: str = "main", limit: int = 100) -> List[Dict]:
        """Get room messages"""
        if not self.current_room:
            raise Exception("Not in a room")

        response = self._send_collab({
            'action': 'get_messages',
            'room_id': self.current_room,
            'channel': channel,
            'limit': limit
        })

        if response['status'] == 'success':
            return response['messages']
        else:
            return []

    # ========================================================================
    # Channels
    # ========================================================================

    def create_channel(self, name: str, topic: str = "") -> str:
        """Create sub-channel"""
        if not self.current_room:
            raise Exception("Not in a room")

        response = self._send_collab({
            'action': 'create_channel',
            'room_id': self.current_room,
            'name': name,
            'topic': topic
        })

        if response['status'] == 'success':
            return response['channel_id']
        else:
            raise Exception(response.get('error', 'Failed to create channel'))

    # ========================================================================
    # File Sharing
    # ========================================================================

    def upload_file(self, file_path: str, channel: str = "main") -> str:
        """
        Upload file to room

        Args:
            file_path: Path to file
            channel: Target channel

        Returns:
            File ID
        """
        if not self.current_room:
            raise Exception("Not in a room")

        # Read file
        with open(file_path, 'rb') as f:
            file_content = f.read()

        # Encode to base64
        file_content_base64 = base64.b64encode(file_content).decode('utf-8')

        # Get file name
        import os
        file_name = os.path.basename(file_path)

        # Detect content type
        content_type = 'application/octet-stream'
        if file_name.endswith('.py'):
            content_type = 'text/x-python'
        elif file_name.endswith('.js'):
            content_type = 'text/javascript'
        elif file_name.endswith('.md'):
            content_type = 'text/markdown'
        elif file_name.endswith('.json'):
            content_type = 'application/json'

        response = self._send_collab({
            'action': 'upload_file',
            'room_id': self.current_room,
            'file_name': file_name,
            'file_content': file_content_base64,
            'content_type': content_type,
            'channel': channel
        })

        if response['status'] == 'success':
            return response['file_id']
        else:
            raise Exception(response.get('error', 'Failed to upload file'))

    # ========================================================================
    # Code Execution
    # ========================================================================

    def execute_code(self, code: str, language: str = "python", channel: str = "main") -> Dict:
        """
        Execute code in sandbox

        Args:
            code: Code to execute
            language: python, javascript, or bash
            channel: Channel to post results

        Returns:
            Execution result with output, error, exit_code, execution_time_ms
        """
        if not self.current_room:
            raise Exception("Not in a room")

        response = self._send_collab({
            'action': 'execute_code',
            'room_id': self.current_room,
            'code': code,
            'language': language,
            'channel': channel
        })

        if response['status'] == 'success':
            return {
                'execution_id': response['execution_id'],
                'output': response['output'],
                'error': response['error'],
                'exit_code': response['exit_code'],
                'execution_time_ms': response['execution_time_ms']
            }
        else:
            raise Exception(response.get('error', 'Failed to execute code'))

    # ========================================================================
    # Voting & Decisions
    # ========================================================================

    def propose_decision(self, text: str, vote_type: str = "simple_majority",
                        required_votes: Optional[int] = None) -> str:
        """
        Propose decision

        Args:
            text: Decision text
            vote_type: simple_majority, consensus, quorum, weighted
            required_votes: Required votes (for quorum)

        Returns:
            Decision ID
        """
        if not self.current_room:
            raise Exception("Not in a room")

        response = self._send_collab({
            'action': 'propose_decision',
            'room_id': self.current_room,
            'text': text,
            'vote_type': vote_type,
            'required_votes': required_votes
        })

        if response['status'] == 'success':
            return response['decision_id']
        else:
            raise Exception(response.get('error', 'Failed to propose decision'))

    def vote(self, decision_id: str, approve: bool = True, veto: bool = False):
        """
        Vote on decision

        Args:
            decision_id: Decision ID
            approve: True to approve, False to abstain
            veto: True to veto (blocks decision)
        """
        if not self.current_room:
            raise Exception("Not in a room")

        response = self._send_collab({
            'action': 'vote',
            'room_id': self.current_room,
            'decision_id': decision_id,
            'approve': approve,
            'veto': veto
        })

        if response['status'] != 'success':
            raise Exception(response.get('error', 'Failed to vote'))

    # ========================================================================
    # Internal
    # ========================================================================

    def _send_collab(self, payload: Dict) -> Dict:
        """Send collaboration message and get response"""
        message = {
            'type': 'collab',
            **payload
        }

        # Send via WebSocket
        self.ws.send(json.dumps(message))

        # Wait for response
        import time
        timeout = 10
        start = time.time()

        while time.time() - start < timeout:
            try:
                data = self.ws.receive(timeout=1)
                if data:
                    response = json.loads(data)
                    if response.get('type') == 'collab_response':
                        return response['response']
            except:
                pass

        raise Exception("Timeout waiting for collab response")


# Example usage
if __name__ == '__main__':
    print("=" * 80)
    print("🤝 Enhanced Client with Collaboration Support")
    print("=" * 80)

    client = CodeClientCollab("claude-code")

    print("\n✅ Features available:")
    print("   - create_room(topic, role)")
    print("   - join_room(room_id, role)")
    print("   - send_to_room(text, channel)")
    print("   - create_channel(name, topic)")
    print("   - upload_file(file_path, channel)")
    print("   - execute_code(code, language)")
    print("   - propose_decision(text, vote_type)")
    print("   - vote(decision_id, approve)")
    print("   - get_summary()")
    print("   - list_rooms()")

    print("\n📝 Example:")
    print("""
    # Create room
    room_id = client.create_room("Build Trading Bot", role="coordinator")

    # Create channel
    code_ch = client.create_channel("code", "Development")

    # Send message
    client.send_to_room("Let's start coding!", channel=code_ch)

    # Execute code
    result = client.execute_code("print('Hello!')", language="python")
    print(result['output'])  # "Hello!"

    # Propose decision
    dec_id = client.propose_decision("Use FastAPI", vote_type="consensus")

    # Vote
    client.vote(dec_id, approve=True)
    """)

    print("\n✅ Client ready for collaboration!")
