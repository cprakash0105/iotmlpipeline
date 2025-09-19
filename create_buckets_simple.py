import requests
import json

def create_minio_buckets():
    """Create MinIO buckets using REST API"""
    
    # MinIO credentials
    access_key = "minioadmin"
    secret_key = "minioadmin"
    minio_url = "http://localhost:9000"
    
    buckets = ['bronze', 'silver', 'gold']
    
    print("Creating MinIO buckets...")
    print(f"MinIO Console: http://localhost:9001")
    print(f"Login: {access_key} / {secret_key}")
    print()
    
    # Instructions for manual creation
    print("MANUAL STEPS:")
    print("1. Open http://localhost:9001 in your browser")
    print("2. Login with: minioadmin / minioadmin")
    print("3. Click 'Create Bucket' button")
    print("4. Create these buckets:")
    for bucket in buckets:
        print(f"   - {bucket}")
    print()
    
    # Also create local directories to simulate the data lake
    import os
    for bucket in buckets:
        os.makedirs(f"../data/{bucket}", exist_ok=True)
        print(f"Created local directory: ../data/{bucket}")
    
    print("\nLocal data lake structure created!")
    print("The pipeline will save data to local files that simulate MinIO buckets.")

if __name__ == "__main__":
    create_minio_buckets()