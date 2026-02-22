# 🚀 Upgrade Guide: v1.1 → v1.2

## What's New in v1.2

### ✨ Production Features

**1. Webhook System** (`webhooks.py`)
- ✅ External notifications for events (Slack, Discord, custom)
- ✅ HMAC signature verification for security
- ✅ Automatic retry with exponential backoff
- ✅ Async delivery (non-blocking)
- ✅ Failed webhook tracking and retry
- ✅ Pre-built integrations (Slack, Discord)

**2. Health Checks** (`health_checks.py`)
- ✅ Kubernetes-style liveness/readiness probes
- ✅ Startup probe for initialization
- ✅ System resource monitoring (CPU, memory, disk)
- ✅ Custom health check functions
- ✅ Combined status endpoint

**3. Message TTL** (`message_ttl.py`)
- ✅ Auto-expire messages after configurable time
- ✅ Per-message-type retention policies
- ✅ Archive before deletion option
- ✅ Background cleanup worker
- ✅ Extend TTL for specific messages
- ✅ Pre-configured policies (errors, logs, commands, etc.)

**4. Enhanced Metrics** (`enhanced_metrics.py`)
- ✅ Counters with labels
- ✅ Gauges (up/down metrics)
- ✅ Histograms with buckets
- ✅ Summaries with percentiles (P50, P90, P95, P99)
- ✅ Prometheus-compatible export
- ✅ Time-series snapshots
- ✅ Detailed performance analytics

**5. Server-Sent Events** (`streaming.py`)
- ✅ Real-time event streaming to browser
- ✅ Event filtering by type
- ✅ Automatic reconnection support
- ✅ Per-client message queues
- ✅ Heartbeat/keep-alive
- ✅ Broadcast to all or filtered clients

---

## Migration Guide

### Option A: Keep Using v1.1

No changes needed. All v1.2 features are optional additions.

---

### Option B: Add Production Features

#### 1. Webhooks - External Notifications

**Use case:** Get notified in Slack when errors occur, messages sent, etc.

```python
from webhooks import WebhookManager, WebhookEndpoint, WebhookEvent

# Create manager
webhook_mgr = WebhookManager()
webhook_mgr.start_worker()

# Register Slack webhook
slack_endpoint = WebhookEndpoint(
    url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    events={WebhookEvent.ERROR_OCCURRED, WebhookEvent.MESSAGE_FAILED},
    secret="webhook_secret_123"
)
webhook_mgr.register(slack_endpoint)

# Trigger webhook when error occurs
webhook_mgr.trigger(WebhookEvent.ERROR_OCCURRED, {
    'error': 'Database connection failed',
    'timestamp': datetime.now(timezone.utc).isoformat()
})
```

**Slack Integration:**

```python
from webhooks import SlackWebhook, WebhookEvent

SlackWebhook.send(
    webhook_url="https://hooks.slack.com/services/...",
    event=WebhookEvent.MESSAGE_SENT,
    data={'from': 'code', 'to': 'browser', 'text': 'Hello'}
)
```

**Verify Incoming Webhooks:**

```python
# Server receiving webhooks
payload = request.json
signature = request.headers.get('X-Webhook-Signature')

valid = webhook_mgr.verify_signature(payload, signature, 'secret123')
if not valid:
    return 'Invalid signature', 403
```

---

#### 2. Health Checks - Kubernetes Probes

**Use case:** Deploy to Kubernetes with proper health monitoring

```python
from health_checks import HealthCheckManager, HealthCheck, CommonChecks
from flask import Flask

app = Flask(__name__)

# Create health check manager
health = HealthCheckManager(app)

# Add custom liveness check
def check_application_state():
    # Check if app is not deadlocked
    return True, "Application responsive"

health.add_liveness_check(HealthCheck(
    name="application_state",
    check_func=check_application_state,
    critical=True
))

# Add readiness check for database
health.add_readiness_check(HealthCheck(
    name="database",
    check_func=CommonChecks.database_check(db_connection),
    critical=True
))
```

**Kubernetes Deployment:**

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: message-bus
    image: multi-agent-bridge:1.2.0
    ports:
    - containerPort: 5001
    livenessProbe:
      httpGet:
        path: /health/live
        port: 5001
      initialDelaySeconds: 10
      periodSeconds: 30
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 5001
      initialDelaySeconds: 5
      periodSeconds: 10
    startupProbe:
      httpGet:
        path: /health/startup
        port: 5001
      failureThreshold: 30
      periodSeconds: 10
