import pickle
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def train(self, data):
        """Train the anomaly detection model"""
        features = self.extract_features(data)
        scaled_features = self.scaler.fit_transform(features)
        self.model.fit(scaled_features)
        self.is_trained = True
        print(f"Model trained on {len(data)} samples")
    
    def predict(self, data):
        """Predict anomalies in new data"""
        if not self.is_trained:
            return [0] * len(data)  # Return normal if not trained
            
        features = self.extract_features(data)
        scaled_features = self.scaler.transform(features)
        predictions = self.model.predict(scaled_features)
        return [-1 if p == -1 else 0 for p in predictions]  # -1 = anomaly, 0 = normal
    
    def extract_features(self, data):
        """Extract features from sensor data"""
        features = []
        for record in data:
            features.append([
                record['temperature'],
                record['humidity'],
                record['temperature'] / record['humidity'] if record['humidity'] > 0 else 0
            ])
        return np.array(features)
    
    def save_model(self, path):
        """Save trained model"""
        with open(path, 'wb') as f:
            pickle.dump({'model': self.model, 'scaler': self.scaler}, f)
    
    def load_model(self, path):
        """Load trained model"""
        with open(path, 'rb') as f:
            saved = pickle.load(f)
            self.model = saved['model']
            self.scaler = saved['scaler']
            self.is_trained = True