#!/bin/bash
sudo apt update && sudo apt install -y python3-pip python3-dev git
sudo apt install -y build-essential libgl1-mesa-glx poppler-utils

# Install system deps for camelot
sudo apt install -y ghostscript python3-opencv tesseract-ocr libglib2.0-0 libsm6 libxrender1 libxext6

# Clone your repo (replace YOUR_REPO_URL)
cd /home/ubuntu
git clone https://github.com/Debasish-87/Document-QA.git
cd Document-QA

# Install Python dependencies
pip3 install -r requirements.txt

# Add your .env if needed (or fetch from SSM later)
echo "GEMINI_API_KEY=AIzaSyCq__z4uytcpzmmLZgB2zm1cRLVnvvYctU" > .env

# Run the app
nohup python3 app.py > log.txt 2>&1 &
