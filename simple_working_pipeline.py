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

class SimpleWorkingPipeline:
    def __init__(self):
        print("=== STARTING SIMPLE IoT PIPELINE ===")
        
        self.detector = AnomalyDetector()
        self.load_model()
        self.sensors = ['sensor_001', 'sensor_002', 'sensor_003', 'sensor_004', 'sensor_005']
        self.setup_database()
        
        self.stats = {
            'total_readings': 0,
            'anomalies_detected': 0,
            'start_time': datetime.now()
        }
        
    def load_model(self):
        try:
            self.detector.load_model('ml-models/anomaly_model.pkl')
            print("SUCCESS: ML model loaded")
        except Exception as e:
            print(f"Training new model: {e}")
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
        print("Connecting to PostgreSQL...")
        try:
            self.conn = psycopg2.connect(
                host="localhost",
                database="iot_analytics",
                user="postgres",
                password="postgres",
                port="5432"
            )
            self.cursor = self.conn.cursor()
            
            # Create tables for Grafana
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
            
            # Clear old data for fresh start
            self.cursor.execute("DELETE FROM sensor_readings WHERE created_at < NOW() - INTERVAL '1 hour'")
            self.cursor.execute("DELETE FROM anomaly_alerts WHERE created_at < NOW() - INTERVAL '1 hour'")
            
            self.conn.commit()
            print("SUCCESS: Database connected and ready")
            
        except Exception as e:
            print(f"ERROR: Database connection failed: {e}")
            exit(1)
    
    def generate_sensor_reading(self, sensor_id):
        is_anomaly = random.random() < 0.2  # 20% anomaly rate for more action
        
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
            return True
            
        except Exception as e:
            print(f"Database save error: {e}")
            return False
    
    def save_to_minio_manually(self, reading, prediction):
        """Save to local files that you can manually upload to MinIO"""
        try:
            os.makedirs('data/bronze', exist_ok=True)
            os.makedirs('data/silver', exist_ok=True)
            os.makedirs('data/gold', exist_ok=True)
            
            data = {
                'sensor_id': reading['sensor_id'],
                'timestamp': reading['timestamp'].isoformat(),
                'temperature': reading['temperature'],
                'humidity': reading['humidity'],
                'ml_prediction': prediction,
                'actual_anomaly': reading['actual_anomaly']
            }
            
            # Save to bronze (all data)
            with open(f"data/bronze/sensor_data_{datetime.now().strftime('%Y%m%d_%H%M')}.json", 'w') as f:
                json.dump(data, f)
            
            # Save to appropriate layer
            if prediction == -1:
                with open(f"data/gold/anomaly_{reading['sensor_id']}_{int(time.time())}.json", 'w') as f:
                    json.dump(data, f)
            else:
                with open(f"data/silver/normal_{reading['sensor_id']}_{int(time.time())}.json", 'w') as f:
                    json.dump(data, f)
            
            return True
            
        except Exception as e:
            print(f"File save error: {e}")
            return False
    
    def print_status(self):
        uptime = datetime.now() - self.stats['start_time']
        anomaly_rate = (self.stats['anomalies_detected'] / self.stats['total_readings'] * 100) if self.stats['total_readings'] > 0 else 0
        
        print(f"\n--- PIPELINE STATUS ---")
        print(f"Uptime: {uptime}")
        print(f"Total Readings: {self.stats['total_readings']}")
        print(f"Anomalies: {self.stats['anomalies_detected']} ({anomaly_rate:.1f}%)")
        print(f"Grafana: http://localhost:3000")
        print(f"MinIO Console: http://localhost:9001")
        print("----------------------")
    
    def run_pipeline(self):
        print("Starting IoT Pipeline...")
        print("Grafana Dashboard: http://localhost:3000 (admin/admin)")
        print("MinIO Console: http://localhost:9001 (minioadmin/minioadmin)")
        print("Data will appear in PostgreSQL for Grafana visualization")
        print("Local files will be created in data/ folder for manual MinIO upload")
        
        batch_count = 0
        
        try:
            while True:
                batch_count += 1
                batch_anomalies = 0
                
                print(f"\nProcessing Batch {batch_count}")
                
                # Process all sensors
                for sensor_id in self.sensors:
                    reading = self.generate_sensor_reading(sensor_id)
                    prediction = self.detector.predict([reading])[0]
                    
                    # Save to database and files
                    self.save_to_database(reading, prediction)
                    self.save_to_minio_manually(reading, prediction)
                    
                    self.stats['total_readings'] += 1
                    
                    if prediction == -1:
                        self.stats['anomalies_detected'] += 1
                        batch_anomalies += 1
                        print(f"  ANOMALY: {sensor_id} - T:{reading['temperature']}C H:{reading['humidity']}%")
                    else:
                        print(f"  Normal:  {sensor_id} - T:{reading['temperature']}C H:{reading['humidity']}%")
                
                print(f"Batch {batch_count}: {len(self.sensors)} readings, {batch_anomalies} anomalies")
                self.print_status()
                
                print("Waiting 10 seconds...")
                time.sleep(10)
                
        except KeyboardInterrupt:
            print("\nPipeline stopped by user")
        finally:
            if self.conn:
                self.conn.close()
            print("Pipeline shutdown complete")

if __name__ == "__main__":
    pipeline = SimpleWorkingPipeline()
    pipeline.run_pipeline()