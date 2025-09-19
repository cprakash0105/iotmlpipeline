import sys
import os
import time
import psycopg2
from datetime import datetime
import random

# Add ml-models to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ml-models'))
from anomaly_detector import AnomalyDetector

class GrafanaPipeline:
    def __init__(self):
        self.detector = AnomalyDetector()
        self.load_model()
        self.sensors = ['sensor_001', 'sensor_002', 'sensor_003', 'sensor_004', 'sensor_005']
        self.setup_database()
        
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
        is_anomaly = random.random() < 0.08  # 8% anomaly rate
        
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
    
    def run_realtime_pipeline(self):
        print("Starting Real-Time IoT Pipeline for Grafana")
        print("Data will be saved to PostgreSQL for dashboard visualization")
        print("=" * 60)
        
        reading_count = 0
        anomaly_count = 0
        
        try:
            while True:
                # Generate readings from all sensors
                for sensor_id in self.sensors:
                    reading = self.generate_sensor_reading(sensor_id)
                    
                    # ML prediction
                    prediction = self.detector.predict([reading])[0]
                    
                    # Save to database
                    self.save_to_database(reading, prediction)
                    
                    reading_count += 1
                    
                    if prediction == -1:
                        anomaly_count += 1
                        print(f"ANOMALY DETECTED: {reading['sensor_id']} - T:{reading['temperature']}°C H:{reading['humidity']}%")
                    else:
                        print(f"Normal: {reading['sensor_id']} - T:{reading['temperature']}°C H:{reading['humidity']}%")
                
                print(f"Batch complete. Total: {reading_count}, Anomalies: {anomaly_count}")
                time.sleep(3)  # 3 second intervals
                
        except KeyboardInterrupt:
            print(f"\nPipeline stopped. Processed {reading_count} readings, detected {anomaly_count} anomalies")
        finally:
            if self.conn:
                self.conn.close()

if __name__ == "__main__":
    pipeline = GrafanaPipeline()
    pipeline.run_realtime_pipeline()