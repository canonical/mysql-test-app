# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Background script that reads the last continuous write from every group member.

Group Replication members are discovered each round by querying
``performance_schema.replication_group_members`` through one of the seed
endpoints. For every discovered member it queries the max value written to the
continuous writes table and emits a single log line to a named pipe (FIFO) that
can be tailed. The value is the per-host last read, or ``-1`` when the read
times out or errors out.

Log line template (values as a single-line JSON object):
    <timestamp> READS: {"<host-0>": <value>, "<host-1>": <value>, "<host-n>": <value>}
"""

import ipaddress
import json
import os
import stat
import sys
from datetime import datetime
from time import sleep
from typing import Dict, List, Tuple

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


def _seed_config(base_config: Dict, endpoint: str) -> Dict:
    """Return a connector config for a seed endpoint (host:port or file://socket)."""
    config = dict(base_config)
    if endpoint.startswith("file://"):
        config["unix_socket"] = endpoint[7:]
    else:
        host, port = endpoint.rsplit(":", 1)
        config["host"] = host
        config["port"] = port
    return config


def _short_host(host: str) -> str:
    """Return the leading hostname label, leaving IP addresses intact."""
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        return host.split(".")[0]


def _member_config(base_config: Dict, host: str, port) -> Dict:
    """Return a connector config targeting a single group member."""
    config = dict(base_config)
    config["host"] = host
    config["port"] = port
    return config


def _discover_members(base_config: Dict, seed_endpoints: List[str]) -> List[Tuple[str, int]]:
    """Discover Group Replication members, returning a list of (host, port).

    Tries each seed endpoint until one answers, then returns the members it
    reports. Returns an empty list when no seed is reachable.
    """
    for endpoint in seed_endpoints:
        try:
            with MySQLConnector(_seed_config(base_config, endpoint), commit=False) as cursor:
                cursor.execute(
                    "SELECT MEMBER_HOST, MEMBER_PORT "
                    "FROM performance_schema.replication_group_members"
                )
                rows = cursor.fetchall()
        except Exception:
            continue

        members = [(row[0], row[1]) for row in rows if row[0]]
        if members:
            return members
    return []


def _read_last_value(member_config: Dict, table_name: str) -> int:
    """Return the max value written to the table, or ``-1`` on timeout/error."""
    try:
        with MySQLConnector(member_config, commit=False) as cursor:
            cursor.execute(f"SELECT MAX(number) FROM `{table_name}`")
            result = cursor.fetchone()
    except Exception:
        return -1

    if not result or result[0] is None:
        return -1
    return result[0]


def continuous_reads(
    base_config: Dict,
    seed_endpoints: List[str],
    table_name: str,
    pipe_path: str,
    read_interval: int,
) -> None:
    """Continuously read the last write from every group member, logging to a pipe.

    Args:
        base_config: a dict with MySQL config (user, password, database) shared by members
        seed_endpoints: endpoints (host:port or file://socket) used to discover members
        table_name: the continuous writes table to read from
        pipe_path: path of the named pipe (FIFO) to write log lines to
        read_interval: time to sleep (seconds) between read rounds
    """
    _ensure_pipe(pipe_path)

    last_known_members: List[Tuple[str, int]] = []

    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Re-discover every round so topology changes are picked up; fall back to
        # the last known members when no seed endpoint is reachable
        members = _discover_members(base_config, seed_endpoints) or last_known_members
        last_known_members = members

        readings: Dict[str, int] = {}
        for host, port in members:
            value = _read_last_value(_member_config(base_config, host, port), table_name)
            readings[_short_host(host)] = value

        line = f"{timestamp} READS={json.dumps(readings)}"

        _write_to_pipe(pipe_path, line)

        if read_interval:
            sleep(read_interval / 1000)


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

    seed_endpoints = [ep.strip() for ep in endpoints_csv.split(",") if ep.strip()]

    continuous_reads(base_config, seed_endpoints, table_name, pipe_path, int(read_interval))


if __name__ == "__main__":
    main()
