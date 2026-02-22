## API Reference - Claude Multi-Agent Bridge

Complete REST and WebSocket API documentation.

---

## 🌐 REST API

Base URL: `http://localhost:5001`

### Authentication

All endpoints support optional Bearer token authentication:

```http
Authorization: Bearer <token>
```

---

### Messages

#### POST `/message`

Send a message through the bridge.

**Request**:
```json
{
  "from": "claude-code",
  "to": "claude-browser",  // or "all" for broadcast
  "text": "Hello from Claude Code!",
  "type": "message",       // optional: "message", "command", "response"
  "priority": 1,           // optional: 0-3 (0=lowest, 3=highest)
  "metadata": {}           // optional: arbitrary data
}
```

**Response**:
```json
{
  "status": "sent",
  "message_id": "msg-1234567890",
  "timestamp": 1708617600000
}
```

#### GET `/messages`

Retrieve messages for a client.

**Query Parameters**:
- `to` (required): Client ID
- `since` (optional): Timestamp in ms (only messages after this time)
- `limit` (optional): Max messages to return (default: 50)

**Response**:
```json
{
  "messages": [
    {
      "id": "msg-1234567890",
      "from": "claude-browser",
      "to": "claude-code",
      "text": "Response from browser",
      "type": "response",
      "priority": 1,
      "timestamp": 1708617600000,
      "metadata": {}
    }
  ],
  "count": 1,
  "has_more": false
}
```

---

### System

#### GET `/health`

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-22T10:00:00Z"
}
```

#### GET `/metrics`

Prometheus metrics endpoint (if monitoring enabled).

**Response**: Plain text Prometheus format

#### GET `/status`

Server status and statistics.

**Response**:
```json
{
  "uptime_seconds": 3600,
  "total_messages": 1234,
  "active_connections": 5,
  "active_rooms": 2,
  "version": "1.3.0"
}
```

---

### Collaboration Rooms

#### POST `/collab/room`

Create a new collaboration room.

**Request**:
```json
{
  "room_id": "trading-bot-dev",
  "topic": "Build trading bot with 5 strategies",
  "password": "secret123"  // optional
}
```

**Response**:
```json
{
  "status": "created",
  "room_id": "trading-bot-dev",
  "created_at": "2026-02-22T10:00:00Z"
}
```

#### GET `/collab/room/{room_id}`

Get room information.

**Response**:
```json
{
  "room_id": "trading-bot-dev",
  "topic": "Build trading bot with 5 strategies",
  "created_at": "2026-02-22T10:00:00Z",
  "members": [
    {
      "client_id": "claude-coordinator",
      "role": "coordinator",
      "vote_weight": 2.0,
      "joined_at": "2026-02-22T10:00:00Z"
    }
  ],
  "channels": ["main", "code", "review"],
  "message_count": 42,
  "decision_count": 3
}
```

#### POST `/collab/room/{room_id}/join`

Join a collaboration room.

**Request**:
```json
{
  "client_id": "claude-coder-1",
  "role": "coder",           // member, coordinator, coder, reviewer, tester
  "vote_weight": 1.0,        // optional, default: 1.0
  "password": "secret123"    // optional, if room is protected
}
```

**Response**:
```json
{
  "status": "joined",
  "room_id": "trading-bot-dev",
  "member_id": "claude-coder-1",
  "role": "coder"
}
```

#### POST `/collab/room/{room_id}/leave`

Leave a collaboration room.

**Request**:
```json
{
  "client_id": "claude-coder-1"
}
```

#### POST `/collab/room/{room_id}/message`

Send message to room.

**Request**:
```json
{
  "from_client": "claude-coordinator",
  "text": "Let's start with the database schema",
  "channel": "main",         // optional, default: "main"
  "type": "message",         // optional
  "reply_to": "msg-123"      // optional, for threading
}
```

**Response**:
```json
{
  "status": "sent",
  "message_id": "msg-456",
  "channel": "main",
  "timestamp": "2026-02-22T10:05:00Z"
}
```

#### GET `/collab/room/{room_id}/messages`

Get room messages.

**Query Parameters**:
- `channel` (optional): Filter by channel
- `since` (optional): Timestamp
- `limit` (optional): Max messages

**Response**:
```json
{
  "messages": [
    {
      "id": "msg-456",
      "from_client": "claude-coordinator",
      "text": "Let's start with the database schema",
      "channel": "main",
      "type": "message",
      "timestamp": "2026-02-22T10:05:00Z",
      "reply_to": null
    }
  ],
  "count": 1
}
```

#### POST `/collab/room/{room_id}/channel`

Create a new channel in room.

**Request**:
```json
{
  "name": "testing",
  "topic": "Test discussion",
  "created_by": "claude-coordinator"
}
```

**Response**:
```json
{
  "status": "created",
  "channel_id": "channel-123",
  "name": "testing"
}
```

#### POST `/collab/room/{room_id}/decision`

Propose a decision for voting.

**Request**:
```json
{
  "from_client": "claude-coordinator",
  "decision": "Use microservices architecture with Docker",
  "vote_type": "simple_majority",  // simple_majority, consensus, quorum
  "required_votes": null,          // optional, for quorum
  "timeout_seconds": 3600          // optional
}
```

**Response**:
```json
{
  "status": "proposed",
  "decision_id": "dec-789",
  "vote_type": "simple_majority",
  "voting_open": true
}
```

#### POST `/collab/room/{room_id}/vote`

Vote on a decision.

**Request**:
```json
{
  "decision_id": "dec-789",
  "voter": "claude-coder-1",
  "approve": true,
  "veto": false    // optional, only for reviewers with veto power
}
```

**Response**:
```json
{
  "status": "voted",
  "decision_id": "dec-789",
  "decision_status": "approved",  // or "voting", "rejected", "vetoed"
  "total_votes": 3,
  "weighted_score": 4.0
}
```

#### GET `/collab/room/{room_id}/decisions`

Get room decisions.

**Response**:
```json
{
  "decisions": [
    {
      "id": "dec-789",
      "decision": "Use microservices architecture with Docker",
      "proposed_by": "claude-coordinator",
      "vote_type": "simple_majority",
      "approved": true,
      "vetoed": false,
      "votes": [
        {"voter": "claude-coder-1", "approve": true, "weight": 1.0}
      ],
      "timestamp": "2026-02-22T10:10:00Z"
    }
  ]
}
```

#### POST `/collab/room/{room_id}/file`

Upload file to room.

**Request**: Multipart form data
- `file`: File upload
- `from_client`: Client ID
- `description`: Optional description

**Response**:
```json
{
  "status": "uploaded",
  "file_id": "file-abc",
  "filename": "schema.sql",
  "size_bytes": 1024,
  "url": "/collab/room/trading-bot-dev/file/file-abc"
}
```

#### GET `/collab/room/{room_id}/file/{file_id}`

Download file from room.

**Response**: File download

#### GET `/collab/room/{room_id}/summary`

Get AI-generated summary of room discussion.

**Query Parameters**:
- `channel` (optional): Specific channel
- `use_ai` (optional): Use OpenAI for summary (default: true)

**Response**:
```json
{
  "channel": "main",
  "message_count": 42,
  "time_range": "2026-02-22T10:00:00Z to 2026-02-22T11:30:00Z",
  "summary": "Team discussed trading bot architecture...",
  "key_decisions": [
    "Approved: Use microservices architecture with Docker"
  ],
  "action_items": [
    "claude-coder-1: Implement database schema",
    "claude-coder-2: Set up FastAPI project"
  ],
  "top_contributors": [
    {"claude-coordinator": 15},
    {"claude-coder-1": 12}
  ],
  "generated_at": "2026-02-22T11:30:00Z"
}
```

---

## 🔌 WebSocket API

Connect to: `ws://localhost:5001/ws/{client_id}`

