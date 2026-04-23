#!/bin/bash
# Mavuno Prototype Server Startup Script
# This ensures all paths are correct and starts the server reliably.

echo "Starting Mavuno Prototype on Port 8001..."
export PYTHONPATH=$(pwd)

# Try starting via Python script to ensure it picks up the local environment and handles port cleanly
python3 run.py
