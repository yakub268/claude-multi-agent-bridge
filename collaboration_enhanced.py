#!/usr/bin/env python3
"""
Enhanced Collaboration Room
Implements improvements identified in collaborative brainstorming session

New features:
- Enhanced voting (consensus mode, veto, quorum)
- Sub-rooms/channels for focused discussions
- File sharing between Claudes
- Code execution sandbox
- Integration with WebSocket server
"""
import os
import time
import json
import uuid
import hashlib
import subprocess
import tempfile
import logging
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from collections import deque
from enum import Enum
from pathlib import Path


class SecurityError(Exception):
    """Raised when a security violation is detected"""
    pass


# Import persistence layer
try:
    from collab_persistence import CollabPersistence
    PERSISTENCE_ENABLED = True
except ImportError:
    PERSISTENCE_ENABLED = False


class MemberRole(Enum):
    """Claude member roles"""
    COORDINATOR = "coordinator"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    DOCUMENTER = "documenter"
    PARTICIPANT = "participant"


class VoteType(Enum):
    """Voting types"""
    SIMPLE_MAJORITY = "simple_majority"  # >50% approval
    CONSENSUS = "consensus"  # 100% approval (all must agree)
    QUORUM = "quorum"  # Minimum participation required
    WEIGHTED = "weighted"  # Votes weighted by role


