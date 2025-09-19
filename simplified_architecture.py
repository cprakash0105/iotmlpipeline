import sys
import os
import psycopg2
from datetime import datetime
import random

# Simplified IoT Pipeline without MinIO
# Focus: Real-time analytics with PostgreSQL + Grafana

sys.path.append(os.path.join(os.path.dirname(__file__), 'ml-models'))
from anomaly_detector import AnomalyDetector

class SimplifiedIoTPipeline:
    def __init__(self):
        print("=== SIMPLIFIED IoT PIPELINE (No MinIO) ===")
        
        self.detector = AnomalyDetector()
        self.load_model()
        self.sensors = ['sensor_001', 'sensor_002', 'sensor_003', 'sensor_004', 'sensor_005']
        self.setup_database()
        
    def load_model(self):
        try:
            self.detector.load_model('ml-models/anomaly_model.pkl')
            print("✓ ML model loaded")
        except:
            self.train_model()
    
    def train_model(self):
        training_data = []
        for i in range(1000):
            is_anomaly = random.random() < 0.1
            temperature = random.uniform(80, 120) if is_anomaly else random.uniform(18, 28)
            humidity = random.uniform(0, 20) if is_anomaly else random.uniform(40, 70)
            
            training_data.append({
                'sensor_id': f'sensor_{random.randint(1, 5):03d}',
                'timestamp': datetime.now().isoformat(),
                'temperature': round(temperature, 2),
                'humidity': round(humidity, 2),
                'is_anomaly': is_anomaly
            })
        
        self.detector.train(training_data)
        self.detector.save_model('ml-models/anomaly_model.pkl')
        print("✓ Model trained")
    
    def setup_database(self):
        self.conn = psycopg2.connect(
            host="localhost", database="iot_analytics",
            user="postgres", password="postgres", port="5432"
        )
        self.cursor = self.conn.cursor()
        
        # Enhanced tables for complete analytics
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
            CREATE TABLE IF NOT EXISTS historical_data (
                id SERIAL PRIMARY KEY,
                sensor_id VARCHAR(50),
                date DATE,
                avg_temperature FLOAT,
                max_temperature FLOAT,
                min_temperature FLOAT,
                anomaly_count INTEGER,
                total_readings INTEGER
            )
        """)
        
        self.conn.commit()
        print("✓ PostgreSQL ready (replaces MinIO for this demo)")
    
    def run_simplified_pipeline(self):
        print("\n🚀 RUNNING SIMPLIFIED PIPELINE")
        print("📊 Grafana: http://localhost:3000")
        print("💾 All data in PostgreSQL (no MinIO needed)")
        
        batch = 0
        try:
            while True:
                batch += 1
                print(f"\nBatch {batch}:")
                
                for sensor_id in self.sensors:
                    # Generate reading
                    is_anomaly = random.random() < 0.2
                    temp = random.uniform(80, 120) if is_anomaly else random.uniform(18, 28)
                    humidity = random.uniform(0, 20) if is_anomaly else random.uniform(40, 70)
                    
                    reading = {
                        'sensor_id': sensor_id,
                        'timestamp': datetime.now(),
                        'temperature': round(temp, 2),
                        'humidity': round(humidity, 2),
                        'actual_anomaly': is_anomaly
                    }
                    
                    # ML prediction
                    prediction = self.detector.predict([reading])[0]
                    
                    # Save to PostgreSQL
                    self.cursor.execute("""
                        INSERT INTO sensor_readings 
                        (sensor_id, timestamp, temperature, humidity, is_anomaly, ml_prediction)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (sensor_id, reading['timestamp'], temp, humidity, is_anomaly, prediction))
                    
                    status = "ANOMALY" if prediction == -1 else "Normal"
                    print(f"  {sensor_id}: {temp}°C, {humidity}% -> {status}")
                
                self.conn.commit()
                print("  ✓ Data saved to PostgreSQL")
                
                import time
                time.sleep(8)
                
        except KeyboardInterrupt:
            print("\n✓ Pipeline stopped")
        finally:
            self.conn.close()

if __name__ == "__main__":
    pipeline = SimplifiedIoTPipeline()
    pipeline.run_simplified_pipeline()