#!/bin/bash
set -euo pipefail

# === Configuration ===
EC2_USER="ubuntu"
EC2_HOST="3.110.124.251"
REPO_URL="https://github.com/Debasish-87/Document-QA.git"
APP_DIR="/home/ubuntu/Document-QA"
SECRET_NAME="hackrx/ssh_private_key"   # AWS Secrets Manager secret name

echo "🚀 Starting remote deployment on EC2 instance $EC2_HOST..."

# Fetch SSH private key from AWS Secrets Manager
echo "🔐 Retrieving SSH private key from AWS Secrets Manager..."
PRIVATE_KEY=$(aws secretsmanager get-secret-value --secret-id "$SECRET_NAME" --query SecretString --output text)

if [[ -z "$PRIVATE_KEY" ]]; then
  echo "❌ ERROR: Retrieved secret is empty or invalid!"
  exit 1
fi

# Save private key to a temp file
TMP_KEY_FILE=$(mktemp)
echo "$PRIVATE_KEY" > "$TMP_KEY_FILE"
chmod 400 "$TMP_KEY_FILE"

echo "🔧 Connecting to EC2 instance $EC2_HOST..."

ssh -o StrictHostKeyChecking=no -i "$TMP_KEY_FILE" "$EC2_USER@$EC2_HOST" bash -s <<'EOF'
set -euo pipefail

timestamp() {
  date +"[%Y-%m-%d %H:%M:%S]"
}

echo "$(timestamp) 🔧 Updating system and installing dependencies..."
sudo apt-get update -y
sudo apt-get install -y ruby python3-pip python3-dev git build-essential libgl1 poppler-utils ghostscript python3-opencv tesseract-ocr libglib2.0-0 libsm6 libxrender1 libxext6 python3.12-venv wget

# Install CodeDeploy agent if not running
if ! systemctl is-active --quiet codedeploy-agent; then
  echo "$(timestamp) Installing CodeDeploy agent..."
  cd /tmp
  wget https://aws-codedeploy-ap-south-1.s3.ap-south-1.amazonaws.com/latest/install -O install
  chmod +x install
  sudo ./install auto
  sudo systemctl start codedeploy-agent
  sudo systemctl enable codedeploy-agent
else
  echo "$(timestamp) ✅ CodeDeploy agent is already running."
fi

# Clone or pull repo
APP_DIR="/home/ubuntu/Document-QA"
REPO_URL="https://github.com/Debasish-87/Document-QA.git"
if [ ! -d "$APP_DIR" ]; then
  echo "$(timestamp) 📦 Cloning repository..."
  git clone "$REPO_URL" "$APP_DIR"
else
  echo "$(timestamp) 🔁 Updating repository..."
  cd "$APP_DIR"
  git pull origin main || git pull
fi

cd "$APP_DIR"

# Setup Python virtual environment
if [ ! -d "venv" ]; then
  echo "$(timestamp) 🐍 Creating virtual environment..."
  python3 -m venv venv
fi

sudo chown -R ubuntu:ubuntu venv

source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install "camelot-py[cv]"

# Setup environment variables
if [ ! -f ".env" ]; then
  echo "$(timestamp) 📄 Creating .env file..."
  echo "GEMINI_API_KEY=${GEMINI_API_KEY:-}" > .env
  echo "API_TOKEN=${API_TOKEN:-}" >> .env
else
  echo "$(timestamp) ✅ .env file already exists."
fi

sudo chown -R ubuntu:ubuntu .

# Restart app
APP_NAME="python3 app.py"
echo "$(timestamp) 🔌 Stopping previous app instance..."
pkill -f "$APP_NAME" || echo "$(timestamp) No existing app process found."

echo "$(timestamp) 🚀 Starting app in background..."
nohup venv/bin/python3 app.py > log.txt 2>&1 &

echo "$(timestamp) ✅ Deployment completed successfully."
EOF

# Cleanup temp private key file
rm -f "$TMP_KEY_FILE"

echo "✅ Remote deployment script finished."
