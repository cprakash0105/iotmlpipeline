import sys
import os
import time
import json
import psycopg2
import logging
from datetime import datetime
import random

# Set up logging with better error handling
os.makedirs('../logs', exist_ok=True)
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

class ResilientPipeline:
    def __init__(self):
        logger.info("=== STARTING RESILIENT IoT PIPELINE ===")
        
        self.detector = AnomalyDetector()
        self.load_model()
        self.sensors = ['sensor_001', 'sensor_002', 'sensor_003', 'sensor_004', 'sensor_005']
        
        # Initialize connections
        self.db_connected = self.setup_database()
        self.minio_connected = False  # We'll skip MinIO for now
        
        # Statistics
        self.stats = {
            'total_readings': 0,
            'anomalies_detected': 0,
            'db_saves': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
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
            
            # Create all necessary tables
            tables = [
                """CREATE TABLE IF NOT EXISTS sensor_readings (
                    id SERIAL PRIMARY KEY,
                    sensor_id VARCHAR(50),
                    timestamp TIMESTAMP,
                    temperature FLOAT,
                    humidity FLOAT,
                    is_anomaly BOOLEAN,
                    ml_prediction INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                
                """CREATE TABLE IF NOT EXISTS anomaly_alerts (
                    id SERIAL PRIMARY KEY,
                    sensor_id VARCHAR(50),
                    timestamp TIMESTAMP,
                    temperature FLOAT,
                    humidity FLOAT,
                    alert_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                
                """CREATE TABLE IF NOT EXISTS system_events (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type VARCHAR(100),
                    event_status VARCHAR(50),
                    message TEXT,
                    details TEXT
                )""",
                
                """CREATE TABLE IF NOT EXISTS pipeline_metrics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metric_name VARCHAR(100),
                    metric_value FLOAT,
                    sensor_id VARCHAR(50),
                    tags TEXT
                )""",
                
                """CREATE TABLE IF NOT EXISTS pipeline_status (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_readings INTEGER,
                    anomalies_detected INTEGER,
                    db_saves INTEGER,
                    errors INTEGER,
                    uptime_seconds INTEGER,
                    minio_status VARCHAR(20),
                    db_status VARCHAR(20)
                )"""
            ]
            
            for table_sql in tables:
                self.cursor.execute(table_sql)
            
            self.conn.commit()
            logger.info("✓ PostgreSQL connected and all tables created")
            self.log_system_event('database_connection', 'success', 'All tables created successfully')
            return True
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            return False
    
    def log_system_event(self, event_type, status, message, details=None):
        """Log system events for Grafana monitoring"""
        if not self.db_connected:
            return
            
        try:
            self.cursor.execute("""
                INSERT INTO system_events (event_type, event_status, message, details)
                VALUES (%s, %s, %s, %s)
            """, (event_type, status, message, str(details) if details else None))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")
    
    def log_metric(self, metric_name, value, sensor_id=None, tags=None):
        """Log metrics for Grafana dashboards"""
        if not self.db_connected:
            return
            
        try:
            self.cursor.execute("""
                INSERT INTO pipeline_metrics (metric_name, metric_value, sensor_id, tags)
                VALUES (%s, %s, %s, %s)
            """, (metric_name, value, sensor_id, str(tags) if tags else None))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to log metric: {e}")
    
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
    
    def save_to_database(self, reading, prediction):
        if not self.db_connected:
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
    
    def save_to_local_files(self, reading, prediction):
        """Save data to local files as MinIO alternative"""
        try:
            # Create directories
            os.makedirs('../data/bronze', exist_ok=True)
            os.makedirs('../data/silver', exist_ok=True)
            os.makedirs('../data/gold', exist_ok=True)
            
            data = {
                'sensor_id': reading['sensor_id'],
                'timestamp': reading['timestamp'].isoformat(),
                'temperature': reading['temperature'],
                'humidity': reading['humidity'],
                'ml_prediction': prediction,
                'actual_anomaly': reading['actual_anomaly']
            }
            
            # Save to bronze (all data)
            bronze_file = f"../data/bronze/sensor_data_{datetime.now().strftime('%Y%m%d_%H')}.jsonl"
            with open(bronze_file, 'a') as f:
                f.write(json.dumps(data) + '\n')
            
            # Save to appropriate layer
            if prediction == -1:
                # Anomaly - save to gold
                gold_file = f"../data/gold/anomalies_{datetime.now().strftime('%Y%m%d_%H')}.jsonl"
                with open(gold_file, 'a') as f:
                    f.write(json.dumps(data) + '\n')
            else:
                # Normal - save to silver
                silver_file = f"../data/silver/normal_data_{datetime.now().strftime('%Y%m%d_%H')}.jsonl"
                with open(silver_file, 'a') as f:
                    f.write(json.dumps(data) + '\n')
            
            return True
            
        except Exception as e:
            logger.error(f"Local file save failed: {e}")
            return False
    
    def update_pipeline_status(self):
        """Update overall pipeline status for monitoring"""
        if not self.db_connected:
            return
            
        try:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
            
            self.cursor.execute("""
                INSERT INTO pipeline_status 
                (total_readings, anomalies_detected, db_saves, errors, uptime_seconds, minio_status, db_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                self.stats['total_readings'],
                self.stats['anomalies_detected'],
                self.stats['db_saves'],
                self.stats['errors'],
                int(uptime),
                'disconnected',  # MinIO status
                'connected' if self.db_connected else 'disconnected'
            ))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Status update failed: {e}")
    
    def print_dashboard(self):
        """Print console dashboard"""
        uptime = datetime.now() - self.stats['start_time']
        anomaly_rate = (self.stats['anomalies_detected'] / self.stats['total_readings'] * 100) if self.stats['total_readings'] > 0 else 0
        
        print("\n" + "="*70)
        print("📊 IoT ML PIPELINE DASHBOARD")
        print("="*70)
        print(f"⏱️  Uptime: {uptime}")
        print(f"📈 Total Readings: {self.stats['total_readings']}")
        print(f"🚨 Anomalies: {self.stats['anomalies_detected']} ({anomaly_rate:.1f}%)")
        print(f"💾 DB Saves: {self.stats['db_saves']}")
        print(f"❌ Errors: {self.stats['errors']}")
        print(f"🗄️  Database: {'✓ Connected' if self.db_connected else '❌ Disconnected'}")
        print(f"📁 MinIO: ❌ Disconnected (using local files)")
        print(f"📊 Grafana: http://localhost:3000")
        print("="*70)
    
    def run_pipeline(self):
        logger.info("🚀 Starting Resilient IoT Pipeline")
        logger.info("📊 Grafana Dashboard: http://localhost:3000 (admin/admin)")
        logger.info("📋 Logs: ../logs/pipeline.log")
        logger.info("📁 Data Files: ../data/ (bronze/silver/gold)")
        
        if not self.db_connected:
            logger.error("❌ Cannot start pipeline - Database connection failed")
            return
        
        batch_count = 0
        
        try:
            while True:
                batch_count += 1
                batch_start_time = time.time()
                batch_anomalies = 0
                
                logger.info(f"🔄 Processing Batch {batch_count}")
                
                # Generate readings from all sensors
                for sensor_id in self.sensors:
                    reading = self.generate_sensor_reading(sensor_id)
                    prediction = self.detector.predict([reading])[0]
                    
                    # Save to database and local files
                    db_success = self.save_to_database(reading, prediction)
                    file_success = self.save_to_local_files(reading, prediction)
                    
                    self.stats['total_readings'] += 1
                    
                    # Log metrics for Grafana
                    self.log_metric('temperature', reading['temperature'], sensor_id)
                    self.log_metric('humidity', reading['humidity'], sensor_id)
                    
                    if prediction == -1:
                        self.stats['anomalies_detected'] += 1
                        batch_anomalies += 1
                        self.log_metric('anomaly_detected', 1, sensor_id)
                        logger.warning(f"🚨 ANOMALY: {sensor_id} - T:{reading['temperature']}°C H:{reading['humidity']}%")
                    else:
                        self.log_metric('normal_reading', 1, sensor_id)
                        logger.info(f"✅ Normal: {sensor_id} - T:{reading['temperature']}°C H:{reading['humidity']}%")
                
                # Log batch metrics
                batch_time = (time.time() - batch_start_time) * 1000
                self.log_metric('batch_processing_time_ms', batch_time)
                self.log_metric('batch_size', len(self.sensors))
                
                # Update status and show dashboard
                self.update_pipeline_status()
                self.print_dashboard()
                
                logger.info(f"⏳ Waiting 8 seconds before next batch...")
                time.sleep(8)  # 8 second intervals
                
        except KeyboardInterrupt:
            logger.info("🛑 Pipeline stopped by user")
            self.log_system_event('pipeline_shutdown', 'success', 'Stopped by user')
        except Exception as e:
            logger.error(f"💥 Pipeline crashed: {e}")
            self.log_system_event('pipeline_crash', 'failed', str(e))
        finally:
            if self.db_connected and self.conn:
                self.conn.close()
            logger.info("🏁 Pipeline shutdown complete")

if __name__ == "__main__":
    pipeline = ResilientPipeline()
    pipeline.run_pipeline()