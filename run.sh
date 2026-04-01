#!/bin/bash
# Quick start script for TheraPredict MVP
# Runs the API backend and optionally the frontend

set -e

echo "=== TheraPredict - Digital Theranostic Simulator ==="
echo ""

# Start API
echo "Starting API server on http://localhost:8000 ..."
echo "  API docs: http://localhost:8000/docs"
echo ""

PYTHONPATH=src python3 -m uvicorn theranostics.api.main:app --host 0.0.0.0 --port 8000 --reload
