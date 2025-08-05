#!/bin/bash

set -e  # Exit on any error

echo "🚀 Starting deployment of Document-QA..."

# Step 1: Update system and install dependencies
echo "🔧 Installing system packages..."
sudo apt update -y
sudo apt install -y python3-pip python3-dev git build-essential \
    libgl1 poppler-utils ghostscript python3-opencv \
    tesseract-ocr libglib2.0-0 libsm6 libxrender1 libxext6 \
    python3-venv

# Step 2: Clone or update the repository
cd /home/ubuntu
if [ ! -d "Document-QA" ]; then
    echo "📥 Cloning Document-QA repository..."
    git clone https://github.com/Debasish-87/vfboefboebfbefsbsfbfbs.git
else
    echo "📁 Updating existing Document-QA repository..."
    cd Document-QA
    git reset --hard
    git pull origin main
fi

cd /home/ubuntu/vfboefboebfbefsbsfbfbs

# Step 3: Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Step 4: Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install "camelot-py[cv]"

# Step 5: Create or update .env file with secrets
echo "⚙️  Writing secrets to .env file..."
touch .env

# Add or update GEMINI_API_KEY
if ! grep -q "^GEMINI_API_KEY=" .env; then
    echo "GEMINI_API_KEY=${GEMINI_API_KEY}" >> .env
else
    sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=${GEMINI_API_KEY}|" .env
fi

# Add or update API_TOKEN
if ! grep -q "^API_TOKEN=" .env; then
    echo "API_TOKEN=${API_TOKEN}" >> .env
else
    sed -i "s|^API_TOKEN=.*|API_TOKEN=${API_TOKEN}|" .env
fi

# Step 6: Fix permissions
echo "🔒 Setting file permissions..."
sudo chown -R ubuntu:ubuntu /home/ubuntu/Document-QA

# Step 7: Stop previous app instance if running
echo "🧼 Killing any existing app processes..."
pkill -f "python3 app.py" || true

# Step 8: Run the app in background with nohup
echo "🚀 Launching the app in background..."
nohup venv/bin/python3 app.py > log.txt 2>&1 &
APP_PID=$!

echo "✅ App started with PID: $APP_PID"
echo "📄 Last 10 lines of log:"
tail -n 10 log.txt

echo "📌 To monitor logs: tail -f /home/ubuntu/Document-QA/log.txt"
