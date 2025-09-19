from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
import sys
import os

# Add the ml-models directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ml-models'))
from anomaly_detector import AnomalyDetector

class IoTMLPipeline:
    def __init__(self):
        self.spark = SparkSession.builder \
            .appName("IoTMLPipeline") \
            .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
            .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
            .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
            .config("spark.hadoop.fs.s3a.path.style.access", "true") \
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
            .getOrCreate()
        
        self.anomaly_detector = AnomalyDetector()
        self.setup_schema()
    
    def setup_schema(self):
        self.sensor_schema = StructType([
            StructField("sensor_id", StringType(), True),
            StructField("timestamp", StringType(), True),
            StructField("temperature", DoubleType(), True),
            StructField("humidity", DoubleType(), True),
            StructField("is_anomaly", BooleanType(), True)
        ])
    
    def process_batch(self, df, epoch_id):
        """Process each micro-batch"""
        if df.count() == 0:
            return
            
        print(f"Processing batch {epoch_id} with {df.count()} records")
        
        # Convert to pandas for ML processing
        pandas_df = df.toPandas()
        sensor_data = pandas_df.to_dict('records')
        
        # Predict anomalies
        predictions = self.anomaly_detector.predict(sensor_data)
        pandas_df['ml_anomaly'] = predictions
        
        # Convert back to Spark DataFrame
        result_df = self.spark.createDataFrame(pandas_df)
        
        # Add processing timestamp
        result_df = result_df.withColumn("processed_at", current_timestamp())
        
        # Write to different buckets based on anomaly status
        normal_data = result_df.filter(col("ml_anomaly") == 0)
        anomaly_data = result_df.filter(col("ml_anomaly") == -1)
        
        if normal_data.count() > 0:
            normal_data.write.mode("append").parquet("s3a://silver/normal-readings/")
        
        if anomaly_data.count() > 0:
            anomaly_data.write.mode("append").parquet("s3a://gold/anomalies/")
            print(f"ALERT: {anomaly_data.count()} anomalies detected!")
    
    def start_streaming(self):
        """Start the streaming pipeline"""
        # Read from Kafka (simulated with file for now)
        df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "localhost:9092") \
            .option("subscribe", "iot-sensors") \
            .load()
        
        # Parse JSON data
        parsed_df = df.select(
            from_json(col("value").cast("string"), self.sensor_schema).alias("data")
        ).select("data.*")
        
        # Start streaming query
        query = parsed_df.writeStream \
            .foreachBatch(self.process_batch) \
            .outputMode("append") \
            .trigger(processingTime='10 seconds') \
            .start()
        
        query.awaitTermination()

if __name__ == "__main__":
    pipeline = IoTMLPipeline()
    pipeline.start_streaming()