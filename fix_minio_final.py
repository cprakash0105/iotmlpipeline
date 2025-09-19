import subprocess
import time

def fix_minio_connection():
    print("=== FIXING MinIO CONNECTION ===")
    
    print("1. Restarting MinIO container...")
    try:
        subprocess.run(["podman", "restart", "config-minio-1"], check=True)
        print("   MinIO container restarted")
        
        print("2. Waiting for MinIO to start...")
        time.sleep(10)
        
        print("3. Testing connection...")
        import boto3
        from botocore.client import Config
        
        # Try with updated configuration
        s3_client = boto3.client(
            's3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='minioadmin',
            aws_secret_access_key='minioadmin',
            region_name='us-east-1',
            config=Config(
                signature_version='s3v4',
                retries={'max_attempts': 3},
                read_timeout=60,
                connect_timeout=60
            )
        )
        
        buckets = s3_client.list_buckets()
        print(f"   SUCCESS: Connected! Buckets: {[b['Name'] for b in buckets['Buckets']]}")
        return True
        
    except Exception as e:
        print(f"   FAILED: {e}")
        return False

if __name__ == "__main__":
    if fix_minio_connection():
        print("\n✅ MinIO is now working! You can use S3 API.")
    else:
        print("\n❌ MinIO still has issues. Use manual upload method.")