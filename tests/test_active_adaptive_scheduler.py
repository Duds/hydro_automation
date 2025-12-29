"""Tests for adaptive scheduler.

Updated to use the new AdaptiveScheduler that implements IScheduler.
"""

import pytest
import threading
import time
from datetime import datetime, time as dt_time
from unittest.mock import Mock, MagicMock, patch, call

from src.schedulers.adaptive_scheduler import AdaptiveScheduler
from src.services.device_service import DeviceRegistry, IDeviceService
from src.services.environmental_service import EnvironmentalService


class TestAdaptiveScheduler:
    """Test suite for AdaptiveScheduler."""

    @pytest.fixture
    def mock_device(self):
        """Create a mock device service."""
        device = Mock(spec=IDeviceService)
        device.get_device_info.return_value = Mock(device_id="pump1", name="Test Pump", brand="tapo", model="P100", ip_address="192.168.1.100")
        device.connect.return_value = True
        device.turn_on.return_value = True
        device.turn_off.return_value = True
        device.is_device_on.return_value = False
        device.is_connected.return_value = True
        device.close.return_value = None
        return device

    @pytest.fixture
    def mock_device_registry(self, mock_device):
        """Create a mock device registry."""
        registry = Mock(spec=DeviceRegistry)
        registry.get_device.return_value = mock_device
        registry.get_all_devices.return_value = [mock_device]
        return registry

    @pytest.fixture
    def mock_env_service(self):
        """Create a mock environmental service."""
        from src.data.daylight import DaylightCalculator
        
        service = Mock()
        # Configure methods to return actual values, not Mock objects
        service.get_temperature = Mock(return_value=22.0)
        service.get_humidity = Mock(return_value=60.0)
        service.get_daylight_info = Mock(return_value={
            "sunrise": "06:00",
            "sunset": "18:00",
            "day_length_hours": 12.0
        })
        
        # For temperature/humidity at time - return numeric values
        service.get_temperature_at_time = Mock(return_value=22.0)
        service.get_humidity_at_time = Mock(return_value=60.0)
        service.last_temperature = 22.0
        service.last_humidity = 60.0
        
        # Add daylight_calc for schedule generation
        daylight_calc = Mock()
        daylight_calc.get_sunrise_sunset = Mock(return_value=(dt_time(6, 0), dt_time(18, 0)))
        service.daylight_calc = daylight_calc
        return service

    @pytest.fixture
    def basic_config(self):
        """Create basic adaptation config."""
        return {
            "enabled": True,
            "adaptive": {
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
            }
        }

    def test_initialization(self, mock_device_registry, mock_env_service, basic_config):
        """Test adaptive scheduler initialization."""
        scheduler = AdaptiveScheduler(
            device_registry=mock_device_registry,
            device_id="pump1",
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            env_service=mock_env_service
        )
        
        assert scheduler is not None
        assert scheduler.device_id == "pump1"
        assert scheduler.flood_duration_minutes == 2.0
        assert scheduler.enabled is True

    def test_initialization_disabled(self, mock_device_registry, mock_env_service):
        """Test adaptive scheduler initialization when disabled."""
        config = {"enabled": False}
        scheduler = AdaptiveScheduler(
            device_registry=mock_device_registry,
            device_id="pump1",
            flood_duration_minutes=2.0,
            adaptation_config=config,
            env_service=mock_env_service
        )
        
        assert scheduler.enabled is False

    def test_schedule_generation(self, mock_device_registry, mock_env_service, basic_config):
        """Test that schedule is generated when enabled."""
        scheduler = AdaptiveScheduler(
            device_registry=mock_device_registry,
            device_id="pump1",
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            env_service=mock_env_service
        )
        
        # Should have generated cycles
        assert len(scheduler.adapted_cycles) > 0

    def test_start_stop(self, mock_device_registry, mock_env_service, basic_config):
        """Test starting and stopping the scheduler."""
        scheduler = AdaptiveScheduler(
            device_registry=mock_device_registry,
            device_id="pump1",
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            env_service=mock_env_service
        )
        
        # Start scheduler
        scheduler.start()
        assert scheduler.is_running() is True
        
        # Stop scheduler
        scheduler.stop()
        assert scheduler.is_running() is False

    def test_get_status(self, mock_device_registry, mock_env_service, basic_config):
        """Test getting scheduler status."""
        scheduler = AdaptiveScheduler(
            device_registry=mock_device_registry,
            device_id="pump1",
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            env_service=mock_env_service
        )
        
        status = scheduler.get_status()
        assert isinstance(status, dict)
        assert "next_event_time" in status or "state" in status

    def test_get_state(self, mock_device_registry, mock_env_service, basic_config):
        """Test getting scheduler state."""
        scheduler = AdaptiveScheduler(
            device_registry=mock_device_registry,
            device_id="pump1",
            flood_duration_minutes=2.0,
            adaptation_config=basic_config,
            env_service=mock_env_service
        )
        
        state = scheduler.get_state()
        assert isinstance(state, str)
        assert state in ["idle", "running", "stopped"]
