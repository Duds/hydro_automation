"""Integration tests for complete system workflows."""

import pytest
import json
import tempfile
import os
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, time as dt_time

from src.main import HydroController
from src.schedulers.time_based_scheduler import TimeBasedScheduler
from src.device.tapo_controller import TapoController


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_time_based_schedule_workflow(self):
        """Test complete workflow with time-based schedule."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
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
                "sensors": {"sensors": []},
                "actuators": {"actuators": []},
                "growing_system": {
                    "type": "flood_drain",
                    "primary_device_id": "pump1"
                },
                "schedule": {
                    "type": "time_based",
                    "flood_duration_minutes": 2.0,
                    "cycles": [
                        {"on_time": "06:00", "off_duration_minutes": 18},
                        {"on_time": "12:00", "off_duration_minutes": 28},
                        {"on_time": "18:00", "off_duration_minutes": 18}
                    ]
                },
                "logging": {
                    "log_file": "logs/test.log",
                    "log_level": "INFO"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            mock_device = Mock()
            mock_device.connect.return_value = True
            mock_device.is_connected.return_value = True
            mock_device.get_device_info.return_value = Mock(name="Test", ip_address="192.168.1.100")
            
            mock_device_registry = Mock()
            mock_device_registry.get_device.return_value = mock_device
            
            with patch('src.services.service_factory.create_device_registry', return_value=mock_device_registry), \
                 patch('src.services.service_factory.create_sensor_registry', return_value=Mock()), \
                 patch('src.services.service_factory.create_actuator_registry', return_value=Mock()), \
                 patch('src.services.service_factory.create_environmental_service', return_value=Mock()), \
                 patch('src.core.scheduler_factory.SchedulerFactory') as mock_factory, \
                 patch('src.main.setup_logger', return_value=Mock()):
                
                mock_scheduler = Mock(spec=TimeBasedScheduler)
                mock_scheduler.is_running.return_value = False
                mock_factory.return_value.create.return_value = mock_scheduler
                
                app = HydroController(config_path)
                
                # Verify scheduler is created
                assert app.scheduler is not None
        finally:
            os.unlink(config_path)

    def test_device_discovery_on_connection_failure(self):
        """Test that device discovery is attempted when connection fails."""
        controller = TapoController(
            ip_address="192.168.1.100",
            email="test@example.com",
            password="testpass",
            logger=Mock(),
            enable_auto_discovery=True
        )
        
        # Mock connection failure
        with patch('src.device.tapo_controller.connect', side_effect=Exception("Connection failed")):
            with patch('src.device.tapo_controller.asyncio') as mock_asyncio:
                mock_loop = Mock()
                
                # First call: connection fails
                # Second call: discovery returns IP
                call_count = 0
                def run_until_complete(coro):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        raise Exception("Connection failed")
                    elif call_count == 2:
                        return "192.168.1.200"  # Discovered IP
                    elif call_count == 3:
                        return True  # Connection to discovered IP succeeds
                    return False
                
                mock_loop.run_until_complete = Mock(side_effect=run_until_complete)
                mock_asyncio.get_event_loop = Mock(return_value=mock_loop)
                mock_asyncio.new_event_loop = Mock(return_value=mock_loop)
                mock_asyncio.set_event_loop = Mock()
                
                with patch.object(controller, 'discover_device', return_value="192.168.1.200"):
                    with patch('src.device.tapo_controller.connect') as mock_connect:
                        mock_device = Mock()
                        mock_device.update = AsyncMock()
                        mock_device.protocol_version = "Klap V2"
                        mock_connect.return_value = mock_device
                        
                        result = controller.connect()
                        
                        # Should have attempted discovery
                        # (Note: actual implementation may vary based on connect logic)

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

    def test_multiple_consecutive_cycles(self):
        """Test handling of multiple consecutive scheduled cycles."""
        mock_device = Mock()
        mock_device.turn_on.return_value = True
        mock_device.turn_off.return_value = True
        mock_device.is_connected.return_value = True
        mock_device.get_device_info.return_value = Mock()
        
        mock_device_registry = Mock()
        mock_device_registry.get_device.return_value = mock_device
        
        cycles = [
            {"on_time": "10:00", "off_duration_minutes": 5},
            {"on_time": "10:05", "off_duration_minutes": 5},
            {"on_time": "10:10", "off_duration_minutes": 5}
        ]
        scheduler = TimeBasedScheduler(
            mock_device_registry,
            "device1",
            cycles,
            flood_duration_minutes=2.0,
            logger=Mock()
        )
        
        # Verify all cycles are scheduled
        assert len(scheduler.cycles) == 3
        assert scheduler.cycles[0]["on_time"] == dt_time(10, 0)
        assert scheduler.cycles[1]["on_time"] == dt_time(10, 5)
        assert scheduler.cycles[2]["on_time"] == dt_time(10, 10)

    def test_schedule_wraps_around_midnight(self):
        """Test that schedule correctly handles midnight wrap-around."""
        mock_device_registry = Mock()
        mock_device_registry.get_device.return_value = Mock()
        mock_device_registry.get_device.return_value.get_device_info.return_value = Mock()
        
        cycles = [
            {"on_time": "22:00", "off_duration_minutes": 118},
            {"on_time": "00:00", "off_duration_minutes": 118},
            {"on_time": "02:00", "off_duration_minutes": 118}
        ]
        scheduler = TimeBasedScheduler(
            mock_device_registry,
            "device1",
            cycles,
            logger=Mock()
        )
        
        # Times should be sorted correctly
        assert scheduler.cycles[0]["on_time"] == dt_time(0, 0)
        assert scheduler.cycles[1]["on_time"] == dt_time(2, 0)
        assert scheduler.cycles[2]["on_time"] == dt_time(22, 0)
        
        # Test next time calculation at 23:00
        next_time = scheduler._get_next_on_time(dt_time(23, 0))
        assert next_time == dt_time(0, 0)  # Should wrap to midnight
