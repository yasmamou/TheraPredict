"""Vercel serverless entrypoint for TheraPredict API.

Vercel expects a FastAPI `app` object in api/index.py.
This wraps the existing FastAPI application.
"""

import sys
from pathlib import Path

# Add src to Python path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from theranostics.api.main import app  # noqa: E402, F401

# Vercel picks up `app` automatically
