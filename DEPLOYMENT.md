# Deployment Guide - Claude Multi-Agent Bridge

Complete guide for deploying the bridge in production.

---

## 🚀 Quick Start

### Development (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start development server
python server_ws.py
# Server running on http://localhost:5001
```

### Production (Linux/Mac)

```bash
# 1. Install production dependencies
pip install -r requirements.txt
pip install gunicorn gevent

# 2. Start with Gunicorn
gunicorn -c gunicorn_config.py wsgi:application
```

### Production (Windows)

```bash
# 1. Install waitress
pip install waitress

# 2. Start production server
python run_production.py
```

---

## 📦 Requirements

### Core Dependencies

```txt
flask>=3.0.0
flask-cors>=4.0.0
flask-sock>=0.6.0
requests>=2.31.0
pyperclip>=1.8.2       # For desktop client
websocket-client>=1.6.0
```

### Production (Linux/Mac)

```txt
gunicorn>=21.0.0
gevent>=23.0.0
```

### Production (Windows)

```txt
waitress>=2.1.0
```

### Optional (Monitoring)

```txt
prometheus-client>=0.18.0
```

### Optional (Desktop Integration)

```txt
pygetwindow>=0.0.9  # Windows only
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer (nginx)                     │
│                   https://bridge.example.com                 │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌─────────────────┐      ┌─────────────────┐
│  Gunicorn #1    │      │  Gunicorn #2    │
│  (4 workers)    │      │  (4 workers)    │
│  Port 5001      │      │  Port 5002      │
└────────┬────────┘      └────────┬────────┘
         │                         │
         └──────────┬──────────────┘
                    ▼
         ┌──────────────────────┐
         │   Redis (optional)    │
         │  Shared state store   │
         └──────────────────────┘
```

---

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```bash
# Server
FLASK_ENV=production
BRIDGE_HOST=0.0.0.0
BRIDGE_PORT=5001

# Authentication
AUTH_ENABLED=true
DEFAULT_TOKEN_EXPIRY_HOURS=720  # 30 days

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60

# Persistence
DATABASE_PATH=./data/bridge.db
ENABLE_PERSISTENCE=true

# OpenAI (for AI summarization)
OPENAI_API_KEY=sk-...

# Monitoring
METRICS_ENABLED=true
METRICS_PORT=9090

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/bridge.log
```

### Gunicorn Configuration

Edit `gunicorn_config.py`:

```python
# Server socket
bind = "0.0.0.0:5001"

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"  # Required for WebSockets

# Timeouts
timeout = 120
keepalive = 5

# Logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
```

---

## 🐳 Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn gevent

# Copy application
COPY . .

# Create data directories
RUN mkdir -p data logs

# Expose ports
EXPOSE 5001 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5001/health')"

# Run
CMD ["gunicorn", "-c", "gunicorn_config.py", "wsgi:application"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  bridge:
    build: .
    ports:
      - "5001:5001"
      - "9090:9090"
    environment:
      - FLASK_ENV=production
      - AUTH_ENABLED=true
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - bridge-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - bridge-network

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    restart: unless-stopped
    networks:
      - bridge-network

networks:
  bridge-network:

volumes:
  redis-data:
  prometheus-data:
```

### Build and Run

```bash
# Build
docker-compose build

# Start
docker-compose up -d

# View logs
docker-compose logs -f bridge

# Stop
docker-compose down
```

---

## 🔐 Security

### Generate Authentication Tokens

```python
from auth import TokenAuth

auth = TokenAuth()

# Generate token for claude-code
token_code = auth.generate_token("claude-code", expires_hours=720)
print(f"claude-code: {token_code}")

# Generate token for claude-browser
token_browser = auth.generate_token("claude-browser", expires_hours=720)
print(f"claude-browser: {token_browser}")
```

### Use Tokens

