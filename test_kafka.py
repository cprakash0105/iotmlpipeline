from kafka import KafkaProducer
import json
import time

def test_kafka_connection():
    try:
        producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Send a test message
        test_data = {'test': 'message', 'timestamp': time.time()}
        producer.send('test-topic', test_data)
        producer.flush()
        producer.close()
        
        print("SUCCESS: Kafka connection successful!")
        return True
    except Exception as e:
        print(f"ERROR: Kafka connection failed: {e}")
        return False

if __name__ == "__main__":
    test_kafka_connection()