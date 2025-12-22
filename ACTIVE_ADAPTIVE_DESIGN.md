# Active Adaptive Schedule Design

## Core Principle

**The active adaptive system is completely independent of the base schedule.**

The base schedule (38 events) exists only for:
- **Analytical validation** during testing
- **Sense checking** to identify if results are "way off base"
- **Regression testing** to ensure changes don't break expected behavior

The active adaptive system:
- Calculates everything from scratch using factors only
- Has no programmatic relationship with base schedule
- Can produce any number of events based on conditions
- Is self-contained and factor-driven

## Architecture

### Input Factors (Independent Calculations)

1. **Time of Day (ToD) Requirements**
   - Morning: High activity → frequent flooding (e.g., every 18-20 min)
   - Day: Peak photosynthesis → regular flooding (e.g., every 28-30 min)
   - Evening: Winding down → frequent but shorter (e.g., every 18-20 min)
   - Night: Minimal activity → infrequent flooding (e.g., every 118-120 min)

2. **Temperature at Time of Day**
   - Fetch/estimate temperature for each cycle time
   - Hot (> 30°C) → compress wait durations
   - Normal (15-25°C) → standard durations
   - Cold (< 15°C) → dilate wait durations

3. **Temperature Trends**
   - Rising temp → anticipate increased needs
   - Falling temp → anticipate decreased needs
   - Stable → maintain current schedule

4. **Humidity at Time of Day**
   - Low humidity (< 40%) → compress wait durations (more transpiration)
   - Normal (40-70%) → standard durations
   - High humidity (> 70%) → dilate wait durations (less transpiration)

5. **Day Length / Season**
   - Long days → more events during extended daylight
   - Short days → fewer events, longer waits

### Calculation Flow

```
1. Determine time periods for the day (morning/day/evening/night)
   - Based on sunrise/sunset times
   - Dynamic boundaries

2. For each period:
   a. Calculate base frequency from ToD requirements
      - NOT from base schedule
      - Based on plant metabolic needs for that period
   
   b. Get environmental conditions for that period
      - Temperature at period time
      - Humidity at period time
      - Temperature trend
   
   c. Calculate adjustment factors
      - temp_factor = f(temperature, trend)
      - humidity_factor = f(humidity)
      - seasonal_factor = f(day_length)
   
   d. Calculate target frequency
      - target = base_frequency × temp_factor × humidity_factor × seasonal_factor
   
   e. Generate events for period
      - Calculate wait durations from target frequency
      - Apply system constraints (min/max)
      - Generate event times

3. Combine all periods into full day schedule
   - Sort by time
   - Ensure no overlaps
   - Validate against system constraints

4. (Testing Only) Compare with base schedule
   - Log differences
   - Flag if "way off base" (e.g., > 50% deviation)
   - Use for validation, not calculation
```

## Dynamic Event Management

### Adding Events
- **When**: High demand conditions (hot + low humidity + peak ToD)
- **How**: Calculate required frequency, if higher than base → add events
- **Example**: Hot afternoon (35°C, 30% humidity) during day period
  - Base day frequency: every 28 min
  - Adjusted frequency: every 18 min (compressed)
  - Result: Add events between existing ones

### Removing Events
- **When**: Low demand conditions (cool + high humidity + low activity ToD)
- **How**: Calculate required frequency, if lower than base → remove events
- **Example**: Cool night (12°C, 85% humidity) during night period
  - Base night frequency: every 118 min
  - Adjusted frequency: every 150 min (dilated)
  - Result: Remove some night events

### Compressing Wait Durations
- **When**: Conditions require more frequent flooding
- **How**: Reduce OFF duration between cycles
- **Example**: Hot day → reduce from 28 min to 20 min

### Dilating Wait Durations
- **When**: Conditions allow less frequent flooding
- **How**: Increase OFF duration between cycles
- **Example**: Cool day → increase from 28 min to 35 min

## System Constraints (Not Base Schedule)

### Hard Limits
- **Minimum wait duration**: 5 minutes (system recovery time)
- **Maximum wait duration**: 180 minutes (root health)
- **Minimum flood duration**: 2 minutes (effective flood time)
- **Maximum flood duration**: 15 minutes (root oxygen needs)

### Soft Limits (Warnings)
- If calculated duration < 50% of base schedule equivalent → log warning
- If calculated duration > 200% of base schedule equivalent → log warning
- These are for validation/testing, not constraints on calculation

## Testing & Validation

### Analytical Comparison (Not Used in Calculation)

```python
def validate_against_base(active_schedule, base_schedule):
    """
    Compare active adaptive schedule with base schedule.
    This is ONLY for testing/validation, NOT used in calculations.
    """
    for active_event in active_schedule:
        # Find closest base event
        base_event = find_closest_base_event(active_event, base_schedule)
        
        # Compare wait durations
        active_wait = active_event.off_duration_minutes
        base_wait = base_event.off_duration_minutes
        
        deviation = abs(active_wait - base_wait) / base_wait
        
        if deviation > 0.5:  # 50% deviation
            log_warning(f"Way off base: {active_wait} min vs {base_wait} min ({deviation*100:.1f}% deviation)")
        
        # Log for analysis
        log_comparison(active_event, base_event, deviation)
```

### Sense Check Criteria

Flag as "way off base" if:
- Wait duration differs by > 50% from base schedule equivalent
- Number of events differs by > 30% from base schedule (38 events)
- Any event has wait duration outside reasonable bounds (< 5 min or > 180 min)

These flags are for **human review**, not automatic correction.

## Implementation Notes

1. **No Base Schedule Dependencies**
   - Active adaptive module should not import or reference base schedule
   - Base schedule comparison is a separate validation module

2. **Factor-Driven Calculations**
   - All calculations start from factors
   - ToD requirements are hardcoded rules, not from base schedule
   - Environmental factors modify these rules

3. **Independent Event Generation**
   - Generate events based on calculated frequencies
   - No reference to base schedule event count or timing

4. **Validation Layer (Separate)**
   - Comparison with base schedule is a separate testing/validation layer
   - Can be enabled/disabled
   - Logs warnings but doesn't affect calculations

