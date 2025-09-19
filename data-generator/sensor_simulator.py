import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer

class IoTSensorSimulator:
    def __init__(self, kafka_bootstrap_servers='localhost:9092'):
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.sensors = ['sensor_001', 'sensor_002', 'sensor_003', 'sensor_004', 'sensor_005']
        
    def generate_sensor_data(self, sensor_id):
        # Simulate normal vs anomaly patterns
        is_anomaly = random.random() < 0.05  # 5% anomaly rate
        
        if is_anomaly:
            temperature = random.uniform(80, 120)  # Abnormal high temp
            humidity = random.uniform(0, 20)       # Abnormal low humidity
        else:
            temperature = random.uniform(18, 28)   # Normal range
            humidity = random.uniform(40, 70)      # Normal range
            
        return {
            'sensor_id': sensor_id,
            'timestamp': datetime.now().isoformat(),
            'temperature': round(temperature, 2),
            'humidity': round(humidity, 2),
            'is_anomaly': is_anomaly
        }
    
    def start_streaming(self, topic='iot-sensors', interval=2):
        print(f"Starting IoT sensor simulation to topic: {topic}")
        try:
            while True:
                for sensor_id in self.sensors:
                    data = self.generate_sensor_data(sensor_id)
                    self.producer.send(topic, data)
                    print(f"Sent: {data}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Stopping sensor simulation...")
        finally:
            self.producer.close()

if __name__ == "__main__":
    simulator = IoTSensorSimulator()
    simulator.start_streaming()