class CodeLanguage(Enum):
    """Supported code execution languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"


@dataclass
class RoomMember:
    """Member of collaboration room"""
    client_id: str
    role: MemberRole = MemberRole.PARTICIPANT
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True
    contributions: int = 0
    vote_weight: float = 1.0  # For weighted voting


@dataclass
class RoomMessage:
    """Message in collaboration room"""
    id: str
    from_client: str
    text: str
    timestamp: datetime
    mentions: Set[str] = field(default_factory=set)
    reply_to: Optional[str] = None
    type: str = "message"
    channel: str = "main"  # Channel/sub-room
    attachments: List[Dict] = field(default_factory=list)
    critiques: List[str] = field(default_factory=list)  # Critique message IDs


@dataclass
class SharedFile:
    """File shared in room"""
    id: str
    name: str
    content: bytes
    uploaded_by: str
    uploaded_at: datetime
    size: int
    content_type: str
    channel: str = "main"


@dataclass
class CodeExecution:
    """Code execution result"""
    id: str
    code: str
    language: CodeLanguage
    executed_by: str
    executed_at: datetime
    output: str
    error: Optional[str] = None
    exit_code: int = 0
    execution_time_ms: float = 0


@dataclass
class EnhancedDecision:
    """Enhanced decision with advanced voting"""
    id: str
    text: str
    proposed_by: str
    proposed_at: datetime
    vote_type: VoteType
    required_votes: int  # For quorum
    approved_by: Set[str] = field(default_factory=set)
    vetoed_by: Set[str] = field(default_factory=set)
    abstained: Set[str] = field(default_factory=set)
    approved: bool = False
    vetoed: bool = False
    total_weight: float = 0  # For weighted voting
    alternatives: List[str] = field(default_factory=list)  # Alternative decision IDs
    amendments: List[Dict] = field(default_factory=list)  # Proposed amendments


@dataclass
class Critique:
    """Structured critique of a message or decision"""
    id: str
    target_message_id: str
    from_client: str
    critique_text: str
    severity: str  # "blocking", "major", "minor", "suggestion"
    timestamp: datetime
    resolved: bool = False


@dataclass
class DebateArgument:
    """Structured argument in debate"""
    id: str
    decision_id: str
    from_client: str
    position: str  # "pro" or "con"
    argument_text: str
    supporting_evidence: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CollaborationChannel:
    """
    Sub-channel for focused discussions
    Like Discord channels within a server
    """
    def __init__(self, channel_id: str, name: str, topic: str = ""):
        self.channel_id = channel_id
        self.name = name
        self.topic = topic
        self.messages = deque(maxlen=1000)
        self.members: Set[str] = set()
        self.created_at = datetime.now(timezone.utc)

    def add_message(self, message: RoomMessage):
        """Add message to channel"""
        self.messages.append(message)

    def get_messages(self, limit: int = 100) -> List[RoomMessage]:
        """Get recent messages"""
        return list(self.messages)[-limit:]


class EnhancedCollaborationRoom:
    """
    Enhanced collaboration room with voting, channels, files, code execution

    New features:
    - Enhanced voting (consensus, veto, quorum, weighted)
    - Sub-channels for focused discussions
    - File sharing between members
    - Code execution sandbox
    - Persistent storage ready
    """

    def __init__(self, room_id: str, topic: str = "General Collaboration",
                 persistence_enabled: bool = True,
                 max_total_file_size_mb: int = 100):
        self.room_id = room_id
        self.topic = topic
        self.members: Dict[str, RoomMember] = {}

        # Channels
        self.channels: Dict[str, CollaborationChannel] = {}
        self._create_channel("main", "Main Discussion")

        # Storage
        self.decisions: List[EnhancedDecision] = []
        self.tasks = []
        self.files: Dict[str, SharedFile] = {}
        self.code_executions: List[CodeExecution] = []
        self.critiques: List[Critique] = []
        self.debate_arguments: List[DebateArgument] = []

        # Memory management
        self.max_total_file_size = max_total_file_size_mb * 1024 * 1024  # Convert MB to bytes
        self._current_file_size = 0

        # Callbacks
        self.message_callbacks: List[Callable] = []
        self.created_at = datetime.now(timezone.utc)

        # Persistence layer
        self.persistence = None
        if persistence_enabled and PERSISTENCE_ENABLED:
            self.persistence = CollabPersistence()
            self.persistence.save_room(room_id, topic, self.created_at)

    def _create_channel(self, channel_id: str, name: str, topic: str = "") -> CollaborationChannel:
        """Create new channel"""
        channel = CollaborationChannel(channel_id, name, topic)
        self.channels[channel_id] = channel
        return channel

    def create_channel(self, name: str, topic: str = "", created_by: str = "") -> str:
        """
        Create sub-channel for focused discussion

        Args:
            name: Channel name
            topic: Channel topic
            created_by: Creator client ID

        Returns:
            Channel ID
        """
        channel_id = f"channel-{len(self.channels)}"
        channel = self._create_channel(channel_id, name, topic)

        # Broadcast creation
        self._broadcast_system_message(
            f"📺 Channel created: #{name} - {topic}",
            channel="main"
        )

        return channel_id

    def join_channel(self, client_id: str, channel_id: str):
        """Join a channel"""
        if channel_id not in self.channels:
            raise ValueError(f"Channel {channel_id} not found")

        self.channels[channel_id].members.add(client_id)

    def leave_channel(self, client_id: str, channel_id: str):
        """Leave a channel"""
        if channel_id in self.channels:
            self.channels[channel_id].members.discard(client_id)

    def join(self, client_id: str, role: MemberRole = MemberRole.PARTICIPANT,
            vote_weight: float = 1.0) -> bool:
        """
        Join the collaboration room

        Args:
            client_id: Client identifier
            role: Member role
            vote_weight: Weight for weighted voting

        Returns:
            True if joined successfully
        """
        if client_id in self.members:
            return False

        member = RoomMember(client_id=client_id, role=role, vote_weight=vote_weight)
        self.members[client_id] = member

        # Auto-join main channel
        self.join_channel(client_id, "main")

        # Persist member
        if self.persistence:
            self.persistence.save_member(
                self.room_id, client_id, role.value,
                member.joined_at, vote_weight
            )

        self._broadcast_system_message(
            f"🎉 {client_id} ({role.value}) joined the room"
        )

        return True

    def leave(self, client_id: str):
        """Leave the room"""
        if client_id in self.members:
            member = self.members[client_id]
            member.active = False

            self._broadcast_system_message(
                f"👋 {client_id} left the room"
            )

    def send_message(self, from_client: str, text: str,
                    reply_to: Optional[str] = None,
                    msg_type: str = "message",
                    channel: str = "main",
                    attachments: List[Dict] = None) -> RoomMessage:
        """
        Send message to channel

        Args:
            from_client: Sender
            text: Message text
            reply_to: Optional message ID to reply to
            msg_type: Message type
            channel: Target channel
            attachments: File attachments

        Returns:
            Room message
        """
        if from_client not in self.members:
            raise ValueError(f"Client {from_client} not in room")

        if channel not in self.channels:
            raise ValueError(f"Channel {channel} not found")

        # Extract @mentions
        mentions = self._extract_mentions(text)

        # Create message
        message = RoomMessage(
            id=str(uuid.uuid4()),
            from_client=from_client,
            text=text,
            timestamp=datetime.now(timezone.utc),
            mentions=mentions,
            reply_to=reply_to,
            type=msg_type,
            channel=channel,
            attachments=attachments or []
        )

        # Add to channel
        self.channels[channel].add_message(message)

        # Update contribution count
        self.members[from_client].contributions += 1

        # Persist message
        if self.persistence:
            self.persistence.save_message(
                message.id, self.room_id, from_client, text,
                message.timestamp, msg_type, channel, reply_to
            )

        # Trigger callbacks
        self._trigger_callbacks(message)

        return message

    def upload_file(self, client_id: str, file_name: str, file_content: bytes,
                   content_type: str = "application/octet-stream",
                   channel: str = "main") -> str:
        """
        Upload file to room

        Args:
            client_id: Uploader
            file_name: File name
            file_content: File bytes
            content_type: MIME type
            channel: Target channel

        Returns:
            File ID
        """
        if client_id not in self.members:
            raise ValueError(f"Client {client_id} not in room")

        # File size limit: 10MB
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
        if len(file_content) > MAX_FILE_SIZE:
            raise ValueError(
                f"File size {len(file_content)} bytes exceeds maximum allowed size of {MAX_FILE_SIZE} bytes (10MB). "
                f"File: {file_name}"
            )

        # Check total room file size limit (prevent memory leak from many files)
        if self._current_file_size + len(file_content) > self.max_total_file_size:
            # Try to evict oldest files first (LRU eviction)
            self._evict_oldest_files(len(file_content))

            # Check again after eviction
            if self._current_file_size + len(file_content) > self.max_total_file_size:
                raise ValueError(
                    f"Room file storage limit reached ({self.max_total_file_size / 1024 / 1024:.1f}MB). "
                    f"Current: {self._current_file_size / 1024 / 1024:.1f}MB, "
                    f"Attempted upload: {len(file_content) / 1024 / 1024:.1f}MB"
                )

        file_id = hashlib.sha256(file_content).hexdigest()[:16]

        shared_file = SharedFile(
            id=file_id,
            name=file_name,
            content=file_content,
            uploaded_by=client_id,
            uploaded_at=datetime.now(timezone.utc),
            size=len(file_content),
            content_type=content_type,
            channel=channel
        )

        self.files[file_id] = shared_file
        self._current_file_size += len(file_content)

        # Persist file
        if self.persistence:
            self.persistence.save_file(
                file_id, self.room_id, file_name, client_id,
                shared_file.uploaded_at, len(file_content),
                content_type, file_content, channel
            )

        # Announce upload
        self.send_message(
            client_id,
            f"📎 Uploaded file: {file_name} ({len(file_content)} bytes)",
            channel=channel,
            msg_type="file_upload",
            attachments=[{
                'file_id': file_id,
                'file_name': file_name,
                'size': len(file_content),
                'type': content_type
            }]
        )

        return file_id

    def download_file(self, file_id: str) -> Optional[SharedFile]:
        """Download file from room"""
        return self.files.get(file_id)

    def _evict_oldest_files(self, needed_bytes: int):
        """
        Evict oldest files to make room for new upload (LRU eviction)

        Args:
            needed_bytes: Bytes needed for new file
        """
        if not self.files:
            return

        # Sort files by upload time (oldest first)
        sorted_files = sorted(
            self.files.items(),
            key=lambda x: x[1].uploaded_at
        )

        freed_bytes = 0
        evicted_count = 0

        for file_id, shared_file in sorted_files:
            if freed_bytes >= needed_bytes:
                break

            # Remove file
            del self.files[file_id]
            self._current_file_size -= shared_file.size
            freed_bytes += shared_file.size
            evicted_count += 1

            # Announce eviction
            self._broadcast_system_message(
                f"🗑️ File evicted due to storage limits: {shared_file.name} ({shared_file.size} bytes)",
                channel="main"
            )

        if evicted_count > 0:
            logger = logging.getLogger(__name__)
            logger.info(
                f"Evicted {evicted_count} files from room {self.room_id}, "
                f"freed {freed_bytes / 1024 / 1024:.1f}MB"
            )

    def execute_code(self, client_id: str, code: str, language: CodeLanguage,
                    channel: str = "main") -> CodeExecution:
        """
        Execute code in sandbox

        Args:
            client_id: Executor
            code: Code to execute
            language: Programming language
            channel: Channel to post results

        Returns:
            Execution result
        """
        if client_id not in self.members:
            raise ValueError(f"Client {client_id} not in room")

        # SECURITY: Code execution disabled by default due to RCE risk
        # To enable, set ENABLE_CODE_EXECUTION=true environment variable
        # AND use Docker sandboxing (see deployment docs)
        import os
        if not os.getenv('ENABLE_CODE_EXECUTION', 'false').lower() == 'true':
            raise SecurityError(
                "Code execution is disabled for security reasons. "
                "This feature allows arbitrary code execution and poses "
                "critical security risks. To enable (NOT recommended for "
                "production), set ENABLE_CODE_EXECUTION=true and implement "
                "Docker sandboxing as described in DEPLOYMENT.md"
            )

        start_time = time.time()

        try:
            if language == CodeLanguage.PYTHON:
                output, error, exit_code = self._execute_python(code)
            elif language == CodeLanguage.JAVASCRIPT:
                output, error, exit_code = self._execute_javascript(code)
            elif language == CodeLanguage.BASH:
                output, error, exit_code = self._execute_bash(code)
            else:
                raise ValueError(f"Unsupported language: {language}")
        except Exception as e:
            output = ""
            error = str(e)
            exit_code = 1

        execution_time_ms = (time.time() - start_time) * 1000

        execution = CodeExecution(
            id=str(uuid.uuid4()),
            code=code,
            language=language,
            executed_by=client_id,
            executed_at=datetime.now(timezone.utc),
            output=output,
            error=error,
            exit_code=exit_code,
            execution_time_ms=execution_time_ms
        )

        self.code_executions.append(execution)

        # Post result to channel
        result_text = f"```{language.value}\n{code}\n```\n"
        if output:
            result_text += f"\n✅ Output:\n```\n{output}\n```"
        if error:
            result_text += f"\n❌ Error:\n```\n{error}\n```"
        result_text += f"\n⏱️ {execution_time_ms:.1f}ms"

        self.send_message(
            client_id,
            result_text,
            channel=channel,
            msg_type="code_execution"
        )

        return execution

    def _execute_python(self, code: str) -> tuple:
        """Execute Python code in sandbox"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=30  # 30 seconds (increased from 5s for complex tasks)
            )
            return result.stdout, result.stderr, result.returncode
        finally:
            os.unlink(temp_file)

    def _execute_javascript(self, code: str) -> tuple:
        """Execute JavaScript code using Node.js"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            result = subprocess.run(
                ['node', temp_file],
                capture_output=True,
                text=True,
                timeout=30  # 30 seconds (increased from 5s for complex tasks)
            )
            return result.stdout, result.stderr, result.returncode
        except FileNotFoundError:
            return "", "Node.js not installed", 1
        finally:
            os.unlink(temp_file)

    def _execute_bash(self, code: str) -> tuple:
        """Execute Bash script"""
        result = subprocess.run(
            code,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout, result.stderr, result.returncode

    def propose_decision(self, from_client: str, decision: str,
                        vote_type: VoteType = VoteType.SIMPLE_MAJORITY,
                        required_votes: int = None) -> str:
        """
        Propose a decision with enhanced voting

        Args:
            from_client: Proposer
            decision: Decision text
            vote_type: Voting mechanism
            required_votes: Required votes (for quorum)

        Returns:
            Decision ID
        """
        if required_votes is None:
            active_count = sum(1 for m in self.members.values() if m.active)
            if vote_type == VoteType.QUORUM:
                required_votes = max(3, active_count // 2)  # At least half
            else:
                required_votes = active_count

        vote_type_desc = {
            VoteType.SIMPLE_MAJORITY: "Simple Majority (>50%)",
            VoteType.CONSENSUS: "Consensus (100%)",
            VoteType.QUORUM: f"Quorum ({required_votes} votes)",
            VoteType.WEIGHTED: "Weighted Vote"
        }

        msg = self.send_message(
            from_client,
            f"🎯 DECISION: {decision}\n📊 Vote Type: {vote_type_desc[vote_type]}",
            msg_type="decision"
        )

        enhanced_decision = EnhancedDecision(
            id=msg.id,
            text=decision,
            proposed_by=from_client,
            proposed_at=msg.timestamp,
            vote_type=vote_type,
            required_votes=required_votes
        )
        self.decisions.append(enhanced_decision)

        # Persist decision
        if self.persistence:
            self.persistence.save_decision(
                msg.id, self.room_id, decision, from_client,
                msg.timestamp, vote_type.value, required_votes
            )

        return msg.id

    def vote(self, decision_id: str, voter: str, approve: bool = True, veto: bool = False):
        """
        Vote on decision

        Args:
            decision_id: Decision ID
            voter: Voter client ID
            approve: True to approve, False to abstain
            veto: True to veto (blocks decision)
        """
        decision = None
        for d in self.decisions:
            if d.id == decision_id:
                decision = d
                break

        if not decision:
            raise ValueError(f"Decision {decision_id} not found")

        if veto:
            decision.vetoed_by.add(voter)
            decision.vetoed = True

            # Persist vote
            if self.persistence:
                self.persistence.save_vote(decision_id, voter, approve=False, veto=True)
                self.persistence.update_decision_status(decision_id, approved=False, vetoed=True)

            self._broadcast_system_message(
                f"🚫 {voter} vetoed decision: {decision.text}"
            )
            return

        if approve:
            decision.approved_by.add(voter)
        else:
            decision.abstained.add(voter)

        # Persist vote
        if self.persistence:
            self.persistence.save_vote(decision_id, voter, approve=approve, veto=False)

        # Calculate if approved
        self._check_decision_approval(decision)

    def _check_decision_approval(self, decision: EnhancedDecision):
        """Check if decision is approved"""
        if decision.vetoed:
            return

        active_count = sum(1 for m in self.members.values() if m.active)
        vote_count = len(decision.approved_by)

        if decision.vote_type == VoteType.SIMPLE_MAJORITY:
            # >50% of active members
            if vote_count > active_count / 2:
                decision.approved = True

        elif decision.vote_type == VoteType.CONSENSUS:
            # 100% approval
            if vote_count == active_count:
                decision.approved = True

        elif decision.vote_type == VoteType.QUORUM:
            # Minimum participation
            if vote_count >= decision.required_votes:
                decision.approved = True

        elif decision.vote_type == VoteType.WEIGHTED:
            # Weighted by role
            total_weight = sum(
                self.members[voter].vote_weight
                for voter in decision.approved_by
            )
            max_weight = sum(m.vote_weight for m in self.members.values() if m.active)
            if total_weight > max_weight / 2:
                decision.approved = True
                decision.total_weight = total_weight

        if decision.approved:
            # Persist approval status
            if self.persistence:
                self.persistence.update_decision_status(decision.id, approved=True, vetoed=False)

            self._broadcast_system_message(
                f"✅ Decision approved: {decision.text}"
            )

    def get_messages(self, channel: str = "main", limit: int = 100) -> List[RoomMessage]:
        """Get messages from channel"""
        if channel not in self.channels:
            return []
        return self.channels[channel].get_messages(limit)

    def get_summary(self) -> Dict:
        """Get room summary"""
        active_members = [m for m in self.members.values() if m.active]

        return {
            'room_id': self.room_id,
            'topic': self.topic,
            'created_at': self.created_at.isoformat(),
            'total_members': len(self.members),
            'active_members': len(active_members),
            'channels': len(self.channels),
            'total_messages': sum(len(ch.messages) for ch in self.channels.values()),
            'total_decisions': len(self.decisions),
            'approved_decisions': sum(1 for d in self.decisions if d.approved),
            'vetoed_decisions': sum(1 for d in self.decisions if d.vetoed),
            'total_tasks': len(self.tasks),
            'files_shared': len(self.files),
            'code_executions': len(self.code_executions)
        }

    def _extract_mentions(self, text: str) -> Set[str]:
        """Extract @mentions from text"""
        import re
        mentions = set()
        for match in re.finditer(r'@(\w+)', text):
            mentions.add(match.group(1))
        return mentions

    def _broadcast_system_message(self, text: str, channel: str = "main"):
        """Broadcast system message"""
        message = RoomMessage(
            id=str(uuid.uuid4()),
            from_client="SYSTEM",
            text=text,
            timestamp=datetime.now(timezone.utc),
            type="system",
            channel=channel
        )
        if channel in self.channels:
            self.channels[channel].add_message(message)
        self._trigger_callbacks(message)

    def _trigger_callbacks(self, message: RoomMessage):
        """Trigger message callbacks"""
        for callback in self.message_callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"Callback error: {e}")

    def on_message(self, callback: Callable):
        """Register callback for new messages"""
        self.message_callbacks.append(callback)

    def _find_message(self, message_id: str) -> Optional[RoomMessage]:
        """Find message by ID across all channels"""
        for channel in self.channels.values():
            for msg in channel.messages:
                if msg.id == message_id:
                    return msg
        return None

    def send_critique(self, from_client: str, target_message_id: str,
                     critique_text: str, severity: str = "suggestion",
                     channel: str = "main") -> RoomMessage:
        """
        Send structured critique of another message

        Args:
            from_client: Critic
            target_message_id: Message being critiqued
            critique_text: Feedback content
            severity: "blocking", "major", "minor", "suggestion"
            channel: Target channel

        Returns:
            Critique message
        """
        # Validate target exists
        target_msg = self._find_message(target_message_id)
        if not target_msg:
            raise ValueError(f"Target message {target_message_id} not found")

        # Validate severity
        if severity not in ["blocking", "major", "minor", "suggestion"]:
            raise ValueError(f"Invalid severity: {severity}")

        # Create critique message
        severity_emoji = {
            "blocking": "🚫",
            "major": "⚠️",
            "minor": "💡",
            "suggestion": "💬"
        }

        critique_msg = self.send_message(
            from_client,
            f"{severity_emoji[severity]} CRITIQUE of {target_msg.from_client}'s message:\n"
            f"Severity: {severity.upper()}\n\n{critique_text}",
            msg_type="critique",
            reply_to=target_message_id,
            channel=channel
        )

        # Track critique
        critique = Critique(
            id=critique_msg.id,
            target_message_id=target_message_id,
            from_client=from_client,
            critique_text=critique_text,
            severity=severity,
            timestamp=critique_msg.timestamp,
            resolved=False
        )
        self.critiques.append(critique)

        # Add to target message's critique list
        target_msg.critiques.append(critique_msg.id)

        return critique_msg

    def propose_alternative(self, from_client: str, original_decision_id: str,
                           alternative_text: str, vote_type: VoteType = None,
                           channel: str = "main") -> str:
        """
        Propose alternative to existing decision

        Args:
            from_client: Proposer
            original_decision_id: Decision being countered
            alternative_text: Alternative proposal
            vote_type: Voting mechanism (inherits from original if None)
            channel: Target channel

        Returns:
            Alternative decision ID
        """
        # Find original decision
        original = next((d for d in self.decisions if d.id == original_decision_id), None)
        if not original:
            raise ValueError(f"Decision {original_decision_id} not found")

        # Use same vote type as original
        if vote_type is None:
            vote_type = original.vote_type

        # Create alternative decision message
        alt_msg = self.send_message(
            from_client,
            f"🔄 ALTERNATIVE to decision {original_decision_id[:8]}:\n"
            f"Original: {original.text}\n"
            f"Alternative: {alternative_text}",
            msg_type="counter_proposal",
            reply_to=original_decision_id,
            channel=channel
        )

        # Create decision for alternative
        alt_decision = EnhancedDecision(
            id=alt_msg.id,
            text=alternative_text,
            proposed_by=from_client,
            proposed_at=alt_msg.timestamp,
            vote_type=vote_type,
            required_votes=original.required_votes
        )
        self.decisions.append(alt_decision)

        # Link to original
        original.alternatives.append(alt_msg.id)

        # Persist decision
        if self.persistence:
            self.persistence.save_decision(
                alt_msg.id, self.room_id, alternative_text, from_client,
                alt_msg.timestamp, vote_type.value, original.required_votes
            )

        return alt_msg.id

    def add_debate_argument(self, from_client: str, decision_id: str,
                           position: str, argument_text: str,
                           evidence: List[str] = None) -> str:
        """
        Add pro/con argument to decision debate

        Args:
            from_client: Arguer
            decision_id: Decision being debated
            position: "pro" or "con"
            argument_text: The argument
            evidence: Supporting evidence (URLs, file IDs, etc.)

        Returns:
            Argument ID
        """
        if position not in ["pro", "con"]:
            raise ValueError("Position must be 'pro' or 'con'")

        # Validate decision exists
        decision = next((d for d in self.decisions if d.id == decision_id), None)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")

        # Create argument message
        emoji = "👍" if position == "pro" else "👎"
        msg = self.send_message(
            from_client,
            f"{emoji} {position.upper()} argument:\n{argument_text}",
            msg_type="debate_argument",
            reply_to=decision_id
        )

        # Track argument
        arg = DebateArgument(
            id=msg.id,
            decision_id=decision_id,
            from_client=from_client,
            position=position,
            argument_text=argument_text,
            supporting_evidence=evidence or []
        )
        self.debate_arguments.append(arg)

        return msg.id

    def get_debate_summary(self, decision_id: str) -> Dict:
        """Get pro/con summary for decision"""
        args = [a for a in self.debate_arguments if a.decision_id == decision_id]
        return {
            'pro': [a for a in args if a.position == "pro"],
            'con': [a for a in args if a.position == "con"],
            'total_pro': len([a for a in args if a.position == "pro"]),
            'total_con': len([a for a in args if a.position == "con"])
        }

    def propose_amendment(self, from_client: str, decision_id: str,
                         amendment_text: str) -> str:
        """
        Propose amendment to existing decision

        Args:
            from_client: Proposer
            decision_id: Decision to amend
            amendment_text: Proposed changes

        Returns:
            Amendment message ID
        """
        decision = next((d for d in self.decisions if d.id == decision_id), None)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")

        # Create amendment message
        msg = self.send_message(
            from_client,
            f"📝 AMENDMENT to decision {decision_id[:8]}:\n{amendment_text}",
            msg_type="amendment",
            reply_to=decision_id
        )

        # Track amendment
        decision.amendments.append({
            'id': msg.id,
            'from': from_client,
            'text': amendment_text,
            'accepted': False,
            'timestamp': msg.timestamp.isoformat()
        })

        return msg.id

    def accept_amendment(self, decision_id: str, amendment_id: str):
        """Accept amendment and update decision text"""
        decision = next((d for d in self.decisions if d.id == decision_id), None)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")

        # Find amendment
        amendment = next((a for a in decision.amendments if a['id'] == amendment_id), None)
        if not amendment:
            raise ValueError(f"Amendment {amendment_id} not found")

        # Update decision text
        decision.text = amendment['text']
        amendment['accepted'] = True

        # Persist update
        if self.persistence:
            self.persistence.update_decision_text(decision_id, amendment['text'])

        # Broadcast update
        self._broadcast_system_message(
            f"✅ Amendment {amendment_id[:8]} accepted for decision {decision_id[:8]}\n"
            f"New text: {amendment['text']}"
        )

    def get_critiques_for_message(self, message_id: str) -> List[Critique]:
        """Get all critiques for a specific message"""
        return [c for c in self.critiques if c.target_message_id == message_id]

    def resolve_critique(self, critique_id: str):
        """Mark critique as resolved"""
        critique = next((c for c in self.critiques if c.id == critique_id), None)
        if critique:
            critique.resolved = True
            self._broadcast_system_message(
                f"✅ Critique {critique_id[:8]} marked as resolved"
            )


class EnhancedCollaborationHub:
    """
    Hub managing multiple enhanced collaboration rooms
    """

    def __init__(self):
        self.rooms: Dict[str, EnhancedCollaborationRoom] = {}

    def create_room(self, topic: str) -> str:
        """Create collaboration room"""
        room_id = str(uuid.uuid4())[:8]
        room = EnhancedCollaborationRoom(room_id=room_id, topic=topic)
        self.rooms[room_id] = room
        return room_id

    def get_room(self, room_id: str) -> Optional[EnhancedCollaborationRoom]:
        """Get room by ID"""
        return self.rooms.get(room_id)

    def list_rooms(self) -> List[Dict]:
        """List all rooms"""
        return [
            {
                'room_id': room.room_id,
                'topic': room.topic,
                'members': len([m for m in room.members.values() if m.active]),
                'channels': len(room.channels),
                'messages': sum(len(ch.messages) for ch in room.channels.values())
            }
            for room in self.rooms.values()
        ]


if __name__ == '__main__':
    print("=" * 80)
    print("🚀 Enhanced Collaboration Room - Feature Demo")
    print("=" * 80)

    hub = EnhancedCollaborationHub()
    room_id = hub.create_room("Build Trading Bot with All Features")
    room = hub.get_room(room_id)

    print(f"\n📍 Room: {room_id}")
    print(f"💡 Topic: {room.topic}\n")

    # Join with roles
    room.join("claude-code", MemberRole.COORDINATOR, vote_weight=2.0)
    room.join("claude-browser", MemberRole.RESEARCHER, vote_weight=1.5)
    room.join("claude-desktop-1", MemberRole.CODER)
    room.join("claude-desktop-2", MemberRole.REVIEWER)

    # Create channels
    print("📺 Creating channels...")
    code_channel = room.create_channel("code", "Code discussion")
    docs_channel = room.create_channel("docs", "Documentation")

    # Join channels
    room.join_channel("claude-desktop-1", code_channel)
    room.join_channel("claude-desktop-2", code_channel)

    # Share file
    print("📎 Sharing file...")
    file_content = b"# Trading Bot\nImport yfinance\n..."
    room.upload_file("claude-code", "trading_bot.py", file_content, "text/x-python")

    # Execute code
    print("💻 Executing code...")
    room.execute_code(
        "claude-desktop-1",
        "print('Hello from collaborative Python!')\nprint(2 + 2)",
        CodeLanguage.PYTHON,
        channel=code_channel
    )

    # Propose decision with consensus
    print("🎯 Proposing decision (consensus mode)...")
    dec_id = room.propose_decision(
        "claude-code",
        "Use Python + FastAPI for the trading bot backend",
        vote_type=VoteType.CONSENSUS
    )

    # Vote
    room.vote(dec_id, "claude-browser", approve=True)
    room.vote(dec_id, "claude-desktop-1", approve=True)
    room.vote(dec_id, "claude-desktop-2", approve=True)
    # Need all 4 votes for consensus
    room.vote(dec_id, "claude-code", approve=True)

    # Summary
    print("\n" + "=" * 80)
    print("📊 ROOM SUMMARY")
    print("=" * 80)
    summary = room.get_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")

    print("\n✅ Enhanced features demonstrated!")
    print("   - Sub-channels for focused discussion")
    print("   - File sharing between Claudes")
    print("   - Code execution sandbox")
    print("   - Enhanced voting (consensus mode)")
