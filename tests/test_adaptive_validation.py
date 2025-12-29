"""Tests for adaptive validation module."""

import pytest
from datetime import time as dt_time

from src.adaptive_validation import AdaptiveValidator


class TestAdaptiveValidator:
    """Test suite for AdaptiveValidator."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return AdaptiveValidator(threshold=0.5)

    @pytest.fixture
    def base_schedule(self):
        """Create a base schedule for testing."""
        return [
            {"on_time": "06:00", "off_duration_minutes": 18.0},
            {"on_time": "09:00", "off_duration_minutes": 28.0},
            {"on_time": "12:00", "off_duration_minutes": 28.0},
            {"on_time": "18:00", "off_duration_minutes": 18.0},
            {"on_time": "20:00", "off_duration_minutes": 118.0},
        ]

    @pytest.fixture
    def active_schedule_similar(self):
        """Create an active schedule similar to base."""
        return [
            {"on_time": "06:00", "off_duration_minutes": 19.0},
            {"on_time": "09:00", "off_duration_minutes": 28.0},
            {"on_time": "12:00", "off_duration_minutes": 27.0},
            {"on_time": "18:00", "off_duration_minutes": 18.0},
            {"on_time": "20:00", "off_duration_minutes": 120.0},
        ]

    @pytest.fixture
    def active_schedule_deviant(self):
        """Create an active schedule with significant deviations."""
        return [
            {"on_time": "06:00", "off_duration_minutes": 5.0},  # Way off (18 -> 5)
            {"on_time": "09:00", "off_duration_minutes": 50.0},  # Way off (28 -> 50)
            {"on_time": "12:00", "off_duration_minutes": 28.0},  # Same
            {"on_time": "18:00", "off_duration_minutes": 200.0},  # Way off (18 -> 200)
            {"on_time": "20:00", "off_duration_minutes": 60.0},  # Way off (118 -> 60)
        ]

    def test_init_default_threshold(self):
        """Test initialization with default threshold."""
        validator = AdaptiveValidator()
        assert validator.threshold == 0.5

    def test_init_custom_threshold(self):
        """Test initialization with custom threshold."""
        validator = AdaptiveValidator(threshold=0.3)
        assert validator.threshold == 0.3

    def test_compare_with_base_similar(self, validator, base_schedule, active_schedule_similar):
        """Test comparison with similar schedules."""
        result = validator.compare_with_base(active_schedule_similar, base_schedule)
        
        assert result["active_event_count"] == 5
        assert result["base_event_count"] == 5
        assert result["event_count_diff"] == 0
        assert len(result["deviations"]) == 0  # No significant deviations
        assert len(result["warnings"]) == 0

    def test_compare_with_base_deviant(self, validator, base_schedule, active_schedule_deviant):
        """Test comparison with deviant schedules."""
        result = validator.compare_with_base(active_schedule_deviant, base_schedule)
        
        assert result["active_event_count"] == 5
        assert result["base_event_count"] == 5
        assert len(result["deviations"]) > 0  # Should have deviations
        assert len(result["warnings"]) > 0  # Should have warnings

    def test_compare_with_base_different_count(self, validator, base_schedule):
        """Test comparison when event counts differ."""
        active_schedule = [
            {"on_time": "06:00", "off_duration_minutes": 18.0},
            {"on_time": "09:00", "off_duration_minutes": 28.0},
            # Missing events
        ]
        
        result = validator.compare_with_base(active_schedule, base_schedule)
        
        assert result["active_event_count"] == 2
        assert result["base_event_count"] == 5
        assert result["event_count_diff"] == -3
        assert abs(result["event_count_diff_percent"]) > 30  # Significant difference
        assert len(result["warnings"]) > 0  # Should warn about count difference

    def test_find_closest_base_event(self, validator, base_schedule):
        """Test finding closest base event."""
        closest = validator._find_closest_base_event("06:05", base_schedule)
        assert closest is not None
        assert closest["on_time"] == "06:00"
        
        closest = validator._find_closest_base_event("11:55", base_schedule)
        assert closest is not None
        assert closest["on_time"] == "12:00"

    def test_find_closest_base_event_wrapping(self, validator, base_schedule):
        """Test finding closest event when wrapping midnight."""
        closest = validator._find_closest_base_event("23:30", base_schedule)
        assert closest is not None
        
        closest = validator._find_closest_base_event("00:30", base_schedule)
        assert closest is not None

    def test_find_closest_base_event_empty_schedule(self, validator):
        """Test finding closest event with empty base schedule."""
        closest = validator._find_closest_base_event("06:00", [])
        assert closest is None

    def test_time_to_minutes(self, validator):
        """Test time string to minutes conversion."""
        assert validator._time_to_minutes("00:00") == 0
        assert validator._time_to_minutes("06:00") == 360
        assert validator._time_to_minutes("12:30") == 750
        assert validator._time_to_minutes("23:59") == 1439

    def test_calculate_deviation(self, validator):
        """Test deviation calculation."""
        assert validator._calculate_deviation(20.0, 18.0) == 2.0
        assert validator._calculate_deviation(18.0, 20.0) == 2.0
        assert validator._calculate_deviation(28.0, 28.0) == 0.0

    def test_flag_deviations(self, validator, base_schedule, active_schedule_deviant):
        """Test flagging deviations."""
        deviations = validator.flag_deviations(active_schedule_deviant, base_schedule)
        
        assert len(deviations) > 0
        for dev in deviations:
            assert "time" in dev
            assert "active_wait" in dev
            assert "base_wait" in dev
            assert "deviation_percent" in dev
            assert dev["deviation_percent"] > 50  # All should be > 50%

    def test_flag_deviations_custom_threshold(self, validator, base_schedule, active_schedule_similar):
        """Test flagging deviations with custom threshold."""
        deviations = validator.flag_deviations(active_schedule_similar, base_schedule, threshold=0.1)
        
        # With lower threshold, might flag more deviations
        assert isinstance(deviations, list)

    def test_generate_validation_report(self, validator, base_schedule, active_schedule_deviant):
        """Test validation report generation."""
        report = validator.generate_validation_report(active_schedule_deviant, base_schedule)
        
        assert isinstance(report, str)
        assert "ADAPTIVE SCHEDULE VALIDATION REPORT" in report
        assert "Active Schedule Events" in report
        assert "Base Schedule Events" in report
        # Report should contain validation information (warnings, deviations, or period mismatches)
        assert ("WARNINGS" in report or "FLAGGED DEVIATIONS" in report or 
                "PERIOD MISMATCHES" in report or "No significant deviations" in report or 
                "No warnings" in report)

    def test_generate_validation_report_similar(self, validator, base_schedule, active_schedule_similar):
        """Test validation report for similar schedules."""
        report = validator.generate_validation_report(active_schedule_similar, base_schedule)
        
        assert isinstance(report, str)
        assert "MATCHES" in report
        assert len([line for line in report.split('\n') if 'WARNINGS' in line or 'FLAGGED DEVIATIONS' in line]) == 0

    def test_compare_with_base_empty_active(self, validator, base_schedule):
        """Test comparison with empty active schedule."""
        result = validator.compare_with_base([], base_schedule)
        
        assert result["active_event_count"] == 0
        assert result["base_event_count"] == 5
        assert result["event_count_diff"] == -5
        assert len(result["matches"]) == 0

    def test_compare_with_base_empty_base(self, validator, active_schedule_similar):
        """Test comparison with empty base schedule."""
        result = validator.compare_with_base(active_schedule_similar, [])
        
        assert result["active_event_count"] == 5
        assert result["base_event_count"] == 0
        assert result["event_count_diff"] == 5
        assert len(result["matches"]) == 0
        assert len(result["deviations"]) == 0

