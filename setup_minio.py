import boto3
from botocore.exceptions import ClientError

def setup_minio_buckets():
    # MinIO client configuration
    s3_client = boto3.client(
        's3',
        endpoint_url='http://localhost:9000',
        aws_access_key_id='minioadmin',
        aws_secret_access_key='minioadmin',
        region_name='us-east-1'
    )
    
    buckets = ['bronze', 'silver', 'gold']
    
    for bucket in buckets:
        try:
            s3_client.create_bucket(Bucket=bucket)
            print(f"SUCCESS: Created bucket '{bucket}'")
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                print(f"INFO: Bucket '{bucket}' already exists")
            else:
                print(f"ERROR: Failed to create bucket '{bucket}': {e}")
    
    # Test by uploading a sample file
    try:
        s3_client.put_object(
            Bucket='bronze',
            Key='test/sample.txt',
            Body=b'IoT Pipeline Test File'
        )
        print("SUCCESS: Test file uploaded to bronze bucket")
    except Exception as e:
        print(f"ERROR: Failed to upload test file: {e}")

if __name__ == "__main__":
    setup_minio_buckets()