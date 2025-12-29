# Configuration Reference

Complete reference for the configuration file format.

## File Location

Configuration file: `config/config.json`

Example file: `config/config.json.example`

## Configuration Structure

### Top-Level Sections

```json
{
  "devices": {...},
  "sensors": {...},
  "actuators": {...},
  "growing_system": {...},
  "schedule": {...},
  "logging": {...},
  "web": {...}
}
```

## Devices Configuration

### Structure

```json
{
  "devices": {
    "devices": [
      {
        "device_id": "pump1",
        "name": "Main Pump",
        "brand": "tapo",
        "type": "power_controller",
        "ip_address": "192.168.1.100",
        "email": "user@example.com",
        "password": "password123",
        "auto_discovery": true
      }
    ]
  }
}
```

### Fields

- **devices.devices[]** (array, required): List of device configurations
  - **device_id** (string, required): Unique identifier for the device
  - **name** (string, required): Human-readable device name
  - **brand** (string, required): Device brand (currently supports `"tapo"`)
  - **type** (string, required): Device type (e.g., `"power_controller"`)
  - **ip_address** (string, required): IP address of the device
  - **email** (string, required): Tapo account email
  - **password** (string, required): Tapo account password
  - **auto_discovery** (boolean, optional): Enable auto-discovery if IP fails (default: `true`)

## Sensors Configuration

### Structure

```json
{
  "sensors": {
    "sensors": []
  }
}
```

Currently, sensors are not implemented. This section is reserved for future use.

## Actuators Configuration

### Structure

```json
{
  "actuators": {
    "actuators": []
  }
}
```

Currently, actuators are not implemented. This section is reserved for future use.

## Growing System Configuration

### Structure

```json
{
  "growing_system": {
    "type": "flood_drain",
    "primary_device_id": "pump1"
  }
}
```

### Fields

- **type** (string, required): Type of hydroponic system
  - `"flood_drain"`: Flood and drain system
  - `"nft"`: Nutrient Film Technique (placeholder)
- **primary_device_id** (string, required): ID of the primary device to control (must match a `device_id` in `devices.devices[]`)

## Schedule Configuration

### Schedule Types

#### Interval-Based Schedule

```json
{
  "schedule": {
    "type": "interval",
    "flood_duration_minutes": 15,
    "drain_duration_minutes": 30,
    "interval_minutes": 120,
    "active_hours": {
      "start": "06:00",
      "end": "22:00"
    }
  }
}
```

**Fields:**
- **type** (string, required): `"interval"`
- **flood_duration_minutes** (number, required): Duration pump is ON (minutes)
- **drain_duration_minutes** (number, required): Duration pump is OFF (minutes)
- **interval_minutes** (number, required): Time between cycle starts (minutes)
- **active_hours** (object, optional): Restrict cycles to specific hours
  - **start** (string, required): Start time (HH:MM format)
  - **end** (string, required): End time (HH:MM format)

#### Time-Based Schedule

```json
{
  "schedule": {
    "type": "time_based",
    "flood_duration_minutes": 2.0,
    "cycles": [
      {"on_time": "06:00", "off_duration_minutes": 18},
      {"on_time": "12:00", "off_duration_minutes": 28},
      {"on_time": "18:00", "off_duration_minutes": 18}
    ]
  }
}
```

**Fields:**
- **type** (string, required): `"time_based"`
- **flood_duration_minutes** (number, required): Duration pump is ON (minutes)
- **cycles** (array, required): List of cycle definitions
  - **on_time** (string, required): Time to turn device ON (HH:MM format)
  - **off_duration_minutes** (number, required): Duration to keep device OFF after flood (minutes)

### Adaptation Configuration

Adaptation settings apply to time-based schedules:

