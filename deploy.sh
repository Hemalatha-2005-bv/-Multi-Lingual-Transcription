#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# GCE VM setup & deploy script
# Run once on a fresh Debian/Ubuntu VM:  bash deploy.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_DIR="/var/www/transcription"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "==> 1. Update system packages"
sudo apt-get update -y

echo "==> 2. Install system dependencies"
sudo apt-get install -y ffmpeg nginx python3 python3-pip python3-venv curl

echo "==> 3. Install Node.js 20"
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

echo "==> 4. Create project directory"
sudo mkdir -p "$PROJECT_DIR"
sudo chown "$USER":"$USER" "$PROJECT_DIR"

echo "==> 5. Copy project files (assumes you cloned/uploaded to ~/transcription-app)"
cp -r ~/transcription-app/* "$PROJECT_DIR/"

echo "==> 6. Set up Python virtual environment"
python3 -m venv "$BACKEND_DIR/venv"
source "$BACKEND_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$BACKEND_DIR/requirements.txt"
deactivate

echo "==> 7. Copy and configure environment files"
if [ ! -f "$BACKEND_DIR/.env" ]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo "   ⚠  Edit $BACKEND_DIR/.env with your GCP credentials before running!"
fi

echo "==> 8. Build React frontend"
cd "$FRONTEND_DIR"
npm install
npm run build
cd -

echo "==> 9. Configure Nginx"
sudo cp "$PROJECT_DIR/nginx.conf" /etc/nginx/sites-available/transcription
sudo ln -sf /etc/nginx/sites-available/transcription /etc/nginx/sites-enabled/transcription
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

echo "==> 10. Create systemd service for FastAPI"
sudo tee /etc/systemd/system/transcription-api.service > /dev/null <<EOF
[Unit]
Description=Transcription API (FastAPI + Uvicorn)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$BACKEND_DIR/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1 --log-level info
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable transcription-api
sudo systemctl start transcription-api

echo ""
echo "✓ Deployment complete!"
echo "  API status: sudo systemctl status transcription-api"
echo "  API logs:   sudo journalctl -u transcription-api -f"
echo "  Frontend:   http://YOUR_VM_IP"
echo ""
echo "  Remember to:"
echo "  1. Edit $BACKEND_DIR/.env with real GCP credentials"
echo "  2. Create your GCS bucket and enable Speech-to-Text API"
echo "  3. Replace YOUR_VM_IP_OR_DOMAIN in nginx.conf"
echo "  4. (Optional) Set up HTTPS with certbot: sudo apt install certbot python3-certbot-nginx"
