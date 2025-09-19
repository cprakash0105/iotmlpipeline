import boto3
import requests
import json
import time
from datetime import datetime
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError

def test_minio_detailed():
    print("=== DETAILED MinIO CONNECTION TEST ===")
    
    # Test 1: Web Console
    print("\n1. Testing MinIO Web Console...")
    try:
        response = requests.get("http://localhost:9001", timeout=10)
        print(f"   ✓ Web Console: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ✗ Web Console failed: {e}")
    
    # Test 2: S3 API Endpoint
    print("\n2. Testing S3 API Endpoint...")
    try:
        response = requests.get("http://localhost:9000", timeout=10)
        print(f"   ✓ S3 API Endpoint: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ✗ S3 API Endpoint failed: {e}")
    
    # Test 3: Different S3 Client Configurations
    endpoints = [
        "http://localhost:9000",
        "http://127.0.0.1:9000",
        "http://0.0.0.0:9000"
    ]
    
    configs = [
        {"signature_version": "s3v4"},
        {"signature_version": "s3v4", "s3": {"addressing_style": "path"}},
        {"signature_version": "s3v4", "s3": {"addressing_style": "virtual"}},
        {"signature_version": "UNSIGNED"},
    ]
    
    print("\n3. Testing S3 Client Configurations...")
    
    for i, endpoint in enumerate(endpoints):
        for j, config_dict in enumerate(configs):
            try:
                print(f"\n   Testing {endpoint} with config {j+1}...")
                
                s3_client = boto3.client(
                    's3',
                    endpoint_url=endpoint,
                    aws_access_key_id='minioadmin',
                    aws_secret_access_key='minioadmin',
                    region_name='us-east-1',
                    config=Config(**config_dict)
                )
                
                # Try to list buckets
                response = s3_client.list_buckets()
                buckets = [b['Name'] for b in response['Buckets']]
                print(f"   ✓ SUCCESS! Found buckets: {buckets}")
                
                # Try to upload a test file
                test_data = {
                    'test': 'connection_successful',
                    'timestamp': datetime.now().isoformat(),
                    'endpoint': endpoint,
                    'config': j+1
                }
                
                s3_client.put_object(
                    Bucket='bronze',
                    Key=f'connection_tests/test_{int(time.time())}.json',
                    Body=json.dumps(test_data, indent=2),
                    ContentType='application/json'
                )
                
                print(f"   ✓ UPLOAD SUCCESS! Test file uploaded to bronze bucket")
                return s3_client, endpoint, config_dict
                
            except EndpointConnectionError as e:
                print(f"   ✗ Endpoint connection failed: {e}")
            except ClientError as e:
                print(f"   ✗ Client error: {e}")
            except Exception as e:
                print(f"   ✗ Other error: {e}")
    
    print("\n❌ All S3 configurations failed!")
    return None, None, None

def create_working_s3_client():
    """Create a working S3 client based on successful test"""
    client, endpoint, config = test_minio_detailed()
    
    if client:
        print(f"\n🎉 WORKING CONFIGURATION FOUND!")
        print(f"   Endpoint: {endpoint}")
        print(f"   Config: {config}")
        return client
    else:
        print(f"\n⚠️ No working S3 configuration found")
        print("   Possible solutions:")
        print("   1. Restart MinIO container: podman restart config-minio-1")
        print("   2. Check MinIO logs: podman logs config-minio-1")
        print("   3. Try different MinIO image version")
        print("   4. Use MinIO web interface for manual uploads")
        return None

def test_manual_upload():
    """Test uploading via MinIO web interface instructions"""
    print("\n=== MANUAL UPLOAD TEST ===")
    
    # Create test files for manual upload
    test_files = {
        'bronze': {'sensor': 'test_001', 'temp': 25.5, 'type': 'raw_data'},
        'silver': {'sensor': 'test_001', 'temp': 25.5, 'type': 'processed_data'},
        'gold': {'sensor': 'test_001', 'temp': 95.2, 'type': 'anomaly_data'}
    }
    
    import os
    os.makedirs('manual_upload_test', exist_ok=True)
    
    for bucket, data in test_files.items():
        filename = f'manual_upload_test/{bucket}_test_file.json'
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"   Created: {filename}")
    
    print("\n📁 MANUAL UPLOAD INSTRUCTIONS:")
    print("1. Go to http://localhost:9001")
    print("2. Login: minioadmin / minioadmin")
    print("3. Navigate to each bucket (bronze, silver, gold)")
    print("4. Upload the corresponding test files from manual_upload_test/ folder")
    print("5. Verify files appear in the buckets")

if __name__ == "__main__":
    print("MinIO Connection Diagnostics")
    print("=" * 50)
    
    # Test S3 API connection
    working_client = create_working_s3_client()
    
    if not working_client:
        # Provide manual upload option
        test_manual_upload()
    
    print("\n" + "=" * 50)
    print("Next steps:")
    print("1. If S3 API works: Use the working configuration in your pipeline")
    print("2. If S3 API fails: Use manual upload via web interface")
    print("3. Check MinIO container: podman logs config-minio-1")