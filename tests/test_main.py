"""Tests for main application and configuration handling."""

import pytest
import json
import sys
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
                "device": {
                    "ip_address": "192.168.1.100",
                    "email": "test@example.com",
                    "password": "testpass",
                    "auto_discovery": True
                },
                "cycle": {
                    "flood_duration_minutes": 15,
                    "drain_duration_minutes": 30,
                    "interval_minutes": 120
                },
                "schedule": {
                    "type": "interval",
                    "enabled": True,
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
            app = HydroController(config_path)
            assert app.config == config
            assert app.controller is not None
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
            with pytest.raises(ValueError):
                HydroController(config_path)
        finally:
            os.unlink(config_path)

    def test_load_config_missing_device_section(self):
        """Test error when device section is missing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "cycle": {
                    "flood_duration_minutes": 15,
                    "drain_duration_minutes": 30,
                    "interval_minutes": 120
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Missing required configuration section: device"):
                HydroController(config_path)
        finally:
            os.unlink(config_path)

    def test_load_config_missing_cycle_section(self):
        """Test error when cycle section is missing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "device": {
                    "ip_address": "192.168.1.100",
                    "email": "test@example.com",
                    "password": "testpass"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Missing required configuration section: cycle"):
                HydroController(config_path)
        finally:
            os.unlink(config_path)

    def test_load_config_missing_device_ip(self):
        """Test error when device IP address is missing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = {
                "device": {
                    "email": "test@example.com",
                    "password": "testpass"
                },
                "cycle": {
                    "flood_duration_minutes": 15,
                    "drain_duration_minutes": 30,
                    "interval_minutes": 120
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Missing required device configuration: ip_address"):
                HydroController(config_path)
        finally:
            os.unlink(config_path)

    def test_load_config_time_based_schedule(self):
        """Test loading time-based schedule configuration."""
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
                 patch('src.main.TimeScheduler') as mock_scheduler_class, \
                 patch('src.main.setup_logger') as mock_logger:
                
                mock_logger.return_value = Mock()
                mock_controller = Mock()
                mock_controller_class.return_value = mock_controller
                
                app = HydroController(config_path)
                assert app.config == config
                
                # Should create TimeScheduler for time_based schedule
                mock_scheduler_class.assert_called_once()
                call_args = mock_scheduler_class.call_args
                assert call_args[1]['flood_duration_minutes'] == 2.0
                assert call_args[1]['on_times'] == ["06:00", "12:00", "18:00"]
        finally:
            os.unlink(config_path)

    def test_load_config_interval_based_schedule(self):
        """Test loading interval-based schedule configuration."""
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
                    "type": "interval",
                    "enabled": True,
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
            with patch('src.main.TapoController') as mock_controller_class, \
                 patch('src.main.CycleScheduler') as mock_scheduler_class, \
                 patch('src.main.setup_logger') as mock_logger:
                
                mock_logger.return_value = Mock()
                mock_controller = Mock()
                mock_controller_class.return_value = mock_controller
                
                app = HydroController(config_path)
                assert app.config == config
                
                # Should create CycleScheduler for interval schedule
                mock_scheduler_class.assert_called_once()
        finally:
            os.unlink(config_path)

    @patch('src.main.signal.signal')
    def test_signal_handlers_registered(self, mock_signal):
        """Test that signal handlers are registered."""
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
                "logging": {
                    "log_file": "logs/test.log",
                    "log_level": "INFO"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('src.main.TapoController'), \
                 patch('src.main.CycleScheduler'), \
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
                "logging": {
                    "log_file": "logs/test.log",
                    "log_level": "INFO"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('src.main.TapoController') as mock_controller_class, \
                 patch('src.main.CycleScheduler') as mock_scheduler_class, \
                 patch('src.main.setup_logger') as mock_logger:
                
                mock_logger.return_value = Mock()
                mock_controller = Mock()
                mock_controller.connect.return_value = True
                mock_controller_class.return_value = mock_controller
                mock_scheduler = Mock()
                mock_scheduler_class.return_value = mock_scheduler
                
                app = HydroController(config_path)
                
                with patch('src.main.signal.pause') as mock_pause:
                    mock_pause.side_effect = KeyboardInterrupt()
                    with pytest.raises(SystemExit):
                        app.start()
                
                mock_controller.connect.assert_called_once()
                mock_scheduler.start.assert_called_once()
        finally:
            os.unlink(config_path)

    def test_start_exits_on_connection_failure(self):
        """Test that start() exits if device connection fails."""
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
                "logging": {
                    "log_file": "logs/test.log",
                    "log_level": "INFO"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('src.main.TapoController') as mock_controller_class, \
                 patch('src.main.CycleScheduler') as mock_scheduler_class, \
                 patch('src.main.setup_logger') as mock_logger, \
                 patch('sys.exit') as mock_exit:
                
                mock_logger.return_value = Mock()
                mock_controller = Mock()
                mock_controller.connect.return_value = False
                mock_controller_class.return_value = mock_controller
                mock_scheduler_class.return_value = Mock()
                
                app = HydroController(config_path)
                app.start()
                
                mock_exit.assert_called_once_with(1)
        finally:
            os.unlink(config_path)

    def test_stop_gracefully_shuts_down(self):
        """Test that stop() gracefully shuts down scheduler."""
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
                "logging": {
                    "log_file": "logs/test.log",
                    "log_level": "INFO"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('src.main.TapoController') as mock_controller_class, \
                 patch('src.main.CycleScheduler') as mock_scheduler_class, \
                 patch('src.main.setup_logger') as mock_logger:
                
                mock_logger.return_value = Mock()
                mock_controller = Mock()
                mock_controller_class.return_value = mock_controller
                mock_scheduler = Mock()
                mock_scheduler_class.return_value = mock_scheduler
                
                app = HydroController(config_path)
                app.stop()
                
                mock_scheduler.stop.assert_called_once()
        finally:
            os.unlink(config_path)

    def test_signal_handler_sets_shutdown_flag(self):
        """Test that signal handler sets shutdown flag."""
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
                "logging": {
                    "log_file": "logs/test.log",
                    "log_level": "INFO"
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('src.main.TapoController'), \
                 patch('src.main.CycleScheduler'), \
                 patch('src.main.setup_logger'):
                
                app = HydroController(config_path)
                assert not app.shutdown_requested
                
                # Simulate signal handler call
                app._signal_handler(None, None)
                
                assert app.shutdown_requested
        finally:
            os.unlink(config_path)

