# Architecture Documentation

This document describes the architecture of the Hydroponic Controller application.

## Overview

The application uses a modular, extensible architecture with clear separation of concerns. The design follows SOLID principles and uses design patterns to promote maintainability and testability.

## Architecture Layers

### 1. Core Layer (`src/core/`)

The core layer provides foundational interfaces and utilities.

#### Scheduler Interface (`scheduler_interface.py`)

Defines the `IScheduler` interface that all schedulers must implement:

```python
class IScheduler(ABC):
    def start(self) -> None
    def stop(self) -> None
    def is_running(self) -> bool
    def get_status(self) -> Dict[str, Any]
    def get_state(self) -> str
```

**Benefits:**
- Unified interface for all scheduler types
- Easy to add new scheduler implementations
- Testable through interface mocking

#### Scheduler Factory (`scheduler_factory.py`)

Encapsulates scheduler creation logic:

```python
class SchedulerFactory:
    def create(self, config: Dict[str, Any]) -> IScheduler
```

**Benefits:**
- Centralised scheduler creation
- Configuration-driven scheduler selection
- Easy to extend with new scheduler types

#### Configuration Schema (`config_schema.py`)

Pydantic models for configuration validation:

```python
class DeviceConfig(BaseModel)
class ScheduleConfig(BaseModel)
class AdaptationConfig(BaseModel)
```

**Benefits:**
- Type-safe configuration
- Automatic validation
- Clear error messages
- IDE autocomplete support

#### Configuration Validator (`config_validator.py`)

Loads and validates configuration files:

```python
def load_and_validate_config(config_path: str) -> Dict[str, Any]
```

**Benefits:**
- Early error detection
- Consistent validation
- Clear error messages

### 2. Services Layer (`src/services/`)

The services layer provides abstractions for devices, sensors, and actuators.

#### Device Service (`device_service.py`)

**DeviceRegistry:**
- Manages multiple device services
- Provides device lookup by ID
- Handles device lifecycle

**IDeviceService Interface:**
```python
class IDeviceService(ABC):
    def connect(self) -> bool
    def disconnect(self) -> None
    def turn_on(self) -> bool
    def turn_off(self) -> bool
    def is_device_on(self) -> bool
    def is_connected(self) -> bool
```

**Benefits:**
- Support for multiple device brands
- Easy to add new device types
- Testable through interface mocking

**TapoDeviceService:**
- Implements `IDeviceService` for Tapo P100 devices
- Handles connection, authentication, and control
- Supports auto-discovery

#### Sensor Service (`sensor_service.py`)

**SensorRegistry:**
- Manages sensor devices
- Provides sensor data access

**ISensor Interface:**
```python
class ISensor(ABC):
    def read(self) -> Dict[str, Any]
    def is_available(self) -> bool
```

**Benefits:**
- Extensible sensor support
- Unified sensor interface
- Easy to add new sensor types

#### Actuator Service (`actuator_service.py`)

**ActuatorRegistry:**
- Manages actuator devices
- Provides actuator control

**IActuator Interface:**
```python
class IActuator(ABC):
    def activate(self) -> bool
    def deactivate(self) -> bool
    def get_state(self) -> str
```

**Benefits:**
- Extensible actuator support
- Unified actuator interface
- Easy to add new actuator types

#### Environmental Service (`environmental_service.py`)

Centralised service for environmental data:

```python
class EnvironmentalService:
    def get_temperature(self) -> Optional[float]
    def get_humidity(self) -> Optional[float]
    def get_daylight_info(self) -> Dict[str, Any]
```

**Benefits:**
- Single source of truth for environmental data
- Supports multiple data sources (BOM, sensors, etc.)
- Caching and update management

#### Service Factory (`service_factory.py`)

Factory functions for creating registries:

```python
def create_device_registry(config: Dict, logger) -> DeviceRegistry
def create_sensor_registry(config: Dict, logger) -> SensorRegistry
def create_actuator_registry(config: Dict, logger) -> ActuatorRegistry
def create_environmental_service(config: Dict, logger) -> EnvironmentalService
```

