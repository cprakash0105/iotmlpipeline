import sys
import os
import time
import json
import psycopg2
import boto3
import logging
from datetime import datetime
import random
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError

# Set up comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add ml-models to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ml-models'))
from anomaly_detector import AnomalyDetector

class MonitoredPipeline:
    def __init__(self):
        # Create logs directory
        os.makedirs('../logs', exist_ok=True)
        
        logger.info("=== STARTING IoT ML PIPELINE ===")
        
        self.stats = {
            'total_readings': 0,
            'anomalies_detected': 0,
            'minio_uploads': 0,
            'db_saves': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
        self.detector = AnomalyDetector()
        self.load_model()
        self.sensors = ['sensor_001', 'sensor_002', 'sensor_003', 'sensor_004', 'sensor_005']
        self.setup_database()
        self.setup_minio()
        
    def load_model(self):
        try:
            self.detector.load_model('../ml-models/anomaly_model.pkl')
            logger.info("✓ ML model loaded successfully")
        except Exception as e:
            logger.warning(f"Model not found: {e}. Training new model...")
            self.train_model()
    
    def train_model(self):
        logger.info("Training new ML model...")
        training_data = self.generate_training_data(1000)
        self.detector.train(training_data)
        self.detector.save_model('../ml-models/anomaly_model.pkl')
        logger.info("✓ New model trained and saved")
    
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
        logger.info("Setting up MinIO connection...")
        try:
            # Test different endpoint configurations
            endpoints = [
                'http://localhost:9000',
                'http://127.0.0.1:9000',
                'http://0.0.0.0:9000'
            ]
            
            self.s3_client = None
            
            for endpoint in endpoints:
                try:
                    logger.info(f"Trying MinIO endpoint: {endpoint}")
                    
                    client = boto3.client(
                        's3',
                        endpoint_url=endpoint,
                        aws_access_key_id='minioadmin',
                        aws_secret_access_key='minioadmin',
                        config=Config(signature_version='s3v4'),
                        region_name='us-east-1'
                    )
                    
                    # Test connection
                    buckets = client.list_buckets()
                    bucket_names = [b['Name'] for b in buckets['Buckets']]
                    
                    self.s3_client = client
                    logger.info(f"✓ Connected to MinIO at {endpoint}")
                    logger.info(f"✓ Found buckets: {bucket_names}")
                    break
                    
                except Exception as e:
                    logger.warning(f"Failed to connect to {endpoint}: {e}")
                    continue
            
            if not self.s3_client:
                logger.error("❌ Could not connect to MinIO on any endpoint")
                logger.info("MinIO troubleshooting:")
                logger.info("1. Check if MinIO container is running: podman ps")
                logger.info("2. Check MinIO logs: podman logs config-minio-1")
                logger.info("3. Try accessing web UI: http://localhost:9001")
                
        except Exception as e:
            logger.error(f"❌ MinIO setup failed: {e}")
            self.s3_client = None
    
    def setup_database(self):
        logger.info("Setting up PostgreSQL connection...")
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
            
            # Create pipeline monitoring table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_stats (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_readings INTEGER,
                    anomalies_detected INTEGER,
                    minio_uploads INTEGER,
                    db_saves INTEGER,
                    errors INTEGER,
                    uptime_seconds INTEGER
                )
            """)
            
            self.conn.commit()
            logger.info("✓ PostgreSQL connected and tables created")
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            self.conn = None
    
    def generate_sensor_reading(self, sensor_id):
        is_anomaly = random.random() < 0.15  # 15% anomaly rate
        
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
            logger.debug("Skipping MinIO save - no connection")
            return False
            
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
                gold_key = f"anomalies/{reading['sensor_id']}/{datetime.now().strftime('%Y/%m/%d')}/{int(time.time())}.json"
                self.s3_client.put_object(
                    Bucket='gold',
                    Key=gold_key,
                    Body=json.dumps(data),
                    ContentType='application/json'
                )
                logger.info(f"📁 Saved anomaly to MinIO: gold/{gold_key}")
            else:
                silver_key = f"processed_data/{reading['sensor_id']}/{datetime.now().strftime('%Y/%m/%d/%H')}/{int(time.time())}.json"
                self.s3_client.put_object(
                    Bucket='silver',
                    Key=silver_key,
                    Body=json.dumps(data),
                    ContentType='application/json'
                )
            
            self.stats['minio_uploads'] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ MinIO save failed: {e}")
            self.stats['errors'] += 1
            return False
    
    def save_to_database(self, reading, prediction):
        if not self.conn:
            logger.debug("Skipping DB save - no connection")
            return False
            
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
            self.stats['db_saves'] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Database save failed: {e}")
            self.stats['errors'] += 1
            return False
    
    def update_pipeline_stats(self):
        if not self.conn:
            return
            
        try:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
            
            self.cursor.execute("""
                INSERT INTO pipeline_stats 
                (total_readings, anomalies_detected, minio_uploads, db_saves, errors, uptime_seconds)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                self.stats['total_readings'],
                self.stats['anomalies_detected'],
                self.stats['minio_uploads'],
                self.stats['db_saves'],
                self.stats['errors'],
                int(uptime)
            ))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Stats update failed: {e}")
    
    def print_status_dashboard(self):
        uptime = datetime.now() - self.stats['start_time']
        
        print("\n" + "="*60)
        print("📊 PIPELINE STATUS DASHBOARD")
        print("="*60)
        print(f"⏱️  Uptime: {uptime}")
        print(f"📈 Total Readings: {self.stats['total_readings']}")
        print(f"🚨 Anomalies Detected: {self.stats['anomalies_detected']}")
        print(f"📁 MinIO Uploads: {self.stats['minio_uploads']}")
        print(f"💾 DB Saves: {self.stats['db_saves']}")
        print(f"❌ Errors: {self.stats['errors']}")
        
        if self.stats['total_readings'] > 0:
            anomaly_rate = (self.stats['anomalies_detected'] / self.stats['total_readings']) * 100
            print(f"📊 Anomaly Rate: {anomaly_rate:.1f}%")
        
        print(f"🔗 MinIO Status: {'✓ Connected' if self.s3_client else '❌ Disconnected'}")
        print(f"🗄️  DB Status: {'✓ Connected' if self.conn else '❌ Disconnected'}")
        print("="*60)
    
    def run_pipeline(self):
        logger.info("🚀 Starting Monitored IoT Pipeline")
        logger.info("📊 MinIO Console: http://localhost:9001 (minioadmin/minioadmin)")
        logger.info("📈 Grafana: http://localhost:3000 (admin/admin)")
        logger.info("📋 Logs: ../logs/pipeline.log")
        
        batch_count = 0
        
        try:
            while True:
                batch_count += 1
                batch_anomalies = 0
                
                logger.info(f"🔄 Processing Batch {batch_count}")
                
                # Generate readings from all sensors
                for sensor_id in self.sensors:
                    reading = self.generate_sensor_reading(sensor_id)
                    
                    # ML prediction
                    prediction = self.detector.predict([reading])[0]
                    
                    # Save to MinIO and database
                    minio_success = self.save_to_minio(reading, prediction)
                    db_success = self.save_to_database(reading, prediction)
                    
                    self.stats['total_readings'] += 1
                    
                    if prediction == -1:
                        self.stats['anomalies_detected'] += 1
                        batch_anomalies += 1
                        logger.warning(f"🚨 ANOMALY: {reading['sensor_id']} - T:{reading['temperature']}°C H:{reading['humidity']}%")
                    else:
                        logger.info(f"✅ Normal: {reading['sensor_id']} - T:{reading['temperature']}°C H:{reading['humidity']}%")
                
                # Update stats and show dashboard
                self.update_pipeline_stats()
                self.print_status_dashboard()
                
                logger.info(f"⏳ Waiting 15 seconds before next batch...")
                time.sleep(15)  # 15 second intervals
                
        except KeyboardInterrupt:
            logger.info("🛑 Pipeline stopped by user")
        except Exception as e:
            logger.error(f"💥 Pipeline crashed: {e}")
        finally:
            if self.conn:
                self.conn.close()
            logger.info("🏁 Pipeline shutdown complete")

if __name__ == "__main__":
    pipeline = MonitoredPipeline()
    pipeline.run_pipeline()