```json
{
  "schedule": {
    "type": "time_based",
    "adaptation": {
      "enabled": true,
      "location": {
        "postcode": "2000",
        "timezone": "Australia/Sydney"
      },
      "temperature": {
        "enabled": false,
        "source": "bom",
        "station_id": "auto",
        "update_interval_minutes": 60
      },
      "daylight": {
        "enabled": false,
        "shift_schedule": true,
        "daylight_boost": 1.2,
        "night_reduction": 0.8,
        "update_frequency": "daily"
      },
      "adaptive": {
        "enabled": true,
        "tod_frequencies": {
          "morning": 18.0,
          "day": 28.0,
          "evening": 18.0,
          "night": 118.0
        },
        "temperature_bands": {
          "cold": {"max": 15, "factor": 1.15},
          "normal": {"min": 15, "max": 25, "factor": 1.0},
          "warm": {"min": 25, "max": 30, "factor": 0.85},
          "hot": {"min": 30, "factor": 0.70}
        },
        "humidity_bands": {
          "low": {"max": 40, "factor": 0.9},
          "normal": {"min": 40, "max": 70, "factor": 1.0},
          "high": {"min": 70, "factor": 1.1}
        },
        "constraints": {
          "min_wait_duration": 5,
          "max_wait_duration": 180,
          "min_flood_duration": 2,
          "max_flood_duration": 15
        }
      }
    }
  }
}
```

**Adaptation Fields:**
- **enabled** (boolean, required): Enable/disable adaptation
- **location** (object, optional): Location for environmental data
  - **postcode** (string, required): Australian postcode
  - **timezone** (string, required): Timezone (e.g., `"Australia/Sydney"`)
- **temperature** (object, optional): Temperature data source
  - **enabled** (boolean): Enable temperature adaptation
  - **source** (string): Data source (`"bom"` for Bureau of Meteorology)
  - **station_id** (string): BOM station ID or `"auto"` for automatic
  - **update_interval_minutes** (number): How often to update data
- **daylight** (object, optional): Daylight adaptation
  - **enabled** (boolean): Enable daylight adaptation
  - **shift_schedule** (boolean): Shift schedule with sunrise/sunset
  - **daylight_boost** (number): Multiplier for daylight hours
  - **night_reduction** (number): Multiplier for night hours
  - **update_frequency** (string): How often to update (`"daily"`, `"hourly"`)
- **adaptive** (object, optional): Adaptive scheduler settings
  - **enabled** (boolean): Enable adaptive scheduling
  - **tod_frequencies** (object): Time-of-day base frequencies (minutes)
  - **temperature_bands** (object): Temperature adjustment factors
  - **humidity_bands** (object): Humidity adjustment factors
  - **constraints** (object): Schedule constraints (minutes)

## Logging Configuration

### Structure

```json
{
  "logging": {
    "log_file": "logs/hydro_controller.log",
    "log_level": "INFO"
  }
}
```

### Fields

- **log_file** (string, optional): Path to log file (default: `"logs/hydro_controller.log"`)
- **log_level** (string, optional): Logging level (default: `"INFO"`)
  - Valid values: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`

## Web UI Configuration

### Structure

```json
{
  "web": {
    "enabled": false,
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

### Fields

- **enabled** (boolean, optional): Enable web UI (default: `false`)
- **host** (string, optional): Host to bind to (default: `"0.0.0.0"` for all interfaces)
- **port** (number, optional): Port to listen on (default: `8000`)

## Validation

The configuration is validated on startup using Pydantic models. Errors will be reported with:
- Field name
- Error type
- Expected value format

## Examples

See `config/config.json.example` for complete examples of:
- Interval-based schedule
- Time-based schedule
- Adaptive schedule with environmental data

## Best Practices

1. **Device IDs**: Use descriptive, unique IDs (e.g., `"pump1"`, `"main_pump"`)
2. **Time Formats**: Always use HH:MM format (24-hour)
3. **Durations**: Use decimal values for sub-minute precision (e.g., `2.5` minutes)
4. **Backup**: Keep backups of working configurations
5. **Validation**: Test configuration changes before deploying

## Troubleshooting

### Common Errors

**"Primary device not found"**
- Ensure `growing_system.primary_device_id` matches a `device_id` in `devices.devices[]`

**"Invalid schedule type"**
- Use `"interval"` for interval-based scheduling
- Use `"time_based"` for time-based or adaptive scheduling

**"Missing required field"**
- Check that all required fields are present
- See `config/config.json.example` for reference

**"Invalid time format"**
- Use HH:MM format (e.g., `"06:00"`, `"22:30"`)
- Use 24-hour format

**"Configuration validation failed"**
- Check JSON syntax
- Verify all required fields are present
- Check field types match expected types

