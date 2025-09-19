from flask import Flask, render_template, jsonify
import psycopg2
import json
from datetime import datetime, timedelta
import os

app = Flask(__name__)

def get_db_connection():
    try:
        return psycopg2.connect(
            host="localhost",
            database="iot_analytics",
            user="postgres",
            password="postgres",
            port="5432"
        )
    except:
        return None

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/stats')
def get_stats():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'})
    
    cursor = conn.cursor()
    
    try:
        # Get latest pipeline stats
        cursor.execute("""
            SELECT total_readings, anomalies_detected, minio_uploads, db_saves, errors, uptime_seconds
            FROM pipeline_stats 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        stats = cursor.fetchone()
        
        if stats:
            total_readings, anomalies, minio_uploads, db_saves, errors, uptime = stats
            anomaly_rate = (anomalies / total_readings * 100) if total_readings > 0 else 0
            
            return jsonify({
                'total_readings': total_readings,
                'anomalies_detected': anomalies,
                'anomaly_rate': round(anomaly_rate, 1),
                'minio_uploads': minio_uploads,
                'db_saves': db_saves,
                'errors': errors,
                'uptime_hours': round(uptime / 3600, 1),
                'status': 'running'
            })
        else:
            return jsonify({'status': 'no_data'})
            
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        conn.close()

@app.route('/api/recent_readings')
def get_recent_readings():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'})
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT sensor_id, temperature, humidity, 
                   CASE WHEN ml_prediction = -1 THEN 'ANOMALY' ELSE 'NORMAL' END as status,
                   timestamp
            FROM sensor_readings 
            WHERE timestamp > NOW() - INTERVAL '10 minutes'
            ORDER BY timestamp DESC 
            LIMIT 50
        """)
        
        readings = []
        for row in cursor.fetchall():
            readings.append({
                'sensor_id': row[0],
                'temperature': row[1],
                'humidity': row[2],
                'status': row[3],
                'timestamp': row[4].strftime('%H:%M:%S')
            })
        
        return jsonify(readings)
        
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        conn.close()

@app.route('/api/anomaly_timeline')
def get_anomaly_timeline():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'})
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT DATE_TRUNC('minute', timestamp) as minute, COUNT(*) as count
            FROM anomaly_alerts 
            WHERE timestamp > NOW() - INTERVAL '1 hour'
            GROUP BY minute
            ORDER BY minute
        """)
        
        timeline = []
        for row in cursor.fetchall():
            timeline.append({
                'time': row[0].strftime('%H:%M'),
                'count': row[1]
            })
        
        return jsonify(timeline)
        
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        conn.close()

# Create templates directory and HTML template
@app.before_first_request
def create_template():
    os.makedirs('templates', exist_ok=True)
    
    html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>IoT Pipeline Monitor</title>
    <meta http-equiv="refresh" content="10">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 2em; font-weight: bold; color: #3498db; }
        .stat-label { color: #7f8c8d; margin-top: 5px; }
        .anomaly { color: #e74c3c !important; }
        .normal { color: #27ae60 !important; }
        .readings-table { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .readings-table table { width: 100%; border-collapse: collapse; }
        .readings-table th { background: #34495e; color: white; padding: 12px; text-align: left; }
        .readings-table td { padding: 12px; border-bottom: 1px solid #ecf0f1; }
        .status-indicator { padding: 4px 8px; border-radius: 4px; color: white; font-size: 0.8em; }
        .status-normal { background: #27ae60; }
        .status-anomaly { background: #e74c3c; }
        .loading { text-align: center; padding: 20px; color: #7f8c8d; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 IoT ML Pipeline Monitor</h1>
            <p>Real-time monitoring dashboard for sensor data processing</p>
        </div>
        
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="total-readings">-</div>
                <div class="stat-label">Total Readings</div>
            </div>
            <div class="stat-card">
                <div class="stat-value anomaly" id="anomalies">-</div>
                <div class="stat-label">Anomalies Detected</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="anomaly-rate">-</div>
                <div class="stat-label">Anomaly Rate (%)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value normal" id="uptime">-</div>
                <div class="stat-label">Uptime (hours)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="minio-uploads">-</div>
                <div class="stat-label">MinIO Uploads</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="errors">-</div>
                <div class="stat-label">Errors</div>
            </div>
        </div>
        
        <div class="readings-table">
            <h3 style="margin: 0; padding: 20px; background: #ecf0f1;">Recent Sensor Readings</h3>
            <table>
                <thead>
                    <tr>
                        <th>Sensor ID</th>
                        <th>Temperature (°C)</th>
                        <th>Humidity (%)</th>
                        <th>Status</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody id="readings-tbody">
                    <tr><td colspan="5" class="loading">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Stats error:', data.error);
                        return;
                    }
                    
                    document.getElementById('total-readings').textContent = data.total_readings || '-';
                    document.getElementById('anomalies').textContent = data.anomalies_detected || '-';
                    document.getElementById('anomaly-rate').textContent = data.anomaly_rate || '-';
                    document.getElementById('uptime').textContent = data.uptime_hours || '-';
                    document.getElementById('minio-uploads').textContent = data.minio_uploads || '-';
                    document.getElementById('errors').textContent = data.errors || '-';
                })
                .catch(error => console.error('Error fetching stats:', error));
        }
        
        function updateReadings() {
            fetch('/api/recent_readings')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Readings error:', data.error);
                        return;
                    }
                    
                    const tbody = document.getElementById('readings-tbody');
                    tbody.innerHTML = '';
                    
                    data.forEach(reading => {
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td>${reading.sensor_id}</td>
                            <td>${reading.temperature}</td>
                            <td>${reading.humidity}</td>
                            <td><span class="status-indicator status-${reading.status.toLowerCase()}">${reading.status}</span></td>
                            <td>${reading.timestamp}</td>
                        `;
                    });
                })
                .catch(error => console.error('Error fetching readings:', error));
        }
        
        // Update every 5 seconds
        setInterval(() => {
            updateStats();
            updateReadings();
        }, 5000);
        
        // Initial load
        updateStats();
        updateReadings();
    </script>
</body>
</html>
    '''
    
    with open('templates/dashboard.html', 'w') as f:
        f.write(html_content)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)