
import boto3
import sagemaker

try:
    sm_client = boto3.client('sagemaker')
    response = sm_client.list_endpoints(SortBy='CreationTime', SortOrder='Descending', MaxResults=5)
    
    print("Recent SageMaker Endpoints:")
    for endpoint in response['Endpoints']:
        print(f"Name: {endpoint['EndpointName']}, Status: {endpoint['EndpointStatus']}, Created: {endpoint['CreationTime']}")
except Exception as e:
    print(f"Error listing endpoints: {e}")