```

**Endpoints:**

- `GET /health/live` - Liveness probe (200 = healthy, 503 = restart)
- `GET /health/ready` - Readiness probe (200 = ready for traffic)
- `GET /health/startup` - Startup probe (200 = initialized)
- `GET /health/status` - Combined health status

---

#### 3. Message TTL - Auto-Cleanup

**Use case:** Automatically delete old messages to prevent database bloat

```python
from message_ttl import MessageTTLManager, StandardPolicies, TTLConfig

# Create manager
ttl_mgr = MessageTTLManager(default_ttl=86400)  # 24 hours default

# Register standard policies
ttl_mgr.register_policy(StandardPolicies.get_error_policy())  # 1 hour
ttl_mgr.register_policy(StandardPolicies.get_log_policy())     # 24 hours
ttl_mgr.register_policy(StandardPolicies.get_command_policy()) # 7 days
ttl_mgr.register_policy(StandardPolicies.get_audit_policy())   # Never delete

# Start background cleanup (runs every 60 seconds)
ttl_mgr.start_cleanup_worker(interval=60)

# Add message with TTL
message = {
    'id': 'msg-123',
    'type': 'error',
    'payload': {...},
    'timestamp': datetime.now(timezone.utc).isoformat()
}
ttl_mgr.add_message(message)
```

**Custom Policy with Callback:**

```python
def on_expire(msg):
    print(f"Message {msg['id']} expired, archiving to S3...")
    # Archive to S3, send to data warehouse, etc.

ttl_mgr.register_policy(TTLConfig(
    message_type="analytics",
    ttl_seconds=3600,  # 1 hour
    on_expire=on_expire,
    archive_before_delete=True
))
```

**Extend TTL:**

```python
# Extend specific message by 1 hour
ttl_mgr.extend_ttl('msg-123', additional_seconds=3600)
```

---

#### 4. Enhanced Metrics - Performance Monitoring

**Use case:** Track detailed performance metrics, export to Prometheus

```python
from enhanced_metrics import MetricsCollector

# Create collector
metrics = MetricsCollector()

# Counter - total messages sent
msg_counter = metrics.counter('messages_sent', 'Total messages sent')
msg_counter.inc(labels={'from': 'code', 'to': 'browser'})

# Gauge - active connections
conn_gauge = metrics.gauge('active_connections', 'Active client connections')
conn_gauge.set(5, labels={'client': 'browser'})
conn_gauge.inc(2)  # +2 connections
conn_gauge.dec(1)  # -1 connection

# Histogram - message size distribution
size_hist = metrics.histogram(
    'message_size_bytes',
    buckets=[100, 1000, 10000, 100000],
    help_text='Message size distribution'
)
size_hist.observe(1250)  # Observe 1250 bytes

# Summary - request latency with percentiles
latency_summary = metrics.summary(
    'request_duration_ms',
    help_text='Request duration',
    max_age=600  # Keep last 10 minutes
)
latency_summary.observe(45.2)  # 45.2ms

# Get statistics
stats = latency_summary.get_stats(quantiles=[0.5, 0.9, 0.95, 0.99])
print(f"P50: {stats['quantiles'][0.5]:.2f}ms")
print(f"P90: {stats['quantiles'][0.9]:.2f}ms")
print(f"P99: {stats['quantiles'][0.99]:.2f}ms")
```

**Prometheus Export:**

```python
from flask import Flask, Response

@app.route('/metrics')
def prometheus_metrics():
    return Response(
        metrics.get_prometheus_metrics(),
        mimetype='text/plain; version=0.0.4'
    )
```

**Grafana Dashboard:**

Query Prometheus metrics in Grafana:
- `rate(messages_sent[5m])` - Messages per second
- `histogram_quantile(0.95, message_size_bytes)` - P95 message size
- `request_duration_ms{quantile="0.99"}` - P99 latency

---

#### 5. Server-Sent Events - Real-Time Streaming

**Use case:** Stream events to browser in real-time (alternative to WebSocket)

```python
from streaming import SSEManager, create_sse_blueprint
from flask import Flask

