# MinIO Troubleshooting Guide

## 🔍 Issue Summary
- **Web Console**: ✅ Working (http://localhost:9001)
- **S3 API**: ❌ Connection timeout/refused
- **Error**: "Connection was closed before we received a valid response"

## 🛠️ Diagnostic Steps

### 1. Check Container Status
```bash
podman ps | grep minio
podman logs config-minio-1 --tail 20
```

### 2. Check Network Connectivity
```bash
# Test web console
curl -I http://localhost:9001

# Test S3 API endpoint
curl -I http://localhost:9000
```

### 3. Check Port Mapping
```bash
podman port config-minio-1
```

## 🔧 Common Fixes

### Fix 1: Restart MinIO Container
```bash
podman restart config-minio-1
# Wait 30 seconds
podman logs config-minio-1
```

### Fix 2: Update Docker Compose Configuration
```yaml
# In config/docker-compose.yml
minio:
  image: minio/minio:RELEASE.2024-01-16T16-07-38Z  # Use specific version
  ports:
    - "9000:9000"
    - "9001:9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  command: server /data --console-address ":9001"
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
    interval: 30s
    timeout: 20s
    retries: 3
```

### Fix 3: Network Configuration
```bash
# Check if MinIO is binding to correct interface
podman exec config-minio-1 netstat -tlnp | grep 9000

# Alternative: Use host networking
# Add to docker-compose.yml:
# network_mode: host
```

### Fix 4: Firewall/Security
```bash
# Windows: Check if ports are blocked
netstat -an | findstr :9000
netstat -an | findstr :9001

# Temporarily disable Windows Firewall to test
```

### Fix 5: Alternative MinIO Setup
```bash
# Stop current MinIO
podman stop config-minio-1

# Run MinIO directly
podman run -d \
  --name minio-direct \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio:latest \
  server /data --console-address ":9001"
```

## 🧪 Test S3 Connection

### Python Test Script
```python
import boto3
from botocore.client import Config

def test_s3_connection():
    configs = [
        # Config 1: Basic
        Config(signature_version='s3v4'),
        
        # Config 2: Path style
        Config(signature_version='s3v4', s3={'addressing_style': 'path'}),
        
        # Config 3: Extended timeout
        Config(
            signature_version='s3v4',
            read_timeout=60,
            connect_timeout=60,
            retries={'max_attempts': 3}
        )
    ]
    
    endpoints = ['http://localhost:9000', 'http://127.0.0.1:9000']
    
    for endpoint in endpoints:
        for i, config in enumerate(configs):
            try:
                client = boto3.client(
                    's3',
                    endpoint_url=endpoint,
                    aws_access_key_id='minioadmin',
                    aws_secret_access_key='minioadmin',
                    region_name='us-east-1',
                    config=config
                )
                
                buckets = client.list_buckets()
                print(f"✅ SUCCESS: {endpoint} with config {i+1}")
                return client
                
            except Exception as e:
                print(f"❌ FAILED: {endpoint} config {i+1} - {e}")
    
    return None

# Run test
working_client = test_s3_connection()
```

## 🔄 Alternative Solutions

### Option 1: Use Different MinIO Image
```yaml
# Try older stable version
minio:
  image: minio/minio:RELEASE.2023-12-23T07-42-11Z
```

### Option 2: Use LocalStack (S3 Alternative)
```yaml
localstack:
  image: localstack/localstack:latest
  ports:
    - "4566:4566"
  environment:
    SERVICES: s3
    DEBUG: 1
```

### Option 3: File-based Storage
```python
# Use local filesystem instead of S3
import os
import json

def save_to_local_s3(bucket, key, data):
    path = f"local_s3/{bucket}/{key}"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f)
```

## 📊 Monitoring MinIO Health

### Health Check Script
```python
import requests
import time

def monitor_minio():
    while True:
        try:
            # Check web console
            web_response = requests.get("http://localhost:9001", timeout=5)
            web_status = "✅" if web_response.status_code == 200 else "❌"
            
            # Check S3 API
            api_response = requests.get("http://localhost:9000", timeout=5)
            api_status = "✅" if api_response.status_code in [200, 403] else "❌"
            
            print(f"MinIO Status - Web: {web_status} | API: {api_status}")
            
        except Exception as e:
            print(f"MinIO Check Failed: {e}")
        
        time.sleep(30)

# Run monitoring
monitor_minio()
```

## 🎯 Next Steps for Investigation

1. **Check MinIO logs** for specific error messages
2. **Test with different MinIO versions**
3. **Verify network configuration** in Podman
4. **Try running MinIO outside containers** for comparison
5. **Check Windows-specific networking issues**

## 📝 Workaround for Now

Until S3 API is fixed, use:
1. **Manual uploads** via MinIO web console
2. **File-based storage** with local directories
3. **Focus on PostgreSQL + Grafana** for analytics

The pipeline is fully functional without MinIO S3 API - it's just missing the data lake storage component.