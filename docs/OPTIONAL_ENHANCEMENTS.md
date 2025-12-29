# Optional Enhancements

This document outlines optional enhancements that can be implemented to extend the functionality of the Hydroponic Controller. These are **not required** for core operation but add value and capabilities.

## Priority Levels

- **High Value**: Significant functionality improvement, moderate effort
- **Medium Value**: Useful feature, moderate to high effort
- **Low Value**: Nice to have, may require significant effort
- **Future Research**: Requires investigation or new technologies

## Enhancement Categories

### 1. Adaptation Strategies

#### 1.1 DaylightAdaptor Implementation
**Priority**: High Value  
**Effort**: Medium (2-4 hours)  
**Status**: Interface exists, implementation stubbed

**Description**:  
Implement daylight-based schedule adaptation that shifts cycles based on sunrise/sunset times.

**Current State**:
- Interface defined in `src/adaptation/adaptor_interface.py`
- Stub implementation exists but returns cycles unchanged
- Configuration structure already supports it

**Implementation Steps**:
1. Implement `adapt()` method to shift cycle times based on daylight
2. Implement `should_update()` to check if sunrise/sunset times changed
3. Integrate with `AdaptiveScheduler` to use daylight adaptor
4. Add tests for daylight adaptation logic

**Configuration**:
```json
{
  "adaptation": {
    "daylight": {
      "enabled": true,
      "shift_schedule": true,
      "daylight_boost": 1.2,
      "night_reduction": 0.8
    }
  }
}
```

**Benefits**:
- Automatically adjusts to seasonal daylight changes
- Optimises cycles for natural light patterns
- Reduces manual configuration updates

---

#### 1.2 TemperatureAdaptor Implementation
**Priority**: High Value  
**Effort**: Medium (2-4 hours)  
**Status**: Interface exists, implementation stubbed

**Description**:  
Implement temperature-based schedule adaptation that adjusts cycle frequency based on temperature bands.

**Current State**:
- Interface defined in `src/adaptation/adaptor_interface.py`
- Stub implementation exists but returns cycles unchanged
- Temperature data available from `EnvironmentalService`
- Temperature bands already configured in adaptive scheduler

**Implementation Steps**:
1. Implement `adapt()` method to adjust cycle frequencies based on temperature
2. Implement `should_update()` to check if temperature changed significantly
3. Integrate with `AdaptiveScheduler` to use temperature adaptor
4. Add tests for temperature adaptation logic

**Configuration**:
```json
{
  "adaptation": {
    "temperature": {
      "enabled": true,
      "source": "bom",
      "update_interval_minutes": 60
    },
    "adaptive": {
      "temperature_bands": {
        "cold": {"max": 15, "factor": 1.15},
        "normal": {"min": 15, "max": 25, "factor": 1.0},
        "warm": {"min": 25, "max": 30, "factor": 0.85},
        "hot": {"min": 30, "factor": 0.70}
      }
    }
  }
}
```

**Benefits**:
- Automatically adjusts to temperature changes
- Optimises cycles for plant needs in different temperatures
- Reduces manual intervention

---

#### 1.3 SensorAdaptor Implementation
**Priority**: Medium Value  
**Effort**: High (8-16 hours)  
**Status**: Interface exists, requires sensor infrastructure

**Description**:  
Implement sensor-based adaptation using reservoir level, EC, pH, and other sensor data.

**Prerequisites**:
- Sensor infrastructure implemented
- Sensor registry populated with actual sensors
- Sensor data available via `SensorRegistry`

**Implementation Steps**:
1. Implement sensor reading logic
2. Implement `adapt()` method based on sensor thresholds
3. Implement `should_update()` based on sensor value changes
4. Add configuration for sensor thresholds
5. Add tests for sensor adaptation

**Configuration**:
```json
{
  "adaptation": {
    "sensors": {
      "enabled": true,
      "reservoir_level": {
        "low_threshold": 20,
        "action": "reduce_frequency"
      },
      "ec": {
        "high_threshold": 2.5,
        "action": "reduce_frequency"
      },
      "ph": {
        "min": 5.5,
        "max": 6.5,
        "action": "adjust_schedule"
      }
    }
  }
}
```

**Benefits**:
- Real-time adaptation based on actual system conditions
- Prevents issues (low reservoir, nutrient imbalance)
- More accurate than environmental data alone

---

### 2. Sensor Integration

#### 2.1 Sensor Registry Implementation
**Priority**: Medium Value  
**Effort**: High (8-16 hours)  
**Status**: Interface exists, no implementations

**Description**:  
Implement actual sensor devices that can be registered and read.

**Sensor Types to Implement**:
- **Water Level Sensors**: Ultrasonic, float switches
- **pH Sensors**: Digital pH meters
- **EC Sensors**: Electrical conductivity meters
- **Temperature Sensors**: DS18B20, DHT22 (for local readings)
- **Humidity Sensors**: DHT22 (for local readings)

