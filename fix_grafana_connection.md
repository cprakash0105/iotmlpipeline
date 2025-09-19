# Fix Grafana PostgreSQL Connection

## The Problem
Grafana is trying to connect using IPv6 (`[::1]:5432`) instead of IPv4, causing "connection refused" error.

## Solution Steps

### 1. Update PostgreSQL Data Source in Grafana
1. Go to http://localhost:3000
2. Login: admin/admin
3. Go to **Configuration** → **Data Sources**
4. Find your PostgreSQL data source and click **Edit**
5. Change the **Host** field from `localhost:5432` to one of these:

**Try these hosts in order:**
```
127.0.0.1:5432
```
OR
```
host.docker.internal:5432
```
OR
```
config-postgres-1:5432
```

### 2. Complete Data Source Settings
```
Name: IoT-PostgreSQL
Host: 127.0.0.1:5432
Database: iot_analytics
User: postgres
Password: postgres
SSL Mode: disable
Version: 13+
```

### 3. Test Connection
- Click **Save & Test**
- Should show green "Database Connection OK"

### 4. Alternative: Check PostgreSQL Container Network
If still having issues, let's check the network:
```bash
podman inspect config-postgres-1 | findstr IPAddress
```

## Quick Test Query
Once connected, test with this query in Grafana:
```sql
SELECT NOW() as time, 'test' as message
```

## If Still Not Working
Try creating the data source with this JSON configuration:

1. Go to **Configuration** → **Data Sources**
2. Click **Add data source** → **PostgreSQL**
3. Use these exact settings:
   - **Host**: `127.0.0.1:5432`
   - **Database**: `iot_analytics`
   - **User**: `postgres`
   - **Password**: `postgres`
   - **SSL Mode**: `disable`
   - **PostgreSQL Version**: `13+`
   - **TimescaleDB**: `false`

The key is using `127.0.0.1` instead of `localhost` to force IPv4 connection.