"""Tests for main application and configuration handling."""

import pytest
import json
import signal
from unittest.mock import Mock, patch
import tempfile
import os

from src.main import HydroController


class TestMainApplication:
    """Test suite for main application."""

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

    def test_load_config_valid(self):
        """Test loading valid configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = self._create_valid_config()
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('src.main.create_device_registry') as mock_dev_reg, \
                 patch('src.main.SchedulerFactory.create_scheduler') as mock_create_scheduler, \
                 patch('src.main.HydroController._setup_logging'):
                
                mock_dev_reg.return_value = Mock()
                mock_scheduler = Mock()
                mock_create_scheduler.return_value = mock_scheduler
                
                app = HydroController(config_path)
                app.logger = Mock()
                assert app.setup() is True
                assert app.scheduler is not None
        finally:
            os.unlink(config_path)

    def test_load_config_file_not_found(self):
        """Test error when configuration file doesn't exist."""
        app = HydroController("nonexistent.json")
        assert app.setup() is False

    def test_load_config_invalid_json(self):
        """Test error when configuration file has invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            config_path = f.name
        
        try:
            with patch('src.main.HydroController._setup_logging'):
                app = HydroController(config_path)
                app.logger = Mock()
                assert app.setup() is False
        finally:
            os.unlink(config_path)

    @patch('src.main.signal.signal')
    def test_signal_handlers_registered(self, mock_signal):
        """Test that signal handlers are registered."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = self._create_valid_config()
            json.dump(config, f)
            config_path = f.name
        
        try:
            with patch('src.main.create_device_registry'), \
                 patch('src.main.SchedulerFactory.create_scheduler'), \
                 patch('src.main.HydroController._setup_logging'), \
                 patch('src.main.time.sleep', side_effect=KeyboardInterrupt):
                app = HydroController(config_path)
                app.logger = Mock()
                try:
                    app.run()
                except KeyboardInterrupt:
                    pass
                assert mock_signal.call_count == 2
        finally:
            os.unlink(config_path)

    def test_start_connects_to_device(self):
        """Test that start() connects to device."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = self._create_valid_config()
            json.dump(config, f)
            config_path = f.name
        
        try:
            mock_device = Mock()
            mock_device.connect.return_value = True
            mock_device_registry = Mock()
            mock_device_registry.get_device.return_value = mock_device
            mock_device_registry.get_all_devices.return_value = [mock_device]
            mock_scheduler = Mock()
            mock_scheduler.is_running.return_value = False
            
            with patch('src.main.create_device_registry', return_value=mock_device_registry), \
                 patch('src.main.SchedulerFactory.create_scheduler', return_value=mock_scheduler), \
                 patch('src.main.HydroController._setup_logging'), \
                 patch('src.main.time.sleep', side_effect=KeyboardInterrupt):
                
                app = HydroController(config_path)
                app.logger = Mock()
                
                try:
                    app.run()
                except KeyboardInterrupt:
                    pass
                
                mock_device.connect.assert_called_once()
                mock_scheduler.start.assert_called_once()
        finally:
            os.unlink(config_path)

    def test_stop_performance(self):
        """Test that stop() shuts down correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config = self._create_valid_config()
            json.dump(config, f)
            config_path = f.name
        
        try:
            mock_scheduler = Mock()
            mock_device_registry = Mock()
            mock_device = Mock()
            mock_device_registry.get_all_devices.return_value = [mock_device]
            
            with patch('src.main.create_device_registry', return_value=mock_device_registry), \
                 patch('src.main.SchedulerFactory.create_scheduler', return_value=mock_scheduler), \
                 patch('src.main.HydroController._setup_logging'):
                
                app = HydroController(config_path)
                app.logger = Mock()
                app.setup()
                app.stop()
                
                mock_scheduler.stop.assert_called_once()
                mock_device.close.assert_called_once()
        finally:
            os.unlink(config_path)