**Implementation Steps**:
1. Create sensor implementations for each type
2. Implement `ISensor` interface for each
3. Add sensor discovery/registration
4. Integrate with `EnvironmentalService`
5. Add sensor data to API endpoints
6. Add sensor configuration to config schema

**Configuration**:
```json
{
  "sensors": {
    "sensors": [
      {
        "sensor_id": "reservoir_level_1",
        "type": "water_level",
        "interface": "gpio",
        "pin": 18
      },
      {
        "sensor_id": "ph_1",
        "type": "ph",
        "interface": "i2c",
        "address": "0x48"
      }
    ]
  }
}
```

**Benefits**:
- Real-time system monitoring
- Enables sensor-based adaptation
- Better system visibility

---

### 3. Actuator Integration

#### 3.1 Actuator Registry Implementation
**Priority**: Medium Value  
**Effort**: High (8-16 hours)  
**Status**: Interface exists, no implementations

**Description**:  
Implement actual actuator devices that can be controlled (pumps, valves, nutrient dosers, etc.).

**Actuator Types to Implement**:
- **Additional Pumps**: Secondary pumps, nutrient pumps
- **Valves**: Solenoid valves for flow control
- **Dosers**: Peristaltic pumps for nutrient dosing
- **Lights**: Grow lights control
- **Fans**: Ventilation control

**Implementation Steps**:
1. Create actuator implementations for each type
2. Implement `IActuator` interface for each
3. Add actuator discovery/registration
4. Add actuator control to API
5. Add actuator scheduling/automation
6. Add actuator configuration to config schema

**Configuration**:
```json
{
  "actuators": {
    "actuators": [
      {
        "actuator_id": "nutrient_pump_1",
        "type": "peristaltic_pump",
        "interface": "gpio",
        "pin": 12
      },
      {
        "actuator_id": "valve_1",
        "type": "solenoid_valve",
        "interface": "gpio",
        "pin": 13
      }
    ]
  }
}
```

**Benefits**:
- Expanded automation capabilities
- Nutrient dosing automation
- Multi-device control

---

### 4. Web UI Enhancements

#### 4.1 WebSocket Support for Real-Time Updates
**Priority**: High Value  
**Effort**: Medium (4-8 hours)  
**Status**: Not implemented

**Description**:  
Add WebSocket support for real-time status updates without polling.

**Implementation Steps**:
1. Add WebSocket support to FastAPI
2. Create WebSocket endpoint for status updates
3. Implement server-side event broadcasting
4. Update frontend to use WebSocket instead of polling
5. Add reconnection logic
6. Add tests for WebSocket functionality

**Benefits**:
- Real-time updates without polling overhead
- Better user experience
- Reduced server load

---

#### 4.2 Historical Data Visualization
**Priority**: Medium Value  
**Effort**: High (8-16 hours)  
**Status**: Not implemented

**Description**:  
Add charts and graphs showing historical cycle data, environmental trends, and system performance.

**Implementation Steps**:
1. Add database for historical data storage
2. Create data collection service
3. Add API endpoints for historical data
4. Implement charting library (Chart.js, D3.js, etc.)
5. Create visualization components
6. Add date range selection
7. Add export functionality

**Benefits**:
- Better system visibility
- Trend analysis
- Performance optimization insights

---

#### 4.3 Mobile App
**Priority**: Low Value  
**Effort**: Very High (40+ hours)  
**Status**: Not implemented

**Description**:  
Create a mobile app (iOS/Android) for remote monitoring and control.

**Implementation Steps**:
1. Design mobile app architecture
2. Create API authentication
3. Implement mobile app (React Native, Flutter, etc.)
4. Add push notifications
5. Add offline support
6. Publish to app stores

**Benefits**:
- Remote access
- Push notifications
- Better mobile experience

---

### 5. Data Storage and Analysis

#### 5.1 Database Integration
**Priority**: Medium Value  
**Effort**: Medium (4-8 hours)  
**Status**: Not implemented

**Description**:  
Add database support for storing historical data, configuration backups, and system logs.

**Database Options**:
- **SQLite**: Simple, file-based, no server required
- **PostgreSQL**: Full-featured, requires server
- **InfluxDB**: Time-series database, optimised for metrics

**Implementation Steps**:
1. Choose database (SQLite recommended for simplicity)
2. Design database schema
3. Create database models
4. Implement data persistence layer
5. Add migration system
6. Add backup/restore functionality

**Benefits**:
- Historical data storage
- Better analytics
- Configuration versioning

---

#### 5.2 Historical Pattern Learning
**Priority**: Low Value  
**Effort**: Very High (40+ hours)  
**Status**: Research phase

**Description**:  
Implement machine learning or pattern recognition to learn from historical schedule effectiveness.

