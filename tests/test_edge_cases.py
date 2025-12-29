"""Tests for edge cases and error conditions."""

import pytest
from unittest.mock import Mock, patch
from datetime import time as dt_time

from src.schedulers.time_based_scheduler import TimeBasedScheduler
from src.services.device_service import DeviceRegistry


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def mock_device_registry(self):
        """Create a mock device registry."""
        registry = Mock(spec=DeviceRegistry)
        mock_device = Mock()
        mock_device.get_device_info.return_value = Mock()
        registry.get_device.return_value = mock_device
        return registry

    def test_empty_cycles_list(self, mock_device_registry):
        """Test that empty cycles list raises error."""
        with pytest.raises(ValueError, match="At least one valid cycle must be provided"):
            TimeBasedScheduler(mock_device_registry, "device1", [], logger=Mock())

    def test_all_invalid_cycles(self, mock_device_registry):
        """Test that all invalid cycles raise error."""
        cycles = [
            {"on_time": "invalid", "off_duration_minutes": 18},
            {"on_time": "also_invalid", "off_duration_minutes": 18},
            {"on_time": "25:99", "off_duration_minutes": 18}
        ]
        with pytest.raises(ValueError, match="At least one valid cycle must be provided"):
            TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())

    def test_single_scheduled_cycle(self, mock_device_registry):
        """Test scheduler with only one scheduled cycle."""
        cycles = [{"on_time": "12:00", "off_duration_minutes": 28}]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        
        assert len(scheduler.cycles) == 1
        assert scheduler.cycles[0]["on_time"] == dt_time(12, 0)
        
        # Next time should wrap to same time tomorrow
        next_time = scheduler._get_next_on_time(dt_time(13, 0))
        assert next_time == dt_time(12, 0)

    def test_very_short_flood_duration(self, mock_device_registry):
        """Test scheduler with very short flood duration."""
        cycles = [{"on_time": "12:00", "off_duration_minutes": 28}]
        scheduler = TimeBasedScheduler(
            mock_device_registry,
            "device1",
            cycles,
            flood_duration_minutes=0.01,  # 0.6 seconds
            logger=Mock()
        )
        
        assert scheduler.flood_duration_minutes == 0.01

    def test_very_long_flood_duration(self, mock_device_registry):
        """Test scheduler with very long flood duration."""
        cycles = [{"on_time": "12:00", "off_duration_minutes": 28}]
        scheduler = TimeBasedScheduler(
            mock_device_registry,
            "device1",
            cycles,
            flood_duration_minutes=120.0,  # 2 hours
            logger=Mock()
        )
        
        assert scheduler.flood_duration_minutes == 120.0

    def test_zero_off_duration(self, mock_device_registry):
        """Test scheduler with zero OFF duration (continuous cycles)."""
        cycles = [
            {"on_time": "12:00", "off_duration_minutes": 0},
            {"on_time": "13:00", "off_duration_minutes": 0}
        ]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        
        assert scheduler.cycles[0]["off_duration_minutes"] == 0
        assert scheduler.cycles[1]["off_duration_minutes"] == 0

    def test_missing_on_time_in_cycle(self, mock_device_registry):
        """Test that cycles missing on_time are filtered out."""
        cycles = [
            {"off_duration_minutes": 18},  # Missing on_time
            {"on_time": "12:00", "off_duration_minutes": 28}
        ]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        
        # Should only have the valid cycle
        assert len(scheduler.cycles) == 1
        assert scheduler.cycles[0]["on_time"] == dt_time(12, 0)

    def test_missing_off_duration_defaults_to_zero(self, mock_device_registry):
        """Test that missing off_duration defaults to zero."""
        cycles = [
            {"on_time": "12:00"}  # Missing off_duration_minutes
        ]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        
        assert scheduler.cycles[0]["off_duration_minutes"] == 0
