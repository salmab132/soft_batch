#!/bin/bash
# Deploy FastAPI service to Google Cloud VM

set -e

PROJECT_ID="iap-2026-sundai"
INSTANCE_NAME="soft-batch-vm"
ZONE="us-central1-a"

echo "[*] Deploying FastAPI service to VM..."

# Transfer API files
echo "[*] Transferring files..."
gcloud compute scp --zone=$ZONE \
  api.py soft-batch-api.service \
  $INSTANCE_NAME:~/

# Install dependencies and set up service
echo "[*] Installing dependencies and configuring service..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
  set -e

  echo '[*] Installing Python dependencies...'
  python3 -m pip install --user fastapi 'uvicorn[standard]'

  echo '[*] Setting up systemd service...'
  sudo cp ~/soft-batch-api.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable soft-batch-api.service
  sudo systemctl restart soft-batch-api.service

  echo '[*] Waiting for service to start...'
  sleep 3

  echo '[*] Checking service status...'
  sudo systemctl status soft-batch-api.service --no-pager || true

  echo ''
  echo '[+] FastAPI service deployed successfully!'
  echo ''
  echo 'Service commands:'
  echo '  sudo systemctl status soft-batch-api   - Check status'
  echo '  sudo systemctl restart soft-batch-api  - Restart service'
  echo '  sudo systemctl stop soft-batch-api     - Stop service'
  echo '  sudo systemctl start soft-batch-api    - Start service'
  echo '  sudo journalctl -u soft-batch-api -f   - View logs'
  echo ''
  echo 'Test the API:'
  echo '  curl http://localhost:8000/'
  echo '  curl http://localhost:8000/health'
  echo '  curl http://localhost:8000/stats'
"

echo ""
echo "[+] Deployment complete!"
echo ""
echo "Get VM external IP:"
echo "  gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)'"
echo ""
echo "Open firewall (if needed):"
echo "  gcloud compute firewall-rules create allow-soft-batch-api --allow tcp:8000 --source-ranges 0.0.0.0/0 --target-tags=http-server"
echo ""
echo "Test API remotely:"
echo "  curl http://VM_EXTERNAL_IP:8000/health"
