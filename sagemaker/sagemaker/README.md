# SageMaker Chandra OCR Container

This folder contains everything needed to build and deploy the Chandra OCR model to AWS SageMaker.

---

## 📁 Folder Structure

```
sagemaker/
├── README.md                           # This file
├── deploy_custom_docker_linux.py       # Build & push Docker image (Linux/Cloud9)
├── update_endpoint_with_timeout.py     # Update endpoint configuration
│
├── sagemaker-custom-image/             # Docker image source
│   ├── Dockerfile                      # Container definition
│   ├── requirements.txt                # Python dependencies
│   └── src/
│       └── inference.py                # SageMaker inference handler
│
└── code/                               # Alternative inference code
    ├── inference.py                    # Simplified inference handler
    └── requirements.txt                # Dependencies
```

---

## 🚀 Quick Start

### Option 1: Use Management Script (Recommended)

From project root:
```bash
python scripts/manage_sagemaker.py status   # Check endpoint
python scripts/manage_sagemaker.py deploy   # Deploy endpoint
python scripts/manage_sagemaker.py stop     # Stop endpoint (save money)
```

### Option 2: Build Custom Image (Advanced)

**Prerequisites:**
- Linux environment (AWS Cloud9, EC2, or WSL)
- Docker installed
- AWS CLI configured

**Build and Push:**
```bash
cd sagemaker
python deploy_custom_docker_linux.py
```

This will:
1. Build Docker image with Chandra OCR
2. Push to AWS ECR
3. Show deployment instructions

---

## 🐳 Docker Image Details

### Base Image
- PyTorch 2.5.1 with CUDA 11.8
- Compatible with AWS SageMaker GPU instances

### Key Components

**sagemaker-custom-image/src/inference.py:**
- Official chandra-ocr package integration
- Uses `Qwen3VLForConditionalGeneration` model
- Memory optimizations:
  - dtype=torch.bfloat16
  - gradient_checkpointing
  - device_map="auto"
- Image preprocessing (max 2048px)
- GPU enforcement (fails if CUDA not available)

**Key Dependencies:**
```
transformers>=4.46.0
torch==2.5.1+cu118
chandra-ocr
qwen-vl-utils
pillow
numpy
```

### Image Size
- Uncompressed: ~10 GB
- Compressed (ECR): ~4 GB
- Build time: 5-7 minutes
- Push time: 3-5 minutes

---

## ⚙️ SageMaker Configuration

### Recommended Instances

| Instance | GPU | VRAM | RAM | Cost/hr | Use Case |
|----------|-----|------|-----|---------|----------|
| ml.g5.2xlarge | A10G | 24GB | 32GB | $1.515 | **Recommended** - Best price/performance |
| ml.g4dn.2xlarge | T4 | 16GB | 32GB | $0.94 | Budget option (may OOM on large images) |
| ml.g4dn.12xlarge | 4xT4 | 64GB | 192GB | $4.89 | High throughput (expensive) |

### Endpoint Configuration

**Timeouts (CRITICAL):**
```python
{
    'ModelDataDownloadTimeoutInSeconds': 1200,  # 20 minutes
    'ContainerStartupHealthCheckTimeoutInSeconds': 1200
}
```

**Container Configuration:**
```python
{
    'Image': '<ECR-IMAGE-URI>',
    'Mode': 'SingleModel'  # NOT inference components!
}
```

**Environment Variables:**
```python
# No special env vars needed
# All config is in inference.py
```

---

## 🔧 Deployment Methods

### Method 1: AWS Console (Manual)

1. **Build and push image:**
   ```bash
   cd sagemaker
   python deploy_custom_docker_linux.py
   ```

2. **Create Model:**
   - Go to SageMaker → Models → Create model
   - Use ECR image URI from step 1
   - Select IAM role with SageMaker permissions

3. **Create Endpoint Config:**
   - Name: `chandra-ocr-endpoint-config`
   - Instance: `ml.g5.2xlarge`
   - Set timeouts to 1200 seconds

4. **Create Endpoint:**
   - Name: `chandra-ocr-endpoint`
   - Use config from step 3
   - Wait 5-10 minutes for deployment

### Method 2: Management Script (Automated)

```bash
# From project root
python scripts/manage_sagemaker.py deploy
```

This handles everything automatically!

### Method 3: Update Existing Endpoint

