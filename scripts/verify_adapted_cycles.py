#!/usr/bin/env python3
"""Script to calculate and display all adapted cycles for verification."""

import json
import sys
from pathlib import Path
from datetime import time as dt_time, datetime
from typing import List, Dict, Any, Optional, Tuple

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import only what we need (avoiding controller dependencies)
from src.daylight import DaylightCalculator
from src.bom_temperature import BOMTemperature


def load_config(config_path: str):
    """Load configuration from JSON file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_time(t) -> str:
    """Format time object as string."""
    if isinstance(t, dt_time):
        return t.strftime("%H:%M")
    return str(t)


def get_time_period(cycle_time: dt_time, sunrise: Optional[dt_time] = None, sunset: Optional[dt_time] = None) -> str:
    """
    Determine which time period a cycle belongs to.
    """
    hour = cycle_time.hour
    minute = cycle_time.minute
    cycle_minutes = hour * 60 + minute
    
    # Define period boundaries (in minutes from midnight)
    morning_start = 6 * 60  # 06:00
    day_start = 9 * 60  # 09:00
    evening_start = 18 * 60  # 18:00
    night_start = 20 * 60  # 20:00
    
    # Adjust boundaries if sunrise/sunset are provided
    if sunrise:
        sunrise_minutes = sunrise.hour * 60 + sunrise.minute
        if 5 * 60 <= sunrise_minutes <= 7 * 60:
            morning_start = sunrise_minutes
    
    if sunset:
        sunset_minutes = sunset.hour * 60 + sunset.minute
        if 17 * 60 <= sunset_minutes <= 19 * 60:
            evening_start = sunset_minutes
    
    # Determine period
    if cycle_minutes >= night_start or cycle_minutes < morning_start:
        return "night"
    elif morning_start <= cycle_minutes < day_start:
        return "morning"
    elif day_start <= cycle_minutes < evening_start:
        return "day"
    else:  # evening_start <= cycle_minutes < night_start
        return "evening"


def shift_schedule_to_sunrise(base_cycles: List[Dict[str, Any]], sunrise_time: dt_time) -> List[Dict[str, Any]]:
    """Shift base schedule cycles to align with sunrise."""
    if not base_cycles:
        return base_cycles

    # Find the earliest cycle time
    earliest_time = None
    for cycle in base_cycles:
        on_time_str = cycle.get("on_time")
        if on_time_str:
            if isinstance(on_time_str, str):
                parts = on_time_str.split(":")
                cycle_time = dt_time(int(parts[0]), int(parts[1]))
            else:
                cycle_time = on_time_str
            
            if earliest_time is None or cycle_time < earliest_time:
                earliest_time = cycle_time

    if earliest_time is None:
        return base_cycles

    # Calculate time difference
    earliest_minutes = earliest_time.hour * 60 + earliest_time.minute
    sunrise_minutes = sunrise_time.hour * 60 + sunrise_time.minute
    shift_minutes = sunrise_minutes - earliest_minutes

    # Shift all cycles
    shifted_cycles = []
    for cycle in base_cycles:
        on_time_str = cycle.get("on_time")
        if on_time_str:
            if isinstance(on_time_str, str):
                parts = on_time_str.split(":")
                cycle_time = dt_time(int(parts[0]), int(parts[1]))
            else:
                cycle_time = on_time_str
            
            # Add shift
            total_minutes = (cycle_time.hour * 60 + cycle_time.minute + shift_minutes) % (24 * 60)
            new_hour = total_minutes // 60
            new_minute = total_minutes % 60
            new_time = dt_time(new_hour, new_minute)
            
            shifted_cycle = cycle.copy()
            shifted_cycle["on_time"] = new_time.strftime("%H:%M")
            shifted_cycles.append(shifted_cycle)
        else:
            shifted_cycles.append(cycle)

    return shifted_cycles


def apply_daylight_boost_reduction(cycles: List[Dict[str, Any]], sunrise: Optional[dt_time], sunset: Optional[dt_time], 
                                   daylight_boost: float, night_reduction: float, preserve_base_durations: bool = False) -> List[Dict[str, Any]]:
    """Apply daylight boost/reduction factors."""
    # If preserve_base_durations is enabled, return cycles unchanged
    if preserve_base_durations:
        return cycles
    
    daylight_factor = 1.0 / daylight_boost if daylight_boost != 0 else 1.0
    night_factor = night_reduction
    
    adjusted_cycles = []
    for cycle in cycles:
        adjusted_cycle = cycle.copy()
        on_time_str = cycle.get("on_time")
        
        if on_time_str:
            if isinstance(on_time_str, str):
                parts = on_time_str.split(":")
                cycle_time = dt_time(int(parts[0]), int(parts[1]))
            else:
                cycle_time = on_time_str
            
            # Determine period
            period = get_time_period(cycle_time, sunrise, sunset)
            
            # Get appropriate factor
            if period == "night":
                adjustment_factor = night_factor
            else:
                adjustment_factor = daylight_factor
            
            # Apply adjustment
            off_duration = cycle.get("off_duration_minutes", 0)
            adjusted_off = off_duration * adjustment_factor
            
            # Apply safety limits
            min_off = 5
            max_off = 180
            adjusted_off = max(min_off, min(max_off, adjusted_off))
            adjusted_cycle["off_duration_minutes"] = adjusted_off
        
        adjusted_cycles.append(adjusted_cycle)
    
    return adjusted_cycles


def apply_temperature_adjustment(cycles: List[Dict[str, Any]], temp: Optional[float], sensitivity: str = "medium") -> List[Dict[str, Any]]:
    """Apply temperature adjustment."""
    if temp is None:
        return cycles
    
    # Calculate adjustment factor
    temp_fetcher = BOMTemperature()
    adjustment_factor = temp_fetcher.get_temperature_adjustment_factor(temp, sensitivity=sensitivity)
    
    if adjustment_factor == 1.0:
        return cycles
    
    # Apply adjustment
    adjusted_cycles = []
    for cycle in cycles:
        adjusted_cycle = cycle.copy()
        off_duration = cycle.get("off_duration_minutes", 0)
        
        adjusted_off = off_duration * adjustment_factor
        min_off = 5
        max_off = 180
        adjusted_off = max(min_off, min(max_off, adjusted_off))
        adjusted_cycle["off_duration_minutes"] = adjusted_off
        
        adjusted_cycles.append(adjusted_cycle)
    
    return adjusted_cycles


def calculate_adapted_cycles(config_path: str = "config/config.json"):
    """Calculate and display all adapted cycles."""
    print("=" * 80)
    print("ADAPTED CYCLE CALCULATION VERIFICATION")
    print("=" * 80)
    print()
    
    # Load config
    config = load_config(config_path)
    schedule_config = config.get("schedule", {})
    cycles = schedule_config.get("cycles", [])
    adaptation_config = schedule_config.get("adaptation", {})
    
    if not adaptation_config.get("enabled", False):
        print("ERROR: Adaptation is not enabled in configuration")
        return
    
    # Get environmental data
    location_config = adaptation_config.get("location", {})
    postcode = location_config.get("postcode")
    timezone = location_config.get("timezone")
    
    sunrise = None
    sunset = None
    if postcode:
        daylight_calc = DaylightCalculator(postcode=postcode, timezone=timezone)
        sunrise, sunset = daylight_calc.get_sunrise_sunset()
    
    temp = schedule_config.get("_current_temperature")
    if temp is None:
        temp_config = adaptation_config.get("temperature", {})
        station_id = temp_config.get("station_id")
        if station_id:
            temp_fetcher = BOMTemperature(station_id=station_id)
            temp = temp_fetcher.fetch_temperature()
    
    print("Configuration:")
    print(f"  Sunrise: {sunrise.strftime('%H:%M') if sunrise else 'N/A'}")
    print(f"  Sunset: {sunset.strftime('%H:%M') if sunset else 'N/A'}")
    print(f"  Temperature: {temp}°C" if temp else "  Temperature: N/A")
    print()
    
    # Get adaptation factors
    daylight_config = adaptation_config.get("daylight", {})
    daylight_boost = daylight_config.get("daylight_boost", 1.2)
    night_reduction = daylight_config.get("night_reduction", 0.8)
    preserve_base_durations = daylight_config.get("preserve_base_durations", False)
    daylight_factor = 1.0 / daylight_boost if daylight_boost != 0 else 1.0
    
    temp_config = adaptation_config.get("temperature", {})
    sensitivity = temp_config.get("adjustment_sensitivity", "medium")
    
    # Calculate temperature factor
    temp_factor = 1.0
    if temp is not None:
        temp_fetcher = BOMTemperature()
        temp_factor = temp_fetcher.get_temperature_adjustment_factor(temp, sensitivity=sensitivity)
    
    # Apply adaptations
    adapted_cycles = cycles.copy()
    
    # Step 1: Daylight shift
    if sunrise and daylight_config.get("shift_schedule", False):
        adapted_cycles = shift_schedule_to_sunrise(adapted_cycles, sunrise)
    
    # Step 2: Daylight boost/reduction
    if daylight_config.get("enabled", False):
        adapted_cycles = apply_daylight_boost_reduction(adapted_cycles, sunrise, sunset, daylight_boost, night_reduction, preserve_base_durations)
    
    # Step 3: Temperature adjustment
    if temp_config.get("enabled", False) and temp is not None:
        adapted_cycles = apply_temperature_adjustment(adapted_cycles, temp, sensitivity)
    
    print("=" * 80)
    print("BASE CYCLES vs ADAPTED CYCLES")
    print("=" * 80)
    print()
    print(f"{'Original Time':<15} {'Base OFF':<12} {'Adapted Time':<15} {'Adapted OFF':<12} {'Period':<10} {'Calculation':<30} {'Status':<8}")
    print("-" * 100)
    
    # Match and display
    for i, base_cycle in enumerate(cycles):
        base_time_str = base_cycle.get("on_time", "")
        base_off = base_cycle.get("off_duration_minutes", 0)
        
        if i < len(adapted_cycles):
            adapted_cycle = adapted_cycles[i]
            adapted_time_str = adapted_cycle.get("on_time", "")
            adapted_off = adapted_cycle.get("off_duration_minutes", 0)
            
            # Determine period
            period = "unknown"
            if adapted_time_str:
                try:
                    parts = adapted_time_str.split(":")
                    cycle_time = dt_time(int(parts[0]), int(parts[1]))
                    period = get_time_period(cycle_time, sunrise, sunset)
                except:
                    pass
            
            # Calculate expected value
            if preserve_base_durations:
                # Base durations are preserved, only temperature adjustment applies
                expected = base_off * temp_factor
                calc_str = f"{base_off} × {temp_factor:.2f} (preserved)"
            elif period == "night":
                expected = base_off * night_reduction * temp_factor
                calc_str = f"{base_off} × {night_reduction} × {temp_factor:.2f}"
            else:
                expected = base_off * daylight_factor * temp_factor
                calc_str = f"{base_off} × {daylight_factor:.4f} × {temp_factor:.2f}"
            
            # Check if calculation matches
            match = "✓" if abs(adapted_off - expected) < 0.1 else "✗"
            
            print(f"{base_time_str:<15} {base_off:<12.1f} {adapted_time_str:<15} {adapted_off:<12.1f} {period:<10} {calc_str:<30} {match}")
        else:
            print(f"{base_time_str:<15} {base_off:<12.1f} {'NOT FOUND':<15} {'N/A':<12} {'N/A':<10} {'N/A':<30} {'✗'}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total cycles: {len(cycles)}")
    print(f"Adapted cycles: {len(adapted_cycles)}")
    print(f"Temperature factor: {temp_factor:.4f}")
    print(f"Daylight factor: {daylight_factor:.4f}")
    print(f"Night factor: {night_reduction:.4f}")
    print()
    
    # Show specific test cases from plan
    print("=" * 80)
    print("SPECIFIC TEST CASES")
    print("=" * 80)
    print()
    
    # Find 00:06 cycle (should be from 18:20)
    for ac in adapted_cycles:
        ac_time_str = ac.get("on_time", "")
        if ac_time_str == "00:06":
            ac_off = ac.get("off_duration_minutes", 0)
            if preserve_base_durations:
                expected = 18.0 * temp_factor  # Base duration preserved
            else:
                expected = 18.0 * 0.8 * temp_factor
            status = "✓" if abs(ac_off - expected) < 0.1 else "✗"
            print(f"00:06 cycle: {ac_off:.1f} min (expected: {expected:.1f} min) {status}")
            if status == "✗":
                print(f"  ERROR: Calculation mismatch! Should be {expected:.1f} min")
            break
    
    # Find 05:46 cycle (should be from 00:00)
    for ac in adapted_cycles:
        ac_time_str = ac.get("on_time", "")
        if ac_time_str == "05:46":
            ac_off = ac.get("off_duration_minutes", 0)
            if preserve_base_durations:
                expected = 118.0 * temp_factor  # Base duration preserved
            else:
                expected = 118.0 * 0.8 * temp_factor
            status = "✓" if abs(ac_off - expected) < 0.1 else "✗"
            print(f"05:46 cycle: {ac_off:.1f} min (expected: {expected:.1f} min) {status}")
            if status == "✗":
                print(f"  ERROR: Calculation mismatch! Should be {expected:.1f} min")
            break
    
    # Find 11:46 cycle (should be from 06:00)
    for ac in adapted_cycles:
        ac_time_str = ac.get("on_time", "")
        if ac_time_str == "11:46":
            ac_off = ac.get("off_duration_minutes", 0)
            if preserve_base_durations:
                expected = 18.0 * temp_factor  # Base duration preserved
            else:
                expected = 18.0 * daylight_factor * temp_factor
            status = "✓" if abs(ac_off - expected) < 0.1 else "✗"
            print(f"11:46 cycle: {ac_off:.1f} min (expected: {expected:.1f} min) {status}")
            if status == "✗":
                print(f"  ERROR: Calculation mismatch! Should be {expected:.1f} min")
            break


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/config.json"
    calculate_adapted_cycles(config_path)
