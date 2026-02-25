"""
Gunicorn configuration for production deployment
Usage: gunicorn -c gunicorn_config.py wsgi:application
"""

import multiprocessing

# Server socket
import os

bind = f"0.0.0.0:{os.getenv('PORT', '5001')}"
backlog = 2048

# Worker processes
# For I/O-bound workloads (WebSockets, HTTP), use more workers than CPU-bound formula
# CPU-bound: (2 * cpu_count) + 1
# I/O-bound: (cpu_count * 4) + 1 (recommended for WebSocket/async workloads)
workers = (multiprocessing.cpu_count() * 2) + 1
worker_class = "gthread"  # Thread-based worker (compatible with flask_sock WebSockets)
threads = 4
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging (use - for stdout/stderr to work correctly in Docker)
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "claude-bridge"

# Server mechanics
daemon = False
pidfile = "claude_bridge.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment for HTTPS)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"
