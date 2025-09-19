# Quick Grafana Dashboard Setup

## 🚀 Step-by-Step Instructions

### 1. Access Grafana
- Open: http://localhost:3000
- Login: admin / admin
- Skip password change or set new password

### 2. Add PostgreSQL Data Source
1. Click **Configuration** (gear icon) → **Data Sources**
2. Click **Add data source**
3. Select **PostgreSQL**
4. Fill in these settings:
   ```
   Name: IoT-PostgreSQL
   Host: localhost:5432
   Database: iot_analytics
   User: postgres
   Password: postgres
   SSL Mode: disable
   Version: 13+
   ```
5. Click **Save & Test** (should show green checkmark)

### 3. Create Your First Dashboard
1. Click **+** → **Dashboard**
2. Click **Add new panel**

### 4. Panel 1: Real-Time Temperature
- **Query**:
```sql
SELECT 
  timestamp as time,
  temperature as value,
  sensor_id as metric
FROM sensor_readings 
WHERE $__timeFilter(timestamp)
ORDER BY timestamp
```
- **Visualization**: Time series
- **Title**: "Real-Time Temperature Readings"

### 5. Panel 2: Anomaly Count
- **Query**:
```sql
SELECT COUNT(*) as value
FROM anomaly_alerts 
WHERE $__timeFilter(timestamp)
```
- **Visualization**: Stat
- **Title**: "Total Anomalies Detected"

### 6. Panel 3: Latest Sensor Status
- **Query**:
```sql
SELECT 
  sensor_id,
  temperature,
  humidity,
  CASE WHEN ml_prediction = -1 THEN 'ANOMALY' ELSE 'NORMAL' END as status,
  timestamp
FROM sensor_readings 
WHERE timestamp > NOW() - INTERVAL '5 minutes'
ORDER BY timestamp DESC
LIMIT 20
```
- **Visualization**: Table
- **Title**: "Latest Sensor Readings"

### 7. Panel 4: Temperature vs Humidity
- **Query**:
```sql
SELECT 
  temperature,
  humidity,
  CASE WHEN ml_prediction = -1 THEN 'Anomaly' ELSE 'Normal' END as series
FROM sensor_readings 
WHERE $__timeFilter(timestamp)
```
- **Visualization**: Scatter plot (or Time series)
- **Title**: "Temperature vs Humidity"

### 8. Dashboard Settings
- Set **Time Range**: Last 1 hour
- Set **Refresh**: 5s
- **Save Dashboard** with name "IoT ML Pipeline Monitor"

## 🎯 What You'll See

Once the pipeline is running, you'll see:
- **Live temperature data** streaming in real-time
- **Anomaly alerts** when sensors detect unusual readings
- **Sensor status table** showing the latest readings
- **Data relationships** in scatter plots

## 📁 MinIO Data Upload

Since the S3 API has connection issues, you can manually upload data:

1. **Access MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
2. **Navigate to buckets**: bronze, silver, gold
3. **Upload files** from the local `data/` folder:
   - `data/bronze/` → Upload to bronze bucket
   - `data/silver/` → Upload to silver bucket  
   - `data/gold/` → Upload to gold bucket

## 🔧 Troubleshooting

### No Data in Grafana?
1. Check if pipeline is running
2. Verify PostgreSQL connection in Grafana
3. Run this query in Grafana to test:
```sql
SELECT COUNT(*) FROM sensor_readings;
```

### Dashboard Not Updating?
1. Check refresh rate (should be 5s)
2. Verify time range includes recent data
3. Check if pipeline is generating new data

### Connection Issues?
1. Ensure all containers are running: `podman ps`
2. Check PostgreSQL: `podman logs config-postgres-1`
3. Check Grafana: `podman logs config-grafana-1`

## 🎉 Success Indicators

You'll know everything is working when:
- ✅ Grafana shows live temperature graphs
- ✅ Anomaly count increases over time
- ✅ Sensor status table updates every few seconds
- ✅ MinIO console shows uploaded files
- ✅ Console shows "ANOMALY" and "Normal" readings

**Ready to start? Run: `python simple_working_pipeline.py`**