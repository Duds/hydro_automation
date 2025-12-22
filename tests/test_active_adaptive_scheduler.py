"""Tests for active adaptive scheduler."""

import pytest
import threading
import time
from datetime import datetime, time as dt_time
from unittest.mock import Mock, MagicMock, patch, call

from src.active_adaptive_scheduler import ActiveAdaptiveScheduler
from src.tapo_controller import TapoController


class TestActiveAdaptiveScheduler:
    """Test suite for ActiveAdaptiveScheduler."""

    @pytest.fixture
    def mock_controller(self):
        """Create a mock TapoController."""
        controller = Mock(spec=TapoController)
        controller.turn_on = Mock(return_value=True)
        controller.turn_off = Mock(return_value=True)
        controller.get_state = Mock(return_value="off")
        return controller

    @pytest.fixture
    def basic_config(self):
        """Create basic adaptation config."""
        return {
            "active_adaptive": {
                "enabled": True,
                "tod_frequencies": {
                    "morning": 18.0,
                    "day": 28.0,
                    "evening": 18.0,
                    "night": 118.0
                },
                "temperature_bands": {
                    "cold": {"max": 15, "factor": 1.15},
                    "normal": {"min": 15, "max": 25, "factor": 1.0},
                    "warm": {"min": 25, "max": 30, "factor": 0.85},
                    "hot": {"min": 30, "factor": 0.70}
                },
                "humidity_bands": {
                    "low": {"max": 40, "factor": 0.9},
                    "normal": {"min": 40, "max": 70, "factor": 1.0},
                    "high": {"min": 70, "factor": 1.1}
                },
                "constraints": {
                    "min_wait_duration": 5,
                    "max_wait_duration": 180,
                    "min_flood_duration": 2,
                    "max_flood_duration": 15
                }
            },
            "location": {
                "postcode": "2617",
                "timezone": "Australia/Sydney"
            },
            "temperature": {
                "enabled": False
            }
        }

    def test_init_disabled(self, mock_controller, basic_config):
        """Test initialization with active adaptive disabled."""
        basic_config["active_adaptive"]["enabled"] = False
        scheduler = ActiveAdaptiveScheduler(
            controller=mock_controller,
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            logger=Mock()
        )
        
        assert not scheduler.enabled
        assert len(scheduler.adapted_cycles) == 0

    def test_calculate_tod_base_frequency(self, mock_controller, basic_config):
        """Test ToD base frequency calculation."""
        scheduler = ActiveAdaptiveScheduler(
            controller=mock_controller,
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            logger=Mock()
        )
        
        assert scheduler.calculate_tod_base_frequency("morning") == 18.0
        assert scheduler.calculate_tod_base_frequency("day") == 28.0
        assert scheduler.calculate_tod_base_frequency("evening") == 18.0
        assert scheduler.calculate_tod_base_frequency("night") == 118.0
        assert scheduler.calculate_tod_base_frequency("unknown") == 28.0  # Default

    def test_get_temperature_factor(self, mock_controller, basic_config):
        """Test temperature factor calculation."""
        scheduler = ActiveAdaptiveScheduler(
            controller=mock_controller,
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            logger=Mock()
        )
        
        # Cold
        assert scheduler.get_temperature_factor(10) == 1.15
        assert scheduler.get_temperature_factor(14) == 1.15
        
        # Normal
        assert scheduler.get_temperature_factor(15) == 1.0
        assert scheduler.get_temperature_factor(20) == 1.0
        assert scheduler.get_temperature_factor(24) == 1.0
        
        # Warm
        assert scheduler.get_temperature_factor(25) == 0.85
        assert scheduler.get_temperature_factor(29) == 0.85
        
        # Hot
        assert scheduler.get_temperature_factor(30) == 0.70
        assert scheduler.get_temperature_factor(35) == 0.70
        
        # None
        assert scheduler.get_temperature_factor(None) == 1.0

    def test_get_humidity_factor(self, mock_controller, basic_config):
        """Test humidity factor calculation."""
        scheduler = ActiveAdaptiveScheduler(
            controller=mock_controller,
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            logger=Mock()
        )
        
        # Low
        assert scheduler.get_humidity_factor(30) == 0.9
        assert scheduler.get_humidity_factor(39) == 0.9
        
        # Normal
        assert scheduler.get_humidity_factor(40) == 1.0
        assert scheduler.get_humidity_factor(50) == 1.0
        assert scheduler.get_humidity_factor(69) == 1.0
        
        # High
        assert scheduler.get_humidity_factor(70) == 1.1
        assert scheduler.get_humidity_factor(85) == 1.1
        
        # None
        assert scheduler.get_humidity_factor(None) == 1.0

    def test_apply_constraints(self, mock_controller, basic_config):
        """Test system constraint application."""
        scheduler = ActiveAdaptiveScheduler(
            controller=mock_controller,
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            logger=Mock()
        )
        
        events = [
            {"on_time": "06:00", "off_duration_minutes": 3},  # Below min
            {"on_time": "10:00", "off_duration_minutes": 50},  # Normal
            {"on_time": "14:00", "off_duration_minutes": 200},  # Above max
        ]
        
        constrained = scheduler._apply_constraints(events)
        
        assert constrained[0]["off_duration_minutes"] == 5  # Min applied
        assert constrained[1]["off_duration_minutes"] == 50  # No change
        assert constrained[2]["off_duration_minutes"] == 180  # Max applied

    @patch('src.active_adaptive_scheduler.DaylightCalculator')
    @patch('src.active_adaptive_scheduler.BOMTemperature')
    def test_generate_schedule_basic(self, mock_bom, mock_daylight, mock_controller, basic_config):
        """Test basic schedule generation."""
        # Mock daylight calculator
        mock_daylight_instance = Mock()
        mock_daylight_instance.get_sunrise_sunset.return_value = (dt_time(6, 0), dt_time(18, 0))
        mock_daylight.return_value = mock_daylight_instance
        
        # Mock BOM temperature
        mock_bom_instance = Mock()
        mock_bom_instance.get_temperature_at_time.return_value = 20.0
        mock_bom_instance.get_humidity_at_time.return_value = 50.0
        mock_bom.return_value = mock_bom_instance
        
        basic_config["temperature"]["enabled"] = True
        basic_config["temperature"]["station_id"] = "94926"
        
        scheduler = ActiveAdaptiveScheduler(
            controller=mock_controller,
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            logger=Mock()
        )
        
        assert scheduler.enabled
        assert len(scheduler.adapted_cycles) > 0
        
        # Verify cycles have required fields
        for cycle in scheduler.adapted_cycles:
            assert "on_time" in cycle
            assert "off_duration_minutes" in cycle
            assert cycle["off_duration_minutes"] >= 5
            assert cycle["off_duration_minutes"] <= 180

    def test_get_adapted_cycles(self, mock_controller, basic_config):
        """Test getting adapted cycles."""
        basic_config["active_adaptive"]["enabled"] = False
        scheduler = ActiveAdaptiveScheduler(
            controller=mock_controller,
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            logger=Mock()
        )
        
        cycles = scheduler.get_adapted_cycles()
        assert isinstance(cycles, list)
        # Should return a copy, not the original
        cycles.append({"test": "data"})
        assert len(scheduler.adapted_cycles) == len(cycles) - 1

    def test_time_to_minutes(self, mock_controller, basic_config):
        """Test time string to minutes conversion."""
        scheduler = ActiveAdaptiveScheduler(
            controller=mock_controller,
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            logger=Mock()
        )
        
        assert scheduler._time_to_minutes("00:00") == 0
        assert scheduler._time_to_minutes("06:00") == 360
        assert scheduler._time_to_minutes("12:30") == 750
        assert scheduler._time_to_minutes("23:59") == 1439

    def test_get_time_period(self, mock_controller, basic_config):
        """Test time period determination."""
        scheduler = ActiveAdaptiveScheduler(
            controller=mock_controller,
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            logger=Mock()
        )
        
        # Morning
        assert scheduler._get_time_period(dt_time(6, 0)) == "morning"
        assert scheduler._get_time_period(dt_time(8, 30)) == "morning"
        
        # Day
        assert scheduler._get_time_period(dt_time(9, 0)) == "day"
        assert scheduler._get_time_period(dt_time(12, 0)) == "day"
        assert scheduler._get_time_period(dt_time(17, 30)) == "day"
        
        # Evening
        assert scheduler._get_time_period(dt_time(18, 0)) == "evening"
        assert scheduler._get_time_period(dt_time(19, 30)) == "evening"
        
        # Night
        assert scheduler._get_time_period(dt_time(20, 0)) == "night"
        assert scheduler._get_time_period(dt_time(23, 0)) == "night"
        assert scheduler._get_time_period(dt_time(0, 0)) == "night"
        assert scheduler._get_time_period(dt_time(5, 0)) == "night"

    def test_start_stop(self, mock_controller, basic_config):
        """Test scheduler start and stop."""
        basic_config["active_adaptive"]["enabled"] = False
        scheduler = ActiveAdaptiveScheduler(
            controller=mock_controller,
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            logger=Mock()
        )
        
        scheduler.start()
        assert scheduler.running
        assert scheduler.base_scheduler.is_running()
        
        scheduler.stop()
        assert not scheduler.running

    def test_update_schedule_when_disabled(self, mock_controller, basic_config):
        """Test schedule update when disabled."""
        basic_config["active_adaptive"]["enabled"] = False
        scheduler = ActiveAdaptiveScheduler(
            controller=mock_controller,
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            logger=Mock()
        )
        
        initial_count = len(scheduler.adapted_cycles)
        scheduler._update_schedule()
        # Should not change when disabled
        assert len(scheduler.adapted_cycles) == initial_count


