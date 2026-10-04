"""
run_web.py
-----------
Entry point for the Canteen Management System Flask web application.

Usage:
    python run_web.py

Prerequisites:
    1. MySQL is running and canteen_db schema exists.
    2. Copy .env.example to .env and fill in your credentials.
    3. pip install -r requirements.txt

The CLI (python -m canteen_system.main) continues to work independently.
"""

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from canteen_system.web.app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print(f"Starting Canteen Web App on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
