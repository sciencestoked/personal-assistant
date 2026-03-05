#!/bin/bash
# Quick start script for the Personal Assistant

# Activate virtual environment
source venv/bin/activate

# Start the server
python -m src.cli server --host 0.0.0.0 --port 8000
