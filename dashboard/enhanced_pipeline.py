import sys
import os
import time
import json
import psycopg2
from datetime import datetime
import random

# Add ml-models to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ml-models'))
from anomaly_detector import AnomalyDetector

class EnhancedPipeline:
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
            
            # Create tables with better structure for Grafana
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
            
            # Create summary table for dashboard metrics
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_name VARCHAR(100),
                    metric_value FLOAT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.conn.commit()
            print("SUCCESS: Database setup complete")
            
        except Exception as e:
            print(f"Database connection failed: {e}")
            self.conn = None
    
    def generate_sensor_reading(self, sensor_id):
        is_anomaly = random.random() < 0.12  # 12% anomaly rate for more action
        
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
    
    def save_to_file(self, reading, prediction):
        """Save data to files for MinIO simulation"""
        try:
            # Create directories if they don't exist
            os.makedirs('../data/bronze', exist_ok=True)
            os.makedirs('../data/silver', exist_ok=True)
            os.makedirs('../data/gold', exist_ok=True)
            
            # Save to bronze (raw data)
            bronze_file = f"../data/bronze/sensor_data_{datetime.now().strftime('%Y%m%d_%H')}.jsonl"
            with open(bronze_file, 'a') as f:
                data = {
                    'sensor_id': reading['sensor_id'],
                    'timestamp': reading['timestamp'].isoformat(),
                    'temperature': reading['temperature'],
                    'humidity': reading['humidity'],
                    'ml_prediction': prediction
                }
                f.write(json.dumps(data) + '\n')
            
            # Save to appropriate layer based on prediction
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
                    
        except Exception as e:
            print(f"File save error: {e}")
    
    def update_dashboard_metrics(self, total_readings, anomaly_count):
        """Update metrics for dashboard"""
        if not self.conn:
            return
            
        try:
            metrics = [
                ('total_readings', total_readings),
                ('anomaly_count', anomaly_count),
                ('anomaly_rate', (anomaly_count / total_readings * 100) if total_readings > 0 else 0),
                ('normal_count', total_readings - anomaly_count)
            ]
            
            for metric_name, value in metrics:
                self.cursor.execute("""
                    INSERT INTO dashboard_metrics (metric_name, metric_value)
                    VALUES (%s, %s)
                """, (metric_name, value))
            
            self.conn.commit()
            
        except Exception as e:
            print(f"Metrics update error: {e}")
    
    def run_realtime_pipeline(self):
        print("Starting Enhanced Real-Time IoT Pipeline")
        print("Data will be saved to PostgreSQL AND local files")
        print("Access Grafana at: http://localhost:3000 (admin/admin)")
        print("=" * 60)
        
        reading_count = 0
        anomaly_count = 0
        batch_count = 0
        
        try:
            while True:
                batch_count += 1
                batch_anomalies = 0
                
                print(f"\n--- Batch {batch_count} ---")
                
                # Generate readings from all sensors
                for sensor_id in self.sensors:
                    reading = self.generate_sensor_reading(sensor_id)
                    
                    # ML prediction
                    prediction = self.detector.predict([reading])[0]
                    
                    # Save to database and files
                    self.save_to_database(reading, prediction)
                    self.save_to_file(reading, prediction)
                    
                    reading_count += 1
                    
                    if prediction == -1:
                        anomaly_count += 1
                        batch_anomalies += 1
                        print(f"  ANOMALY: {reading['sensor_id']} - T:{reading['temperature']}°C H:{reading['humidity']}%")
                    else:
                        print(f"  Normal:  {reading['sensor_id']} - T:{reading['temperature']}°C H:{reading['humidity']}%")
                
                # Update dashboard metrics
                self.update_dashboard_metrics(reading_count, anomaly_count)
                
                print(f"Batch Summary: {5 - batch_anomalies} normal, {batch_anomalies} anomalies")
                print(f"Total: {reading_count} readings, {anomaly_count} anomalies ({anomaly_count/reading_count*100:.1f}%)")
                
                time.sleep(5)  # 5 second intervals for better visualization
                
        except KeyboardInterrupt:
            print(f"\nPipeline stopped. Final stats:")
            print(f"Total readings: {reading_count}")
            print(f"Anomalies detected: {anomaly_count}")
            print(f"Anomaly rate: {anomaly_count/reading_count*100:.1f}%")
        finally:
            if self.conn:
                self.conn.close()

if __name__ == "__main__":
    pipeline = EnhancedPipeline()
    pipeline.run_realtime_pipeline()