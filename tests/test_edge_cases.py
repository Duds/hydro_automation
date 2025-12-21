"""Tests for edge cases and error conditions."""

import pytest
from unittest.mock import Mock, patch
from datetime import time as dt_time

from src.time_scheduler import TimeScheduler
from src.tapo_controller import TapoController


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_schedule_list(self):
        """Test that empty schedule list raises error."""
        with pytest.raises(ValueError, match="At least one valid ON time must be provided"):
            TimeScheduler(Mock(), [], logger=Mock())

    def test_all_invalid_times(self):
        """Test that all invalid times raise error."""
        with pytest.raises(ValueError, match="At least one valid ON time must be provided"):
            TimeScheduler(Mock(), ["invalid", "also_invalid", "25:99"], logger=Mock())

    def test_single_scheduled_time(self):
        """Test scheduler with only one scheduled time."""
        controller = Mock()
        scheduler = TimeScheduler(controller, ["12:00"], logger=Mock())
        
        assert len(scheduler.on_times) == 1
        assert scheduler.on_times[0] == dt_time(12, 0)
        
        # Next time should wrap to same time tomorrow
        next_time = scheduler._get_next_on_time(dt_time(13, 0))
        assert next_time == dt_time(12, 0)

    def test_very_short_flood_duration(self):
        """Test scheduler with very short flood duration."""
        controller = Mock()
        scheduler = TimeScheduler(
            controller,
            ["12:00"],
            flood_duration_minutes=0.01,  # 0.6 seconds
            logger=Mock()
        )
        
        assert scheduler.flood_duration_minutes == 0.01

    def test_very_long_flood_duration(self):
        """Test scheduler with very long flood duration."""
        controller = Mock()
        scheduler = TimeScheduler(
            controller,
            ["12:00"],
            flood_duration_minutes=1440.0,  # 24 hours
            logger=Mock()
        )
        
        assert scheduler.flood_duration_minutes == 1440.0

    def test_duplicate_scheduled_times(self):
        """Test scheduler with duplicate scheduled times."""
        controller = Mock()
        scheduler = TimeScheduler(
            controller,
            ["12:00", "12:00", "12:00"],
            logger=Mock()
        )
        
        # Should handle duplicates (may keep all or filter)
        assert len(scheduler.on_times) >= 1
        assert dt_time(12, 0) in scheduler.on_times

    def test_times_out_of_order(self):
        """Test scheduler with times provided out of order."""
        controller = Mock()
        scheduler = TimeScheduler(
            controller,
            ["18:00", "06:00", "12:00", "03:00"],
            logger=Mock()
        )
        
        # Should be sorted
        assert scheduler.on_times[0] == dt_time(3, 0)
        assert scheduler.on_times[1] == dt_time(6, 0)
        assert scheduler.on_times[2] == dt_time(12, 0)
        assert scheduler.on_times[3] == dt_time(18, 0)

    def test_controller_with_none_logger(self):
        """Test controller initialization with None logger."""
        controller = TapoController(
            ip_address="192.168.1.100",
            email="test@example.com",
            password="testpass",
            logger=None
        )
        
        assert controller.logger is None
        # Should not raise errors when logger is None
        assert controller.is_connected() is False

    def test_scheduler_with_none_logger(self):
        """Test scheduler initialization with None logger."""
        scheduler = TimeScheduler(Mock(), ["12:00"], logger=None)
        
        assert scheduler.logger is None
        # Should not raise errors when logger is None
        assert scheduler.get_state() == "idle"

    def test_stop_when_not_running(self):
        """Test stopping scheduler when it's not running."""
        controller = Mock()
        scheduler = TimeScheduler(controller, ["12:00"], logger=Mock())
        
        # Should not raise error
        scheduler.stop()
        assert not scheduler.running

    def test_start_when_already_running(self):
        """Test starting scheduler when it's already running."""
        controller = Mock()
        logger = Mock()
        scheduler = TimeScheduler(controller, ["12:00"], logger=logger)
        scheduler.running = True
        
        scheduler.start()
        
        # Should log warning but not create new thread
        logger.warning.assert_called()

    def test_get_state_thread_safety(self):
        """Test that get_state() is thread-safe."""
        controller = Mock()
        scheduler = TimeScheduler(controller, ["12:00"], logger=Mock())
        
        # Should be able to call from multiple "threads" (mocked)
        state1 = scheduler.get_state()
        with scheduler.lock:
            scheduler.current_state = "flood"
        state2 = scheduler.get_state()
        
        assert state1 == "idle"
        assert state2 == "flood"

    def test_time_parsing_with_whitespace(self):
        """Test time parsing with various whitespace."""
        controller = Mock()
        scheduler = TimeScheduler([" 06:00 ", "12:00", "  18:00  "], logger=Mock())
        
        # Should handle whitespace
        assert dt_time(6, 0) in scheduler.on_times
        assert dt_time(12, 0) in scheduler.on_times
        assert dt_time(18, 0) in scheduler.on_times

    def test_mixed_time_formats(self):
        """Test scheduler with mixed 12-hour and 24-hour formats."""
        controller = Mock()
        scheduler = TimeScheduler(
            controller,
            ["06:00", "6:00 pm", "12:00", "12:00 am"],
            logger=Mock()
        )
        
        # Should parse all formats correctly
        assert dt_time(6, 0) in scheduler.on_times
        assert dt_time(18, 0) in scheduler.on_times  # 6:00 pm
        assert dt_time(12, 0) in scheduler.on_times
        assert dt_time(0, 0) in scheduler.on_times  # 12:00 am

    def test_ensure_off_with_exception(self):
        """Test ensure_off when device update raises exception."""
        controller = TapoController(
            ip_address="192.168.1.100",
            email="test@example.com",
            password="testpass",
            logger=Mock()
        )
        
        mock_device = Mock()
        mock_device.update = AsyncMock(side_effect=Exception("Update failed"))
        controller.device = mock_device
        controller.connected = True
        
        with patch('src.tapo_controller.asyncio') as mock_asyncio:
            mock_loop = Mock()
            mock_loop.run_until_complete = Mock(side_effect=Exception("Update failed"))
            mock_asyncio.get_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.new_event_loop = Mock(return_value=mock_loop)
            mock_asyncio.set_event_loop = Mock()
            
            result = controller.ensure_off()
            assert result is False

    def test_connection_with_network_error(self):
        """Test connection handling network errors."""
        controller = TapoController(
            ip_address="192.168.1.100",
            email="test@example.com",
            password="testpass",
            logger=Mock()
        )
        
        with patch('src.tapo_controller.connect', side_effect=Exception("Network error")):
            with patch('src.tapo_controller.asyncio') as mock_asyncio:
                mock_loop = Mock()
                mock_loop.run_until_complete = Mock(side_effect=Exception("Network error"))
                mock_asyncio.get_event_loop = Mock(return_value=mock_loop)
                mock_asyncio.new_event_loop = Mock(return_value=mock_loop)
                mock_asyncio.set_event_loop = Mock()
                
                result = controller.connect(max_retries=1, retry_delay=0.01)
                assert result is False
                assert not controller.connected

