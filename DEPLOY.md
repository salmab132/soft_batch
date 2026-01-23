# Deployment Commands for Google Cloud VM

## Quick Deploy (All-in-One)

Run the deployment script:
```bash
bash deploy.sh
```

## Manual Step-by-Step Commands

### 1. Create the VM Instance

```bash
gcloud compute instances create soft-batch-vm \
  --project=iap-2026-sundai \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --boot-disk-type=pd-standard \
  --tags=http-server,https-server
```

### 2. Wait for VM to be ready (30-60 seconds)

```bash
# Check VM status
gcloud compute instances describe soft-batch-vm --zone=us-central1-a --format="get(status)"
```

### 3. Transfer your files to the VM

```bash
gcloud compute scp --zone=us-central1-a \
  main.py articles.py llm.py mastodon_client.py notion.py replicate_client.py requirements.txt \
  soft-batch-vm:~/
```

### 4. SSH into the VM and set up environment

```bash
gcloud compute ssh soft-batch-vm --zone=us-central1-a
```

Once inside the VM, run:

```bash
# Update system
sudo apt-get update

# Install Python and pip
sudo apt-get install -y python3 python3-pip git

# Upgrade pip
python3 -m pip install --upgrade pip

# Install dependencies
python3 -m pip install --user -r requirements.txt

# Create .env file (you'll need to add your API keys)
nano .env
# Add your environment variables:
# OPENAI_API_KEY=your_key_here
# NOTION_API_KEY=your_key_here
# MASTODON_ACCESS_TOKEN=your_token_here
# MASTODON_API_BASE_URL=your_url_here
# REPLICATE_API_TOKEN=your_token_here
```

### 5. Run your application

```bash
# Run the default post flow
python3 main.py

# Run the baking flow
python3 main.py baking --articles 5 --comments 2
```

## Useful Management Commands

### SSH into VM
```bash
gcloud compute ssh soft-batch-vm --zone=us-central1-a
```

### Run command remotely
```bash
gcloud compute ssh soft-batch-vm --zone=us-central1-a --command="cd ~ && python3 main.py"
```

### Transfer updated files
```bash
gcloud compute scp --zone=us-central1-a \
  main.py articles.py llm.py mastodon_client.py notion.py replicate_client.py requirements.txt \
  soft-batch-vm:~/
```

### Stop the VM (to save costs)
```bash
gcloud compute instances stop soft-batch-vm --zone=us-central1-a
```

### Start the VM
```bash
gcloud compute instances start soft-batch-vm --zone=us-central1-a
```

### Delete the VM
```bash
gcloud compute instances delete soft-batch-vm --zone=us-central1-a
```

### View VM details
```bash
gcloud compute instances describe soft-batch-vm --zone=us-central1-a
```

## Setting up Environment Variables

After SSHing into the VM, create a `.env` file in your home directory:

```bash
nano ~/.env
```

Add your API keys:
```
OPENAI_API_KEY=sk-...
NOTION_API_KEY=secret_...
MASTODON_ACCESS_TOKEN=...
MASTODON_API_BASE_URL=https://...
REPLICATE_API_TOKEN=r8_...
```

## Running as a Service (Optional)

To run your application as a systemd service that starts on boot:

1. Create a service file on the VM:
```bash
sudo nano /etc/systemd/system/soft-batch.service
```

2. Add this content:
```ini
[Unit]
Description=Soft Batch Application
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME
Environment="PATH=/home/YOUR_USERNAME/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 /home/YOUR_USERNAME/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable soft-batch.service
sudo systemctl start soft-batch.service
```
