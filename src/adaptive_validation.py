"""Validation module for comparing adaptive schedules with base schedule.

This module is ONLY for testing/validation purposes.
It has NO role in production calculations.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import time as dt_time


class AdaptiveValidator:
    """
    Validates adaptive schedules by comparing with base schedule.
    
    This is ONLY for analytical validation during testing.
    The base schedule is NOT used in any calculations.
    """

    def __init__(self, threshold: float = 0.5):
        """
        Initialize validator.
        
        Args:
            threshold: Deviation threshold (0.5 = 50%) for flagging "way off base"
        """
        self.threshold = threshold

    def compare_with_base(
        self,
        active_schedule: List[Dict[str, Any]],
        base_schedule: List[Dict[str, Any]],
        sunrise: Optional[dt_time] = None,
        sunset: Optional[dt_time] = None
    ) -> Dict[str, Any]:
        """
        Compare adaptive schedule with base schedule.
        
        Args:
            active_schedule: Adaptive schedule cycles
            base_schedule: Base schedule cycles
            sunrise: Sunrise time (optional, for period calculation)
            sunset: Sunset time (optional, for period calculation)
            
        Returns:
            Comparison report dictionary
        """
        report = {
            "active_event_count": len(active_schedule),
            "base_event_count": len(base_schedule),
            "event_count_diff": len(active_schedule) - len(base_schedule),
            "event_count_diff_percent": 0.0,
            "deviations": [],
            "warnings": [],
            "matches": [],
            "period_mismatches": []
        }
        
        if len(base_schedule) > 0:
            report["event_count_diff_percent"] = (
                (len(active_schedule) - len(base_schedule)) / len(base_schedule) * 100
            )
        
        # Flag if event count differs significantly
        if abs(report["event_count_diff_percent"]) > 30:
            report["warnings"].append(
                f"Event count differs by {report['event_count_diff_percent']:.1f}% "
                f"({report['active_event_count']} vs {report['base_event_count']})"
            )
        
        # Compare wait durations for similar times
        for active_event in active_schedule:
            active_time = active_event.get("on_time", "")
            active_wait = active_event.get("off_duration_minutes", 0)
            active_period = active_event.get("period")  # Period is already in active events
            
            # Find closest base event (preferring same period)
            closest_base, same_period = self._find_closest_base_event(
                active_time, base_schedule, active_period, sunrise, sunset
            )
            
            if closest_base:
                base_wait = closest_base.get("off_duration_minutes", 0)
                base_time = closest_base.get("on_time", "")
                base_period = self._get_time_period(base_time, sunrise, sunset)
                
                comparison = {
                    "active_time": active_time,
                    "active_wait": active_wait,
                    "active_period": active_period,
                    "base_time": base_time,
                    "base_wait": base_wait,
                    "base_period": base_period,
                    "same_period": same_period,
                    "deviation": self._calculate_deviation(active_wait, base_wait),
                    "deviation_percent": 0.0
                }
                
                if base_wait > 0:
                    comparison["deviation_percent"] = (comparison["deviation"] / base_wait * 100)
                
                # Only flag deviations when periods match
                if same_period:
                    if abs(comparison["deviation_percent"]) > self.threshold * 100:
                        comparison["flagged"] = True
                        report["deviations"].append(comparison)
                        report["warnings"].append(
                            f"Way off base: {active_time} has {active_wait:.1f} min wait "
                            f"(base: {base_wait:.1f} min, {comparison['deviation_percent']:.1f}% deviation)"
                        )
                    else:
                        comparison["flagged"] = False
                        report["matches"].append(comparison)
                else:
                    # Period mismatch - don't flag as deviation, but track it
                    comparison["flagged"] = False
                    comparison["period_mismatch"] = True
                    report["period_mismatches"].append(comparison)
        
        return report

    def _find_closest_base_event(
        self,
        active_time: str,
        base_schedule: List[Dict[str, Any]],
        active_period: Optional[str] = None,
        sunrise: Optional[dt_time] = None,
        sunset: Optional[dt_time] = None
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Find closest base event to active event time, preferring same period.
        
        Args:
            active_time: Active event time string
            base_schedule: Base schedule cycles
            active_period: Period of active event (optional)
            sunrise: Sunrise time (optional, for period calculation)
            sunset: Sunset time (optional, for period calculation)
            
        Returns:
            Tuple of (closest_event, same_period: bool)
        """
        if not base_schedule:
            return None, False
        
        active_minutes = self._time_to_minutes(active_time)
        
        # First, try to find events in the same period
        if active_period:
            same_period_events = []
            for base_event in base_schedule:
                base_time = base_event.get("on_time", "")
                base_period = self._get_time_period(base_time, sunrise, sunset)
                if base_period == active_period:
                    same_period_events.append(base_event)
            
            if same_period_events:
                # Find closest within same period
                closest = None
                min_diff = float('inf')
                for base_event in same_period_events:
                    base_time = base_event.get("on_time", "")
                    base_minutes = self._time_to_minutes(base_time)
                    
                    # Handle wrapping around midnight
                    diff1 = abs(active_minutes - base_minutes)
                    diff2 = abs(active_minutes - (base_minutes + 24 * 60))
                    diff3 = abs((active_minutes + 24 * 60) - base_minutes)
                    diff = min(diff1, diff2, diff3)
                    
                    if diff < min_diff:
                        min_diff = diff
                        closest = base_event
                
                if closest:
                    return closest, True
        
        # Fall back to closest by time (any period)
        closest = None
        min_diff = float('inf')
        
        for base_event in base_schedule:
            base_time = base_event.get("on_time", "")
            base_minutes = self._time_to_minutes(base_time)
            
            # Handle wrapping around midnight
            diff1 = abs(active_minutes - base_minutes)
            diff2 = abs(active_minutes - (base_minutes + 24 * 60))
            diff3 = abs((active_minutes + 24 * 60) - base_minutes)
            diff = min(diff1, diff2, diff3)
            
            if diff < min_diff:
                min_diff = diff
                closest = base_event
        
        return closest, False

    def _get_time_period(self, cycle_time, sunrise: Optional[dt_time] = None, sunset: Optional[dt_time] = None) -> str:
        """
        Determine which time period a cycle belongs to.
        
        Args:
            cycle_time: Time of the cycle (str "HH:MM" or dt_time)
            sunrise: Sunrise time (optional)
            sunset: Sunset time (optional)
            
        Returns:
            Period name: "morning", "day", "evening", or "night"
        """
        # Convert to dt_time if string
        if isinstance(cycle_time, str):
            parts = cycle_time.split(":")
            cycle_time = dt_time(int(parts[0]), int(parts[1]))
        
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

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert time string to minutes from midnight."""
        if isinstance(time_str, dt_time):
            return time_str.hour * 60 + time_str.minute
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    def _calculate_deviation(self, active_value: float, base_value: float) -> float:
        """Calculate absolute deviation between active and base values."""
        return abs(active_value - base_value)

    def flag_deviations(
        self,
        active_schedule: List[Dict[str, Any]],
        base_schedule: List[Dict[str, Any]],
        threshold: Optional[float] = None,
        sunrise: Optional[dt_time] = None,
        sunset: Optional[dt_time] = None
    ) -> List[Dict[str, Any]]:
        """
        Flag events that deviate significantly from base schedule.
        Only flags deviations when periods match.
        
        Args:
            active_schedule: Active adaptive schedule
            base_schedule: Base schedule
            threshold: Deviation threshold (overrides instance threshold if provided)
            sunrise: Sunrise time (optional, for period calculation)
            sunset: Sunset time (optional, for period calculation)
            
        Returns:
            List of flagged deviations
        """
        if threshold is None:
            threshold = self.threshold
        
        deviations = []
        for active_event in active_schedule:
            active_time = active_event.get("on_time", "")
            active_wait = active_event.get("off_duration_minutes", 0)
            active_period = active_event.get("period")
            
            closest_base, same_period = self._find_closest_base_event(
                active_time, base_schedule, active_period, sunrise, sunset
            )
            
            # Only flag if periods match
            if closest_base and same_period:
                base_wait = closest_base.get("off_duration_minutes", 0)
                if base_wait > 0:
                    deviation_percent = abs(active_wait - base_wait) / base_wait
                    if deviation_percent > threshold:
                        deviations.append({
                            "time": active_time,
                            "active_wait": active_wait,
                            "base_wait": base_wait,
                            "deviation_percent": deviation_percent * 100
                        })
        
        return deviations

    def generate_validation_report(
        self,
        active_schedule: List[Dict[str, Any]],
        base_schedule: List[Dict[str, Any]],
        sunrise: Optional[dt_time] = None,
        sunset: Optional[dt_time] = None
    ) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            active_schedule: Active adaptive schedule
            base_schedule: Base schedule
            sunrise: Sunrise time (optional, for period calculation)
            sunset: Sunset time (optional, for period calculation)
            
        Returns:
            Formatted report string
        """
        comparison = self.compare_with_base(active_schedule, base_schedule, sunrise, sunset)
        
        report_lines = [
            "=" * 80,
            "ADAPTIVE SCHEDULE VALIDATION REPORT",
            "=" * 80,
            "",
            f"Active Schedule Events: {comparison['active_event_count']}",
            f"Base Schedule Events: {comparison['base_event_count']}",
            f"Event Count Difference: {comparison['event_count_diff']} ({comparison['event_count_diff_percent']:.1f}%)",
            "",
            "Note: Deviations are only flagged when comparing events within the same period.",
            ""
        ]
        
        if comparison["warnings"]:
            report_lines.append("WARNINGS:")
            report_lines.append("-" * 80)
            for warning in comparison["warnings"]:
                report_lines.append(f"  ⚠ {warning}")
            report_lines.append("")
        
        if comparison["deviations"]:
            report_lines.append("FLAGGED DEVIATIONS (>50% difference, same period):")
            report_lines.append("-" * 80)
            for dev in comparison["deviations"]:
                report_lines.append(
                    f"  {dev['active_time']} ({dev.get('active_period', 'unknown')}): "
                    f"{dev['active_wait']:.1f} min "
                    f"(base: {dev['base_wait']:.1f} min, {dev['deviation_percent']:.1f}% diff)"
                )
            report_lines.append("")
        
        if comparison["period_mismatches"]:
            report_lines.append(f"PERIOD MISMATCHES ({len(comparison['period_mismatches'])} events):")
            report_lines.append("-" * 80)
            report_lines.append("These events couldn't be compared because they're in different periods.")
            for mismatch in comparison["period_mismatches"][:10]:  # Show first 10
                report_lines.append(
                    f"  {mismatch['active_time']} ({mismatch.get('active_period', 'unknown')}) vs "
                    f"{mismatch['base_time']} ({mismatch.get('base_period', 'unknown')})"
                )
            if len(comparison["period_mismatches"]) > 10:
                report_lines.append(f"  ... and {len(comparison['period_mismatches']) - 10} more mismatches")
            report_lines.append("")
        
        if comparison["matches"]:
            report_lines.append(f"MATCHES ({len(comparison['matches'])} events within threshold, same period):")
            report_lines.append("-" * 80)
            for match in comparison["matches"][:10]:  # Show first 10
                report_lines.append(
                    f"  {match['active_time']}: {match['active_wait']:.1f} min "
                    f"(base: {match['base_wait']:.1f} min, {match['deviation_percent']:.1f}% diff)"
                )
            if len(comparison["matches"]) > 10:
                report_lines.append(f"  ... and {len(comparison['matches']) - 10} more matches")
            report_lines.append("")
        
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)

