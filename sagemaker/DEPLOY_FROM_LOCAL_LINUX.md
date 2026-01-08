# Deploy from Your Own Linux Machine

If you have Linux (Ubuntu, Debian, Fedora, etc.) or WSL2 on Windows, you can deploy directly from your local machine.

## Prerequisites

- Linux OS or WSL2 (Windows Subsystem for Linux)
- Internet connection
- AWS credentials (Access Key ID and Secret Access Key)

## Step 1: Install Required Packages

### For Ubuntu/Debian/WSL2:
```bash
# Update package list
sudo apt-get update

# Install Docker
sudo apt-get install -y docker.io

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group (avoid using sudo for docker commands)
sudo usermod -aG docker $USER

# Install Python and pip
sudo apt-get install -y python3 python3-pip git

# Log out and back in for group changes to take effect
# For WSL2: close and reopen terminal
# For Linux: logout and login again
```

### For Fedora/RHEL/Amazon Linux:
```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker git python3-pip

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Log out and back in
```

## Step 2: Install Python Packages

```bash
# Install boto3 and sagemaker
pip3 install boto3 "sagemaker<3"

# Verify installation
python3 -c "import boto3; print('boto3 version:', boto3.__version__)"
```

## Step 3: Configure AWS Credentials

```bash
# Configure AWS CLI
aws configure
```

Enter your credentials:
- **AWS Access Key ID**: (your access key)
- **AWS Secret Access Key**: (your secret key)
- **Default region name**: `us-east-1`
- **Default output format**: `json`

## Step 4: Clone Repository (if not already)

```bash
# If you already have the code locally, skip this
cd ~
git clone https://github.com/wongkaishen/Data-collection-and-storage.git
cd Data-collection-and-storage/backend
```

**Or if you already have the code:**
```bash
cd /path/to/your/Data-collection-and-storage/backend
```

## Step 5: Verify Docker is Running

```bash
# Check Docker is accessible (should not require sudo)
docker ps

# If you get permission denied, logout and login again
# Or run: newgrp docker
```

## Step 6: Run Deployment

```bash
# Make sure you're in the backend directory
cd Data-collection-and-storage/backend

# Run the deployment script
python3 deploy_custom_docker_linux.py
```

This will:
1. ✅ Build Docker image with transformers 4.57.2 (~5-7 minutes)
2. ✅ Create Docker v2 schema 2 manifest (SageMaker compatible)
3. ✅ Push to ECR (~3-5 minutes for 4.2GB image)
4. ✅ Deploy to SageMaker endpoint (~10-15 minutes)
5. ✅ Wait for endpoint to be ready

**Total time: ~25-35 minutes**

## Step 7: Monitor Progress

The script will show progress:
```
🔨 Building Docker image...
[+] Building 345.2s (11/11) FINISHED
✅ Build completed

📤 Pushing to ECR...
✅ Push completed

🚀 Deploying to SageMaker...
⏳ Waiting for endpoint to be ready...
✅ Endpoint is InService!

Endpoint URL: chandra-ocr-custom-endpoint
```

## Step 8: Test the Endpoint

```bash
# Test the deployment
python3 test_endpoint.py
```

## Step 9: Cleanup (Stop Billing)

```bash
# Delete the endpoint when not in use
aws sagemaker delete-endpoint --endpoint-name chandra-ocr-custom-endpoint
```

---

## Troubleshooting

### Docker permission denied

```bash
# Make sure you're in the docker group
groups

# If 'docker' is not listed, add yourself and reload:
sudo usermod -aG docker $USER
newgrp docker

# Or logout and login again
```

### Docker daemon not running

```bash
# Start Docker
sudo systemctl start docker

# Check status
sudo systemctl status docker
```

### AWS credentials not configured

```bash
# Check current configuration
aws sts get-caller-identity

# If it fails, reconfigure
aws configure
```

### Out of disk space during Docker build

```bash
# Check disk space
df -h

# Clean Docker cache
docker system prune -a -f

# Free up at least 10GB for the build
```

### Out of memory during Docker build

```bash
# Check available memory
free -h

# If you have less than 4GB RAM, create swap:
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## Advantages of Local Linux

✅ **No EC2 costs** - Free (except SageMaker endpoint)
✅ **Faster internet** - Likely faster than EC2 for large downloads
✅ **No SSH needed** - Work directly on your machine
✅ **Reusable** - Can rebuild/redeploy anytime
✅ **No instance management** - No need to start/stop EC2

## Requirements

- **Disk space**: At least 10GB free
- **RAM**: At least 4GB (8GB recommended)
- **Internet**: Stable connection for downloading PyTorch (~2GB)
- **Time**: ~25-35 minutes for full deployment

---

## WSL2 on Windows (Special Notes)

If using WSL2:

1. Make sure you have WSL2 (not WSL1):
   ```bash
   wsl --list --verbose
   # Should show VERSION 2
   ```

2. Docker Desktop is NOT needed - install Docker directly in WSL2:
   ```bash
   sudo apt-get install docker.io
   ```

3. This will create Docker v2 manifests (SageMaker compatible)!

4. Access your Windows files from WSL2:
   ```bash
   cd /mnt/c/Users/wongk/Documents/Github/Data-collection-and-storage/backend
   ```

---

## Summary

Your local Linux machine can deploy to SageMaker just like EC2, but:
- ✅ No EC2 costs
- ✅ Faster if you have good internet
- ✅ More convenient (no SSH)
- ⚠️ Still costs ~$4.89/hour for SageMaker endpoint

Once deployed, the Docker image stays in ECR, so you only need to do this once!
