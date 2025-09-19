import sys
import os
import time
import json
import psycopg2
from datetime import datetime
import random

# Add ml-models to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'ml-models'))
from anomaly_detector import AnomalyDetector

class FinalWorkingPipeline:
    def __init__(self):
        print("=== IoT ML PIPELINE STARTING ===")
        
        self.detector = AnomalyDetector()
        self.load_model()
        self.sensors = ['sensor_001', 'sensor_002', 'sensor_003', 'sensor_004', 'sensor_005']
        self.setup_database()
        self.setup_file_storage()
        
        self.stats = {
            'total_readings': 0,
            'anomalies_detected': 0,
            'files_created': 0,
            'start_time': datetime.now()
        }
        
    def load_model(self):
        try:
            self.detector.load_model('ml-models/anomaly_model.pkl')
            print("SUCCESS: ML model loaded")
        except Exception as e:
            print(f"Training new model...")
            self.train_model()
    
    def train_model(self):
        print("Training ML model...")
        training_data = []
        for i in range(1000):
            is_anomaly = random.random() < 0.1
            if is_anomaly:
                temperature = random.uniform(80, 120)
                humidity = random.uniform(0, 20)
            else:
                temperature = random.uniform(18, 28)
                humidity = random.uniform(40, 70)
            
            training_data.append({
                'sensor_id': f'sensor_{random.randint(1, 5):03d}',
                'timestamp': datetime.now().isoformat(),
                'temperature': round(temperature, 2),
                'humidity': round(humidity, 2),
                'is_anomaly': is_anomaly
            })
        
        self.detector.train(training_data)
        self.detector.save_model('ml-models/anomaly_model.pkl')
        print("SUCCESS: Model trained and saved")
    
    def setup_database(self):
        print("Connecting to PostgreSQL for Grafana...")
        try:
            self.conn = psycopg2.connect(
                host="localhost",
                database="iot_analytics", 
                user="postgres",
                password="postgres",
                port="5432"
            )
            self.cursor = self.conn.cursor()
            
            # Create tables for Grafana dashboards
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
                    severity VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Clean old data for fresh demo
            self.cursor.execute("DELETE FROM sensor_readings WHERE created_at < NOW() - INTERVAL '2 hours'")
            self.cursor.execute("DELETE FROM anomaly_alerts WHERE created_at < NOW() - INTERVAL '2 hours'")
            
            self.conn.commit()
            print("SUCCESS: Database connected and ready for Grafana")
            
        except Exception as e:
            print(f"ERROR: Database connection failed: {e}")
            exit(1)
    
    def setup_file_storage(self):
        """Setup local file storage for MinIO upload"""
        print("Setting up file storage for MinIO...")
        
        # Create directory structure
        directories = [
            'minio_data/bronze/raw_data',
            'minio_data/silver/processed_data', 
            'minio_data/gold/anomalies'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        print("SUCCESS: File storage ready for MinIO upload")
    
    def generate_sensor_reading(self, sensor_id):
        # Higher anomaly rate for more interesting demo
        is_anomaly = random.random() < 0.25  # 25% anomaly rate
        
        if is_anomaly:
            temperature = random.uniform(80, 120)
            humidity = random.uniform(0, 20)
            severity = 'HIGH' if temperature > 100 else 'MEDIUM'
        else:
            temperature = random.uniform(18, 28)
            humidity = random.uniform(40, 70)
            severity = 'LOW'
            
        return {
            'sensor_id': sensor_id,
            'timestamp': datetime.now(),
            'temperature': round(temperature, 2),
            'humidity': round(humidity, 2),
            'actual_anomaly': is_anomaly,
            'severity': severity
        }
    
    def save_to_database(self, reading, prediction):
        """Save to PostgreSQL for Grafana visualization"""
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
                    (sensor_id, timestamp, temperature, humidity, alert_type, severity)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    reading['sensor_id'],
                    reading['timestamp'],
                    reading['temperature'],
                    reading['humidity'],
                    'ML_DETECTED',
                    reading['severity']
                ))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"Database save error: {e}")
            return False
    
    def save_to_files(self, reading, prediction):
        """Save to files for manual MinIO upload"""
        try:
            timestamp_str = reading['timestamp'].strftime('%Y%m%d_%H%M%S')
            
            data = {
                'sensor_id': reading['sensor_id'],
                'timestamp': reading['timestamp'].isoformat(),
                'temperature': reading['temperature'],
                'humidity': reading['humidity'],
                'ml_prediction': prediction,
                'actual_anomaly': reading['actual_anomaly'],
                'severity': reading['severity'],
                'processing_time': datetime.now().isoformat()
            }
            
            # Save to bronze (all data)
            bronze_file = f"minio_data/bronze/raw_data/{reading['sensor_id']}_{timestamp_str}.json"
            with open(bronze_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Save to appropriate layer based on prediction
            if prediction == -1:
                # Anomaly - save to gold
                gold_file = f"minio_data/gold/anomalies/anomaly_{reading['sensor_id']}_{timestamp_str}.json"
                with open(gold_file, 'w') as f:
                    json.dump(data, f, indent=2)
            else:
                # Normal - save to silver
                silver_file = f"minio_data/silver/processed_data/normal_{reading['sensor_id']}_{timestamp_str}.json"
                with open(silver_file, 'w') as f:
                    json.dump(data, f, indent=2)
            
            self.stats['files_created'] += 1
            return True
            
        except Exception as e:
            print(f"File save error: {e}")
            return False
    
    def print_status(self):
        uptime = datetime.now() - self.stats['start_time']
        anomaly_rate = (self.stats['anomalies_detected'] / self.stats['total_readings'] * 100) if self.stats['total_readings'] > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"IoT ML PIPELINE STATUS")
        print(f"{'='*60}")
        print(f"Uptime: {uptime}")
        print(f"Total Readings: {self.stats['total_readings']}")
        print(f"Anomalies Detected: {self.stats['anomalies_detected']} ({anomaly_rate:.1f}%)")
        print(f"Files Created: {self.stats['files_created']}")
        print(f"")
        print(f"DASHBOARDS & INTERFACES:")
        print(f"  Grafana Dashboard: http://localhost:3000")
        print(f"  MinIO Console: http://localhost:9001")
        print(f"")
        print(f"DATA LOCATIONS:")
        print(f"  PostgreSQL: Live data for Grafana")
        print(f"  Files: minio_data/ folder (ready for MinIO upload)")
        print(f"{'='*60}")
    
    def run_pipeline(self):
        print("\nStarting IoT ML Pipeline...")
        print("=" * 50)
        print("LIVE DASHBOARDS:")
        print("  Grafana: http://localhost:3000 (admin/admin)")
        print("  MinIO: http://localhost:9001 (minioadmin/minioadmin)")
        print("")
        print("DATA FLOW:")
        print("  1. Sensors -> ML Model -> PostgreSQL (for Grafana)")
        print("  2. Sensors -> Files (for MinIO manual upload)")
        print("=" * 50)
        
        batch_count = 0
        
        try:
            while True:
                batch_count += 1
                batch_anomalies = 0
                
                print(f"\nProcessing Batch {batch_count} at {datetime.now().strftime('%H:%M:%S')}")
                
                # Process all sensors
                for sensor_id in self.sensors:
                    reading = self.generate_sensor_reading(sensor_id)
                    prediction = self.detector.predict([reading])[0]
                    
                    # Save to database and files
                    self.save_to_database(reading, prediction)
                    self.save_to_files(reading, prediction)
                    
                    self.stats['total_readings'] += 1
                    
                    if prediction == -1:
                        self.stats['anomalies_detected'] += 1
                        batch_anomalies += 1
                        print(f"  ANOMALY: {sensor_id} - T:{reading['temperature']}C H:{reading['humidity']}% [{reading['severity']}]")
                    else:
                        print(f"  Normal:  {sensor_id} - T:{reading['temperature']}C H:{reading['humidity']}%")
                
                print(f"\nBatch {batch_count} Complete: {len(self.sensors)} readings, {batch_anomalies} anomalies")
                
                # Show status every 3 batches
                if batch_count % 3 == 0:
                    self.print_status()
                
                print("Waiting 12 seconds for next batch...")
                time.sleep(12)
                
        except KeyboardInterrupt:
            print("\n\nPipeline stopped by user")
            self.print_status()
            print("\nFINAL INSTRUCTIONS:")
            print("1. Check Grafana dashboards for live data visualization")
            print("2. Upload files from minio_data/ folders to MinIO buckets:")
            print("   - minio_data/bronze/ -> bronze bucket")
            print("   - minio_data/silver/ -> silver bucket") 
            print("   - minio_data/gold/ -> gold bucket")
        finally:
            if self.conn:
                self.conn.close()
            print("Pipeline shutdown complete")

if __name__ == "__main__":
    pipeline = FinalWorkingPipeline()
    pipeline.run_pipeline()