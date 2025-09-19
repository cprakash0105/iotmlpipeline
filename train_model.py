import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'ml-models'))
from anomaly_detector import AnomalyDetector
from datetime import datetime, timedelta
import random

def generate_training_data(num_samples=1000):
    """Generate synthetic training data"""
    data = []
    
    for i in range(num_samples):
        # 90% normal data, 10% anomalies
        is_anomaly = random.random() < 0.1
        
        if is_anomaly:
            temperature = random.uniform(80, 120)
            humidity = random.uniform(0, 20)
        else:
            temperature = random.uniform(18, 28)
            humidity = random.uniform(40, 70)
        
        data.append({
            'sensor_id': f'sensor_{random.randint(1, 5):03d}',
            'timestamp': datetime.now() - timedelta(minutes=random.randint(0, 1440)),
            'temperature': round(temperature, 2),
            'humidity': round(humidity, 2),
            'is_anomaly': is_anomaly
        })
    
    return data

def main():
    print("Generating training data...")
    training_data = generate_training_data(1000)
    
    print("Training anomaly detection model...")
    detector = AnomalyDetector()
    detector.train(training_data)
    
    # Save the trained model
    detector.save_model('ml-models/anomaly_model.pkl')
    print("Model saved to ml-models/anomaly_model.pkl")
    
    # Test the model
    test_data = generate_training_data(100)
    predictions = detector.predict(test_data)
    
    anomaly_count = sum(1 for p in predictions if p == -1)
    print(f"Test completed: {anomaly_count} anomalies detected out of {len(test_data)} samples")

if __name__ == "__main__":
    main()