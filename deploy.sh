#!/bin/bash
set -e

echo "🚀 Starting deployment of Document-QA..."

# Update system and install Ruby (required for CodeDeploy agent)
sudo apt update
sudo apt install -y ruby

# Navigate to home directory
cd /home/ubuntu

# Download and install CodeDeploy agent
wget https://aws-codedeploy-ap-south-1.s3.ap-south-1.amazonaws.com/latest/install
chmod +x ./install
sudo ./install auto
sudo service codedeploy-agent start

echo "🔧 Installing system packages..."
sudo apt update
sudo apt install -y python3-pip python3-dev git build-essential libgl1 poppler-utils ghostscript python3-opencv tesseract-ocr libglib2.0-0 libsm6 libxrender1 libxext6

cd /home/ubuntu

# Clone repo if not present, else update it
if [ ! -d "Document-QA" ]; then
  echo "📥 Cloning Document-QA repository..."
  git clone https://github.com/Debasish-87/Document-QA.git
else
  echo "📁 Updating existing Document-QA repository..."
  cd Document-QA
  git pull
fi

cd Document-QA

# Setup Python virtual environment if missing
if [ ! -d "venv" ]; then
  echo "🐍 Creating Python virtual environment..."
  sudo apt install -y python3.12-venv
  python3 -m venv venv
fi

# Change ownership of venv folder to ubuntu user
sudo chown -R ubuntu:ubuntu venv

# Activate virtual environment
source venv/bin/activate

echo "📦 Installing Python dependencies..."
pip install --upgrade pip setuptools
pip install -r requirements.txt
pip install "camelot-py[cv]"

# Setup .env file with API keys if it doesn't exist
if [ ! -f ".env" ]; then
  echo "⚙️  Creating .env file with API keys..."
  echo "GEMINI_API_KEY=$GEMINI_API_KEY" > .env
  echo "API_TOKEN=$API_TOKEN" >> .env
else
  echo "ℹ️  .env file exists."
fi

# Ensure ownership of all files is set to ubuntu user
sudo chown -R ubuntu:ubuntu .

echo "🧼 Cleaning up old app processes (if any)..."
pkill -f "python3 app.py" || true

echo "🚀 Starting the app in background..."
nohup venv/bin/python3 app.py > log.txt 2>&1 &

APP_PID=$!
echo "✅ App running with PID $APP_PID"
tail -n 10 log.txt

echo "📌 Use 'tail -f log.txt' to follow logs."
