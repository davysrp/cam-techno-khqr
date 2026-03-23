"""
passenger_wsgi.py — cPanel Passenger WSGI entry point.

cPanel's Phusion Passenger uses this file to serve the Flask app.
DO NOT rename this file unless you update the cPanel Python App settings.
"""

import sys
import os

# Add the app directory to Python path
INTERP = os.path.join(os.environ.get("VIRTUAL_ENV", ""), "bin", "python3")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.insert(0, os.path.dirname(__file__))

from app import app as application  # 'application' is required by WSGI standard