app = Flask(__name__)

# Create SSE manager
sse_mgr = SSEManager(
    max_queue_size=100,
    heartbeat_interval=30  # Send heartbeat every 30s
)

# Register blueprint
app.register_blueprint(create_sse_blueprint(sse_mgr))

# Broadcast event to all clients
sse_mgr.broadcast('notification', {
    'type': 'info',
    'message': 'System maintenance in 10 minutes'
})

# Send to specific client
sse_mgr.send_event('client-123', 'message_received', {
    'from': 'code',
    'text': 'Hello world'
})
```

**Browser Client:**

```javascript
// Connect to SSE stream
const eventSource = new EventSource('/stream/events?client_id=browser-1');

// Listen for specific event types
eventSource.addEventListener('message_received', (e) => {
    const data = JSON.parse(e.data);
    console.log('Message:', data);
});

eventSource.addEventListener('notification', (e) => {
    const data = JSON.parse(e.data);
    showNotification(data.message);
});

// Reconnection happens automatically
eventSource.onerror = (e) => {
    console.log('Connection lost, reconnecting...');
};
```

**Filter Events:**

```javascript
// Only subscribe to specific event types
const eventSource = new EventSource(
    '/stream/events?subscribe=message_received,notification'
);
```

**Endpoints:**

- `GET /stream/events?client_id=xyz` - Stream events for client
- `POST /stream/broadcast` - Broadcast to all clients
- `POST /stream/send` - Send to specific client
- `GET /stream/stats` - Streaming statistics
- `GET /stream/clients` - List connected clients

---

## Production Deployment Checklist

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Health checks
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/health/live || exit 1

# Expose ports
EXPOSE 5001

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5001", \
     "--workers", "4", \
     "--worker-class", "gevent", \
     "--timeout", "120", \
     "server_ws:app"]
```

### Environment Variables

```bash
# .env
MESSAGE_BUS_PORT=5001
MESSAGE_BUS_HOST=0.0.0.0
DEFAULT_TTL=86400
WEBHOOK_SECRET=your-webhook-secret-here
ENABLE_AUTH=true
ENABLE_METRICS=true
METRICS_PORT=9090
LOG_LEVEL=INFO
```

### Monitoring Stack

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  message-bus:
    build: .
    ports:
      - "5001:5001"
    environment:
      - ENABLE_METRICS=true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health/live"]
      interval: 30s
      timeout: 3s
      retries: 3

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana

volumes:
  grafana-storage:
```

**prometheus.yml:**

```yaml
scrape_configs:
  - job_name: 'message-bus'
    static_configs:
      - targets: ['message-bus:5001']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

---

## Performance Comparison

| Feature | v1.1 | v1.2 |
|---------|------|------|
| **WebSocket** | ✅ | ✅ |
| **REST API** | ✅ | ✅ |
| **SSE Streaming** | ❌ | ✅ |
| **Health Checks** | Basic | Kubernetes-ready |
| **Metrics** | Basic | Prometheus + percentiles |
| **Webhooks** | ❌ | ✅ |
| **Message TTL** | Manual | Automatic |
| **Monitoring** | Limited | Production-grade |

---

## What's Next (v1.3+)

Planned features:
- 🔐 End-to-end encryption
- 🐘 PostgreSQL persistence option
- 🌐 Multi-server clustering
- 📱 React admin dashboard
- 🎯 Advanced routing rules
- 📊 Built-in analytics dashboard
- 🔄 Message replay from specific timestamp

---

## Questions?

**"Should I upgrade to v1.2?"**
- Production deployment: **Yes** - health checks, metrics, webhooks are essential
- Development/testing: v1.1 is fine
- New projects: start with v1.2

**"Are v1.2 features breaking changes?"**
- No - all v1.2 features are optional additions
- v1.1 code works unchanged in v1.2

**"Which features should I enable first?"**
1. Health checks (for deployment)
2. Enhanced metrics (for monitoring)
3. Message TTL (for cleanup)
4. Webhooks (for notifications)
5. SSE (if you need browser streaming)

---

**Happy upgrading!** 🚀

Docs: https://github.com/yakub268/claude-multi-agent-bridge
Issues: https://github.com/yakub268/claude-multi-agent-bridge/issues
