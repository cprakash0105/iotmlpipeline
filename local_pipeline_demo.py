import sys
import os
import time
import json
from datetime import datetime
import random

# Add ml-models to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'ml-models'))
from anomaly_detector import AnomalyDetector

class LocalIoTPipelineDemo:
    def __init__(self):
        self.detector = AnomalyDetector()
        self.load_model()
        self.sensors = ['sensor_001', 'sensor_002', 'sensor_003', 'sensor_004', 'sensor_005']
        
    def load_model(self):
        """Load the trained model"""
        try:
            self.detector.load_model('ml-models/anomaly_model.pkl')
            print("SUCCESS: ML model loaded successfully")
        except:
            print("! Model not found, training new model...")
            self.train_model()
    
    def train_model(self):
        """Train a new model if not found"""
        training_data = self.generate_training_data(1000)
        self.detector.train(training_data)
        self.detector.save_model('ml-models/anomaly_model.pkl')
        print("SUCCESS: New model trained and saved")
    
    def generate_training_data(self, num_samples):
        """Generate synthetic training data"""
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
    
    def generate_sensor_reading(self, sensor_id):
        """Generate a single sensor reading"""
        is_anomaly = random.random() < 0.05  # 5% anomaly rate
        
        if is_anomaly:
            temperature = random.uniform(80, 120)
            humidity = random.uniform(0, 20)
        else:
            temperature = random.uniform(18, 28)
            humidity = random.uniform(40, 70)
            
        return {
            'sensor_id': sensor_id,
            'timestamp': datetime.now().isoformat(),
            'temperature': round(temperature, 2),
            'humidity': round(humidity, 2),
            'actual_anomaly': is_anomaly
        }
    
    def process_batch(self, readings):
        """Process a batch of sensor readings"""
        if not readings:
            return
            
        print(f"\n--- Processing batch of {len(readings)} readings ---")
        
        # ML prediction
        predictions = self.detector.predict(readings)
        
        normal_count = 0
        anomaly_count = 0
        
        for i, reading in enumerate(readings):
            prediction = predictions[i]
            actual = reading['actual_anomaly']
            
            status = "ANOMALY" if prediction == -1 else "NORMAL"
            accuracy = "CORRECT" if (prediction == -1) == actual else "WRONG"
            
            print(f"{reading['sensor_id']}: T={reading['temperature']}°C, H={reading['humidity']}% -> {status} {accuracy}")
            
            if prediction == -1:
                anomaly_count += 1
                # Simulate saving to "gold" bucket
                print(f"  ALERT: Anomaly detected in {reading['sensor_id']}!")
            else:
                normal_count += 1
        
        print(f"Summary: {normal_count} normal, {anomaly_count} anomalies detected")
        return normal_count, anomaly_count
    
    def run_demo(self, duration_seconds=60, batch_size=5):
        """Run the demo pipeline"""
        print("Starting IoT ML Pipeline Demo")
        print(f"Duration: {duration_seconds}s, Batch size: {batch_size}")
        print("=" * 50)
        
        start_time = time.time()
        batch_readings = []
        total_normal = 0
        total_anomalies = 0
        
        try:
            while time.time() - start_time < duration_seconds:
                # Generate readings from all sensors
                for sensor_id in self.sensors:
                    reading = self.generate_sensor_reading(sensor_id)
                    batch_readings.append(reading)
                
                # Process batch when it reaches the desired size
                if len(batch_readings) >= batch_size:
                    normal, anomalies = self.process_batch(batch_readings)
                    total_normal += normal
                    total_anomalies += anomalies
                    batch_readings = []
                
                time.sleep(2)  # Wait 2 seconds between sensor cycles
                
        except KeyboardInterrupt:
            print("\nDemo stopped by user")
        
        # Process remaining readings
        if batch_readings:
            normal, anomalies = self.process_batch(batch_readings)
            total_normal += normal
            total_anomalies += anomalies
        
        print("\n" + "=" * 50)
        print(f"FINAL RESULTS:")
        print(f"Total readings processed: {total_normal + total_anomalies}")
        print(f"Normal readings: {total_normal}")
        print(f"Anomalies detected: {total_anomalies}")
        print(f"Anomaly rate: {total_anomalies/(total_normal + total_anomalies)*100:.1f}%")

if __name__ == "__main__":
    demo = LocalIoTPipelineDemo()
    demo.run_demo(duration_seconds=30, batch_size=10)