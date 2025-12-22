"""Validation module for comparing active adaptive schedules with base schedule.

This module is ONLY for testing/validation purposes.
It has NO role in production calculations.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import time as dt_time


class AdaptiveValidator:
    """
    Validates active adaptive schedules by comparing with base schedule.
    
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
        base_schedule: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare active adaptive schedule with base schedule.
        
        Args:
            active_schedule: Active adaptive schedule cycles
            base_schedule: Base schedule cycles
            
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
            "matches": []
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
            
            # Find closest base event
            closest_base = self._find_closest_base_event(active_time, base_schedule)
            
            if closest_base:
                base_wait = closest_base.get("off_duration_minutes", 0)
                deviation = self._calculate_deviation(active_wait, base_wait)
                
                comparison = {
                    "active_time": active_time,
                    "active_wait": active_wait,
                    "base_time": closest_base.get("on_time", ""),
                    "base_wait": base_wait,
                    "deviation": deviation,
                    "deviation_percent": (deviation / base_wait * 100) if base_wait > 0 else 0
                }
                
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
        
        return report

    def _find_closest_base_event(
        self,
        active_time: str,
        base_schedule: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find closest base event to active event time."""
        if not base_schedule:
            return None
        
        active_minutes = self._time_to_minutes(active_time)
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
        
        return closest

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
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Flag events that deviate significantly from base schedule.
        
        Args:
            active_schedule: Active adaptive schedule
            base_schedule: Base schedule
            threshold: Deviation threshold (overrides instance threshold if provided)
            
        Returns:
            List of flagged deviations
        """
        if threshold is None:
            threshold = self.threshold
        
        deviations = []
        for active_event in active_schedule:
            active_time = active_event.get("on_time", "")
            active_wait = active_event.get("off_duration_minutes", 0)
            
            closest_base = self._find_closest_base_event(active_time, base_schedule)
            if closest_base:
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
        base_schedule: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            active_schedule: Active adaptive schedule
            base_schedule: Base schedule
            
        Returns:
            Formatted report string
        """
        comparison = self.compare_with_base(active_schedule, base_schedule)
        
        report_lines = [
            "=" * 80,
            "ACTIVE ADAPTIVE SCHEDULE VALIDATION REPORT",
            "=" * 80,
            "",
            f"Active Schedule Events: {comparison['active_event_count']}",
            f"Base Schedule Events: {comparison['base_event_count']}",
            f"Event Count Difference: {comparison['event_count_diff']} ({comparison['event_count_diff_percent']:.1f}%)",
            ""
        ]
        
        if comparison["warnings"]:
            report_lines.append("WARNINGS:")
            report_lines.append("-" * 80)
            for warning in comparison["warnings"]:
                report_lines.append(f"  ⚠ {warning}")
            report_lines.append("")
        
        if comparison["deviations"]:
            report_lines.append("FLAGGED DEVIATIONS (>50% difference):")
            report_lines.append("-" * 80)
            for dev in comparison["deviations"]:
                report_lines.append(
                    f"  {dev['active_time']}: {dev['active_wait']:.1f} min "
                    f"(base: {dev['base_wait']:.1f} min, {dev['deviation_percent']:.1f}% diff)"
                )
            report_lines.append("")
        
        if comparison["matches"]:
            report_lines.append(f"MATCHES ({len(comparison['matches'])} events within threshold):")
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

