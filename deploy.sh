#!/bin/bash
# Deployment script for soft_batch on Google Cloud VM

set -e

PROJECT_ID="iap-2026-sundai"
INSTANCE_NAME="soft-batch-vm"
ZONE="us-central1-a"
MACHINE_TYPE="e2-medium"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"

echo "🚀 Creating VM instance: $INSTANCE_NAME"

# Create the VM instance
gcloud compute instances create $INSTANCE_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=$MACHINE_TYPE \
  --image-family=$IMAGE_FAMILY \
  --image-project=$IMAGE_PROJECT \
  --boot-disk-size=20GB \
  --boot-disk-type=pd-standard \
  --tags=http-server,https-server \
  --metadata=startup-script='#!/bin/bash
    apt-get update
    apt-get install -y python3 python3-pip git
    pip3 install --upgrade pip
  '

echo "⏳ Waiting for VM to be ready..."
sleep 30

echo "📦 Transferring files to VM..."
# Transfer all Python files
gcloud compute scp --zone=$ZONE \
  main.py articles.py llm.py mastodon_client.py notion.py replicate_client.py requirements.txt \
  $INSTANCE_NAME:~/

echo "🔧 Setting up Python environment on VM..."
# SSH into VM and set up environment
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
  cd ~
  python3 -m pip install --user -r requirements.txt
  echo '✅ Setup complete!'
  echo ''
  echo 'To run your application:'
  echo '  python3 main.py'
  echo '  python3 main.py baking --articles 5 --comments 2'
"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "To SSH into your VM:"
echo "  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "To run your application:"
echo "  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='cd ~ && python3 main.py'"
echo ""
echo "To stop the VM:"
echo "  gcloud compute instances stop $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "To delete the VM:"
echo "  gcloud compute instances delete $INSTANCE_NAME --zone=$ZONE"
