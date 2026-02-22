"""
Gunicorn configuration for production deployment
Usage: gunicorn -c gunicorn_config.py wsgi:application
"""
import multiprocessing

# Server socket
bind = "0.0.0.0:5001"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"  # Async worker for WebSockets
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "access.log"
errorlog = "error.log"
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
