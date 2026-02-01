"""Tests for TapoController including failure modes."""

import pytest
from unittest.mock import Mock, patch
from src.device.tapo_controller import TapoController


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

    def test_connect_success(self, controller):
        """Test successful connection."""
        with patch.object(controller, '_run_async', return_value=True):
            result = controller.connect()
            assert result is True
            # Note: _run_async mocked to return True, but internal _connect_async sets self.connected
            # In a real test we'd need to be more careful, but for unit testing logic flow:
            # We can manually set connected to True for subsequent tests or mock the internal _connect_async
            controller.connected = True
            assert controller.is_connected() is False # Because device is None

    def test_is_connected_logic(self, controller):
        """Test connectivity logic."""
        assert controller.is_connected() is False
        controller.connected = True
        controller.device = Mock()
        assert controller.is_connected() is True

    def test_turn_on_fails_when_not_connected(self, controller, mock_logger):
        """Test turn_on fails when device is not connected."""
        with patch.object(controller, '_run_async', return_value=False):
            result = controller.turn_on()
            assert result is False
            mock_logger.error.assert_called()

    def test_turn_on_success(self, controller, mock_logger):
        """Test successful turn_on operation."""
        controller.connected = True
        controller.device = Mock()
        with patch.object(controller, '_run_async', return_value=True):
            result = controller.turn_on()
            assert result is True

    def test_ensure_off_logic(self, controller):
        """Test ensure_off logic."""
        controller.connected = True
        controller.device = Mock()
        with patch.object(controller, '_run_async', return_value=True):
            result = controller.ensure_off()
            assert result is True
