#!/bin/bash
echo "Installing dependencies..."
cd /home/ubuntu/Document-QA
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install "camelot-py[cv]"
