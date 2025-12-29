# Configuration Migration Guide

This guide helps you migrate from the old configuration format to the new structured format.

## Overview

The new configuration format introduces:
- Multiple device support
- Structured device, sensor, and actuator registries
- Unified scheduler interface
- Pydantic-based validation
- Extensible adaptation system

## Migration Steps

### Step 1: Backup Your Current Configuration

```bash
cp config/config.json config/config.json.backup
```

### Step 2: Understand the Changes

#### Old Format (v1)
```json
{
  "device": {
    "ip_address": "192.168.1.100",
    "email": "user@example.com",
    "password": "password123"
  },
  "cycle": {
    "flood_duration_minutes": 15,
    "drain_duration_minutes": 30,
    "interval_minutes": 120
  },
  "schedule": {
    "enabled": true,
    "active_hours": {
      "start": "06:00",
      "end": "22:00"
    }
  }
}
```

#### New Format (v2)
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
  },
  "growing_system": {
    "type": "flood_drain",
    "primary_device_id": "pump1"
  },
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

### Step 3: Migration Mapping

| Old Field | New Field | Notes |
|----------|-----------|-------|
| `device.ip_address` | `devices.devices[0].ip_address` | Now in array |
| `device.email` | `devices.devices[0].email` | Now in array |
| `device.password` | `devices.devices[0].password` | Now in array |
| `device.auto_discovery` | `devices.devices[0].auto_discovery` | Default: `true` |
| `cycle.flood_duration_minutes` | `schedule.flood_duration_minutes` | Moved to schedule |
| `cycle.drain_duration_minutes` | `schedule.drain_duration_minutes` | Moved to schedule |
| `cycle.interval_minutes` | `schedule.interval_minutes` | Moved to schedule |
| `schedule.enabled` | `schedule.type: "interval"` | Use type instead |
| `schedule.active_hours` | `schedule.active_hours` | Same structure |

### Step 4: Create New Configuration

1. **Create device entry:**
   - Use `device_id`: `"pump1"` (or your preferred ID)
   - Add `name`: `"Main Pump"` (or your preferred name)
   - Set `brand`: `"tapo"`
   - Set `type`: `"power_controller"`
   - Copy IP, email, password from old config
   - Set `auto_discovery`: `true` (recommended)

2. **Create growing system:**
   - Set `type`: `"flood_drain"`
   - Set `primary_device_id`: Use the same `device_id` from step 1

3. **Update schedule:**
   - Set `type`: `"interval"` (for interval-based) or `"time_based"` (for time-based)
   - Move cycle settings from `cycle.*` to `schedule.*`
   - Keep `active_hours` if using interval scheduler

4. **Add required sections:**
   - `sensors`: `{"sensors": []}` (empty for now)
   - `actuators`: `{"actuators": []}` (empty for now)
   - `logging`: Copy from old config or use defaults
   - `web`: Copy from old config or use defaults

### Step 5: Validate Configuration

The new system validates configuration on startup. If there are errors, check:
- JSON syntax is valid
- All required fields are present
- Device IDs match between `devices` and `growing_system.primary_device_id`
- Schedule type matches the structure

### Step 6: Test the Migration

1. Start the application:
   ```bash
   python -m src.main
   ```

2. Check logs for validation errors
3. Verify device connects successfully
4. Verify scheduler starts correctly

## Common Migration Scenarios

### Scenario 1: Simple Interval-Based Schedule

**Old:**
```json
{
  "device": {...},
  "cycle": {
    "flood_duration_minutes": 15,
    "drain_duration_minutes": 30,
    "interval_minutes": 120
  },
  "schedule": {
    "enabled": false
  }
}
```

**New:**
```json
{
  "devices": {
    "devices": [{
      "device_id": "pump1",
      "name": "Main Pump",
      "brand": "tapo",
      "type": "power_controller",
      "ip_address": "...",
      "email": "...",
      "password": "..."
    }]
  },
  "growing_system": {
    "type": "flood_drain",
    "primary_device_id": "pump1"
  },
  "schedule": {
    "type": "interval",
    "flood_duration_minutes": 15,
    "drain_duration_minutes": 30,
    "interval_minutes": 120
  }
}
```

### Scenario 2: Time-Based Schedule

**Old:**
```json
{
  "schedule": {
    "type": "time_based",
    "cycles": [...]
  }
}
```

**New:**
```json
{
  "schedule": {
    "type": "time_based",
    "flood_duration_minutes": 2.0,
    "cycles": [...]
  }
}
```

### Scenario 3: Adaptive Schedule

If you were using adaptive scheduling, the configuration structure has changed:

**Old:**
```json
{
  "schedule": {
    "type": "adaptive",
    "adaptation": {...}
  }
}
```

**New:**
```json
{
  "schedule": {
    "type": "time_based",
    "flood_duration_minutes": 2.0,
    "adaptation": {
      "enabled": true,
      "adaptive": {
        "enabled": true,
        "tod_frequencies": {...},
        "temperature_bands": {...},
        "humidity_bands": {...}
      }
    }
  }
}
```

## Troubleshooting

### Error: "Primary device not found"
- Ensure `growing_system.primary_device_id` matches a `device_id` in `devices.devices[]`

### Error: "Invalid schedule type"
- Use `"interval"` for interval-based scheduling
- Use `"time_based"` for time-based or adaptive scheduling

### Error: "Missing required field"
- Check that all required fields are present (see `config/config.json.example`)
- Ensure JSON syntax is valid

### Error: "Device connection failed"
- Verify device credentials are correct
- Check IP address is accessible
- Enable `auto_discovery` if IP may change

## Rollback

If you need to rollback to the old format:

1. Restore backup:
   ```bash
   cp config/config.json.backup config/config.json
   ```

2. Note: The old format is no longer supported. You'll need to use an older version of the application.

## Need Help?

- Check `config/config.json.example` for a complete example
- Review logs for specific error messages
- See [CONFIGURATION.md](CONFIGURATION.md) for detailed configuration options

