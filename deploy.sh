#!/bin/bash
set -e

# EC2 instance details
EC2_USER=ubuntu
EC2_HOST=3.110.124.251  # Replace with your instance's public IP or DNS
KEY_PATH=/path/to/hackRX.pem  # Path to your private key for SSH access

echo "🚀 Starting remote deployment on EC2 instance..."

ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" $EC2_USER@$EC2_HOST << 'EOF'
set -e

echo "Updating system and installing dependencies..."
sudo apt update
sudo apt install -y ruby python3-pip python3-dev git build-essential libgl1 poppler-utils ghostscript python3-opencv tesseract-ocr libglib2.0-0 libsm6 libxrender1 libxext6 python3.12-venv

cd /home/ubuntu

# Download and install CodeDeploy agent if not installed
if ! command -v codedeploy-agent &> /dev/null; then
  echo "Installing CodeDeploy agent..."
  wget https://aws-codedeploy-ap-south-1.s3.ap-south-1.amazonaws.com/latest/install
  chmod +x ./install
  sudo ./install auto
  sudo service codedeploy-agent start
fi

# Clone or update the repo
if [ ! -d "Document-QA" ]; then
  echo "Cloning Document-QA repository..."
  git clone https://github.com/Debasish-87/Document-QA.git
else
  echo "Updating existing Document-QA repository..."
  cd Document-QA
  git pull
  cd ..
fi

cd Document-QA

# Setup Python virtual environment if missing
if [ ! -d "venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv venv
fi

# Change ownership of venv folder to ubuntu user
sudo chown -R ubuntu:ubuntu venv

# Activate virtual environment and install requirements
source venv/bin/activate
pip install --upgrade pip setuptools
pip install -r requirements.txt
pip install "camelot-py[cv]"

# Setup .env file with API keys
if [ ! -f ".env" ]; then
  echo "Creating .env file with API keys..."
  echo "GEMINI_API_KEY=$GEMINI_API_KEY" > .env
  echo "API_TOKEN=$API_TOKEN" >> .env
else
  echo ".env file exists."
fi

sudo chown -R ubuntu:ubuntu .

# Kill old app processes and start new one
pkill -f "python3 app.py" || true

echo "Starting the app in background..."
nohup venv/bin/python3 app.py > log.txt 2>&1 &

echo "Deployment completed on EC2."
EOF