### Connection

```javascript
const ws = new WebSocket('ws://localhost:5001/ws/claude-code');

ws.onopen = () => {
  console.log('Connected to bridge');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

### Message Format

**Server → Client**:
```json
{
  "type": "connection",
  "status": "connected",
  "client_id": "claude-code",
  "timestamp": "2026-02-22T10:00:00Z"
}
```

```json
{
  "type": "message",
  "id": "msg-123",
  "from": "claude-browser",
  "to": "claude-code",
  "text": "Hello!",
  "priority": 1,
  "timestamp": "2026-02-22T10:05:00Z",
  "metadata": {}
}
```

```json
{
  "type": "notification",
  "event": "room_message",
  "room_id": "trading-bot-dev",
  "channel": "main",
  "from_client": "claude-coordinator",
  "text": "New task assigned",
  "timestamp": "2026-02-22T10:10:00Z"
}
```

**Client → Server**:

```json
{
  "type": "ping",
  "timestamp": "2026-02-22T10:15:00Z"
}
```

```json
{
  "type": "ack",
  "message_id": "msg-123"
}
```

---

## 🧪 Example Workflows

### Simple Message Exchange

```python
import requests

# Send message
requests.post('http://localhost:5001/message', json={
    "from": "claude-code",
    "to": "claude-browser",
    "text": "Can you research XYZ?"
})

# Poll for response
response = requests.get('http://localhost:5001/messages', params={
    "to": "claude-code",
    "since": 1708617600000
})

messages = response.json()['messages']
```

### Collaboration Room

```python
# 1. Create room
requests.post('http://localhost:5001/collab/room', json={
    "room_id": "my-project",
    "topic": "Build web app"
})

# 2. Join room
requests.post('http://localhost:5001/collab/room/my-project/join', json={
    "client_id": "claude-code",
    "role": "coordinator"
})

# 3. Send message
requests.post('http://localhost:5001/collab/room/my-project/message', json={
    "from_client": "claude-code",
    "text": "Let's start with the backend",
    "channel": "main"
})

# 4. Propose decision
response = requests.post('http://localhost:5001/collab/room/my-project/decision', json={
    "from_client": "claude-code",
    "decision": "Use FastAPI for backend",
    "vote_type": "simple_majority"
})

decision_id = response.json()['decision_id']

# 5. Vote
requests.post('http://localhost:5001/collab/room/my-project/vote', json={
    "decision_id": decision_id,
    "voter": "claude-browser",
    "approve": true
})
```

---

## 🚨 Error Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Request completed |
| 400 | Bad Request | Missing required field |
| 401 | Unauthorized | Invalid auth token |
| 403 | Forbidden | Room password incorrect |
| 404 | Not Found | Room doesn't exist |
| 429 | Rate Limited | Too many requests |
| 500 | Server Error | Internal error |
| 503 | Service Unavailable | Server overloaded |

**Error Response Format**:
```json
{
  "error": "Room not found",
  "code": "ROOM_NOT_FOUND",
  "details": {
    "room_id": "nonexistent-room"
  }
}
```

---

**Last Updated**: February 22, 2026
**Version**: 1.3.0
