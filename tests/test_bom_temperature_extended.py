"""Tests for extended BOM temperature module (humidity, trends, time-based queries)."""

import pytest
from datetime import datetime, time as dt_time, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.data.bom_temperature import BOMTemperature


class TestBOMTemperatureExtended:
    """Test suite for extended BOM temperature functionality."""

    @pytest.fixture
    def bom_fetcher(self):
        """Create a BOMTemperature instance."""
        return BOMTemperature(station_id="94926", logger=Mock())

    @patch('src.bom_temperature.requests.get')
    def test_fetch_humidity_success(self, mock_get, bom_fetcher):
        """Test successful humidity fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "observations": {
                "data": [{
                    "air_temp": 22.0,
                    "rel_hum": 45
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        humidity = bom_fetcher.fetch_humidity()
        assert humidity == 45.0

    @patch('src.bom_temperature.requests.get')
    def test_fetch_humidity_none(self, mock_get, bom_fetcher):
        """Test humidity fetch when not available."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "observations": {
                "data": [{
                    "air_temp": 22.0,
                    "rel_hum": None
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        humidity = bom_fetcher.fetch_humidity()
        assert humidity is None

    @patch('src.bom_temperature.requests.get')
    def test_fetch_temperature_with_humidity(self, mock_get, bom_fetcher):
        """Test that temperature fetch also captures humidity."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "observations": {
                "data": [{
                    "air_temp": 22.5,
                    "rel_hum": 45
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        temp = bom_fetcher.fetch_temperature()
        
        assert temp == 22.5
        assert bom_fetcher.last_humidity == 45.0
        assert bom_fetcher.last_update is not None

    def test_get_temperature_at_time_with_history(self, bom_fetcher):
        """Test temperature estimation with historical data."""
        # Add historical data
        now = datetime.now()
        bom_fetcher.historical_data.append((now - timedelta(hours=2), 20.0, 50.0))
        bom_fetcher.historical_data.append((now - timedelta(hours=1), 22.0, 48.0))
        bom_fetcher.last_temperature = 24.0
        bom_fetcher.last_update = now
        
        # Estimate for future time
        estimated = bom_fetcher.get_temperature_at_time(dt_time(14, 0))
        
        assert estimated is not None
        assert 0 <= estimated <= 50  # Reasonable range

    def test_get_temperature_at_time_no_history(self, bom_fetcher):
        """Test temperature estimation without historical data."""
        bom_fetcher.last_temperature = 22.0
        bom_fetcher.last_update = datetime.now()
        
        # Estimate for different times
        morning_temp = bom_fetcher.get_temperature_at_time(dt_time(7, 0))
        afternoon_temp = bom_fetcher.get_temperature_at_time(dt_time(14, 0))
        night_temp = bom_fetcher.get_temperature_at_time(dt_time(22, 0))
        
        assert morning_temp is not None
        assert afternoon_temp is not None
        assert night_temp is not None
        # Afternoon should typically be warmer than morning
        assert afternoon_temp >= morning_temp - 5  # Allow some variance

    def test_get_temperature_at_time_none(self, bom_fetcher):
        """Test temperature estimation when no temperature available."""
        bom_fetcher.last_temperature = None
        
        estimated = bom_fetcher.get_temperature_at_time(dt_time(12, 0))
        assert estimated is None

    def test_get_humidity_at_time(self, bom_fetcher):
        """Test humidity estimation for different times."""
        bom_fetcher.last_humidity = 50.0
        bom_fetcher.last_update = datetime.now()
        
        # Estimate for different times
        morning_humidity = bom_fetcher.get_humidity_at_time(dt_time(7, 0))
        afternoon_humidity = bom_fetcher.get_humidity_at_time(dt_time(14, 0))
        night_humidity = bom_fetcher.get_humidity_at_time(dt_time(22, 0))
        
        assert morning_humidity is not None
        assert afternoon_humidity is not None
        assert night_humidity is not None
        assert 0 <= morning_humidity <= 100
        assert 0 <= afternoon_humidity <= 100
        assert 0 <= night_humidity <= 100
        # Night should typically have higher humidity
        assert night_humidity >= afternoon_humidity - 10  # Allow variance

    def test_get_humidity_at_time_none(self, bom_fetcher):
        """Test humidity estimation when no humidity available."""
        bom_fetcher.last_humidity = None
        
        estimated = bom_fetcher.get_humidity_at_time(dt_time(12, 0))
        assert estimated is None

    def test_calculate_temperature_trend_rising(self, bom_fetcher):
        """Test temperature trend calculation - rising."""
        now = datetime.now()
        # Add historical data showing rising trend
        # Deque.append() adds to the end, so oldest first, newest last
        bom_fetcher.historical_data.append((now - timedelta(hours=3), 18.0, 50.0))  # Oldest
        bom_fetcher.historical_data.append((now - timedelta(hours=2), 20.0, 48.0))
        bom_fetcher.historical_data.append((now - timedelta(hours=1), 22.0, 45.0))
        bom_fetcher.historical_data.append((now, 24.0, 45.0))  # Newest
        bom_fetcher.last_temperature = 24.0
        bom_fetcher.last_update = now
        
        trend = bom_fetcher.calculate_temperature_trend(hours=3)
        assert trend == "rising"

    def test_calculate_temperature_trend_falling(self, bom_fetcher):
        """Test temperature trend calculation - falling."""
        now = datetime.now()
        # Add historical data showing falling trend
        # Deque.append() adds to the end, so oldest first, newest last
        bom_fetcher.historical_data.append((now - timedelta(hours=3), 24.0, 45.0))  # Oldest
        bom_fetcher.historical_data.append((now - timedelta(hours=2), 22.0, 48.0))
        bom_fetcher.historical_data.append((now - timedelta(hours=1), 20.0, 50.0))
        bom_fetcher.historical_data.append((now, 18.0, 50.0))  # Newest
        bom_fetcher.last_temperature = 18.0
        bom_fetcher.last_update = now
        
        trend = bom_fetcher.calculate_temperature_trend(hours=3)
        assert trend == "falling"

    def test_calculate_temperature_trend_stable(self, bom_fetcher):
        """Test temperature trend calculation - stable."""
        now = datetime.now()
        # Add historical data showing stable trend
        bom_fetcher.historical_data.append((now - timedelta(hours=3), 20.0, 50.0))
        bom_fetcher.historical_data.append((now - timedelta(hours=2), 20.5, 49.0))
        bom_fetcher.historical_data.append((now - timedelta(hours=1), 20.2, 50.0))
        bom_fetcher.last_temperature = 20.0
        bom_fetcher.last_update = now
        
        trend = bom_fetcher.calculate_temperature_trend(hours=3)
        assert trend == "stable"

    def test_calculate_temperature_trend_insufficient_data(self, bom_fetcher):
        """Test temperature trend with insufficient data."""
        bom_fetcher.last_temperature = 20.0
        bom_fetcher.last_update = datetime.now()
        
        trend = bom_fetcher.calculate_temperature_trend(hours=3)
        assert trend == "stable"  # Default when insufficient data

    def test_get_humidity_adjustment_factor_low(self, bom_fetcher):
        """Test humidity adjustment factor for low humidity."""
        assert bom_fetcher.get_humidity_adjustment_factor(30) == 0.9
        assert bom_fetcher.get_humidity_adjustment_factor(39) == 0.9

    def test_get_humidity_adjustment_factor_normal(self, bom_fetcher):
        """Test humidity adjustment factor for normal humidity."""
        assert bom_fetcher.get_humidity_adjustment_factor(40) == 1.0
        assert bom_fetcher.get_humidity_adjustment_factor(50) == 1.0
        assert bom_fetcher.get_humidity_adjustment_factor(69) == 1.0

    def test_get_humidity_adjustment_factor_high(self, bom_fetcher):
        """Test humidity adjustment factor for high humidity."""
        # 70 is in normal range (<= 70), so use 71+ for high
        assert bom_fetcher.get_humidity_adjustment_factor(71) == 1.1
        assert bom_fetcher.get_humidity_adjustment_factor(85) == 1.1

    def test_get_humidity_adjustment_factor_none(self, bom_fetcher):
        """Test humidity adjustment factor when humidity is None."""
        assert bom_fetcher.get_humidity_adjustment_factor(None) == 1.0

    def test_historical_data_storage(self, bom_fetcher):
        """Test that historical data is stored correctly."""
        now = datetime.now()
        bom_fetcher.last_temperature = 22.0
        bom_fetcher.last_humidity = 50.0
        bom_fetcher.last_update = now
        
        # Simulate fetch (which should add to historical data)
        bom_fetcher.historical_data.append((now, 22.0, 50.0))
        
        assert len(bom_fetcher.historical_data) > 0
        latest = bom_fetcher.historical_data[0]
        assert latest[1] == 22.0  # Temperature
        assert latest[2] == 50.0  # Humidity

    def test_historical_data_maxlen(self, bom_fetcher):
        """Test that historical data respects maxlen (24 hours)."""
        now = datetime.now()
        # Add more than 24 data points
        for i in range(30):
            bom_fetcher.historical_data.append((
                now - timedelta(hours=i),
                20.0 + i * 0.1,
                50.0
            ))
        
        # Should only keep last 24
        assert len(bom_fetcher.historical_data) == 24

