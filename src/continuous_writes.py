# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""This file is meant to run in the background continuously writing entries to MySQL."""

import sys
from time import sleep
from typing import Dict

import mysql.connector

from connector import MySQLConnector


def continuous_writes(
    database_config: Dict, table_name: str, starting_number: int, sleep_interval: int
) -> None:
    """Continuously write to the MySQL cluster.

    Args:
        database_config: a dictionary with MySQL config to connect to the database
        table_name: the table name to direct continuous writes to
        starting_number: number from which to start writing data to the table (and increment from)
        sleep_interval: the time to sleep (milliseconds) between writes
    """
    try:
        with MySQLConnector(database_config) as cursor:
            cursor.execute(
                (
                    f"CREATE TABLE IF NOT EXISTS `{table_name}`("
                    "id INTEGER NOT NULL AUTO_INCREMENT,"
                    "number INTEGER, "
                    "PRIMARY KEY(id));"
                )
            )
    except Exception:
        pass

    next_value_to_insert = starting_number

    while True:
        try:
            with MySQLConnector(database_config) as cursor:
                cursor.execute(
                    f"INSERT INTO `{table_name}`(number) VALUES ({next_value_to_insert})"
                )
        except mysql.connector.errors.DatabaseError as e:
            if e.errno == 1062:
                try:
                    with MySQLConnector(database_config) as cursor:
                        cursor.execute(f"SELECT max(number) FROM `{table_name}`")
                        result = cursor.fetchall()
                        if result[0][0] is not None:
                            next_value_to_insert = result[0][0] + 1
                except Exception:
                    # Unexpected exception, ignore it to keep going
                    pass
        except Exception:
            # Unexpected exception, ignore it to keep going
            pass
        else:
            next_value_to_insert += 1

        if sleep_interval:
            sleep(sleep_interval / 1000)


def main():
    """Run the continuous writes script."""
    if len(sys.argv) == 9:
        [
            _,
            username,
            password,
            database,
            table_name,
            starting_number,
            sleep_interval,
            host,
            port,
        ] = sys.argv
        socket = None
    else:
        [_, username, password, database, table_name, starting_number, sleep_interval, socket] = (
            sys.argv
        )

    database_config = {
        "user": username,
        "password": password,
        "database": database,
        "use_pure": True,
        "connection_timeout": 5,
    }
    if socket:
        database_config["unix_socket"] = socket
    else:
        database_config["host"] = host
        database_config["port"] = port

    continuous_writes(database_config, table_name, int(starting_number), int(sleep_interval))


if __name__ == "__main__":
    main()
