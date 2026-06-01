# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Background script that reads the last continuous write from every endpoint.

For each configured endpoint it queries the max value written to the continuous
writes table and emits a single log line to a named pipe (FIFO) that can be
tailed. The value is the per-unit last read, or ``NA`` when the read times out
or errors out.

Log line template:
    <timestamp> - <unit-0>: <value> | <unit-1>: <value> | <unit-n>: <value>
"""

import os
import stat
import sys
from datetime import datetime
from time import sleep
from typing import Dict, List

from connector import MySQLConnector


def _ensure_pipe(pipe_path: str) -> None:
    """Create the named pipe (FIFO) if it does not already exist."""
    if os.path.exists(pipe_path):
        if not stat.S_ISFIFO(os.stat(pipe_path).st_mode):
            os.remove(pipe_path)
            os.mkfifo(pipe_path)
    else:
        os.mkfifo(pipe_path)


def _write_to_pipe(pipe_path: str, line: str) -> None:
    """Write a line to the named pipe without blocking when no reader is attached."""
    try:
        # O_NONBLOCK so the script never hangs waiting for a `tail` reader
        fd = os.open(pipe_path, os.O_WRONLY | os.O_NONBLOCK)
    except OSError:
        # No reader connected to the pipe, drop the line
        return

    try:
        os.write(fd, f"{line}\n".encode())
    except OSError:
        # Reader went away mid-write, ignore
        pass
    finally:
        os.close(fd)


def _build_endpoint_config(base_config: Dict, endpoint: str) -> Dict:
    """Return a connector config for a single endpoint (host:port or file://socket)."""
    config = dict(base_config)
    if endpoint.startswith("file://"):
        config["unix_socket"] = endpoint[7:]
    else:
        host, port = endpoint.rsplit(":", 1)
        config["host"] = host
        config["port"] = port
    return config


def _read_last_value(endpoint_config: Dict, table_name: str) -> str:
    """Return the max value written to the table, or ``NA`` on timeout/error."""
    try:
        with MySQLConnector(endpoint_config, commit=False) as cursor:
            cursor.execute(f"SELECT MAX(number) FROM `{table_name}`")
            result = cursor.fetchone()
    except Exception:
        return "NA"

    if not result or result[0] is None:
        return "NA"
    return str(result[0])


def continuous_reads(
    base_config: Dict,
    endpoints: List[str],
    table_name: str,
    pipe_path: str,
    read_interval: int,
) -> None:
    """Continuously read the last write from every endpoint and log it to a pipe.

    Args:
        base_config: a dict with MySQL config (user, password, database) shared by endpoints
        endpoints: list of endpoints (host:port or file://socket) to read from
        table_name: the continuous writes table to read from
        pipe_path: path of the named pipe (FIFO) to write log lines to
        read_interval: time to sleep (seconds) between read rounds
    """
    _ensure_pipe(pipe_path)

    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        readings = []
        for index, endpoint in enumerate(endpoints):
            endpoint_config = _build_endpoint_config(base_config, endpoint)
            value = _read_last_value(endpoint_config, table_name)
            readings.append(f"unit-{index}: {value}")

        line = f"{timestamp} - " + " | ".join(readings)
        _write_to_pipe(pipe_path, line)

        if read_interval:
            sleep(read_interval)


def main():
    """Run the continuous reads script."""
    [_, username, password, database, table_name, read_interval, pipe_path, endpoints_csv] = (
        sys.argv
    )

    base_config = {
        "user": username,
        "password": password,
        "database": database,
        "use_pure": True,
        "connection_timeout": 5,
    }

    endpoints = [ep.strip() for ep in endpoints_csv.split(",") if ep.strip()]

    continuous_reads(base_config, endpoints, table_name, pipe_path, int(read_interval))


if __name__ == "__main__":
    main()