**Implementation Steps**:
1. Design learning algorithm
2. Collect training data
3. Implement pattern recognition
4. Add feedback mechanism
5. Create recommendation system
6. Add user interface for suggestions

**Benefits**:
- Automated optimization
- Learning from experience
- Better schedule effectiveness

---

### 6. Scheduler Enhancements

#### 6.1 NFT Scheduler Implementation
**Priority**: Medium Value  
**Effort**: Medium (4-8 hours)  
**Status**: Placeholder exists

**Description**:  
Complete the NFT (Nutrient Film Technique) scheduler implementation.

**NFT Requirements**:
- Continuous or near-continuous flow
- Different timing than flood/drain
- Flow rate considerations

**Implementation Steps**:
1. Research NFT system requirements
2. Design NFT scheduler logic
3. Implement `IScheduler` interface
4. Add NFT configuration schema
5. Add tests
6. Update documentation

**Benefits**:
- Support for NFT systems
- Expanded system compatibility

---

#### 6.2 Multi-Device Scheduling
**Priority**: Medium Value  
**Effort**: High (8-16 hours)  
**Status**: Architecture supports it, not implemented

**Description**:  
Support scheduling multiple devices with coordination (e.g., main pump + nutrient pump).

**Implementation Steps**:
1. Design multi-device scheduler
2. Implement device coordination logic
3. Add configuration for device groups
4. Add API endpoints
5. Add tests
6. Update UI for multi-device control

**Benefits**:
- Complex system support
- Coordinated device operation
- Advanced automation

---

### 7. Advanced Features

#### 7.1 Energy Efficiency Optimization
**Priority**: Low Value  
**Effort**: Medium (4-8 hours)  
**Status**: Not implemented

**Description**:  
Optimize schedule for electricity costs based on time-of-use rates.

**Implementation Steps**:
1. Add electricity rate configuration
2. Implement cost calculation
3. Add optimization algorithm
4. Add cost display to UI
5. Add scheduling constraints for peak times

**Configuration**:
```json
{
  "energy": {
    "time_of_use_rates": {
      "peak": {"start": "14:00", "end": "20:00", "rate": 0.30},
      "off_peak": {"start": "22:00", "end": "06:00", "rate": 0.15},
      "shoulder": {"rate": 0.20}
    },
    "optimize_for_cost": true
  }
}
```

**Benefits**:
- Cost savings
- Peak demand management
- Energy efficiency

---

#### 7.2 Weather Forecast Integration
**Priority**: Low Value  
**Effort**: Medium (4-8 hours)  
**Status**: Not implemented

**Description**:  
Use weather forecasts to proactively adjust schedules for upcoming weather changes.

**Implementation Steps**:
1. Integrate weather forecast API (BOM, OpenWeatherMap, etc.)
2. Add forecast data to `EnvironmentalService`
3. Implement proactive scheduling
4. Add forecast display to UI
5. Add tests

**Benefits**:
- Proactive adaptation
- Better preparation for weather changes
- Improved system resilience

---

#### 7.3 Remote Access (VPN/SSH Tunnel)
**Priority**: Low Value  
**Effort**: Low (2-4 hours)  
**Status**: Documentation only

**Description**:  
Add documentation and configuration for remote access via VPN or SSH tunnel.

**Implementation Steps**:
1. Add authentication to web API
2. Create remote access documentation
3. Add SSH tunnel setup guide
4. Add VPN configuration examples
5. Add security best practices

**Benefits**:
- Remote monitoring
- Remote control
- Better accessibility

---

## Implementation Priority Recommendations

### Phase 1: High-Value, Low Effort
1. ✅ DaylightAdaptor implementation
2. ✅ TemperatureAdaptor implementation
3. ✅ WebSocket support

### Phase 2: High-Value, Medium Effort
4. Database integration (SQLite)
5. Historical data visualization
6. NFT Scheduler implementation

### Phase 3: Medium-Value Enhancements
7. Sensor integration (if sensors available)
8. Actuator integration (if actuators available)
9. Multi-device scheduling

### Phase 4: Advanced Features
10. Energy efficiency optimization
11. Weather forecast integration
12. Historical pattern learning (research)

## Getting Started

To implement an enhancement:

1. **Review the enhancement** in this document
2. **Check prerequisites** (dependencies, infrastructure)
3. **Design the implementation** (architecture, interfaces)
4. **Implement incrementally** (small, testable changes)
5. **Add tests** (unit, integration)
6. **Update documentation** (API, configuration, user guide)
7. **Update this document** (mark as implemented)

## Contributing

When implementing enhancements:
- Follow existing code patterns
- Maintain backward compatibility
- Add comprehensive tests
- Update all relevant documentation
- Consider configuration migration if needed

## Notes

- All enhancements should maintain the open-loop nature of the system unless explicitly adding closed-loop features
- Sensor and actuator enhancements require hardware integration
- Some enhancements may require additional dependencies
- Consider security implications for remote access features

