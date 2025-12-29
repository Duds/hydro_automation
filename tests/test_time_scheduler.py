"""Tests for time-based scheduler."""

import pytest
import threading
import time
from datetime import datetime, time as dt_time, timedelta
from unittest.mock import Mock, MagicMock, patch, call

from src.schedulers.time_based_scheduler import TimeBasedScheduler
from src.services.device_service import DeviceRegistry


class TestTimeBasedScheduler:
    """Test suite for TimeBasedScheduler."""

    @pytest.fixture
    def mock_device_registry(self):
        """Create a mock device registry."""
        registry = Mock(spec=DeviceRegistry)
        mock_device = Mock()
        mock_device.turn_on.return_value = True
        mock_device.turn_off.return_value = True
        mock_device.is_connected.return_value = True
        mock_device.is_device_on.return_value = None
        mock_device.get_device_info.return_value = Mock(name="Test Device", ip_address="192.168.1.100")
        registry.get_device.return_value = mock_device
        return registry

    def test_parse_time_valid_24hour(self):
        """Test parsing valid 24-hour format times."""
        scheduler = TimeBasedScheduler(
            Mock(), "device1",
            [{"on_time": "06:00", "off_duration_minutes": 18}],
            logger=Mock()
        )
        
        assert scheduler._parse_time("06:00") == dt_time(6, 0)
        assert scheduler._parse_time("23:59") == dt_time(23, 59)
        assert scheduler._parse_time("00:00") == dt_time(0, 0)
        assert scheduler._parse_time("12:00") == dt_time(12, 0)

    def test_parse_time_invalid_formats(self):
        """Test parsing invalid time formats."""
        scheduler = TimeBasedScheduler(
            Mock(), "device1",
            [{"on_time": "06:00", "off_duration_minutes": 18}],
            logger=Mock()
        )
        
        assert scheduler._parse_time("invalid") is None
        assert scheduler._parse_time("25:00") is None  # Invalid hour
        assert scheduler._parse_time("12:60") is None  # Invalid minute
        assert scheduler._parse_time("") is None
        assert scheduler._parse_time("abc:def") is None

    def test_init_valid_schedule(self, mock_device_registry):
        """Test initialisation with valid schedule."""
        logger = Mock()
        cycles = [
            {"on_time": "06:00", "off_duration_minutes": 18},
            {"on_time": "12:00", "off_duration_minutes": 28},
            {"on_time": "18:00", "off_duration_minutes": 18}
        ]
        scheduler = TimeBasedScheduler(
            mock_device_registry,
            "device1",
            cycles,
            flood_duration_minutes=2.0,
            logger=logger
        )
        
        assert scheduler.device_registry == mock_device_registry
        assert scheduler.device_id == "device1"
        assert len(scheduler.cycles) == 3
        assert scheduler.flood_duration_minutes == 2.0
        assert scheduler.logger == logger
        assert not scheduler.running
        assert scheduler.current_state == "idle"

    def test_init_sorts_cycles(self, mock_device_registry):
        """Test that cycles are sorted by on_time on initialisation."""
        cycles = [
            {"on_time": "18:00", "off_duration_minutes": 18},
            {"on_time": "06:00", "off_duration_minutes": 18},
            {"on_time": "12:00", "off_duration_minutes": 28}
        ]
        scheduler = TimeBasedScheduler(
            mock_device_registry,
            "device1",
            cycles,
            logger=Mock()
        )
        
        assert scheduler.cycles[0]["on_time"] == dt_time(6, 0)
        assert scheduler.cycles[1]["on_time"] == dt_time(12, 0)
        assert scheduler.cycles[2]["on_time"] == dt_time(18, 0)

    def test_init_filters_invalid_cycles(self, mock_device_registry):
        """Test that invalid cycles are filtered out."""
        cycles = [
            {"on_time": "06:00", "off_duration_minutes": 18},
            {"on_time": "invalid", "off_duration_minutes": 18},
            {"on_time": "12:00", "off_duration_minutes": 28},
            {"on_time": "25:00", "off_duration_minutes": 18}
        ]
        scheduler = TimeBasedScheduler(
            mock_device_registry,
            "device1",
            cycles,
            logger=Mock()
        )
        
        assert len(scheduler.cycles) == 2
        assert scheduler.cycles[0]["on_time"] == dt_time(6, 0)
        assert scheduler.cycles[1]["on_time"] == dt_time(12, 0)

    def test_init_no_valid_cycles_raises_error(self, mock_device_registry):
        """Test that initialisation with no valid cycles raises error."""
        with pytest.raises(ValueError, match="At least one valid cycle must be provided"):
            TimeBasedScheduler(
                mock_device_registry,
                "device1",
                [{"on_time": "invalid", "off_duration_minutes": 18}],
                logger=Mock()
            )

    def test_get_next_on_time_same_day(self, mock_device_registry):
        """Test getting next ON time later same day."""
        cycles = [
            {"on_time": "06:00", "off_duration_minutes": 18},
            {"on_time": "12:00", "off_duration_minutes": 28},
            {"on_time": "18:00", "off_duration_minutes": 18}
        ]
        scheduler = TimeBasedScheduler(
            mock_device_registry,
            "device1",
            cycles,
            logger=Mock()
        )
        
        current = dt_time(10, 0)
        next_time = scheduler._get_next_on_time(current)
        assert next_time == dt_time(12, 0)

    def test_get_next_on_time_wraps_midnight(self, mock_device_registry):
        """Test getting next ON time wraps around midnight."""
        cycles = [
            {"on_time": "06:00", "off_duration_minutes": 18},
            {"on_time": "12:00", "off_duration_minutes": 28},
            {"on_time": "18:00", "off_duration_minutes": 18}
        ]
        scheduler = TimeBasedScheduler(
            mock_device_registry,
            "device1",
            cycles,
            logger=Mock()
        )
        
        current = dt_time(20, 0)
        next_time = scheduler._get_next_on_time(current)
        assert next_time == dt_time(6, 0)  # First time tomorrow

    def test_time_until_next_event_future(self, mock_device_registry):
        """Test calculating time until future event."""
        cycles = [{"on_time": "12:00", "off_duration_minutes": 28}]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        
        with patch('src.schedulers.time_based_scheduler.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.combine
            
            target = dt_time(12, 0)
            seconds = scheduler._time_until_next_event(target)
            assert seconds == 7200.0  # 2 hours

    def test_start_creates_thread(self, mock_device_registry):
        """Test that start() creates and starts a thread."""
        cycles = [{"on_time": "12:00", "off_duration_minutes": 28}]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        
        assert scheduler.thread is None
        scheduler.start()
        
        assert scheduler.running
        assert scheduler.thread is not None
        assert scheduler.thread.is_alive()
        
        # Clean up
        scheduler.stop()

    def test_stop_gracefully_shuts_down(self, mock_device_registry):
        """Test that stop() gracefully shuts down scheduler."""
        cycles = [{"on_time": "12:00", "off_duration_minutes": 28}]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        
        scheduler.start()
        assert scheduler.running
        
        scheduler.stop()
        
        assert not scheduler.running
        mock_device = mock_device_registry.get_device.return_value
        mock_device.ensure_off.assert_called_once()

    def test_get_state(self, mock_device_registry):
        """Test getting current scheduler state."""
        cycles = [{"on_time": "12:00", "off_duration_minutes": 28}]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        
        assert scheduler.get_state() == "idle"

    def test_is_running(self, mock_device_registry):
        """Test checking if scheduler is running."""
        cycles = [{"on_time": "12:00", "off_duration_minutes": 28}]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        
        assert not scheduler.is_running()
        scheduler.start()
        assert scheduler.is_running()
        scheduler.stop()
        assert not scheduler.is_running()

    def test_get_status(self, mock_device_registry):
        """Test getting scheduler status."""
        cycles = [
            {"on_time": "06:00", "off_duration_minutes": 18},
            {"on_time": "12:00", "off_duration_minutes": 28}
        ]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        
        status = scheduler.get_status()
        
        assert status["scheduler_type"] == "time_based"
        assert status["running"] == False
        assert status["state"] == "idle"
        assert status["device_id"] == "device1"
        assert status["flood_duration_minutes"] == 2.0
        assert status["total_cycles"] == 2
        assert "cycles" in status

    def test_get_next_event_time_not_running(self, mock_device_registry):
        """Test getting next event time when scheduler not running."""
        cycles = [{"on_time": "12:00", "off_duration_minutes": 28}]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        
        assert scheduler.get_next_event_time() is None

    def test_get_next_event_time_running(self, mock_device_registry):
        """Test getting next event time when scheduler is running."""
        cycles = [{"on_time": "12:00", "off_duration_minutes": 28}]
        scheduler = TimeBasedScheduler(mock_device_registry, "device1", cycles, logger=Mock())
        
        scheduler.running = True
        next_time = scheduler.get_next_event_time()
        
        assert next_time is not None
        assert isinstance(next_time, datetime)
