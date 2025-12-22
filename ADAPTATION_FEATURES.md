# Adaptation Features Documentation

## Current Implementation Status

### ✅ Temperature Adaptation (IMPLEMENTED)

**What it does:**
- Adjusts the OFF duration (drain time) for all cycles based on current air temperature
- Fetches temperature from BOM (Bureau of Meteorology) every hour (configurable)
- Applies a multiplier to all cycle OFF durations based on temperature bands

**How it works:**
1. Fetches temperature from BOM station (configured by postcode or station ID)
2. Calculates adjustment factor based on temperature:
   - **< 15°C (Cold)**: Factor = 1.15 (15% longer OFF duration = less frequent flooding)
   - **15-25°C (Normal)**: Factor = 1.0 (no adjustment)
   - **25-30°C (Warm)**: Factor = 0.85 (15% shorter OFF duration = more frequent flooding)
   - **> 30°C (Hot)**: Factor = 0.70 (30% shorter OFF duration = much more frequent flooding)
3. Multiplies each cycle's `off_duration_minutes` by the factor
4. Applies safety limits: minimum 5 minutes, maximum 180 minutes

**Example:**
- Base cycle: `{"on_time": "10:00", "off_duration_minutes": 28.0}`
- Temperature: 28°C (warm)
- Adjusted: `{"on_time": "10:00", "off_duration_minutes": 23.8}` (28 × 0.85)

**Location:** `src/adaptive_scheduler.py` → `_apply_temperature_adjustment()`
**Temperature logic:** `src/bom_temperature.py` → `get_temperature_adjustment_factor()`

---

### ✅ Daylight Adaptation (IMPLEMENTED)

**What it does:**
- Shifts the entire schedule to align with sunrise (optional, if `shift_schedule` is enabled)
- Applies `daylight_boost` factor to increase flooding frequency during daylight hours
- Applies `night_reduction` factor to decrease flooding frequency during night hours

**How it works:**

**1. Sunrise Shift (optional):**
- Calculates sunrise/sunset times for the configured postcode
- Finds the earliest cycle time in the base schedule
- Calculates the time difference between earliest cycle and sunrise
- Shifts ALL cycle times by that difference to align with sunrise
- Updates daily when scheduler starts

**2. Daylight Boost/Night Reduction:**
- For each cycle, determines if `on_time` is during daylight (between sunrise and sunset) or night
- **Daylight cycles**: Applies `daylight_boost` factor (default 1.2)
  - Factor of 1.2 means 20% more frequent flooding
  - OFF duration is multiplied by `1/1.2 = 0.83` (shorter OFF = more frequent)
- **Night cycles**: Applies `night_reduction` factor (default 0.8)
  - Factor of 0.8 means 20% less frequent flooding
  - OFF duration is multiplied by `0.8` (longer OFF = less frequent)
- Applies safety limits: minimum 5 minutes, maximum 180 minutes

**Example (sunrise shift):**
- Base schedule earliest cycle: 06:00
- Sunrise: 05:46
- Shift: -14 minutes
- All cycles shift earlier by 14 minutes

**Example (daylight boost/reduction):**
- Base cycle: `{"on_time": "10:00", "off_duration_minutes": 28.0}` (daylight)
- `daylight_boost`: 1.2
- Adjusted: `{"on_time": "10:00", "off_duration_minutes": 23.3}` (28 × 0.83)

- Base cycle: `{"on_time": "02:00", "off_duration_minutes": 118.0}` (night)
- `night_reduction`: 0.8
- Adjusted: `{"on_time": "02:00", "off_duration_minutes": 94.4}` (118 × 0.8)

**Location:** `src/adaptive_scheduler.py` → `_apply_daylight_shift()`, `_apply_daylight_boost_reduction()`
**Daylight calculation:** `src/daylight.py` → `shift_schedule_to_sunrise()`, `get_sunrise_sunset()`

---

### 🔒 Learning System (SHELVED)

**Current status:**
- UI elements have been removed (hidden from user interface)
- Config structure remains for future implementation
- **No code exists to implement these features**
- Shelved until feedback mechanisms can be added

**The Problem:**
This is an **open-loop system** with no feedback sensors. The system can:
- ✅ Control when the pump turns on/off
- ✅ Know environmental conditions (temperature, daylight)
- ❌ **Cannot measure plant health, growth, or system effectiveness**

**What would be needed for learning:**

#### Option 1: Manual Feedback (User Input)
- User rates system effectiveness (e.g., 1-5 stars)
- User reports issues (overwatering, underwatering, plant health)
- System correlates feedback with schedule patterns
- Suggests schedule adjustments based on patterns

#### Option 2: Proxy Metrics (Indirect Measurement)
- Track schedule adherence (did cycles run as planned?)
- Track environmental patterns (temperature trends, daylight hours)
- Track manual overrides (user manually turned pump on/off)
- Correlate patterns with time of year, weather patterns
- Suggest optimisations based on historical patterns

#### Option 3: External Sensors (Future Enhancement)
- Soil moisture sensors
- Water level sensors
- Plant growth cameras
- pH/EC sensors
- These would provide closed-loop feedback

**What "Track Effectiveness" could do:**
- Log schedule execution (actual vs planned cycles)
- Track environmental conditions during each cycle
- Record user manual interventions
- Build historical database of schedule patterns
- Calculate schedule adherence metrics

**What "Suggest Improvements" could do:**
- Analyse historical patterns (e.g., "You often override cycles at 14:00")
- Compare with environmental data (e.g., "Temperature spikes at 13:00, consider more frequent cycles")
- Seasonal adjustments (e.g., "Sunrise is 30 minutes earlier now, shift schedule?")
- Pattern recognition (e.g., "You manually add cycles on hot days, enable temperature adaptation?")

---

## Configuration

All adaptation features require:
1. `adaptation.enabled = true` (master switch)
2. Individual feature enabled (`temperature.enabled`, `daylight.enabled`)
3. Location configured (`adaptation.location.postcode`)

**Note:** Even if adaptation is disabled, environmental data sources (daylight calculator, temperature fetcher) are still initialized for API access (dashboard display).

---

## Recommendations

### For Learning System Implementation:

1. **Start with logging:**
   - Log all cycle executions with timestamps
   - Log environmental conditions at cycle time
   - Log manual overrides
   - Store in JSON/CSV for analysis

2. **Add user feedback mechanism:**
   - Simple rating system in web UI
   - Optional notes/comments
   - Correlate with schedule patterns

3. **Implement pattern analysis:**
   - Detect schedule drift (actual vs planned)
   - Identify common override patterns
   - Suggest schedule adjustments based on historical data

4. **Future: Add sensors:**
   - Soil moisture sensors for closed-loop control
   - Water level sensors for flood detection
   - These would enable true effectiveness tracking

---

## Code Locations

- **Adaptive Scheduler:** `src/adaptive_scheduler.py`
- **Temperature Logic:** `src/bom_temperature.py`
- **Daylight Logic:** `src/daylight.py`
- **BOM Stations:** `src/bom_stations.py`
- **Configuration:** `config/config.json` → `schedule.adaptation`

