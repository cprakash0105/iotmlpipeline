import boto3
import requests
import json
import time
from datetime import datetime
from botocore.client import Config

def test_minio_simple():
    print("=== SIMPLE MinIO TEST ===")
    
    # Test web console first
    print("1. Testing MinIO Web Console...")
    try:
        response = requests.get("http://localhost:9001", timeout=5)
        print(f"   Web Console: HTTP {response.status_code} - OK")
    except Exception as e:
        print(f"   Web Console failed: {e}")
        return False
    
    # Test S3 API with different configurations
    print("\n2. Testing S3 API connections...")
    
    configs_to_try = [
        {
            'endpoint': 'http://localhost:9000',
            'config': Config(signature_version='s3v4')
        },
        {
            'endpoint': 'http://127.0.0.1:9000', 
            'config': Config(signature_version='s3v4')
        },
        {
            'endpoint': 'http://localhost:9000',
            'config': Config(signature_version='s3v4', s3={'addressing_style': 'path'})
        }
    ]
    
    for i, setup in enumerate(configs_to_try):
        try:
            print(f"\n   Trying configuration {i+1}: {setup['endpoint']}")
            
            s3_client = boto3.client(
                's3',
                endpoint_url=setup['endpoint'],
                aws_access_key_id='minioadmin',
                aws_secret_access_key='minioadmin',
                region_name='us-east-1',
                config=setup['config']
            )
            
            # Test list buckets
            buckets = s3_client.list_buckets()
            bucket_names = [b['Name'] for b in buckets['Buckets']]
            print(f"   SUCCESS: Found buckets: {bucket_names}")
            
            # Test upload
            test_data = {
                'test': 'upload_successful',
                'timestamp': datetime.now().isoformat(),
                'config_used': i+1
            }
            
            s3_client.put_object(
                Bucket='bronze',
                Key=f'test_uploads/success_{int(time.time())}.json',
                Body=json.dumps(test_data, indent=2),
                ContentType='application/json'
            )
            
            print(f"   SUCCESS: File uploaded to bronze bucket!")
            print(f"   Working endpoint: {setup['endpoint']}")
            return s3_client
            
        except Exception as e:
            print(f"   FAILED: {e}")
            continue
    
    print("\n   All S3 API attempts failed!")
    return None

def create_manual_upload_files():
    print("\n=== CREATING FILES FOR MANUAL UPLOAD ===")
    
    import os
    os.makedirs('minio_manual_upload', exist_ok=True)
    
    # Create sample data files
    sample_data = {
        'bronze_sample.json': {
            'sensor_id': 'sensor_001',
            'timestamp': datetime.now().isoformat(),
            'temperature': 24.5,
            'humidity': 65.2,
            'data_type': 'raw_sensor_reading'
        },
        'silver_sample.json': {
            'sensor_id': 'sensor_001', 
            'timestamp': datetime.now().isoformat(),
            'temperature': 24.5,
            'humidity': 65.2,
            'ml_prediction': 0,
            'data_type': 'processed_normal_reading'
        },
        'gold_sample.json': {
            'sensor_id': 'sensor_002',
            'timestamp': datetime.now().isoformat(), 
            'temperature': 95.8,
            'humidity': 12.1,
            'ml_prediction': -1,
            'data_type': 'anomaly_detection'
        }
    }
    
    for filename, data in sample_data.items():
        filepath = f'minio_manual_upload/{filename}'
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"   Created: {filepath}")
    
    print("\n   MANUAL UPLOAD INSTRUCTIONS:")
    print("   1. Open MinIO Console: http://localhost:9001")
    print("   2. Login: minioadmin / minioadmin")
    print("   3. Go to 'bronze' bucket -> Upload bronze_sample.json")
    print("   4. Go to 'silver' bucket -> Upload silver_sample.json") 
    print("   5. Go to 'gold' bucket -> Upload gold_sample.json")
    print("   6. Refresh buckets to see the uploaded files")

def check_minio_logs():
    print("\n=== MinIO TROUBLESHOOTING ===")
    print("If S3 API still doesn't work, try these steps:")
    print("1. Check MinIO container logs:")
    print("   podman logs config-minio-1")
    print("\n2. Restart MinIO container:")
    print("   podman restart config-minio-1")
    print("\n3. Check if MinIO is listening on correct ports:")
    print("   podman port config-minio-1")
    print("\n4. Alternative: Use MinIO web interface for all uploads")

def main():
    print("MinIO Connection Test")
    print("=" * 40)
    
    # Test S3 API
    working_client = test_minio_simple()
    
    if working_client:
        print("\nSUCCESS: MinIO S3 API is working!")
        print("You can now use boto3 to upload files programmatically.")
    else:
        print("\nS3 API failed - using manual upload method")
        create_manual_upload_files()
        check_minio_logs()
    
    print("\n" + "=" * 40)
    print("MinIO Console: http://localhost:9001 (minioadmin/minioadmin)")

if __name__ == "__main__":
    main()