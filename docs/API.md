# Web API Documentation

The Hydroponic Controller provides a REST API for monitoring and controlling the system. The API is available when the web UI is enabled.

## Base URL

- Local: `http://localhost:8000`
- Network: `http://<mac-ip-address>:8000`

## Endpoints

### Status & Monitoring

#### GET `/api/status`

Get current system status including scheduler state, device state, and next event time.

**Response:**
```json
{
  "scheduler_running": true,
  "scheduler_state": "running",
  "device_connected": true,
  "device_state": "on",
  "device_ip": "192.168.1.100",
  "next_event_time": "2024-01-15T14:30:00",
  "time_until_next_cycle": "2 hours 15 minutes",
  "current_cycle": {
    "phase": "flood",
    "start_time": "2024-01-15T12:00:00",
    "duration_minutes": 15
  }
}
```

#### GET `/api/device/info`

Get detailed device information.

**Response:**
```json
{
  "device_id": "pump1",
  "name": "Main Pump",
  "brand": "tapo",
  "ip_address": "192.168.1.100",
  "connected": true,
  "state": "on",
  "last_update": "2024-01-15T12:00:00"
}
```

#### GET `/api/environment`

Get current environmental data (temperature, humidity, daylight).

**Response:**
```json
{
  "temperature": {
    "value": 22.5,
    "unit": "celsius",
    "source": "bom",
    "timestamp": "2024-01-15T12:00:00"
  },
  "humidity": {
    "value": 65.0,
    "unit": "percent",
    "source": "bom",
    "timestamp": "2024-01-15T12:00:00"
  },
  "daylight": {
    "sunrise": "06:00",
    "sunset": "18:00",
    "day_length_hours": 12.0
  }
}
```

### Device Control

#### POST `/api/device/on`

Turn the device ON.

**Response:**
```json
{
  "success": true,
  "message": "Device turned ON",
  "state": "on"
}
```

#### POST `/api/device/off`

Turn the device OFF.

**Response:**
```json
{
  "success": true,
  "message": "Device turned OFF",
  "state": "off"
}
```

#### POST `/api/device/toggle`

Toggle device state (ON ↔ OFF).

**Response:**
```json
{
  "success": true,
  "message": "Device toggled",
  "state": "on"
}
```

#### POST `/api/device/emergency-stop`

Emergency stop - immediately turn device OFF and stop scheduler.

**Response:**
```json
{
  "success": true,
  "message": "Emergency stop activated",
  "device_state": "off",
  "scheduler_running": false
}
```

### Scheduler Control

#### POST `/api/scheduler/start`

Start the scheduler.

**Response:**
```json
{
  "success": true,
  "message": "Scheduler started",
  "state": "running"
}
```

#### POST `/api/scheduler/stop`

Stop the scheduler.

**Response:**
```json
{
  "success": true,
  "message": "Scheduler stopped",
  "state": "stopped"
}
```

#### GET `/api/scheduler/status`

Get detailed scheduler status.

**Response:**
```json
{
  "running": true,
  "state": "running",
  "type": "time_based",
  "next_event_time": "2024-01-15T14:30:00",
  "current_cycle": {
    "phase": "flood",
    "start_time": "2024-01-15T12:00:00",
    "duration_minutes": 15
  },
  "cycles_today": 5,
  "total_cycles": 120
}
```

### Configuration

#### GET `/api/config`

Get current configuration.

**Response:**
```json
{
  "schedule": {
    "type": "time_based",
    "flood_duration_minutes": 2.0,
    "cycles": [...]
  },
  "devices": {...},
  "growing_system": {...}
}
```

#### PUT `/api/config/schedule`

Update schedule configuration.

**Request Body:**
```json
{
  "type": "interval",
  "flood_duration_minutes": 15,
  "drain_duration_minutes": 30,
  "interval_minutes": 120
}
```

**Response:**
```json
{
  "success": true,
  "message": "Configuration updated",
  "requires_restart": true
}
```

#### PUT `/api/config/schedule/adaptive`

Update adaptive scheduler configuration.

**Request Body:**
```json
{
  "enabled": true,
  "tod_frequencies": {
    "morning": 18.0,
    "day": 28.0,
    "evening": 18.0,
    "night": 118.0
  },
  "temperature_bands": {...},
  "humidity_bands": {...}
}
```

**Response:**
```json
{
  "success": true,
  "message": "Adaptive configuration updated",
  "requires_restart": true
}
```

### Logs

#### GET `/api/logs`

Get recent log entries.

**Query Parameters:**
- `lines` (optional): Number of lines to return (default: 100, max: 1000)

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2024-01-15T12:00:00",
      "level": "INFO",
      "message": "Scheduler started"
    },
    ...
  ],
  "total_lines": 100
}
```

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**HTTP Status Codes:**
- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## WebSocket (Future)

Real-time updates via WebSocket are planned for future releases.

