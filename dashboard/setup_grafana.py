import requests
import json
import time

def setup_grafana():
    """Set up Grafana data source and dashboard"""
    
    grafana_url = "http://localhost:3000"
    username = "admin"
    password = "admin"
    
    print("Setting up Grafana...")
    print(f"URL: {grafana_url}")
    print(f"Login: {username}/{password}")
    
    # Wait for Grafana to be ready
    print("Waiting for Grafana to be ready...")
    for i in range(30):
        try:
            response = requests.get(f"{grafana_url}/api/health")
            if response.status_code == 200:
                print("Grafana is ready!")
                break
        except:
            pass
        time.sleep(2)
        print(f"  Waiting... ({i+1}/30)")
    
    # Create PostgreSQL data source
    datasource_config = {
        "name": "PostgreSQL-IoT",
        "type": "postgres",
        "url": "localhost:5432",
        "database": "iot_analytics",
        "user": "postgres",
        "secureJsonData": {
            "password": "postgres"
        },
        "jsonData": {
            "sslmode": "disable",
            "postgresVersion": 1300
        }
    }
    
    try:
        response = requests.post(
            f"{grafana_url}/api/datasources",
            auth=(username, password),
            headers={"Content-Type": "application/json"},
            data=json.dumps(datasource_config)
        )
        
        if response.status_code in [200, 409]:  # 409 = already exists
            print("SUCCESS: PostgreSQL data source configured")
        else:
            print(f"Data source setup failed: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"Error setting up data source: {e}")
    
    print("\nMANUAL GRAFANA SETUP STEPS:")
    print("1. Open http://localhost:3000")
    print("2. Login: admin/admin (change password when prompted)")
    print("3. Go to Configuration > Data Sources")
    print("4. Add PostgreSQL data source:")
    print("   - Host: localhost:5432")
    print("   - Database: iot_analytics")
    print("   - User: postgres")
    print("   - Password: postgres")
    print("   - SSL Mode: disable")
    print("5. Test & Save")
    print("6. Create dashboard with these queries:")
    print()
    print("QUERY 1 (Temperature Time Series):")
    print("SELECT timestamp as time, temperature as value, sensor_id as metric")
    print("FROM sensor_readings")
    print("WHERE $__timeFilter(timestamp)")
    print("ORDER BY timestamp")
    print()
    print("QUERY 2 (Anomaly Count):")
    print("SELECT COUNT(*) as value")
    print("FROM anomaly_alerts")
    print("WHERE $__timeFilter(timestamp)")
    print()
    print("QUERY 3 (Latest Readings Table):")
    print("SELECT sensor_id, temperature, humidity, ")
    print("CASE WHEN ml_prediction = -1 THEN 'ANOMALY' ELSE 'NORMAL' END as status,")
    print("timestamp")
    print("FROM sensor_readings")
    print("WHERE timestamp > NOW() - INTERVAL '5 minutes'")
    print("ORDER BY timestamp DESC")
    print("LIMIT 20")

if __name__ == "__main__":
    setup_grafana()