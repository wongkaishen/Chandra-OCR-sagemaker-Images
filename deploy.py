# WARNING: This snippet is not yet compatible with SageMaker version >= 3.0.0.
# To use this snippet, install a compatible version:
# pip install 'sagemaker<3.0.0'
import os
import sagemaker
import boto3
from dotenv import load_dotenv
from sagemaker.huggingface import HuggingFaceModel

load_dotenv()

try:
	role = sagemaker.get_execution_role()
except ValueError:
	iam = boto3.client('iam')
	try:
		role = iam.get_role(RoleName='sagemaker_execution_role')['Role']['Arn']
	except Exception:
		# Use the specific role provided by the user
		role = "arn:aws:iam::563224522620:role/service-role/AmazonSageMaker-ExecutionRole-20251123T165775"

print(f"Using SageMaker Execution Role: {role}")

# Hub Model configuration. https://huggingface.co/models
hub = {
	'HF_MODEL_ID':'datalab-to/chandra',
	'HF_TASK':'image-to-text'
}

# create Hugging Face Model Class
huggingface_model = HuggingFaceModel(
	transformers_version='4.51.3',
	pytorch_version='2.6.0',
	py_version='py312',
	env=hub,
	role=role, 
	entry_point='inference.py',
	source_dir='sagemaker/code'
)

# deploy model to SageMaker Inference
predictor = huggingface_model.deploy(
	initial_instance_count=1, # number of instances
	instance_type='ml.m5.xlarge' # ec2 instance type
)

