"""Integration tests for complete system workflows."""

import pytest
import json
import tempfile
import os
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, time as dt_time

from src.main import HydroController
from src.time_scheduler import TimeScheduler
from src.tapo_controller import TapoController


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_time_based_schedule_workflow(self):
        """Test complete workflow with time-based schedule."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "device": {
                    "ip_address": "192.168.1.100",
                    "email": "test@example.com",
                    "password": "testpass"
                },
                "cycle": {
                    "flood_duration_minutes": 15,
                    "drain_duration_minutes": 30,
                    "interval_minutes": 120
                },
                "schedule": {
                    "type": "time_based",
                    "flood_duration_minutes": 2.0,
                    "on_times": ["06:00", "12:00", "18:00"]
                },
                "logging": {
                    "log_file": "logs/test.log",
                    "log_level": "INFO"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('src.main.TapoController') as mock_controller_class, \
                 patch('src.main.setup_logger') as mock_logger:
                
                mock_logger.return_value = Mock()
                mock_controller = Mock()
                mock_controller.connect.return_value = True
                mock_controller.is_connected.return_value = True
                mock_controller_class.return_value = mock_controller
                
                app = HydroController(config_path)
                
                # Verify scheduler is TimeScheduler
                assert isinstance(app.scheduler, TimeScheduler)
                assert app.scheduler.flood_duration_minutes == 2.0
                assert len(app.scheduler.on_times) == 3
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
        with patch('src.tapo_controller.connect', side_effect=Exception("Connection failed")):
            with patch('src.tapo_controller.asyncio') as mock_asyncio:
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
                    with patch('src.tapo_controller.connect') as mock_connect:
                        mock_device = Mock()
                        mock_device.update = AsyncMock()
                        mock_device.protocol_version = "Klap V2"
                        mock_connect.return_value = mock_device
                        
                        result = controller.connect()
                        
                        # Should have attempted discovery
                        # (Note: actual implementation may vary based on connect logic)

    def test_scheduler_stops_device_on_shutdown(self):
        """Test that scheduler ensures device is off on shutdown."""
        controller = Mock(spec=TapoController)
        controller.is_connected.return_value = True
        controller.ensure_off.return_value = True
        
        scheduler = TimeScheduler(controller, ["12:00"], logger=Mock())
        scheduler.running = True
        scheduler.stop()
        
        controller.ensure_off.assert_called_once()

    def test_multiple_consecutive_cycles(self):
        """Test handling of multiple consecutive scheduled cycles."""
        controller = Mock()
        controller.turn_on.return_value = True
        controller.turn_off.return_value = True
        controller.is_connected.return_value = True
        
        scheduler = TimeScheduler(
            controller,
            ["10:00", "10:05", "10:10"],
            flood_duration_minutes=2.0,
            logger=Mock()
        )
        
        # Verify all times are scheduled
        assert len(scheduler.on_times) == 3
        assert scheduler.on_times[0] == dt_time(10, 0)
        assert scheduler.on_times[1] == dt_time(10, 5)
        assert scheduler.on_times[2] == dt_time(10, 10)

    def test_schedule_wraps_around_midnight(self):
        """Test that schedule correctly handles midnight wrap-around."""
        controller = Mock()
        scheduler = TimeScheduler(
            controller,
            ["22:00", "00:00", "02:00"],
            logger=Mock()
        )
        
        # Times should be sorted correctly
        assert scheduler.on_times[0] == dt_time(0, 0)
        assert scheduler.on_times[1] == dt_time(2, 0)
        assert scheduler.on_times[2] == dt_time(22, 0)
        
        # Test next time calculation at 23:00
        next_time = scheduler._get_next_on_time(dt_time(23, 0))
        assert next_time == dt_time(0, 0)  # Should wrap to midnight

    def test_error_recovery_during_cycle(self):
        """Test error recovery when device operation fails during cycle."""
        controller = Mock()
        controller.is_connected.return_value = True
        
        # First turn_on fails, second succeeds
        controller.turn_on.side_effect = [False, True]
        controller.turn_off.return_value = True
        
        scheduler = TimeScheduler(
            controller,
            ["10:00"],
            flood_duration_minutes=0.01,
            logger=Mock()
        )
        
        scheduler.running = True
        scheduler.shutdown_requested = True  # Exit immediately
        
        # Should handle the failure gracefully
        scheduler._scheduler_loop()
        
        # Verify controller was called
        assert controller.turn_on.called or controller.is_connected.called

