# Grafana Dashboard Setup Guide

## 🎯 Complete Monitoring Solution

This guide will help you set up comprehensive monitoring and logging dashboards in Grafana for the IoT ML Pipeline.

## 📊 What You'll Get

### 1. **Real-Time Monitoring**
- Live sensor temperature and humidity readings
- Anomaly detection alerts and rates
- System performance metrics
- Pipeline processing times

### 2. **System Health Monitoring**
- MinIO upload success rates
- Database save success rates
- Error tracking and logging
- Component connectivity status

### 3. **Business Intelligence**
- Anomaly trends over time
- Sensor performance comparison
- Processing efficiency metrics
- Historical data analysis

## 🚀 Setup Steps

### Step 1: Access Grafana
1. Open your browser and go to: `http://localhost:3000`
2. Login with:
   - Username: `admin`
   - Password: `admin`
3. Change password when prompted (or skip)

### Step 2: Add PostgreSQL Data Source
1. Click on **Configuration** (gear icon) → **Data Sources**
2. Click **Add data source**
3. Select **PostgreSQL**
4. Configure with these settings:
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

### Step 3: Create Dashboard Panels

#### Panel 1: Real-Time Temperature Readings
- **Visualization**: Time series
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

#### Panel 2: Anomaly Detection Count
- **Visualization**: Stat
- **Query**:
```sql
SELECT COUNT(*) as value
FROM anomaly_alerts 
WHERE $__timeFilter(timestamp)
```

#### Panel 3: System Events Log
- **Visualization**: Logs
- **Query**:
```sql
SELECT 
  timestamp,
  CONCAT(event_type, ': ', event_status, ' - ', message) as message
FROM system_events 
WHERE $__timeFilter(timestamp)
ORDER BY timestamp DESC
LIMIT 100
```

#### Panel 4: Pipeline Performance
- **Visualization**: Time series
- **Query**:
```sql
SELECT 
  timestamp as time,
  metric_value as value,
  metric_name as metric
FROM pipeline_metrics 
WHERE metric_name IN ('batch_processing_time_ms', 'ml_inference_time_ms', 'minio_upload_time_ms')
  AND $__timeFilter(timestamp)
ORDER BY timestamp
```

#### Panel 5: Sensor Status Table
- **Visualization**: Table
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

#### Panel 6: MinIO Upload Success Rate
- **Visualization**: Stat
- **Query**:
```sql
SELECT 
  (SUM(CASE WHEN metric_name = 'minio_upload_success' THEN metric_value ELSE 0 END) / 
   NULLIF(SUM(CASE WHEN metric_name IN ('minio_upload_success', 'minio_upload_failed') THEN metric_value ELSE 0 END), 0)) * 100 as value
FROM pipeline_metrics 
WHERE $__timeFilter(timestamp)
```

#### Panel 7: Temperature vs Humidity Scatter Plot
- **Visualization**: Scatter plot (if available) or Time series
- **Query**:
```sql
SELECT 
  temperature,
  humidity,
  CASE WHEN ml_prediction = -1 THEN 'Anomaly' ELSE 'Normal' END as series
FROM sensor_readings 
WHERE $__timeFilter(timestamp)
```

#### Panel 8: Anomaly Rate Trend
- **Visualization**: Time series
- **Query**:
```sql
SELECT 
  timestamp as time,
  metric_value as value
FROM pipeline_metrics 
WHERE metric_name = 'anomaly_rate_percent'
  AND $__timeFilter(timestamp)
ORDER BY timestamp
```

### Step 4: Configure Dashboard Settings
1. **Time Range**: Set to "Last 1 hour" with auto-refresh every 5 seconds
2. **Variables**: Create a sensor filter variable:
   ```sql
   SELECT DISTINCT sensor_id FROM sensor_readings
   ```
3. **Alerts**: Set up alerts for:
   - High anomaly rate (>20%)
   - System errors
   - Connection failures

## 📈 Dashboard Features

### Real-Time Updates
- All panels refresh every 5 seconds
- Live data streaming from the pipeline
- Automatic time range adjustment

### Interactive Elements
- Click on sensor names to filter data
- Zoom into time ranges for detailed analysis
- Hover over data points for exact values

### Alert Notifications
- Email/Slack notifications for anomalies
- System health alerts
- Performance degradation warnings

## 🔧 Troubleshooting

### Data Source Issues
```bash
# Check PostgreSQL connection
podman logs config-postgres-1

# Test database connectivity
psql -h localhost -U postgres -d iot_analytics
```

### No Data Showing
1. Ensure the pipeline is running
2. Check that data is being inserted:
```sql
SELECT COUNT(*) FROM sensor_readings WHERE timestamp > NOW() - INTERVAL '10 minutes';
```

### Performance Issues
- Reduce refresh rate if needed
- Limit time ranges for large datasets
- Add database indexes for better performance

## 📊 Sample Queries for Custom Panels

### Average Temperature by Sensor
```sql
SELECT 
  sensor_id,
  AVG(temperature) as avg_temp
FROM sensor_readings 
WHERE $__timeFilter(timestamp)
GROUP BY sensor_id
```

### Hourly Anomaly Count
```sql
SELECT 
  DATE_TRUNC('hour', timestamp) as time,
  COUNT(*) as value
FROM anomaly_alerts 
WHERE $__timeFilter(timestamp)
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY time
```

### System Uptime
```sql
SELECT 
  EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/3600 as uptime_hours
FROM system_events
WHERE event_type = 'pipeline_start'
```

## 🎯 Next Steps

1. **Start the Pipeline**: Run `python grafana_optimized_pipeline.py`
2. **Monitor Live Data**: Watch the dashboards populate with real-time data
3. **Set Up Alerts**: Configure notifications for critical events
4. **Customize Views**: Add more panels based on your specific needs

Your Grafana dashboard will now provide comprehensive monitoring and logging for the entire IoT ML pipeline!