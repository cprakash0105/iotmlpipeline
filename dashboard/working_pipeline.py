import sys
import os
import time
import json
import psycopg2
import boto3
from datetime import datetime
import random
from botocore.client import Config

# Add ml-models to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ml-models'))
from anomaly_detector import AnomalyDetector

class WorkingPipeline:
    def __init__(self):
        self.detector = AnomalyDetector()
        self.load_model()
        self.sensors = ['sensor_001', 'sensor_002', 'sensor_003', 'sensor_004', 'sensor_005']
        self.setup_database()
        self.setup_minio()
        
    def load_model(self):
        try:
            self.detector.load_model('../ml-models/anomaly_model.pkl')
            print("SUCCESS: ML model loaded")
        except:
            print("Training new model...")
            self.train_model()
    
    def train_model(self):
        training_data = self.generate_training_data(1000)
        self.detector.train(training_data)
        self.detector.save_model('../ml-models/anomaly_model.pkl')
        print("SUCCESS: Model trained and saved")
    
    def generate_training_data(self, num_samples):
        data = []
        for i in range(num_samples):
            is_anomaly = random.random() < 0.1
            if is_anomaly:
                temperature = random.uniform(80, 120)
                humidity = random.uniform(0, 20)
            else:
                temperature = random.uniform(18, 28)
                humidity = random.uniform(40, 70)
            
            data.append({
                'sensor_id': f'sensor_{random.randint(1, 5):03d}',
                'timestamp': datetime.now().isoformat(),
                'temperature': round(temperature, 2),
                'humidity': round(humidity, 2),
                'is_anomaly': is_anomaly
            })
        return data
    
    def setup_minio(self):
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url='http://localhost:9000',
                aws_access_key_id='minioadmin',
                aws_secret_access_key='minioadmin',
                config=Config(signature_version='s3v4'),
                region_name='us-east-1'
            )
            
            # Test connection by listing buckets
            buckets = self.s3_client.list_buckets()
            print(f"SUCCESS: Connected to MinIO. Found buckets: {[b['Name'] for b in buckets['Buckets']]}")
            
        except Exception as e:
            print(f"MinIO connection failed: {e}")
            self.s3_client = None
    
    def setup_database(self):
        try:
            self.conn = psycopg2.connect(
                host="localhost",
                database="iot_analytics",
                user="postgres",
                password="postgres",
                port="5432"
            )
            self.cursor = self.conn.cursor()
            
            # Create tables
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id SERIAL PRIMARY KEY,
                    sensor_id VARCHAR(50),
                    timestamp TIMESTAMP,
                    temperature FLOAT,
                    humidity FLOAT,
                    is_anomaly BOOLEAN,
                    ml_prediction INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS anomaly_alerts (
                    id SERIAL PRIMARY KEY,
                    sensor_id VARCHAR(50),
                    timestamp TIMESTAMP,
                    temperature FLOAT,
                    humidity FLOAT,
                    alert_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.conn.commit()
            print("SUCCESS: Database setup complete")
            
        except Exception as e:
            print(f"Database connection failed: {e}")
            self.conn = None
    
    def generate_sensor_reading(self, sensor_id):
        is_anomaly = random.random() < 0.15  # 15% anomaly rate for more action
        
        if is_anomaly:
            temperature = random.uniform(80, 120)
            humidity = random.uniform(0, 20)
        else:
            temperature = random.uniform(18, 28)
            humidity = random.uniform(40, 70)
            
        return {
            'sensor_id': sensor_id,
            'timestamp': datetime.now(),
            'temperature': round(temperature, 2),
            'humidity': round(humidity, 2),
            'actual_anomaly': is_anomaly
        }
    
    def save_to_minio(self, reading, prediction):
        if not self.s3_client:
            return
            
        try:
            data = {
                'sensor_id': reading['sensor_id'],
                'timestamp': reading['timestamp'].isoformat(),
                'temperature': reading['temperature'],
                'humidity': reading['humidity'],
                'ml_prediction': prediction,
                'actual_anomaly': reading['actual_anomaly']
            }
            
            # Save to bronze bucket (raw data)
            bronze_key = f"raw_data/{reading['sensor_id']}/{datetime.now().strftime('%Y/%m/%d/%H')}/{int(time.time())}.json"
            self.s3_client.put_object(
                Bucket='bronze',
                Key=bronze_key,
                Body=json.dumps(data),
                ContentType='application/json'
            )
            
            # Save to appropriate bucket based on prediction
            if prediction == -1:
                # Anomaly - save to gold bucket
                gold_key = f"anomalies/{reading['sensor_id']}/{datetime.now().strftime('%Y/%m/%d')}/{int(time.time())}.json"
                self.s3_client.put_object(
                    Bucket='gold',
                    Key=gold_key,
                    Body=json.dumps(data),
                    ContentType='application/json'
                )
                print(f"  -> Saved anomaly to MinIO: gold/{gold_key}")
            else:
                # Normal - save to silver bucket
                silver_key = f"processed_data/{reading['sensor_id']}/{datetime.now().strftime('%Y/%m/%d/%H')}/{int(time.time())}.json"
                self.s3_client.put_object(
                    Bucket='silver',
                    Key=silver_key,
                    Body=json.dumps(data),
                    ContentType='application/json'
                )
            
        except Exception as e:
            print(f"MinIO save error: {e}")
    
    def save_to_database(self, reading, prediction):
        if not self.conn:
            return
            
        try:
            # Save sensor reading
            self.cursor.execute("""
                INSERT INTO sensor_readings 
                (sensor_id, timestamp, temperature, humidity, is_anomaly, ml_prediction)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                reading['sensor_id'],
                reading['timestamp'],
                reading['temperature'],
                reading['humidity'],
                reading['actual_anomaly'],
                prediction
            ))
            
            # Save anomaly alert if detected
            if prediction == -1:
                self.cursor.execute("""
                    INSERT INTO anomaly_alerts 
                    (sensor_id, timestamp, temperature, humidity, alert_type)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    reading['sensor_id'],
                    reading['timestamp'],
                    reading['temperature'],
                    reading['humidity'],
                    'ML_DETECTED'
                ))
            
            self.conn.commit()
            
        except Exception as e:
            print(f"Database save error: {e}")
    
    def run_pipeline(self):
        print("Starting Working IoT Pipeline")
        print("Data will be saved to MinIO buckets AND PostgreSQL")
        print("MinIO Console: http://localhost:9001 (minioadmin/minioadmin)")
        print("Grafana: http://localhost:3000 (admin/admin)")
        print("=" * 60)
        
        reading_count = 0
        anomaly_count = 0
        
        try:
            while True:
                print(f"\n--- Processing Batch {reading_count//5 + 1} ---")
                
                # Generate readings from all sensors
                for sensor_id in self.sensors:
                    reading = self.generate_sensor_reading(sensor_id)
                    
                    # ML prediction
                    prediction = self.detector.predict([reading])[0]
                    
                    # Save to MinIO and database
                    self.save_to_minio(reading, prediction)
                    self.save_to_database(reading, prediction)
                    
                    reading_count += 1
                    
                    if prediction == -1:
                        anomaly_count += 1
                        print(f"  ANOMALY: {reading['sensor_id']} - T:{reading['temperature']}°C H:{reading['humidity']}%")
                    else:
                        print(f"  Normal:  {reading['sensor_id']} - T:{reading['temperature']}°C H:{reading['humidity']}%")
                
                print(f"Total: {reading_count} readings, {anomaly_count} anomalies ({anomaly_count/reading_count*100:.1f}%)")
                print("Check MinIO console to see new files!")
                
                time.sleep(10)  # 10 second intervals
                
        except KeyboardInterrupt:
            print(f"\nPipeline stopped.")
            print(f"Final stats: {reading_count} readings, {anomaly_count} anomalies")
        finally:
            if self.conn:
                self.conn.close()

if __name__ == "__main__":
    pipeline = WorkingPipeline()
    pipeline.run_pipeline()