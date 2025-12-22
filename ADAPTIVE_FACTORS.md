# Adaptive Schedule Factors

This document lists all factors that should influence an actively adaptive flood & drain schedule for optimal plant growth and energy efficiency.

## Core Factors (Currently Implemented)

### 1. **Time of Day (ToD)**
- **Description**: Different periods have different plant metabolic needs
- **Periods**:
  - **Morning** (sunrise to 09:00): High metabolic activity, increased water/nutrient uptake
  - **Day** (09:00 to sunset): Peak photosynthesis, consistent water needs
  - **Evening** (sunset to 20:00): Winding down, reduced water needs
  - **Night** (20:00 to sunrise): Minimal activity, minimal water needs
- **Impact**: Determines base frequency requirements for each period
- **Current Implementation**: Period-based factors (morning, day, evening, night)

### 2. **Temperature**
- **Description**: Air temperature affects plant metabolism, transpiration, and water uptake
- **Bands**:
  - **< 15°C (Cold)**: Reduced metabolism, less frequent flooding needed
  - **15-25°C (Normal)**: Optimal range, standard schedule
  - **25-30°C (Warm)**: Increased transpiration, more frequent flooding needed
  - **> 30°C (Hot)**: Heat stress, significantly increased flooding frequency
- **Impact**: Compresses (hot) or dilates (cold) wait durations
- **Current Implementation**: Temperature adjustment factor applied to all cycles
- **Enhancement Needed**: Time-of-day specific temperature (temp at cycle time, not just current temp)

### 3. **Sunrise/Sunset Times**
- **Description**: Natural daylight boundaries for plant activity
- **Impact**: Shifts schedule to align with natural day/night cycle
- **Current Implementation**: Schedule shift to align earliest cycle with sunrise

## Extended Factors (Should Be Implemented)

### 4. **Temperature at Time of Day (ToD-specific Temperature)**
- **Description**: Temperature varies throughout the day - need temp at each cycle time, not just current temp
- **Impact**: 
  - Hot afternoon (e.g., 35°C at 14:00) → compress wait durations during that period
  - Cool morning (e.g., 18°C at 07:00) → normal wait durations
- **Implementation**: Fetch temperature forecast or use historical patterns to predict temp at each cycle time

### 5. **Temperature Trends**
- **Description**: Is temperature rising, falling, or stable?
- **Impact**:
  - Rising temp → anticipate need for more frequent flooding
  - Falling temp → can reduce frequency
- **Implementation**: Track temperature changes over time windows (e.g., last hour, last 3 hours)

### 6. **Temperature Forecast**
- **Description**: Predicted temperature for next 6-24 hours
- **Impact**: Proactively adjust schedule based on predicted conditions
- **Implementation**: Use BOM forecast data or historical patterns

### 7. **Plant Growth Stage** ⚠️ SHELVED
- **Status**: Shelved - No data-driven detection method available
- **Description**: Different growth stages have different water/nutrient needs
- **Stages**:
  - **Seedling**: Frequent, small amounts (more events, shorter waits)
  - **Vegetative**: Regular schedule (base schedule)
  - **Flowering/Fruiting**: Increased water needs (more frequent during day)
  - **Mature**: Established schedule (base schedule)
- **Impact**: Would adjust base frequency requirements
- **Why Shelved**: Requires manual mode switching or sensors - user wants robust all-rounder model
- **See**: TODO.md for details

### 8. **Day Length / Season**
- **Description**: Longer days = more active hours = more water needs
- **Impact**: 
  - Summer (long days) → more events during extended daylight
  - Winter (short days) → fewer events, longer waits
- **Implementation**: Calculate from sunrise/sunset times

### 9. **Humidity** ✅ PRIORITY - AVAILABLE FROM BOM
- **Description**: High humidity reduces transpiration, low humidity increases it
- **Impact**:
  - Low humidity (< 40%) → more frequent flooding needed (increased transpiration)
  - Normal humidity (40-70%) → standard schedule
  - High humidity (> 70%) → less frequent flooding needed (reduced transpiration)
- **Implementation**: Fetch from BOM observation data (`rel_hum` field - relative humidity %)
- **Status**: ✅ BOM provides this data - should be implemented
- **BOM Field**: `rel_hum` (percentage, e.g., 32 = 32%)

### 10. **Light Intensity** ⚠️ SHELVED
- **Status**: Shelved - Requires sensors (system is open-loop)
- **Description**: Actual light levels affect photosynthesis rate
- **Impact**: 
  - Bright day → more frequent flooding
  - Cloudy day → less frequent flooding
- **Implementation**: Requires light sensors (future enhancement)
- **See**: TODO.md for sensor-based features

## Advanced Factors (Future Enhancements)

### 11. **Historical Patterns**
- **Description**: Learn from past schedule effectiveness
- **Impact**: Adjust based on what worked well historically
- **Implementation**: Track schedule adherence, user feedback, plant health indicators

