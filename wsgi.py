#!/usr/bin/env python3
"""
WSGI entry point for production deployment
Use with gunicorn or waitress
"""
from server_ws import app

# WSGI application
application = app

if __name__ == "__main__":
    # For development only
    app.run(host="0.0.0.0", port=5001, debug=False)
