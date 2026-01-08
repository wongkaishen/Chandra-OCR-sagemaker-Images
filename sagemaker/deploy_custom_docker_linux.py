import boto3
import subprocess
import os
import sys
import time

# Configuration
REGION = boto3.session.Session().region_name
ACCOUNT_ID = boto3.client('sts').get_caller_identity().get('Account')
IMAGE_NAME = "chandra-ocr"
TAG = "latest"
ECR_URI = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{IMAGE_NAME}:{TAG}"
SAGEMAKER_ROLE = "arn:aws:iam::{}:role/service-role/AmazonSageMaker-ExecutionRole-20251123T165775" # Placeholder - update this!
INSTANCE_TYPE = "ml.g5.2xlarge"

def run_command(command):
    print(f"Running: {command}")
    try:
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        sys.exit(1)

def get_role():
    try:
        # Try to guess role or ask user to provide it
        iam = boto3.client('iam')
        roles = iam.list_roles()
        for role in roles['Roles']:
            if 'SageMaker' in role['RoleName'] and 'Execution' in role['RoleName']:
                return role['Arn']
        print("Could not find a SageMaker Execution Role automatically.")
        return input("Please enter your SageMaker Execution Role ARN: ")
    except Exception as e:
        print(f"Error getting roles: {e}")
        return input("Please enter your SageMaker Execution Role ARN: ")

def main():
    print(f"Deploying {IMAGE_NAME} to Region: {REGION} Account: {ACCOUNT_ID}")
    
    # 1. Login to ECR
    login_cmd = f"aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com"
    run_command(login_cmd)
    
    # 2. Create Repository if not exists
    ecr_client = boto3.client('ecr', region_name=REGION)
    try:
        ecr_client.create_repository(repositoryName=IMAGE_NAME)
        print(f"Repository {IMAGE_NAME} created.")
    except ecr_client.exceptions.RepositoryAlreadyExistsException:
        print(f"Repository {IMAGE_NAME} already exists.")
        
    # 3. Build Docker Image
    print("Building Docker image...")
    # Navigate to the directory containing Dockerfile
    build_dir = "sagemaker-custom-image"
    if not os.path.exists(build_dir):
        print(f"Error: Directory {build_dir} not found. Run this script from the 'sagemaker' directory.")
        sys.exit(1)
        
    run_command(f"docker build -t {IMAGE_NAME} {build_dir}")
    
    # 4. Tag and Push
    print("Tagging and Pushing...")
    run_command(f"docker tag {IMAGE_NAME}:latest {ECR_URI}")
    run_command(f"docker push {ECR_URI}")
    
    # 5. Deploy to SageMaker?
    deploy = input("Do you want to create/update the SageMaker endpoint now? (y/n): ")
    if deploy.lower() != 'y':
        print("Done! Image pushed to ECR.")
        return

    sm_client = boto3.client('sagemaker', region_name=REGION)
    role = get_role()
    print(f"Using Role: {role}")
    
    model_name = f"{IMAGE_NAME}-model"
    endpoint_config_name = f"{IMAGE_NAME}-config"
    endpoint_name = f"{IMAGE_NAME}-endpoint"
    
    # Create Model
    primary_container = {
        'Image': ECR_URI,
        'Mode': 'SingleModel',
    }
    
    print(f"Creating Model: {model_name}")
    try:
        sm_client.create_model(
            ModelName=model_name,
            PrimaryContainer=primary_container,
            ExecutionRoleArn=role
        )
    except sm_client.exceptions.ResourceInUse:
        print(f"Model {model_name} already exists. Deleting...")
        sm_client.delete_model(ModelName=model_name)
        time.sleep(2)
        sm_client.create_model(
            ModelName=model_name,
            PrimaryContainer=primary_container,
            ExecutionRoleArn=role
        )

    # Create Endpoint Config
    print(f"Creating Endpoint Config: {endpoint_config_name}")
    try:
        sm_client.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=[
                {
                    'VariantName': 'AllTraffic',
                    'ModelName': model_name,
                    'InitialInstanceCount': 1,
                    'InstanceType': INSTANCE_TYPE,
                    'ContainerStartupHealthCheckTimeoutInSeconds': 3600,
                    'ModelDataDownloadTimeoutInSeconds': 3600,
                },
            ]
        )
    except sm_client.exceptions.ResourceInUse:
        print(f"Endpoint Config {endpoint_config_name} already exists. Deleting...")
        sm_client.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
        time.sleep(2)
        sm_client.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=[
                {
                    'VariantName': 'AllTraffic',
                    'ModelName': model_name,
                    'InitialInstanceCount': 1,
                    'InstanceType': INSTANCE_TYPE,
                },
            ]
        )

    # Create/Update Endpoint
    print(f"Deploying to Endpoint: {endpoint_name}")
    try:
        sm_client.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=endpoint_config_name
        )
        print("Creating endpoint... this may take 5-10 minutes.")
    except sm_client.exceptions.ResourceInUse:
        print(f"Endpoint {endpoint_name} already exists. Updating...")
        sm_client.update_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=endpoint_config_name
        )
        print("Updating endpoint...")

if __name__ == "__main__":
    main()
