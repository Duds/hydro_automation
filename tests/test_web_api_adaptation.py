"""Tests for web API adaptation enable/disable and save scenarios."""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.main import HydroController
from src.web.api import WebAPI


class TestWebAPIAdaptation:
    """Test suite for web API adaptation and save scenarios."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
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
                    {"on_time": "06:00", "off_duration_minutes": 20},
                    {"on_time": "12:00", "off_duration_minutes": 30},
                    {"on_time": "18:00", "off_duration_minutes": 20}
                ],
                "adaptation": {
                    "enabled": False,
                    "active_adaptive": {
                        "enabled": False
                    },
                    "location": {
                        "postcode": "2000",
                        "timezone": "Australia/Sydney"
                    },
                    "temperature": {
                        "enabled": False,
                        "source": "bom",
                        "station_id": "auto"
                    },
                    "daylight": {
                        "enabled": False
                    }
                }
            },
            "logging": {
                "log_file": "logs/test.log",
                "log_level": "INFO"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f, indent=2)
            config_path = f.name
        
        yield config_path
        
        # Cleanup
        if os.path.exists(config_path):
            os.unlink(config_path)

    @pytest.fixture
    def controller(self, temp_config_file):
        """Create a controller instance for testing."""
        mock_device = Mock()
        mock_device.connect.return_value = True
        mock_device.is_connected.return_value = True
        mock_device.is_device_on.return_value = False
        mock_device.get_device_info.return_value = Mock(name="Test Device", ip_address="192.168.1.100")
        
        mock_device_registry = Mock()
        mock_device_registry.get_device.return_value = mock_device
        
        mock_scheduler = Mock()
        mock_scheduler.is_running.return_value = False
        mock_scheduler.get_state.return_value = "idle"
        mock_scheduler.get_status.return_value = {
            "scheduler_type": "time_based",
            "running": False,
            "state": "idle",
            "device_id": "pump1",
            "next_event_time": None
        }
        
        mock_env_service = Mock()
        mock_env_service.daylight_calc = None
        mock_env_service.temperature_service = None
        
        with patch('src.services.service_factory.create_device_registry', return_value=mock_device_registry), \
             patch('src.services.service_factory.create_sensor_registry', return_value=Mock()), \
             patch('src.services.service_factory.create_actuator_registry', return_value=Mock()), \
             patch('src.services.service_factory.create_environmental_service', return_value=mock_env_service), \
             patch('src.core.scheduler_factory.SchedulerFactory') as mock_factory, \
             patch('src.main.setup_logger', return_value=Mock()):
            
            mock_factory.return_value.create.return_value = mock_scheduler
            
            app = HydroController(temp_config_file)
            yield app

    @pytest.fixture
    def web_api(self, controller):
        """Create a WebAPI instance for testing."""
        return WebAPI(controller, host="127.0.0.1", port=8001)

    @pytest.fixture
    def client(self, web_api):
        """Create a test client."""
        return TestClient(web_api.app)

    def test_get_status(self, client):
        """Test getting system status."""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "controller_running" in data
        assert "scheduler_running" in data
        assert "device_connected" in data

    def test_get_environment(self, client):
        """Test getting environment data."""
        response = client.get("/api/environment")
        assert response.status_code == 200
        data = response.json()
        assert "temperature" in data
        assert "adaptation_enabled" in data

    def test_get_schedule_config(self, client):
        """Test getting schedule configuration."""
        response = client.get("/api/config/schedule")
        assert response.status_code == 200
        data = response.json()
        assert "type" in data
        assert "cycles" in data
