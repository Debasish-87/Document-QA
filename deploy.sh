#!/bin/bash
set -euo pipefail

# === Configuration ===
EC2_USER="ubuntu"
EC2_HOST="3.110.124.251"
REPO_URL="https://github.com/Debasish-87/Document-QA.git"
APP_DIR="/home/ubuntu/Document-QA"
SECRET_NAME="hackrx/ssh_private_key"

# === Logging ===
timestamp() {
  date +"[%Y-%m-%d %H:%M:%S]"
}

log() {
  echo "$(timestamp) $1"
}

log "🚀 Starting remote deployment to EC2 instance: $EC2_HOST"

# === Fetch private key from Secrets Manager ===
log "🔐 Fetching SSH private key from AWS Secrets Manager: $SECRET_NAME"

TMP_KEY_FILE=$(mktemp)

if ! aws secretsmanager get-secret-value \
  --secret-id "$SECRET_NAME" \
  --query SecretString \
  --output text > "$TMP_KEY_FILE"; then
  log "❌ ERROR: Failed to retrieve secret: $SECRET_NAME"
  exit 1
fi

if [[ ! -s "$TMP_KEY_FILE" ]]; then
  log "❌ ERROR: Retrieved private key is empty"
  rm -f "$TMP_KEY_FILE"
  exit 1
fi

chmod 400 "$TMP_KEY_FILE"

# === SSH and Deploy ===
log "🔧 Connecting to EC2 and starting deployment..."

ssh -o StrictHostKeyChecking=no -i "$TMP_KEY_FILE" "$EC2_USER@$EC2_HOST" bash -s <<'EOF'
set -euo pipefail

timestamp() {
  date +"[%Y-%m-%d %H:%M:%S]"
}

log() {
  echo "$(timestamp) $1"
}

log "🔧 Updating system and installing dependencies..."
sudo apt-get update -y
sudo apt-get install -y ruby python3-pip python3-dev git build-essential libgl1 poppler-utils ghostscript python3-opencv tesseract-ocr libglib2.0-0 libsm6 libxrender1 libxext6 python3.12-venv wget

log "🛠️ Checking CodeDeploy agent..."
if ! systemctl is-active --quiet codedeploy-agent; then
  log "📦 Installing CodeDeploy agent..."
  cd /tmp
  wget https://aws-codedeploy-ap-south-1.s3.ap-south-1.amazonaws.com/latest/install -O install
  chmod +x install
  sudo ./install auto
  sudo systemctl start codedeploy-agent
  sudo systemctl enable codedeploy-agent
else
  log "✅ CodeDeploy agent is already active."
fi

APP_DIR="/home/ubuntu/Document-QA"
REPO_URL="https://github.com/Debasish-87/Document-QA.git"

if [ ! -d "$APP_DIR" ]; then
  log "📁 Cloning repository..."
  git clone "$REPO_URL" "$APP_DIR"
else
  log "🔁 Pulling latest code..."
  cd "$APP_DIR"
  git reset --hard
  git pull origin main || git pull
fi

cd "$APP_DIR"

if [ ! -d "venv" ]; then
  log "🐍 Creating virtual environment..."
  python3 -m venv venv
fi

sudo chown -R ubuntu:ubuntu venv
source venv/bin/activate

log "📦 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install "camelot-py[cv]"

if [ ! -f ".env" ]; then
  log "🔑 Creating .env file..."
  echo "GEMINI_API_KEY=${GEMINI_API_KEY:-}" > .env
  echo "API_TOKEN=${API_TOKEN:-}" >> .env
else
  log "✅ .env file already exists."
fi

sudo chown -R ubuntu:ubuntu .

APP_NAME="python3 app.py"
log "🛑 Stopping previous app if running..."
pkill -f "$APP_NAME" || log "No previous app process found."

log "🚀 Starting app..."
nohup venv/bin/python3 app.py > log.txt 2>&1 &

log "✅ App deployed and running successfully."
EOF

# === Cleanup ===
log "🧹 Cleaning up temporary private key file..."
rm -f "$TMP_KEY_FILE"

log "✅ Deployment script completed successfully."