```python
import requests

headers = {
    "Authorization": f"Bearer {token}"
}

response = requests.post(
    "http://localhost:5001/message",
    headers=headers,
    json={"from": "claude-code", "to": "all", "text": "Hello"}
)
```

### SSL/TLS

Use nginx reverse proxy:

```nginx
server {
    listen 443 ssl http2;
    server_name bridge.example.com;

    ssl_certificate /etc/letsencrypt/live/bridge.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bridge.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📊 Monitoring

### Prometheus Configuration

`prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'claude-bridge'
    static_configs:
      - targets: ['bridge:9090']
```

### Grafana Dashboard

Import dashboard JSON from `monitoring/grafana_dashboard.json`

Key metrics:
- `bridge_messages_total` - Total messages
- `bridge_connections_active` - Active connections
- `bridge_rooms_active` - Active rooms
- `bridge_message_latency_seconds` - Message latency

---

## 🧪 Testing

### Health Check

```bash
curl http://localhost:5001/health
# {"status": "healthy", "timestamp": "2026-02-22T..."}
```

### Send Test Message

```bash
curl -X POST http://localhost:5001/message \
  -H "Content-Type: application/json" \
  -d '{
    "from": "test-client",
    "to": "all",
    "text": "Hello bridge!"
  }'
```

### WebSocket Test

```python
import websocket

ws = websocket.create_connection("ws://localhost:5001/ws/test-client")
print(ws.recv())  # Connection confirmation
ws.close()
```

### Load Testing

```bash
# 100 clients, 60 seconds
python load_test.py --clients 100 --duration 60 --test all
```

---

## 🚦 Scaling

### Horizontal Scaling

1. **Use Redis for state**:
   ```python
   # Edit server_ws.py to use Redis
   import redis
   r = redis.Redis(host='localhost', port=6379)
   ```

2. **Run multiple instances**:
   ```bash
   # Instance 1
   gunicorn -c gunicorn_config.py -b 0.0.0.0:5001 wsgi:application

   # Instance 2
   gunicorn -c gunicorn_config.py -b 0.0.0.0:5002 wsgi:application
   ```

3. **Load balancer** (nginx):
   ```nginx
   upstream bridge_backend {
       server localhost:5001;
       server localhost:5002;
   }

   server {
       location / {
           proxy_pass http://bridge_backend;
       }
   }
   ```

### Vertical Scaling

Increase Gunicorn workers:

```python
# gunicorn_config.py
workers = 16  # Instead of cpu_count * 2 + 1
```

---

## 📝 Maintenance

### Backup Database

```bash
# SQLite backup
sqlite3 data/bridge.db ".backup data/bridge_backup.db"

# Or copy file
cp data/bridge.db data/bridge_backup_$(date +%Y%m%d).db
```

### Rotate Logs

```bash
# logrotate config: /etc/logrotate.d/claude-bridge
/app/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### Update Application

```bash
# Pull latest
git pull

# Install dependencies
pip install -r requirements.txt

# Restart
docker-compose restart bridge
# OR
systemctl restart claude-bridge
```

---

## 🐛 Troubleshooting

### WebSocket Connection Fails

```bash
# Check firewall
sudo ufw allow 5001

# Check if server is running
ps aux | grep gunicorn

# Check logs
tail -f logs/error.log
```

### High Memory Usage

```bash
# Reduce workers
# Edit gunicorn_config.py: workers = 4

# Or increase server memory
```

### Database Lock Errors

```bash
# Check if another process is using DB
lsof data/bridge.db

# Enable WAL mode (better concurrency)
sqlite3 data/bridge.db "PRAGMA journal_mode=WAL;"
```

---

## 📚 Additional Resources

- [API Reference](./API.md)
- [Chrome Extension Setup](./extension/README.md)
- [Desktop Client Guide](./docs/desktop_client.md)
- [ML Orchestrator Guide](./docs/orchestrator.md)

---

**Last Updated**: February 22, 2026
**Version**: 1.3.0