**Benefits:**
- Centralised service creation
- Consistent initialization
- Easy to test

### 3. Schedulers Layer (`src/schedulers/`)

Scheduler implementations that control device operation.

#### Interval Scheduler (`interval_scheduler.py`)

Fixed interval-based scheduling:
- Flood duration
- Drain duration
- Interval between cycles
- Optional active hours

**Use Cases:**
- Simple flood and drain cycles
- Consistent timing requirements
- Basic automation

#### Time-Based Scheduler (`time_based_scheduler.py`)

Time-of-day based scheduling:
- Specific on/off times
- Variable off durations
- Multiple cycles per day

**Use Cases:**
- Precise timing requirements
- Variable cycle frequencies
- Complex daily schedules

#### Adaptive Scheduler (`adaptive_scheduler.py`)

Environmentally-adaptive scheduling:
- Generates schedules from scratch
- Considers time of day, temperature, humidity
- Adjusts based on environmental factors

**Use Cases:**
- Dynamic scheduling based on conditions
- Optimised for plant growth
- Seasonal adjustments

**Implementation:**
- Uses `TimeBasedScheduler` internally
- Generates cycles based on environmental data
- Updates schedule periodically

#### NFT Scheduler (`nft_scheduler.py`)

Placeholder for Nutrient Film Technique systems.

### 4. Device Layer (`src/device/`)

Device-specific implementations.

#### Tapo Controller (`tapo_controller.py`)

Tapo P100 device implementation:
- Connection management
- Authentication (supports KLAP V2)
- Device control (on/off)
- State verification
- Auto-discovery

**Features:**
- Automatic protocol detection
- Retry logic
- Connection pooling
- Error handling

### 5. Data Layer (`src/data/`)

Data source implementations.

#### BOM Temperature (`bom_temperature.py`)

Australian Bureau of Meteorology temperature data:
- Station lookup
- Temperature and humidity retrieval
- Caching

#### Daylight Calculator (`daylight.py`)

Sunrise/sunset calculations:
- Postcode-based location
- Timezone support
- Day length calculations

### 6. Adaptation Layer (`src/adaptation/`)

Adaptation strategy interfaces.

#### Adaptor Interface (`adaptor_interface.py`)

Defines adaptation strategies:
```python
class IAdaptor(ABC):
    def adapt(self, schedule: List[Dict], context: Dict) -> List[Dict]
```

**Benefits:**
- Pluggable adaptation strategies
- Easy to add new adaptation logic
- Testable strategies

### 7. Web Layer (`src/web/`)

Web UI and API.

#### Web API (`api.py`)

FastAPI-based REST API:
- Status endpoints
- Device control endpoints
- Configuration management
- Log access

**Features:**
- Real-time status
- Device control
- Configuration updates
- Log streaming

#### Models (`models.py`)

Pydantic models for API requests/responses:
- Request validation
- Response serialization
- Type safety

#### Static Files (`static/`)

Frontend assets:
- HTML, CSS, JavaScript
- Real-time UI updates
- Responsive design

### 8. Main Application (`src/main.py`)

Application entry point and orchestration.

**HydroController:**
- Initializes all services
- Manages application lifecycle
- Handles signals for graceful shutdown
- Coordinates scheduler and web server

**Initialization Flow:**
1. Load and validate configuration
2. Create service registries
3. Create environmental service
4. Create scheduler via factory
5. Setup signal handlers
6. Start scheduler
7. Start web server (if enabled)

## Design Patterns

### Factory Pattern

Used for:
- Scheduler creation (`SchedulerFactory`)
- Service creation (`ServiceFactory`)

**Benefits:**
- Encapsulates creation logic
- Easy to extend
- Testable

### Registry Pattern

Used for:
- Device management (`DeviceRegistry`)
- Sensor management (`SensorRegistry`)
- Actuator management (`ActuatorRegistry`)

**Benefits:**
- Centralised management
- Easy lookup
- Lifecycle management

### Strategy Pattern

