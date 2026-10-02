# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import MagicMock, patch

from charm import MySQLTestApplication
from literals import PROC_PID_KEY

DATABASE_CONFIG = {
    "user": "user",
    "password": "pass",
    "database": "test_db",
    "host": "host",
    "port": "3306",
}


def test_start_continuous_writes(charm):
    """Test that _start_continuous_writes launches subprocess and stores pid."""
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    with (
        patch.object(MySQLTestApplication, "_database_config", DATABASE_CONFIG),
        patch.object(charm, "_stop_continuous_writes", lambda: None),
        patch("subprocess.Popen", return_value=mock_proc),
    ):
        charm._start_continuous_writes(1)

    assert charm.unit_peer_data[PROC_PID_KEY] == "12345"


def test_stop_continuous_writes(charm):
    """Test that _stop_continuous_writes kills process and returns last written value."""
    charm.unit_peer_data[PROC_PID_KEY] = "12345"
    with (
        patch("subprocess.run"),
        patch("charm.sleep"),
        patch.object(charm, "_max_written_value", lambda: 42),
    ):
        result = charm._stop_continuous_writes()

    assert result == 42
    assert PROC_PID_KEY not in charm.unit_peer_data


def test_write_random_value(charm):
    """Test that _write_random_value writes and returns a random value."""
    mock_cursor = MagicMock()
    mock_connector = MagicMock()
    mock_connector.return_value.__enter__.return_value = mock_cursor
    with (
        patch.object(MySQLTestApplication, "_database_config", DATABASE_CONFIG),
        patch("charm.MySQLConnector", mock_connector),
    ):
        result = charm._write_random_value()

    assert result != ""
    assert len(result) == 10
