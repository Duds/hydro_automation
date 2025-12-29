"""Tests for main application and configuration handling."""

import pytest
import json
import sys
import signal
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from src.main import HydroController


class TestMainApplication:
    """Test suite for main application."""

    def test_load_config_valid(self):
        """Test loading valid configuration file."""
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
                            "password": "testpass",
                            "auto_discovery": True
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
                    "type": "interval",
                    "enabled": True,
                    "flood_duration_minutes": 15,
                    "drain_duration_minutes": 30,
                    "interval_minutes": 120,
                    "active_hours": {
                        "start": "06:00",
                        "end": "22:00"
                    }
                },
                "logging": {
                    "log_file": "logs/test.log",
                    "log_level": "INFO"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('src.services.service_factory.create_device_registry') as mock_dev_reg, \
                 patch('src.services.service_factory.create_sensor_registry') as mock_sensor_reg, \
                 patch('src.services.service_factory.create_actuator_registry') as mock_actuator_reg, \
                 patch('src.services.service_factory.create_environmental_service') as mock_env_service, \
                 patch('src.core.scheduler_factory.SchedulerFactory') as mock_factory, \
                 patch('src.main.setup_logger') as mock_logger:
                
                mock_logger.return_value = Mock()
                mock_dev_reg.return_value = Mock()
                mock_sensor_reg.return_value = Mock()
                mock_actuator_reg.return_value = Mock()
                mock_env_service.return_value = Mock()
                mock_scheduler = Mock()
                mock_factory.return_value.create.return_value = mock_scheduler
                
                app = HydroController(config_path)
                assert app.scheduler is not None
        finally:
            os.unlink(config_path)

    def test_load_config_file_not_found(self):
        """Test error when configuration file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            HydroController("nonexistent.json")

    def test_load_config_invalid_json(self):
        """Test error when configuration file has invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            config_path = f.name
        
        try:
            with pytest.raises((ValueError, Exception)):  # ConfigValidationError or ValueError
                HydroController(config_path)
        finally:
            os.unlink(config_path)

    def test_load_config_time_based_schedule(self):
        """Test loading time-based schedule configuration."""
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
            with patch('src.services.service_factory.create_device_registry') as mock_dev_reg, \
                 patch('src.services.service_factory.create_sensor_registry') as mock_sensor_reg, \
                 patch('src.services.service_factory.create_actuator_registry') as mock_actuator_reg, \
                 patch('src.services.service_factory.create_environmental_service') as mock_env_service, \
                 patch('src.core.scheduler_factory.SchedulerFactory') as mock_factory, \
                 patch('src.main.setup_logger') as mock_logger:
                
                mock_logger.return_value = Mock()
                mock_dev_reg.return_value = Mock()
                mock_sensor_reg.return_value = Mock()
                mock_actuator_reg.return_value = Mock()
                mock_env_service.return_value = Mock()
                mock_scheduler = Mock()
                mock_factory.return_value.create.return_value = mock_scheduler
                
                app = HydroController(config_path)
                assert app.scheduler is not None
        finally:
            os.unlink(config_path)

    def test_load_config_interval_based_schedule(self):
        """Test loading interval-based schedule configuration."""
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
                    "type": "interval",
                    "enabled": True,
                    "flood_duration_minutes": 15,
                    "drain_duration_minutes": 30,
                    "interval_minutes": 120,
                    "active_hours": {
                        "start": "06:00",
                        "end": "22:00"
                    }
                },
                "logging": {
                    "log_file": "logs/test.log",
                    "log_level": "INFO"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('src.services.service_factory.create_device_registry') as mock_dev_reg, \
                 patch('src.services.service_factory.create_sensor_registry') as mock_sensor_reg, \
                 patch('src.services.service_factory.create_actuator_registry') as mock_actuator_reg, \
                 patch('src.services.service_factory.create_environmental_service') as mock_env_service, \
                 patch('src.core.scheduler_factory.SchedulerFactory') as mock_factory, \
                 patch('src.main.setup_logger') as mock_logger:
                
                mock_logger.return_value = Mock()
                mock_dev_reg.return_value = Mock()
                mock_sensor_reg.return_value = Mock()
                mock_actuator_reg.return_value = Mock()
                mock_env_service.return_value = Mock()
                mock_scheduler = Mock()
                mock_factory.return_value.create.return_value = mock_scheduler
                
                app = HydroController(config_path)
                assert app.scheduler is not None
        finally:
            os.unlink(config_path)

    @patch('src.main.signal.signal')
    def test_signal_handlers_registered(self, mock_signal):
        """Test that signal handlers are registered."""
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
                    "type": "interval",
                    "flood_duration_minutes": 15,
                    "drain_duration_minutes": 30,
                    "interval_minutes": 120
                },
                "logging": {
                    "log_file": "logs/test.log",
                    "log_level": "INFO"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('src.services.service_factory.create_device_registry'), \
                 patch('src.services.service_factory.create_sensor_registry'), \
                 patch('src.services.service_factory.create_actuator_registry'), \
                 patch('src.services.service_factory.create_environmental_service'), \
                 patch('src.core.scheduler_factory.SchedulerFactory'), \
                 patch('src.main.setup_logger'):
                
                app = HydroController(config_path)
                
                # Should register SIGINT and SIGTERM handlers
                assert mock_signal.call_count == 2
        finally:
            os.unlink(config_path)

    def test_start_connects_to_device(self):
        """Test that start() connects to device."""
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
                    "type": "interval",
                    "flood_duration_minutes": 15,
                    "drain_duration_minutes": 30,
                    "interval_minutes": 120
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
            mock_device_registry = Mock()
            mock_device_registry.get_device.return_value = mock_device
            mock_scheduler = Mock()
            mock_scheduler.is_running.return_value = False
            
            with patch('src.services.service_factory.create_device_registry', return_value=mock_device_registry), \
                 patch('src.services.service_factory.create_sensor_registry', return_value=Mock()), \
                 patch('src.services.service_factory.create_actuator_registry', return_value=Mock()), \
                 patch('src.services.service_factory.create_environmental_service', return_value=Mock()), \
                 patch('src.core.scheduler_factory.SchedulerFactory') as mock_factory_class, \
                 patch('src.main.setup_logger', return_value=Mock()), \
                 patch('src.main.HydroController._start_web_server'):  # Skip web server
                
                # SchedulerFactory is instantiated, so we need to mock the instance
                mock_factory_instance = Mock()
                mock_factory_instance.create.return_value = mock_scheduler
                mock_factory_class.return_value = mock_factory_instance
                
                app = HydroController(config_path)
                
                # Ensure the app has the mocked registries
                app.device_registry = mock_device_registry
                app.scheduler = mock_scheduler
                # Ensure get_all_devices returns a list for stop() method
                mock_device_registry.get_all_devices.return_value = [mock_device]
                
                # Patch signal.pause to raise KeyboardInterrupt after allowing start() to complete
                # The start() method calls: device.connect(), scheduler.start(), then enters loop with signal.pause()
                original_pause = signal.pause
                call_count = {'count': 0}
                
                def mock_pause():
                    call_count['count'] += 1
                    if call_count['count'] == 1:
                        # First call - allow start() to complete, then raise interrupt
                        raise KeyboardInterrupt()
                    return original_pause()
                
                with patch('src.main.signal.pause', side_effect=mock_pause):
                    try:
                        app.start()
                    except (SystemExit, KeyboardInterrupt):
                        pass  # Expected
                
                # Verify calls were made (these should happen before signal.pause)
                mock_device_registry.get_device.assert_called_with('pump1')
                mock_device.connect.assert_called_once()
                mock_scheduler.start.assert_called_once()
        finally:
            os.unlink(config_path)

    def test_start_exits_on_connection_failure(self):
        """Test that start() exits if device connection fails."""
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
                    "type": "interval",
                    "flood_duration_minutes": 15,
                    "drain_duration_minutes": 30,
                    "interval_minutes": 120
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
            mock_device.connect.return_value = False
            mock_device_registry = Mock()
            mock_device_registry.get_device.return_value = mock_device
            
            with patch('src.services.service_factory.create_device_registry', return_value=mock_device_registry), \
                 patch('src.services.service_factory.create_sensor_registry', return_value=Mock()), \
                 patch('src.services.service_factory.create_actuator_registry', return_value=Mock()), \
                 patch('src.services.service_factory.create_environmental_service', return_value=Mock()), \
                 patch('src.core.scheduler_factory.SchedulerFactory') as mock_factory, \
                 patch('src.main.setup_logger', return_value=Mock()), \
                 patch('sys.exit') as mock_exit:
                
                mock_factory.return_value.create.return_value = Mock()
                
                app = HydroController(config_path)
                app.start()
                
                mock_exit.assert_called_once_with(1)
        finally:
            os.unlink(config_path)

    def test_stop_gracefully_shuts_down(self):
        """Test that stop() gracefully shuts down scheduler."""
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
                    "type": "interval",
                    "flood_duration_minutes": 15,
                    "drain_duration_minutes": 30,
                    "interval_minutes": 120
                },
                "logging": {
                    "log_file": "logs/test.log",
                    "log_level": "INFO"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            mock_scheduler = Mock()
            mock_device = Mock()
            mock_device_registry = Mock()
            mock_device_registry.get_all_devices.return_value = [mock_device]
            mock_device_registry.get_device.return_value = mock_device
            
            with patch('src.services.service_factory.create_device_registry', return_value=mock_device_registry), \
                 patch('src.services.service_factory.create_sensor_registry', return_value=Mock()), \
                 patch('src.services.service_factory.create_actuator_registry', return_value=Mock()), \
                 patch('src.services.service_factory.create_environmental_service', return_value=Mock()), \
                 patch('src.core.scheduler_factory.SchedulerFactory') as mock_factory_class, \
                 patch('src.main.setup_logger', return_value=Mock()):
                
                # SchedulerFactory is instantiated, so we need to mock the instance
                mock_factory_instance = Mock()
                mock_factory_instance.create.return_value = mock_scheduler
                mock_factory_class.return_value = mock_factory_instance
                
                app = HydroController(config_path)
                
                # Ensure scheduler and device_registry are set
                app.scheduler = mock_scheduler
                app.device_registry = mock_device_registry
                
                app.stop()
                
                mock_scheduler.stop.assert_called_once()
                mock_device_registry.get_all_devices.assert_called_once()
                mock_device.close.assert_called_once()
        finally:
            os.unlink(config_path)

    def test_signal_handler_sets_shutdown_flag(self):
        """Test that signal handler sets shutdown flag."""
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
                    "type": "interval",
                    "flood_duration_minutes": 15,
                    "drain_duration_minutes": 30,
                    "interval_minutes": 120
                },
                "logging": {
                    "log_file": "logs/test.log",
                    "log_level": "INFO"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('src.services.service_factory.create_device_registry', return_value=Mock()), \
                 patch('src.services.service_factory.create_sensor_registry', return_value=Mock()), \
                 patch('src.services.service_factory.create_actuator_registry', return_value=Mock()), \
                 patch('src.services.service_factory.create_environmental_service', return_value=Mock()), \
                 patch('src.core.scheduler_factory.SchedulerFactory'), \
                 patch('src.main.setup_logger', return_value=Mock()):
                
                app = HydroController(config_path)
                assert not app.shutdown_requested
                
                # Simulate signal handler call with valid signal number
                app._signal_handler(signal.SIGINT, None)
                
                assert app.shutdown_requested
        finally:
            os.unlink(config_path)
