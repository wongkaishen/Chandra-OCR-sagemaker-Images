#!/usr/bin/env python3
"""
Build custom Docker image and push to ECR for SageMaker deployment
This script is designed to run on Linux (Cloud9/EC2) where Docker creates Docker v2 manifests
Only builds and pushes to ECR - deploy manually via AWS Console
"""
import boto3
import subprocess
import os

# Configuration
REGION = "us-east-1"
ACCOUNT_ID = "563224522620"
IMAGE_NAME = "chandra-ocr-custom"
IMAGE_TAG = "latest"

# ECR repository URI
ECR_REPOSITORY = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{IMAGE_NAME}"
IMAGE_URI = f"{ECR_REPOSITORY}:{IMAGE_TAG}"

def check_prerequisites():
    """Check if Docker and AWS CLI are available"""
    print("="*70)
    print("CHECKING PREREQUISITES")
    print("="*70)
    
    # Check Docker
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        print(f"✅ Docker: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker first.")
        print("   sudo yum install -y docker")
        print("   sudo service docker start")
        exit(1)
    
    # Check AWS CLI
    try:
        result = subprocess.run(["aws", "--version"], capture_output=True, text=True)
        print(f"✅ AWS CLI: {result.stderr.strip()}")  # aws --version outputs to stderr
    except FileNotFoundError:
        print("❌ AWS CLI not found. Please install AWS CLI first.")
        exit(1)
    
    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS Account: {identity['Account']}")
        print(f"✅ AWS User: {identity['Arn']}")
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        print("   Run: aws configure")
        exit(1)
    
    print()

def build_and_push_image():
    """
    Build Docker image and push to ECR
    """
    print("="*70)
    print("STEP 1: BUILD AND PUSH DOCKER IMAGE")
    print("="*70)
    
    # Change to the directory containing the Dockerfile
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(script_dir, "sagemaker-custom-image")
    
    if not os.path.exists(image_dir):
        print(f"❌ sagemaker-custom-image directory not found!")
        print(f"   Looking for: {image_dir}")
        exit(1)
    
    os.chdir(image_dir)
    
    # Login to ECR
    print("\n📋 Logging in to ECR...")
    login_cmd = f"aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com"
    result = subprocess.run(login_cmd, shell=True)
    if result.returncode != 0:
        print("❌ ECR login failed")
        exit(1)
    print("   ✓ Login successful")
    
    # Create ECR repository if it doesn't exist
    print(f"\n📋 Creating ECR repository: {IMAGE_NAME}")
    ecr_client = boto3.client('ecr', region_name=REGION)
    try:
        ecr_client.create_repository(repositoryName=IMAGE_NAME)
        print(f"   ✓ Repository created")
    except ecr_client.exceptions.RepositoryAlreadyExistsException:
        print(f"   ✓ Repository already exists")
    
    # Delete existing image with 'latest' tag if it exists
    print(f"\n🗑️  Deleting old image from ECR (if exists)...")
    try:
        ecr_client.batch_delete_image(
            repositoryName=IMAGE_NAME,
            imageIds=[{'imageTag': IMAGE_TAG}]
        )
        print(f"   ✓ Old image deleted")
    except:
        print(f"   ✓ No old image to delete")
    
    # Build Docker image
    print(f"\n🐳 Building Docker image...")
    print(f"   This will take 5-7 minutes (downloading ~4GB of dependencies)...")
    build_cmd = f"docker build --platform linux/amd64 -t {IMAGE_NAME}:{IMAGE_TAG} ."
    
    # Remove existing local image if present
    subprocess.run(f"docker rmi {IMAGE_NAME}:{IMAGE_TAG} 2>/dev/null", shell=True)
    
    result = subprocess.run(build_cmd, shell=True)
    if result.returncode != 0:
        print("❌ Docker build failed")
        exit(1)
    print(f"   ✓ Image built: {IMAGE_NAME}:{IMAGE_TAG}")
    
    # Verify manifest type (Linux should create Docker v2)
    print(f"\n🔍 Verifying image manifest type...")
    inspect_cmd = f"docker inspect {IMAGE_NAME}:{IMAGE_TAG}"
    result = subprocess.run(inspect_cmd, shell=True, capture_output=True, text=True)
    if "oci" in result.stdout.lower():
        print(f"   ⚠️  Warning: Image may have OCI manifest")
    else:
        print(f"   ✓ Image appears to have Docker v2 manifest")
    
    # Tag image
    print(f"\n🏷️  Tagging image for ECR...")
    tag_cmd = f"docker tag {IMAGE_NAME}:{IMAGE_TAG} {IMAGE_URI}"
    subprocess.run(tag_cmd, shell=True, check=True)
    print(f"   ✓ Tagged as: {IMAGE_URI}")
    
    # Push to ECR
    print(f"\n⬆️  Pushing to ECR...")
    print(f"   This will take 3-5 minutes (pushing ~4GB compressed)...")
    push_cmd = f"docker push {IMAGE_URI}"
    result = subprocess.run(push_cmd, shell=True)
    if result.returncode != 0:
        print("❌ Docker push failed")
        exit(1)
    print(f"   ✓ Pushed to ECR")
    
    # Verify pushed image manifest
    print(f"\n🔍 Verifying ECR manifest type...")
    try:
        response = ecr_client.batch_get_image(
            repositoryName=IMAGE_NAME,
            imageIds=[{'imageTag': IMAGE_TAG}],
            acceptedMediaTypes=['application/vnd.docker.distribution.manifest.v2+json',
                              'application/vnd.oci.image.manifest.v1+json']
        )
        if response['images']:
            manifest_media_type = response['images'][0].get('imageManifest', '')
            if 'oci' in manifest_media_type:
                print(f"   ❌ ECR image has OCI manifest: {manifest_media_type}")
                print(f"   This may cause SageMaker deployment to fail")
            else:
                print(f"   ✅ ECR image has Docker v2 manifest")
    except Exception as e:
        print(f"   ⚠️  Could not verify manifest: {e}")
    
    # Change back to original directory
    os.chdir("..")
    
    print("\n✅ Docker image ready!")
    return IMAGE_URI

def main():
    """
    Main deployment flow - build and push to ECR only
    """
    print("="*70)
    print("CUSTOM DOCKER IMAGE BUILD FOR CHANDRA OCR")
    print("Building from Linux environment")
    print("Using transformers>=4.46.0 in custom container")
    print("="*70)
    print()
    
    # Check prerequisites
    check_prerequisites()
    
    # Build and push Docker image
    image_uri = build_and_push_image()
    
    print("\n" + "="*70)
    print("✅ BUILD COMPLETE!")
    print("="*70)
    print(f"\nECR Image URI: {image_uri}")
    print(f"Region: {REGION}")
    print(f"Account: {ACCOUNT_ID}")
    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print("1. Deploy to SageMaker via AWS Console:")
    print("   - See DEPLOY_FROM_ECR_CONSOLE.md for detailed steps")
    print(f"   - Use image: {image_uri}")
    print("   - IMPORTANT: Create as STANDARD endpoint (NOT inference components)")
    print("\n2. Recommended instance types:")
    print("   - ml.g4dn.xlarge   - $0.736/hour  (1 GPU, 16GB RAM)")
    print("   - ml.g4dn.2xlarge  - $0.94/hour   (1 GPU, 32GB RAM)")
    print("   - ml.g4dn.12xlarge - $4.89/hour   (4 GPUs, 192GB RAM)")
    print("\n3. When done, delete endpoint to save costs:")
    print("   aws sagemaker delete-endpoint --endpoint-name <your-endpoint-name>")
    print("="*70)

if __name__ == "__main__":
    main()
