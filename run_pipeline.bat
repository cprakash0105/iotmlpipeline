@echo off
echo IoT ML Pipeline Launcher
echo ========================

echo 1. Starting infrastructure (Kafka, MinIO, PostgreSQL)...
cd config
docker-compose up -d
cd ..

echo 2. Waiting for services to start...
timeout /t 30

echo 3. Training ML model...
python train_model.py

echo 4. Pipeline ready! 
echo.
echo To start data generation: python data-generator/sensor_simulator.py
echo To run Spark pipeline: spark-submit streaming/spark_ml_pipeline.py
echo.
echo MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
echo Kafka: localhost:9092
echo PostgreSQL: localhost:5432 (postgres/postgres)

pause