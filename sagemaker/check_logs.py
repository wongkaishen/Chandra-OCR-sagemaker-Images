import boto3
import sys

def get_logs():
    log_group = '/aws/sagemaker/Endpoints/chandra-ocr-endpoint'
    
    # Try to detect region or default to us-east-1
    session = boto3.session.Session()
    region = session.region_name or 'us-east-1'
    
    print(f"Fetching logs from {log_group} ({region})...")
    client = boto3.client('logs', region_name=region)
    
    try:
        # Get the most recent log stream
        streams = client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if not streams.get('logStreams'):
            print("No log streams found!")
            return

        stream_name = streams['logStreams'][0]['logStreamName']
        print(f"Reading stream: {stream_name}")
        
        events = client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            limit=50,
            startFromHead=False
        )
        
        print("\n--- RECENT LOGS ---\n")
        for e in events['events']:
            print(f"[{e['timestamp']}] {e['message'].strip()}")
            
    except Exception as e:
        print(f"Error fetching logs: {e}")

if __name__ == "__main__":
    get_logs()