```bash
cd sagemaker
python update_endpoint_with_timeout.py
```

Updates endpoint configuration (instance type, timeouts).

---

## 📊 Monitoring

### CloudWatch Logs

```bash
# View logs
aws logs tail /aws/sagemaker/Endpoints/chandra-ocr-endpoint --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/sagemaker/Endpoints/chandra-ocr-endpoint \
  --filter-pattern "ERROR"
```

### Key Metrics

- `ModelLatency` - Inference time
- `Invocations` - Request count
- `Invocation4XXErrors` - Client errors
- `Invocation5XXErrors` - Server errors
- `GPUUtilization` - GPU usage
- `GPUMemoryUtilization` - VRAM usage

### Expected Performance

**First Request (Cold Start):**
- Time: 5-6 minutes
- Reason: Model loading (13GB)
- GPU memory: 13GB

**Subsequent Requests (Warm):**
- Time: 10-30 seconds
- GPU memory: 24GB (13GB model + 11GB inference)

---

## 🐛 Troubleshooting

### Build Issues

**Problem: Docker permission denied**
```bash
# Fix (Linux)
sudo usermod -aG docker $USER
sudo service docker restart
# Log out and back in
```

**Problem: Out of disk space**
```bash
# Clean up Docker
docker system prune -a
```

### Deployment Issues

**Problem: Endpoint timeout**
- Solution: Ensure timeouts set to 1200s
- Use: `update_endpoint_with_timeout.py`

**Problem: OOM error**
- Solution: Use ml.g5.2xlarge (24GB VRAM)
- Images auto-resize to 2048px max

**Problem: Inference Component error**
- Solution: Set `SAGEMAKER_INFERENCE_COMPONENT_NAME=` (blank)
- We use STANDARD endpoint, not inference components

### Runtime Issues

**Problem: CUDA not available**
- Check: Instance type has GPU
- Fix: Use ml.g5.x or ml.g4dn.x instances

**Problem: Model loading fails**
- Check CloudWatch logs
- Verify internet connectivity (downloads model from HuggingFace)
- Increase timeout to 1200s

---

## 💰 Cost Management

### Daily Costs (24/7)

- ml.g5.2xlarge: $1.515/hr = $36.36/day
- ml.g4dn.2xlarge: $0.94/hr = $22.56/day
- ml.g4dn.12xlarge: $4.89/hr = $117.36/day

### Cost Saving Strategies

1. **Delete endpoint when not in use:**
   ```bash
   python scripts/manage_sagemaker.py stop
   ```

2. **Use smaller instance for testing:**
   ```bash
   python scripts/manage_sagemaker.py deploy --instance-type ml.g4dn.2xlarge
   ```

3. **Schedule deletion:**
   - Delete at end of workday
   - Recreate next morning
   - Save 16 hours/day = ~$24/day

4. **Batch processing:**
   - Upload multiple documents at once
   - Process in bulk
   - Reduces total endpoint time

---

## 🔐 Security

### IAM Role Permissions

Required permissions:
- `sagemaker:CreateModel`
- `sagemaker:CreateEndpointConfig`
- `sagemaker:CreateEndpoint`
- `sagemaker:DescribeEndpoint`
- `sagemaker:DeleteEndpoint`
- `ecr:GetAuthorizationToken`
- `ecr:BatchGetImage`
- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`

### Network Security

- Endpoints are public by default
- For production: Deploy in VPC
- Use security groups to restrict access
- Enable encryption at rest

---

## 📚 Additional Resources

- [Main Handbook](../HANDBOOK.md) - Complete project guide
- [Quick Reference](../QUICK_REFERENCE.md) - Command cheatsheet
- [SageMaker Docs](https://docs.aws.amazon.com/sagemaker/)
- [Chandra OCR](https://huggingface.co/datalab-to/chandra)

---

## 🆘 Support

**For issues:**
1. Check [HANDBOOK.md](../HANDBOOK.md) → Troubleshooting
2. Check CloudWatch logs
3. Review this README
4. Check AWS SageMaker console for errors

**Common fixes:**
- Timeout: Set 1200s in endpoint config
- OOM: Use ml.g5.2xlarge instance
- Inference component error: Leave env var blank
- Build fails: Use Linux environment (Cloud9/EC2)

---

**Last Updated:** November 27, 2025  
**Version:** 1.0  
**Maintained by:** wongkaishen