Used for:
- Scheduler selection (different scheduler types)
- Adaptation strategies (`IAdaptor`)

**Benefits:**
- Pluggable algorithms
- Easy to add new strategies
- Testable strategies

### Interface Segregation

All major components use interfaces:
- `IScheduler`
- `IDeviceService`
- `ISensor`
- `IActuator`
- `IAdaptor`

**Benefits:**
- Loose coupling
- Easy to mock for testing
- Clear contracts

## Data Flow

### Scheduler Operation

1. **Startup:**
   - Configuration loaded
   - Services initialized
   - Scheduler created
   - Scheduler started

2. **Runtime:**
   - Scheduler checks for next event
   - When event time reached:
     - Device turned on/off
     - State verified
     - Next event scheduled
   - Environmental data updated (if adaptive)

3. **Shutdown:**
   - Signal received
   - Scheduler stopped
   - Device turned off
   - Connections closed

### Adaptive Scheduling

1. **Initial Schedule Generation:**
   - Environmental data fetched
   - Time of day determined
   - Temperature/humidity bands evaluated
   - Schedule generated

2. **Periodic Updates:**
   - Environmental data refreshed
   - Schedule regenerated if needed
   - Cycles updated

## Extension Points

### Adding a New Device Brand

1. Implement `IDeviceService` interface
2. Add device creation logic to `ServiceFactory`
3. Update configuration schema if needed

### Adding a New Scheduler Type

1. Implement `IScheduler` interface
2. Add scheduler creation logic to `SchedulerFactory`
3. Update configuration schema

### Adding a New Sensor Type

1. Implement `ISensor` interface
2. Add sensor creation logic to `ServiceFactory`
3. Integrate with `EnvironmentalService` if needed

### Adding a New Adaptation Strategy

1. Implement `IAdaptor` interface
2. Integrate with `AdaptiveScheduler`
3. Update configuration schema

## Testing Strategy

### Unit Tests

- Test each component in isolation
- Mock dependencies using interfaces
- Test error cases

### Integration Tests

- Test component interactions
- Test with real configuration
- Test end-to-end workflows

### Test Structure

```
tests/
├── test_main.py              # Main application tests
├── test_integration.py       # Integration tests
├── test_time_scheduler.py    # Scheduler tests
├── test_tapo_controller.py   # Device tests
└── ...
```

## Configuration Management

### Configuration Structure

- Hierarchical JSON structure
- Pydantic validation
- Type-safe access
- Clear error messages

### Configuration Flow

1. Load from file
2. Validate with Pydantic
3. Create services from config
4. Create scheduler from config

## Error Handling

### Strategy

- Fail fast on configuration errors
- Retry on transient errors (network, device)
- Log all errors
- Graceful degradation where possible

### Error Types

- **Configuration Errors**: Validation failures, missing fields
- **Connection Errors**: Device unreachable, authentication failures
- **Runtime Errors**: Device control failures, scheduler errors

## Logging

### Log Levels

- `DEBUG`: Detailed information for debugging
- `INFO`: General information about operation
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical errors

### Log Structure

- Timestamp
- Log level
- Component name
- Message
- Exception details (if applicable)

## Performance Considerations

### Caching

- Environmental data cached
- Device state cached
- Configuration cached

### Threading

- Schedulers run in separate threads
- Web server runs in separate thread
- Non-blocking operations where possible

### Resource Management

- Connection pooling
- Proper cleanup on shutdown
- Memory-efficient data structures

## Security Considerations

### Credentials

- Stored in configuration file (local only)
- Not exposed in API responses
- Consider environment variables for production

### Network

- Web UI accessible on local network only
- No authentication (local network assumed safe)
- Consider adding authentication for production

## Future Enhancements

### Planned

- WebSocket support for real-time updates
- Database for historical data
- Multiple device support (already architected)
- Sensor integration (already architected)
- Actuator integration (already architected)

### Potential

- Remote access via VPN/SSH tunnel
- Mobile app
- Cloud integration
- Machine learning for optimisation

