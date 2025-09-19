import requests
import boto3
import psycopg2
import json
from datetime import datetime

def test_minio():
    print("=== Testing MinIO Connection ===")
    try:
        # Test MinIO web console first
        response = requests.get("http://localhost:9001", timeout=5)
        print(f"MinIO Web Console: {response.status_code} - Available")
        
        # Test S3 API
        s3_client = boto3.client(
            's3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='minioadmin',
            aws_secret_access_key='minioadmin',
            region_name='us-east-1'
        )
        
        # List buckets
        buckets = s3_client.list_buckets()
        print(f"MinIO S3 API: Connected")
        print(f"Buckets found: {[b['Name'] for b in buckets['Buckets']]}")
        
        # Test upload
        test_data = {
            'test': 'data',
            'timestamp': datetime.now().isoformat()
        }
        
        s3_client.put_object(
            Bucket='bronze',
            Key='test/connection_test.json',
            Body=json.dumps(test_data),
            ContentType='application/json'
        )
        print("SUCCESS: Test file uploaded to bronze bucket")
        
        return True
        
    except Exception as e:
        print(f"ERROR: MinIO connection failed: {e}")
        return False

def test_postgres():
    print("\n=== Testing PostgreSQL Connection ===")
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="iot_analytics",
            user="postgres",
            password="postgres",
            port="5432"
        )
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"PostgreSQL: Connected")
        print(f"Version: {version[0][:50]}...")
        
        # Test insert
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT INTO test_table (message) VALUES (%s)
        """, ("Connection test successful",))
        
        conn.commit()
        print("SUCCESS: Test data inserted")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERROR: PostgreSQL connection failed: {e}")
        return False

def test_grafana():
    print("\n=== Testing Grafana Connection ===")
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        print(f"Grafana Web UI: {response.status_code} - Available")
        
        # Test API
        response = requests.get("http://localhost:3000/api/health", timeout=5)
        if response.status_code == 200:
            print("Grafana API: Healthy")
        
        print("SUCCESS: Grafana is accessible")
        return True
        
    except Exception as e:
        print(f"ERROR: Grafana connection failed: {e}")
        return False

def main():
    print("Testing all connections...\n")
    
    minio_ok = test_minio()
    postgres_ok = test_postgres()
    grafana_ok = test_grafana()
    
    print("\n=== SUMMARY ===")
    print(f"MinIO: {'✓ Working' if minio_ok else '✗ Failed'}")
    print(f"PostgreSQL: {'✓ Working' if postgres_ok else '✗ Failed'}")
    print(f"Grafana: {'✓ Working' if grafana_ok else '✗ Failed'}")
    
    if all([minio_ok, postgres_ok, grafana_ok]):
        print("\n🎉 All services are working! Ready to start the pipeline.")
    else:
        print("\n⚠️ Some services have issues. Check the errors above.")
    
    print("\nNext steps:")
    print("1. MinIO Console: http://localhost:9001 (minioadmin/minioadmin)")
    print("2. Grafana Dashboard: http://localhost:3000 (admin/admin)")
    print("3. Check if test file appears in MinIO bronze bucket")

if __name__ == "__main__":
    main()