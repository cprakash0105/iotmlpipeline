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

# Set up logging
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

class GrafanaOptimizedPipeline:
    def __init__(self):
        os.makedirs('../logs', exist_ok=True)
        
        logger.info("=== STARTING GRAFANA-OPTIMIZED IoT PIPELINE ===")
        
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
            endpoints = [
                'http://localhost:9000',
                'http://127.0.0.1:9000'
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
                    
                    buckets = client.list_buckets()
                    bucket_names = [b['Name'] for b in buckets['Buckets']]
                    
                    self.s3_client = client
                    logger.info(f"✓ Connected to MinIO at {endpoint}")
                    logger.info(f"✓ Found buckets: {bucket_names}")
                    
                    # Log connection success to database for Grafana
                    self.log_system_event('minio_connection', 'success', f'Connected to {endpoint}')
                    break
                    
                except Exception as e:
                    logger.warning(f"Failed to connect to {endpoint}: {e}")
                    continue
            
            if not self.s3_client:
                logger.error("❌ Could not connect to MinIO on any endpoint")
                self.log_system_event('minio_connection', 'failed', 'All endpoints failed')
                
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
            
            # Create sensor readings table
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
            
            # Create anomaly alerts table
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
            
            # Create system events table for logging
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_events (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type VARCHAR(100),
                    event_status VARCHAR(50),
                    message TEXT,
                    details JSONB
                )
            """)
            
            # Create pipeline metrics table for Grafana dashboards
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_metrics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metric_name VARCHAR(100),
                    metric_value FLOAT,
                    sensor_id VARCHAR(50),
                    tags JSONB
                )
            """)
            
            # Create performance metrics table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_time_ms FLOAT,
                    batch_size INTEGER,
                    minio_upload_time_ms FLOAT,
                    db_save_time_ms FLOAT,
                    ml_inference_time_ms FLOAT
                )
            """)
            
            self.conn.commit()
            logger.info("✓ PostgreSQL connected and tables created")
            self.log_system_event('database_connection', 'success', 'All tables created')
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            self.conn = None
    
    def log_system_event(self, event_type, status, message, details=None):
        """Log system events for Grafana monitoring"""
        if not self.conn:
            return
            
        try:
            self.cursor.execute("""
                INSERT INTO system_events (event_type, event_status, message, details)
                VALUES (%s, %s, %s, %s)
            """, (event_type, status, message, json.dumps(details) if details else None))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")
    
    def log_metric(self, metric_name, value, sensor_id=None, tags=None):
        """Log metrics for Grafana dashboards"""
        if not self.conn:
            return
            
        try:
            self.cursor.execute("""
                INSERT INTO pipeline_metrics (metric_name, metric_value, sensor_id, tags)
                VALUES (%s, %s, %s, %s)
            """, (metric_name, value, sensor_id, json.dumps(tags) if tags else None))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to log metric: {e}")
    
    def generate_sensor_reading(self, sensor_id):
        is_anomaly = random.random() < 0.12  # 12% anomaly rate
        
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
        start_time = time.time()
        
        if not self.s3_client:
            self.log_metric('minio_upload_failed', 1, reading['sensor_id'])
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
            
            # Save to bronze bucket
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
            
            upload_time = (time.time() - start_time) * 1000
            self.log_metric('minio_upload_success', 1, reading['sensor_id'])
            self.log_metric('minio_upload_time_ms', upload_time, reading['sensor_id'])
            return True
            
        except Exception as e:
            logger.error(f"❌ MinIO save failed: {e}")
            self.log_metric('minio_upload_failed', 1, reading['sensor_id'])
            self.log_system_event('minio_upload', 'failed', str(e))
            return False
    
    def save_to_database(self, reading, prediction):
        start_time = time.time()
        
        if not self.conn:
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
            
            db_time = (time.time() - start_time) * 1000
            self.log_metric('db_save_success', 1, reading['sensor_id'])
            self.log_metric('db_save_time_ms', db_time, reading['sensor_id'])
            return True
            
        except Exception as e:
            logger.error(f"❌ Database save failed: {e}")
            self.log_metric('db_save_failed', 1, reading['sensor_id'])
            return False
    
    def run_pipeline(self):
        logger.info("🚀 Starting Grafana-Optimized IoT Pipeline")
        logger.info("📊 MinIO Console: http://localhost:9001 (minioadmin/minioadmin)")
        logger.info("📈 Grafana Dashboard: http://localhost:3000 (admin/admin)")
        
        batch_count = 0
        total_readings = 0
        total_anomalies = 0
        
        try:
            while True:
                batch_count += 1
                batch_start_time = time.time()
                batch_anomalies = 0
                
                logger.info(f"🔄 Processing Batch {batch_count}")
                
                # Generate readings from all sensors
                for sensor_id in self.sensors:
                    ml_start_time = time.time()
                    
                    reading = self.generate_sensor_reading(sensor_id)
                    prediction = self.detector.predict([reading])[0]
                    
                    ml_time = (time.time() - ml_start_time) * 1000
                    
                    # Save to MinIO and database
                    minio_success = self.save_to_minio(reading, prediction)
                    db_success = self.save_to_database(reading, prediction)
                    
                    total_readings += 1
                    
                    # Log individual sensor metrics
                    self.log_metric('temperature', reading['temperature'], sensor_id)
                    self.log_metric('humidity', reading['humidity'], sensor_id)
                    self.log_metric('ml_inference_time_ms', ml_time, sensor_id)
                    
                    if prediction == -1:
                        total_anomalies += 1
                        batch_anomalies += 1
                        self.log_metric('anomaly_detected', 1, sensor_id)
                        logger.warning(f"🚨 ANOMALY: {sensor_id} - T:{reading['temperature']}°C H:{reading['humidity']}%")
                    else:
                        self.log_metric('normal_reading', 1, sensor_id)
                        logger.info(f"✅ Normal: {sensor_id} - T:{reading['temperature']}°C H:{reading['humidity']}%")
                
                # Log batch metrics
                batch_time = (time.time() - batch_start_time) * 1000
                anomaly_rate = (total_anomalies / total_readings) * 100 if total_readings > 0 else 0
                
                self.log_metric('batch_processing_time_ms', batch_time)
                self.log_metric('batch_size', len(self.sensors))
                self.log_metric('total_readings', total_readings)
                self.log_metric('total_anomalies', total_anomalies)
                self.log_metric('anomaly_rate_percent', anomaly_rate)
                
                logger.info(f"📊 Batch {batch_count}: {len(self.sensors)} readings, {batch_anomalies} anomalies, {batch_time:.1f}ms")
                logger.info(f"📈 Total: {total_readings} readings, {total_anomalies} anomalies ({anomaly_rate:.1f}%)")
                
                time.sleep(10)  # 10 second intervals
                
        except KeyboardInterrupt:
            logger.info("🛑 Pipeline stopped by user")
            self.log_system_event('pipeline_shutdown', 'success', 'Stopped by user')
        except Exception as e:
            logger.error(f"💥 Pipeline crashed: {e}")
            self.log_system_event('pipeline_crash', 'failed', str(e))
        finally:
            if self.conn:
                self.conn.close()
            logger.info("🏁 Pipeline shutdown complete")

if __name__ == "__main__":
    pipeline = GrafanaOptimizedPipeline()
    pipeline.run_pipeline()