class TestActiveAdaptiveSchedulerIntegration:
    """Integration tests for ActiveAdaptiveScheduler."""

    @pytest.fixture
    def mock_controller(self):
        """Create a mock TapoController."""
        controller = Mock(spec=TapoController)
        controller.turn_on = Mock(return_value=True)
        controller.turn_off = Mock(return_value=True)
        controller.get_state = Mock(return_value="off")
        return controller

    @pytest.fixture
    def full_config(self):
        """Create full adaptation config with all features."""
        return {
            "active_adaptive": {
                "enabled": True,
                "tod_frequencies": {
                    "morning": 18.0,
                    "day": 28.0,
                    "evening": 18.0,
                    "night": 118.0
                },
                "temperature_bands": {
                    "cold": {"max": 15, "factor": 1.15},
                    "normal": {"min": 15, "max": 25, "factor": 1.0},
                    "warm": {"min": 25, "max": 30, "factor": 0.85},
                    "hot": {"min": 30, "factor": 0.70}
                },
                "humidity_bands": {
                    "low": {"max": 40, "factor": 0.9},
                    "normal": {"min": 40, "max": 70, "factor": 1.0},
                    "high": {"min": 70, "factor": 1.1}
                },
                "constraints": {
                    "min_wait_duration": 5,
                    "max_wait_duration": 180,
                    "min_flood_duration": 2,
                    "max_flood_duration": 15
                }
            },
            "location": {
                "postcode": "2617",
                "timezone": "Australia/Sydney"
            },
            "temperature": {
                "enabled": True,
                "source": "bom",
                "station_id": "94926",
                "update_interval_minutes": 60
            }
        }

    @patch('src.active_adaptive_scheduler.DaylightCalculator')
    @patch('src.active_adaptive_scheduler.BOMTemperature')
    def test_full_schedule_generation(self, mock_bom, mock_daylight, mock_controller, full_config):
        """Test full schedule generation with all factors."""
        # Mock daylight calculator
        mock_daylight_instance = Mock()
        mock_daylight_instance.location_info = Mock()
        mock_daylight_instance.location_info.latitude = -35.3
        mock_daylight_instance.location_info.longitude = 149.2
        mock_daylight_instance.get_sunrise_sunset.return_value = (dt_time(6, 0), dt_time(18, 0))
        mock_daylight.return_value = mock_daylight_instance
        
        # Mock BOM temperature
        mock_bom_instance = Mock()
        mock_bom_instance.station_name = "Canberra"
        mock_bom_instance.find_nearest_station.return_value = "94926"
        mock_bom_instance.get_temperature_at_time.return_value = 22.0
        mock_bom_instance.get_humidity_at_time.return_value = 55.0
        mock_bom_instance.fetch_temperature.return_value = 22.0
        mock_bom.return_value = mock_bom_instance
        
        scheduler = ActiveAdaptiveScheduler(
            controller=mock_controller,
            flood_duration_minutes=2.0,
            adaptation_config=full_config,
            logger=Mock()
        )
        
        assert scheduler.enabled
        assert len(scheduler.adapted_cycles) > 0
        
        # Verify all cycles are valid
        for cycle in scheduler.adapted_cycles:
            assert "on_time" in cycle
            assert "off_duration_minutes" in cycle
            assert 5 <= cycle["off_duration_minutes"] <= 180

