#!/bin/bash
echo "Stopping running app..."
pkill -f app.py || echo "No app was running"
