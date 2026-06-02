"""WSGI entry point for gunicorn.

Usage: gunicorn wsgi:app
       PYTHONPATH=src gunicorn wsgi:app
"""

from sask.web import create_app

app = create_app()
