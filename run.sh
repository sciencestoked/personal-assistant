#!/bin/bash
# Quick start script for the Personal Assistant

# Activate virtual environment
source venv/bin/activate

# Check for --quiet flag
if [[ "$*" == *"--quiet"* ]] || [[ "$*" == *"-q"* ]]; then
    echo "Starting server in quiet mode (HTTP logs disabled, agentic logs enabled)..."
    python -m src.cli server --host 0.0.0.0 --port 8000 --quiet
else
    # Start the server with default settings
    python -m src.cli server --host 0.0.0.0 --port 8000
fi
