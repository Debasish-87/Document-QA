#!/bin/bash
set -euo pipefail

# === Configuration ===
EC2_USER=ubuntu
EC2_HOST=3.110.124.251               # Replace with your EC2 public IP or DNS
SECRET_NAME="hackrx/ssh_private_key"  # Your secret name in Secrets Manager
REPO_URL="https://github.com/Debasish-87/Document-QA.git"
APP_DIR="/home/ubuntu/Document-QA"

echo "🚀 Starting remote deployment on EC2 instance $EC2_HOST..."

# Fetch the SSH private key from AWS Secrets Manager and save it locally
echo "🔐 Retrieving SSH private key from AWS Secrets Manager..."
aws secretsmanager get-secret-value --secret-id "$SECRET_NAME" --query SecretString --output text > hackRX.pem

# Set permissions so only the user can read the key
chmod 400 hackRX.pem

# Use the private key to SSH into EC2 and run the deployment commands
ssh -o StrictHostKeyChecking=no -i hackRX.pem "$EC2_USER@$EC2_HOST" bash -s <<EOF
set -euo pipefail

timestamp() {
  date +"[%Y-%m-%d %H:%M:%S]"
}

echo "\$(timestamp) Updating system and installing dependencies..."

# Update and install necessary packages
sudo apt-get update -y
sudo apt-get install -y ruby python3-pip python3-dev git build-essential libgl1 poppler-utils ghostscript python3-opencv tesseract-ocr libglib2.0-0 libsm6 libxrender1 libxext6 python3.12-venv wget

# Install CodeDeploy agent if missing
if ! systemctl is-active --quiet codedeploy-agent; then
  echo "\$(timestamp) Installing CodeDeploy agent..."
  cd /tmp
  wget https://aws-codedeploy-ap-south-1.s3.ap-south-1.amazonaws.com/latest/install -O install
  chmod +x install
  sudo ./install auto
  sudo systemctl start codedeploy-agent
  sudo systemctl enable codedeploy-agent
else
  echo "\$(timestamp) CodeDeploy agent is already installed and running."
fi

# Clone or update the application repository
if [ ! -d "$APP_DIR" ]; then
  echo "\$(timestamp) Cloning Document-QA repository..."
  git clone "$REPO_URL" "$APP_DIR"
else
  echo "\$(timestamp) Updating existing Document-QA repository..."
  cd "$APP_DIR"
  git pull origin main || git pull  # fallback if no origin/main
fi

cd "$APP_DIR"

# Create Python virtual environment if it does not exist
if [ ! -d "venv" ]; then
  echo "\$(timestamp) Creating Python virtual environment..."
  python3 -m venv venv
fi

# Ensure ownership to ubuntu user
sudo chown -R ubuntu:ubuntu venv

# Activate venv and install dependencies
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install "camelot-py[cv]"

# Setup .env file with API keys if missing (note: values come from your remote env)
if [ ! -f ".env" ]; then
  echo "\$(timestamp) Creating .env file with API keys..."
  echo "GEMINI_API_KEY=\${GEMINI_API_KEY:-}" > .env
  echo "API_TOKEN=\${API_TOKEN:-}" >> .env
else
  echo "\$(timestamp) .env file exists."
fi

sudo chown -R ubuntu:ubuntu .

# Gracefully restart the app
APP_NAME="python3 app.py"
echo "\$(timestamp) Stopping old app processes if any..."
pkill -f "\$APP_NAME" || echo "\$(timestamp) No running app processes found."

echo "\$(timestamp) Starting the app in background..."
nohup venv/bin/python3 app.py > log.txt 2>&1 &

echo "\$(timestamp) Deployment completed successfully."
EOF

# Clean up the temporary key file
rm -f hackRX.pem

echo "✅ Remote deployment script finished."
