#!/bin/bash
echo "Starting the app..."
cd /home/ubuntu/Document-QA
source venv/bin/activate
nohup python3 app.py > log.txt 2>&1 &