### 12. **Energy Efficiency / Cost**
- **Description**: Optimize for electricity costs
- **Impact**: 
  - Peak rate times → avoid or reduce flooding
  - Off-peak times → schedule more flooding if needed
- **Implementation**: Time-of-use electricity rates configuration

### 13. **System Constraints**
- **Description**: Physical limits of the system
- **Constraints**:
  - Minimum flood duration (pump startup time, minimum effective flood)
  - Maximum flood duration (root health, oxygen needs)
  - Minimum drain time (system recovery, safety)
  - Maximum drain time (root drying out)
- **Impact**: Hard limits on schedule adjustments
- **Implementation**: Configuration parameters

### 14. **Water Level / Reservoir Status** ⚠️ SHELVED
- **Status**: Shelved - Requires sensors (system is open-loop)
- **Description**: Monitor actual water levels
- **Impact**: 
  - Low reservoir → reduce frequency to conserve
  - Normal levels → standard schedule
- **Implementation**: Requires water level sensors
- **See**: TODO.md for sensor-based features

### 15. **pH / EC Levels** ⚠️ SHELVED
- **Status**: Shelved - Requires sensors (system is open-loop)
- **Description**: Nutrient solution quality
- **Impact**: Adjust schedule if nutrient levels are off
- **Implementation**: Requires pH/EC sensors
- **See**: TODO.md for sensor-based features

## Factor Interaction Model

The adaptive system calculates everything independently using a **factor-driven model** (NO base schedule dependency):

```
For each time period (morning/day/evening/night):
  # Calculate base frequency from ToD requirements (NOT from base schedule)
  tod_base_frequency = calculate_from_ToD_period(period)
  
  # Apply environmental factors
  temp_adjustment = f(temperature_at_ToD, temp_trend, temp_forecast)
  humidity_adjustment = f(humidity_at_ToD)
  seasonal_adjustment = f(day_length, season)
  
  # Combine factors
  target_frequency = tod_base_frequency × temp_adjustment × humidity_adjustment × seasonal_adjustment
  
  # Apply system constraints (safety limits, not base schedule)
  Apply constraints:
    - Min/max wait durations (system limits)
    - Min/max flood durations (system limits)
    - Energy efficiency limits (if configured)
  
  # Generate events dynamically
  events = generate_events_for_period(period, target_frequency, constraints)
```

**Key Points**:
- All calculations are independent of base schedule
- Factors determine everything
- Base schedule is ONLY used for analytical comparison during testing

## Dynamic Event Management

The system should be able to:
1. **Add events** when conditions require more frequent flooding:
   - Hot afternoon → insert additional cycles between existing ones
   - Extended daylight → add cycles during peak hours
   
2. **Remove events** when conditions allow less frequent flooding:
   - Cool day → remove some cycles
   - Short daylight → reduce night cycles
   
3. **Compress wait durations** (make more frequent):
   - Hot conditions → reduce OFF duration between cycles
   - Peak growth period → increase frequency
   
4. **Dilate wait durations** (make less frequent):
   - Cool conditions → increase OFF duration
   - Low activity period → decrease frequency

## Base Schedule as Analytical Reference (Testing Only)

**IMPORTANT**: The active adaptive system has **NO programmatic relationship** with the base schedule. The base schedule is **ONLY** used for analytical validation during testing and development.

### Base Schedule Role:
- **Analytical Proof Point**: Compare active adaptive results against base schedule to validate logic
- **Sense Check**: Identify if wait durations are "way off base" (e.g., 5 min when base is 118 min might indicate a bug)
- **Testing Tool**: Use for regression testing and validation
- **NOT Used For**:
  - ❌ Calculation inputs
  - ❌ Fallback values
  - ❌ Bounds or constraints
  - ❌ Reference points in the adaptive algorithm

### Active Adaptive System:
- **Completely Independent**: Calculates everything from scratch based on factors only
- **Factor-Driven**: Uses ToD, Temperature, Humidity, Trends, etc. to determine schedule
- **Self-Contained**: No dependency on base schedule for any calculations
- **Dynamic**: Can produce any number of events (not constrained by base schedule's 38 events)

## Priority Factors (Must Have)

1. **Time of Day** - Core requirement ✅
2. **Temperature at ToD** - Critical for hot day response ✅
3. **Temperature Trends** - Anticipate changes ✅
4. **Humidity** - Available from BOM, affects transpiration ✅

## Secondary Factors (Should Have)

5. **Day Length / Season** - Seasonal adjustments
6. **Temperature Forecast** - Proactive planning
7. **System Constraints** - Safety and limits

## Shelved Factors (Future)

- **Plant Growth Stage** - See TODO.md (no data-driven detection)
- **Sensor-Based Features** - See TODO.md (system is open-loop)

## Future Factors (Nice to Have)

8. **Humidity** - If data available
9. **Historical Patterns** - Learning system
10. **Energy Efficiency** - Cost optimization
11. **Sensors** - Light, water level, pH/EC

