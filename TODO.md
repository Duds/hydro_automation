# TODO - Future Enhancements

This document tracks ideas and features that are shelved for future implementation.

## Shelved Features

### Plant Growth Stage Adaptation
**Status**: Shelved - No data-driven detection method available

**Idea**: Different growth stages (seedling, vegetative, flowering, mature) have different water/nutrient needs. The system could adjust schedule based on growth stage.

**Why Shelved**: 
- No automated way to detect plant growth stage
- Manual mode switching is possible but user wants a robust all-rounder model
- Would require user input or external sensors to determine stage

**Future Consideration**: 
- If sensors become available (cameras, growth monitoring)
- If user feedback mechanism is implemented
- If historical pattern analysis can infer growth stage from schedule patterns

---

### Sensor-Based Features
**Status**: Shelved - System is 100% open-loop (BOM data + pump control only)

**Ideas**:

#### Light Intensity Sensors
- **Purpose**: Measure actual light levels to adjust flooding frequency
- **Impact**: Bright days → more frequent flooding, cloudy days → less frequent
- **Implementation**: Requires light sensors (photodiodes, lux meters)
- **Future**: If sensors are added, integrate light intensity as a factor

#### Water Level Sensors
- **Purpose**: Monitor reservoir water levels
- **Impact**: Low reservoir → reduce frequency to conserve, normal → standard schedule
- **Implementation**: Requires water level sensors (ultrasonic, float switches)
- **Future**: If sensors are added, use for adaptive scheduling and alerts

#### pH/EC Sensors
- **Purpose**: Monitor nutrient solution quality
- **Impact**: Adjust schedule if nutrient levels are off
- **Implementation**: Requires pH and EC (electrical conductivity) sensors
- **Future**: If sensors are added, integrate into adaptation logic

#### Soil Moisture Sensors (for non-hydroponic systems)
- **Purpose**: Direct measurement of plant water needs
- **Impact**: Most accurate way to determine when flooding is needed
- **Implementation**: Requires soil moisture sensors
- **Future**: If expanding to soil-based systems

**Note**: All sensor features assume the system remains open-loop with only BOM environmental data and pump ON/OFF control. Sensors would provide additional input factors but the system would still be open-loop (no feedback from plant health directly).

---

## Future Research Areas

### Historical Pattern Learning
- Track schedule effectiveness over time
- Learn from user manual interventions
- Suggest schedule optimizations based on patterns
- Requires logging and analysis infrastructure

### Energy Efficiency Optimization
- Time-of-use electricity rates
- Peak demand management
- Cost optimization
- Requires electricity rate data/configuration

### Advanced Weather Integration
- Multi-day forecasts for proactive scheduling
- Weather pattern recognition
- Extreme weather event handling
- Requires forecast API access

---

## Implementation Notes

When implementing shelved features:
1. Review this TODO list
2. Check if prerequisites are met (sensors, data sources, etc.)
3. Update ADAPTIVE_FACTORS.md with new factors
4. Design integration with existing adaptive system
5. Maintain backward compatibility with open-loop operation

