"""Integration tests for complete system workflows."""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import time as dt_time

from src.main import HydroController
from src.schedulers.time_based_scheduler import TimeBasedScheduler


class TestIntegration:
    """Integration tests for complete workflows."""

    def _create_valid_config(self):
        """Helper to create a valid configuration dict."""
        return {
            "devices": {
                "devices": [
                    {
                        "device_id": "pump1",
                        "name": "Main Pump",
                        "brand": "tapo",
                        "ip_address": "192.168.1.100",
                        "email": "test@example.com",
                        "password": "testpass"
                    }
                ]
            },
            "growing_system": {
                "type": "flood_drain",
                "primary_device_id": "pump1"
            },
            "schedule": {
                "type": "time_based",
                "flood_duration_minutes": 2.0,
                "cycles": [
                    {"on_time": "06:00", "off_duration_minutes": 18}
                ]
            },
            "logging": {
                "log_file": "logs/test.log",
                "log_level": "INFO"
            }
        }

    def test_full_time_based_schedule_workflow(self):
        """Test complete workflow with time-based schedule initialization."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = self._create_valid_config()
            json.dump(config, f)
            config_path = f.name
        
        try:
            mock_device = Mock()
            mock_device_registry = Mock()
            mock_device_registry.get_device.return_value = mock_device
            mock_device_registry.get_all_devices.return_value = [mock_device]
            
            with patch('src.main.create_device_registry', return_value=mock_device_registry), \
                 patch('src.main.SchedulerFactory.create_scheduler') as mock_create_scheduler, \
                 patch('src.main.HydroController._setup_logging'):
                
                mock_scheduler = Mock()
                mock_create_scheduler.return_value = mock_scheduler
                
                app = HydroController(config_path)
                app.logger = Mock()
                assert app.setup() is True
                assert app.scheduler is not None
        finally:
            os.unlink(config_path)

    def test_scheduler_stops_device_on_shutdown(self):
        """Test that scheduler ensures device is off on shutdown."""
        mock_device = Mock()
        mock_device.is_connected.return_value = True
        mock_device.ensure_off.return_value = True
        mock_device.get_device_info.return_value = Mock()
        
        mock_device_registry = Mock()
        mock_device_registry.get_device.return_value = mock_device
        
        cycles = [{"on_time": "12:00", "off_duration_minutes": 28}]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        scheduler.running = True
        scheduler.stop()
        
        mock_device.ensure_off.assert_called_once()

    def test_schedule_wraps_around_midnight(self):
        """Test that schedule correctly handles midnight wrap-around."""
        mock_device_registry = Mock()
        mock_device_registry.get_device.return_value = Mock()
        mock_device_registry.get_device.return_value.get_device_info.return_value = Mock()
        
        cycles = [
            {"on_time": "22:00", "off_duration_minutes": 118},
            {"on_time": "00:00", "off_duration_minutes": 118}
        ]
        scheduler = TimeBasedScheduler(
            mock_device_registry,
            "device1",
            cycles,
            logger=Mock()
        )
        
        # Times should be sorted correctly
        assert scheduler.cycles[0]["on_time"] == dt_time(0, 0)
        assert scheduler.cycles[1]["on_time"] == dt_time(22, 0)
        
        # Test next time calculation at 23:00
        next_time = scheduler._get_next_on_time(dt_time(23, 0))
        assert next_time == dt_time(0, 0)  # Should wrap to midnight
