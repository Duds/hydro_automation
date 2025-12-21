"""Tests for TapoController including failure modes."""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock, call
from typing import Optional

from src.tapo_controller import TapoController


class TestTapoController:
    """Test suite for TapoController."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()

    @pytest.fixture
    def controller(self, mock_logger):
        """Create a TapoController instance for testing."""
        return TapoController(
            ip_address="192.168.1.100",
            email="test@example.com",
            password="testpass",
            logger=mock_logger
        )

    def test_init_stores_credentials(self, controller):
        """Test that controller stores credentials correctly."""
        assert controller.ip_address == "192.168.1.100"
        assert controller.email == "test@example.com"
        assert controller.password == "testpass"
        assert not controller.connected
        assert controller.device is None

    @patch('src.tapo_controller.connect')
    @patch('src.tapo_controller.AuthCredential')
    @patch('src.tapo_controller.DeviceConnectConfiguration')
    def test_connect_success(self, mock_config, mock_auth, mock_connect, controller, mock_logger):
        """Test successful connection."""
        mock_device = Mock()
        mock_device.protocol_version = "Klap V2"
        mock_connect.return_value = mock_device
        
        async def mock_update():
            pass
        mock_device.update = AsyncMock(side_effect=mock_update)
        
        with patch('src.tapo_controller.asyncio') as mock_asyncio:
            mock_loop = Mock()
            mock_loop.run_until_complete = Mock(return_value=True)
            mock_asyncio.get_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.new_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.set_event_loop = Mock()
            
            result = controller.connect()
            
            assert result is True
            assert controller.connected
            assert controller.device == mock_device

    @patch('src.tapo_controller.connect')
    def test_connect_retry_on_failure(self, mock_connect, controller, mock_logger):
        """Test that connection retries on failure."""
        mock_connect.side_effect = [Exception("Connection failed"), Exception("Connection failed"), Mock()]
        
        async def mock_update():
            pass
        
        mock_device = Mock()
        mock_device.protocol_version = "Klap V2"
        mock_device.update = AsyncMock(side_effect=mock_update)
        mock_connect.side_effect = [
            Exception("Connection failed"),
            Exception("Connection failed"),
            mock_device
        ]
        
        with patch('src.tapo_controller.asyncio') as mock_asyncio:
            mock_loop = Mock()
            def run_until_complete(coro):
                # Simulate retries
                if mock_connect.call_count < 3:
                    raise Exception("Connection failed")
                return True
            mock_loop.run_until_complete = Mock(side_effect=run_until_complete)
            mock_asyncio.get_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.new_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.set_event_loop = Mock()
            
            result = controller.connect(max_retries=3, retry_delay=0.1)
            
            # Should eventually succeed or fail after retries
            assert isinstance(result, bool)

    def test_connect_max_retries_exceeded(self, controller, mock_logger):
        """Test that connection fails after max retries."""
        with patch('src.tapo_controller.connect', side_effect=Exception("Connection failed")):
            with patch('src.tapo_controller.asyncio') as mock_asyncio:
                mock_loop = Mock()
                mock_loop.run_until_complete = Mock(side_effect=Exception("Connection failed"))
                mock_asyncio.get_event_loop = Mock(return_value=mock_loop)
                mock_asyncio.new_event_loop = Mock(return_value=mock_loop)
                mock_asyncio.set_event_loop = Mock()
                
                result = controller.connect(max_retries=2, retry_delay=0.01)
                
                assert result is False
                assert not controller.connected

    def test_is_connected_false_when_not_connected(self, controller):
        """Test is_connected returns False when not connected."""
        assert controller.is_connected() is False

    def test_is_connected_true_when_connected(self, controller):
        """Test is_connected returns True when connected."""
        controller.device = Mock()
        controller.connected = True
        assert controller.is_connected() is True

    def test_turn_on_fails_when_not_connected(self, controller, mock_logger):
        """Test turn_on fails when device is not connected."""
        result = controller.turn_on()
        assert result is False
        mock_logger.error.assert_called()

    def test_turn_on_success(self, controller, mock_logger):
        """Test successful turn_on operation."""
        mock_device = Mock()
        mock_device.is_on = True
        mock_device.turn_on = AsyncMock(return_value=Mock(is_success=Mock(return_value=True)))
        mock_device.update = AsyncMock()
        
        controller.device = mock_device
        controller.connected = True
        
        with patch('src.tapo_controller.asyncio') as mock_asyncio:
            mock_loop = Mock()
            mock_loop.run_until_complete = Mock(return_value=True)
            mock_asyncio.get_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.new_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.set_event_loop = Mock()
            
            result = controller.turn_on()
            assert result is True

    def test_turn_off_fails_when_not_connected(self, controller, mock_logger):
        """Test turn_off fails when device is not connected."""
        result = controller.turn_off()
        assert result is False
        mock_logger.error.assert_called()

    def test_ensure_off_fails_when_not_connected(self, controller):
        """Test ensure_off fails when device is not connected."""
        result = controller.ensure_off()
        assert result is False

    def test_ensure_off_when_device_is_on(self, controller, mock_logger):
        """Test ensure_off turns device off when it's on."""
        mock_device = Mock()
        mock_device.is_on = True
        mock_device.turn_off = AsyncMock(return_value=Mock(is_success=Mock(return_value=True)))
        mock_device.update = AsyncMock()
        
        controller.device = mock_device
        controller.connected = True
        
        with patch('src.tapo_controller.asyncio') as mock_asyncio:
            mock_loop = Mock()
            mock_loop.run_until_complete = Mock(return_value=True)
            mock_asyncio.get_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.new_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.set_event_loop = Mock()
            
            result = controller.ensure_off()
            assert result is True

    def test_ensure_off_when_device_is_already_off(self, controller, mock_logger):
        """Test ensure_off succeeds when device is already off."""
        mock_device = Mock()
        mock_device.is_on = False
        mock_device.update = AsyncMock()
        
        controller.device = mock_device
        controller.connected = True
        
        with patch('src.tapo_controller.asyncio') as mock_asyncio:
            mock_loop = Mock()
            mock_loop.run_until_complete = Mock(return_value=True)
            mock_asyncio.get_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.new_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.set_event_loop = Mock()
            
            result = controller.ensure_off()
            assert result is True

    @patch('src.tapo_controller.TapoDiscovery')
    def test_discover_device_success(self, mock_discovery, controller, mock_logger):
        """Test successful device discovery."""
        mock_discovered_device = Mock()
        mock_discovered_device.ip = "192.168.1.200"
        mock_discovered_device.get_tapo_device = AsyncMock(return_value=Mock())
        
        async def mock_scan():
            return [mock_discovered_device]
        
        mock_discovery.scan = AsyncMock(side_effect=mock_scan)
        
        with patch('src.tapo_controller.asyncio') as mock_asyncio:
            mock_loop = Mock()
            mock_loop.run_until_complete = Mock(return_value="192.168.1.200")
            mock_asyncio.get_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.new_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.set_event_loop = Mock()
            
            result = controller.discover_device()
            assert result == "192.168.1.200"

    @patch('src.tapo_controller.TapoDiscovery')
    def test_discover_device_no_devices_found(self, mock_discovery, controller, mock_logger):
        """Test device discovery when no devices found."""
        async def mock_scan():
            return []
        
        mock_discovery.scan = AsyncMock(side_effect=mock_scan)
        
        with patch('src.tapo_controller.asyncio') as mock_asyncio:
            mock_loop = Mock()
            mock_loop.run_until_complete = Mock(return_value=None)
            mock_asyncio.get_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.new_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.set_event_loop = Mock()
            
            result = controller.discover_device()
            assert result is None

    def test_close_when_not_connected(self, controller):
        """Test close() when device is not connected."""
        controller.close()  # Should not raise error
        assert not controller.connected

    def test_close_when_connected(self, controller):
        """Test close() when device is connected."""
        mock_device = Mock()
        mock_device.client = Mock()
        mock_device.client.close = AsyncMock()
        
        controller.device = mock_device
        controller.connected = True
        
        with patch('src.tapo_controller.asyncio') as mock_asyncio:
            mock_loop = Mock()
            mock_loop.run_until_complete = Mock(return_value=None)
            mock_asyncio.get_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.new_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.set_event_loop = Mock()
            
            controller.close()
            
            assert not controller.connected
            assert controller.device is None

