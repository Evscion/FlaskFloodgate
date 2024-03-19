import os
import time
import json
import sqlite3
import logging

from .exceptions import *

from flask import Request
from typing import Literal, Callable, Union
from threading import Thread
from datetime import timedelta
from abc import ABC, abstractmethod
from contextlib import contextmanager

__all__ = ["DBHandler", "MemoryHandler", "Sqlite3Handler"]

class DBHandler(ABC):   
    """
    The storage handler for the rate-limit handler. You can create your own custom subclass and use it accordingly.

    Default Handlers provided
    *************************
        :clasS:`MemoryHandler`\n
        :clasS:`Sqlite3Handler`

    :TODO: Add support for `JSON`.
    """
    @classmethod
    @abstractmethod
    def update_ip(self, ip: str):
        """
        Used to save / update data regarding an `IP`.

        :param ip: The IP to store / update data about.
        :type ip: str

        :raises IPRateLimitExceeded: Indicates that the IP has exceeded the specified rate limit.
        :raises IPBlackListed: Indicates that the IP has been blacklisted for exceeding the specified block limit.
        :raises NotImplementedError: Indicates that the custom subclass has not implemented this method.                
        """
        raise NotImplementedError("Custom subclass must implement `update_ip`.")
    
    @classmethod
    @abstractmethod
    def blacklist_ip(self, ip: str):
        """
        Used to blacklist an `IP`.

        :param ip: The IP to blacklist.
        :type ip: str

        :raises NotImplementedError: Indicates that the custom subclass has not implemented this method.
        """
        raise NotImplementedError("Custom subclass must implement `blacklist_ip`.")
    
class MemoryHandler(DBHandler):
    def __init__(
            self,
            amount: int,
            time_window: timedelta,
            block_limit: int = 5,
            block_exceed_duration: Union[timedelta, Literal["FOREVER"]] = timedelta(days=1),
            relative_block: bool = True,
            block_exceed_reset: bool = True,
            max_window_duration: Union[timedelta, Literal["FOREVER"]] = timedelta(days=1),
            accumulate_requests: bool = False,
            request_data_check: Callable[[Request], bool] = None,
            logger: logging.Logger = None,
            export_dir: Union[str, None] = 0
        ) -> None:
        """
        A custom subclass of `DBHandler`. Represents a `RAM / Memory` Handler for IP-related data.

        :param amount: The maximum amount of requests allowed for an IP in `time_window` time.
        :type amount: int

        :param time_window: The time window in which the `amount` requests is allowed.
        :type amount: :class:`datetime.timedelta`

        :param block_limit: The maximum number of times an IP can be blocked, defaults to `5`.
        :type block_limit: int, optional

        :param block_exceed_duration: The time duration for which the IP is blocked when it exceeds the specified `block_limit`. If set to 'FOREVER', as the name implies, it will be blacklisted forever until specifically removed from the blacklist, defaults to :class:`datetime.timedelta(days=1)`.
        :type block_exceed_duration: Union[:class:`datetime.timedelta`, Literal['FOREVER']], optional

        :param relative_block: If set to `True`, the `block_exceed_duration` timer (if set to a `timedelta` object) will reset and start again everytime the IP sends a request during the ongoing `block_exceed_duration` timer. If set to `False`, the `block_exceed_duration` timer (if set to a `timedelta` object) will not reset and start from the first ever blocked request for the window, defaults to `True`.
        :type relative_block: bool, optional

        :param block_exceed_reset: If an IP exceeds the specified `block limit` and the `block_exceed_duration` is set to a `timedelta` object, then the IP will be blocked by `block_exceed_duration` everytime it exceeds the specified `amount` per specified `time_window`, defaults to `True`.
        :type block_exceed_reset: bool, optional

        :param max_window_duration: The time duration in which a request window data is removed from the DB. (Does not include the Blacklist DB.) Defaults to :class:`datetime.timedelta(days=1)`.
        :type max_window_duration: Union[:class:`datetime.timedelta`, Literal['FOREVER']], optional

        :param accumulate_requests: If set to `True`, it allows an IP to use the left-over amount of requests from the previous time-window along with the new one, defaults to `True`.
        :type accumulate_requests: bool, optional

        :param request_data_check: A function that takes in the `Flask request` as a positional argument and returns a `bool` indicating whether the IP is free from rate-limit checks. If it returns `True`, the IP is excluded from rate-limit checks, defaults to `None`.
        :type request_data_check: Union[function, Callable[[Flask.Request], bool]], optional

        :param logger: The logger to use, defaults to `None`.
        :type logger: :class:`logging.Logger`, optional

        :param export_dir: The directory where the parameters will be exported to prevent data-loss in case of a server failure. If set to `None`, the parameters are not exported, defaults to `0`.
        :type export_dir: Union[str, None], optional
        """
        super().__init__()
        self._cache = {}

        self.amount = amount
        self.window = time_window.total_seconds()
        self.block_limit = block_limit
        self.bld = block_exceed_duration.total_seconds() if not isinstance(block_exceed_duration, str) else block_exceed_duration
        self.ber = block_exceed_reset
        self.relative_block = relative_block
        self.accumulate = accumulate_requests
        self.logger = logger
        self.rdc = request_data_check

        self.blacklist = []

        if max_window_duration:
            self.mwd = round(max_window_duration.total_seconds())
            self.cleanup_thread = Thread(target=self.cleanup)
            self.cleanup_thread.start()

        if export_dir == 0:
            export_dir = os.getcwd()

        if not export_dir is None:
            expfp = os.path.join(export_dir, "Rate-Limit-Params.json")
            with open(expfp, "w") as f:
                json.dump(
                    obj={
                        "amount": self.amount,
                        "window": self.window,
                        "block-limit": block_limit,
                        "bld": self.bld,
                        "ber": self.ber,
                        "relative-block": self.relative_block,
                        "accumulate": accumulate_requests,
                        "mwd": self.mwd
                    },
                    fp=f,
                    indent=4
                )

            print(f"The Rate-Limit Parameters have been exported to the following file:\n{expfp}\nTo load the parameters, use the `load_params` method. (The logger is not exported. You'll need to specify it again when loading the parameters.)")

    def load_params(export_fp: str = None, request_data_check: Callable[[Request], bool] = None, logger = None):
        """
        Used to load the previously exported parameters.

        :param export_fp: The path of the JSON file where the exported data was stored. If not specified, looks for `Rate-Limit-Params.json` in the current working dir.
        :type export_fp: str
                
        :param request_data_check: The function to check validity of request. It needs to specified (if used earlier) while loading the parameters as it is not exported, defaults to `None`.
        :type request_data_check: Union[function, Callable[[Flask.Request], bool]], optional

        :param logger: The logger to use needs to specified (if used earlier) while loading the parameters as the logger is not exported, defaults to `None`.
        :type logger: logging.Logger

        :raises ValueError: Indicates that there is something wrong with the `export_fp`.
        :raises json.JSONDecodeError: Indicates that the `export_fp` does not contain valid JSON data.
        :raises KeyError: Indicates that the data stored in the file was invalid.
        """
        if not export_fp:
            export_fp = os.path.join(os.getcwd(), "Rate-Limit-Params.json")
            if not os.path.exists(export_fp):
                raise ValueError("`export_fp` parameter was not defined and the current working directory does not contain `Rate-Limit-Params.json`.")
            
        if not os.path.exists(export_fp):
            raise ValueError("Invalid `export_fp`. The path specified does not exist.")
        
        with open(export_fp, "r") as f:
            data = json.load(f)

        return MemoryHandler(
            amount=data["amount"],
            time_window=data["window"],
            block_limit=data["block-limit"],
            block_exceed_duration=data["bld"],
            block_exceed_reset=data["ber"],
            relative_block=data["relative-block"],
            accumulate_requests=data["accumulate"],
            max_window_duration=data["mwd"],
            request_data_check=request_data_check,
            logger=logger,
            export_dir=None
        )

    def log_info(self, msg: str):
        """
        Used to log `INFO` level messages using the logger.
        Helps prevent excess lines of checking if the logger is set or not.

        :param msg: The message to log.
        :type msg: str
        """
        if self.logger:
            self.logger.info(msg)

    def cleanup(self):
        """
        The cleanup function that is run in a thread and cleans up `expired` request windows if the following inequality is true:\n
        `request_window_init_time + max_window_duration < current_time`\n
        Is only run if `max_window_duration != 'FOREVER'`.        
        """
        while True:
            time.sleep(self.mwd)
            self.log_info(f"Cleaning up request windows.")
            crtime = time.time()
            ol = len(self._cache)
            self._cache = {
                ip: data for ip, data in self._cache.items() if (data["last-window-request-limit"] + self.mwd) > crtime
            }
            self.log_info(f"({ol - len(self._cache)}) Request windows cleaned.")

    def update_ip(self, ip: str):
        """
        Used to save / update data regarding an `IP`.

        :param ip: The IP to store / update data about.
        :type ip: str

        :raises IPRateLimitExceeded: Indicates that the IP has exceeded the specified rate limit.
        :raises IPBlackListed: Indicates that the IP has been blacklisted for exceeding the specified block limit. 
        """
        crtime = time.time()

        if ip in self.blacklist:
            self.log_info(f"IP - '{ip}' sent a request when it is already blacklisted.")
            raise IPBlackListed(f"IP - '{ip}' is already blacklisted for exceeding the `block_limit`.")

        if not ip in self._cache or self._cache[ip]["last-window-request-limit"] <= crtime:
            org_amt = self._cache[ip]["amount"]
            self._cache[ip] = {
                "amount": (1 - (self.amount - org_amt)) if self.accumulate and not org_amt > self.amount else 0,
                "last-window-request-limit": (crtime + self.window),
                "blocked": 0
            }
            return
        
        ip_data = self._cache[ip]
        ip_data["amount"] += 1

        if ip_data["amount"] > self.amount:
            if not self.relative_block and ip_data["amount"] - 2 >= self.amount:
                ip_data["amount"] = self.amount + 1
            else:
                ip_data["last-window-request-limit"] = (crtime + self.window)

            ip_data["blocked"] += 1

            if ip_data["blocked"] > self.block_limit:
                if self.bld == "FOREVER":
                    del self._cache[ip]
                    self.blacklist_ip(ip)

                    self.log_info(f"IP - '{ip}' has been blacklisted.")
                    raise IPBlackListed(f"IP - '{ip}' has been blacklisted for exceeding the `block_limit` i.e. {self.block_limit}.")
                
                ip_data["blocked"] = 0 if self.ber else self.block_limit
                ip_data["last-window-request-limit"] += self.bld
                self._cache[ip] = ip_data

                self.log_info(f"IP - '{ip}' has been rate-limited.")
                raise IPRateLimitExceeded(f"IP - '{ip}' has been rate-limited. Please wait {round(ip_data['last-window-request-limit'] - crtime)}s.")
            
            self._cache[ip] = ip_data
            self.log_info(f"IP - '{ip}' has been rate-limited.")
            raise IPRateLimitExceeded(f"IP - '{ip}' has been rate-limited. Please wait {round(ip_data['last-window-request-limit'] - crtime)}s.")

        self._cache[ip] = ip_data

    def blacklist_ip(self, ip: str):
        """
        Used to blacklist an `IP`.

        :param ip: The IP to blacklist.
        :type ip: str
        """
        self._cache.pop(ip, None)
        self.blacklist.append(ip)

class Sqlite3Handler(DBHandler):
    def __init__(
            self,
            fp: str,
            table_name: str,
            amount: int,
            time_window: timedelta,
            block_limit: int = 5,
            block_exceed_duration: Union[timedelta, Literal["FOREVER"]] = timedelta(days=1),
            relative_block: bool = True,
            block_exceed_reset: bool = True,
            max_window_duration: Union[timedelta, Literal["FOREVER"]] = timedelta(days=7),
            accumulate_requests: bool = False,
            request_data_check: Callable[[Request], bool] = None,
            logger: logging.Logger = None,
            export_dir: Union[str, None] = 0
        ) -> None:
        """
        A custom subclass of `DBHandler`. Represents an `Sqlite3` Handler for IP-related data.

        :param fp: The file-path of the `.db` file.
        :type fp: str

        :param table_name: The name of the table.
        :type table_name: str

        :param amount: The maximum amount of requests allowed for an IP in `time_window` time.
        :type amount: int

        :param time_window: The time window in which the `amount` requests is allowed.
        :type amount: :class:`datetime.timedelta`

        :param block_limit: The maximum number of times an IP can be blocked, defaults to `5`.
        :type block_limit: int, optional

        :param block_exceed_duration: The time duration for which the IP is blocked when it exceeds the specified `block_limit`. If set to 'FOREVER', as the name implies, it will be blacklisted forever until specifically removed from the blacklist, defaults to :class:`datetime.timedelta(days=1)`.
        :type block_exceed_duration: Union[:class:`datetime.timedelta`, Literal['FOREVER']], optional

        :param relative_block: If set to `True`, the `block_exceed_duration` timer (if set to a `timedelta` object) will reset and start again everytime the IP sends a request during the ongoing `block_exceed_duration` timer. If set to `False`, the `block_exceed_duration` timer (if set to a `timedelta` object) will not reset and start from the first ever blocked request for the window, defaults to `True`.
        :type relative_block: bool, optional

        :param block_exceed_reset: If an IP exceeds the specified `block limit` and the `block_exceed_duration` is set to a `timedelta` object, then the IP will be blocked by `block_exceed_duration` everytime it exceeds the specified `amount` per specified `time_window`, defaults to `True`.
        :type block_exceed_reset: bool, optional

        :param max_window_duration: The time duration in which a request window data is removed from the DB. (Does not include the Blacklist DB.) Defaults to :class:`datetime.timedelta(days=1)`.
        :type max_window_duration: Union[:class:`datetime.timedelta`, Literal['FOREVER']], optional

        :param accumulate_requests: If set to `True`, it allows an IP to use the left-over amount of requests from the previous time-window along with the new one, defaults to `True`.
        :type accumulate_requests: bool, optional

        :param request_data_check: A function that takes in the `Flask request` as a positional argument and returns a `bool` indicating whether the IP is free from rate-limit checks. If it returns `True`, the IP is excluded from rate-limit checks, defaults to `None`.
        :type request_data_check: Union[function, Callable[[Flask.Request], bool]], optional

        :param logger: The logger to use, defaults to `None`.
        :type logger: :class:`logging.Logger`, optional

        :param export_dir: The directory where the parameters will be exported to prevent data-loss in case of a server failure. If set to `None`, the parameters are not exported, defaults to `0`.
        :type export_dir: Union[str, None], optional
        """
        self._fp = fp
        self.table = table_name

        with self._connect() as (conn, cursor):
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table} (
                    ip TEXT PRIMARY KEY,
                    amount INTEGER,
                    last_window_request_limit INTEGER,
                    blocked INTEGER
                )
            """)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table}Blacklist (
                    ip TEXT NOT NULL
                )
            """)
            conn.commit()

        self.amount = amount
        self.window = time_window.total_seconds()
        self.block_limit = block_limit
        self.bld = block_exceed_duration.total_seconds() if not isinstance(block_exceed_duration, str) else block_exceed_duration
        self.ber = block_exceed_reset
        self.relative_block = relative_block
        self.accumulate = accumulate_requests
        self.logger = logger
        self.rdc = request_data_check

        if max_window_duration != 'FOREVER':
            self.mwd = round(max_window_duration.total_seconds())
            self.cleanup_thread = Thread(target=self.cleanup)
            self.cleanup_thread.start()

        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        if export_dir == 0:
            export_dir = os.getcwd()

        if not export_dir is None:
            expfp = os.path.join(export_dir, "Rate-Limit-Params.json")
            with open(expfp, "w") as f:
                json.dump(
                    obj={
                        "fp": self._fp,
                        "table": self.table,
                        "amount": self.amount,
                        "window": self.window,
                        "block-limit": block_limit,
                        "bld": self.bld,
                        "ber": self.ber,
                        "relative-block": self.relative_block,
                        "accumulate": accumulate_requests,
                        "mwd": self.mwd
                    },
                    fp=f,
                    indent=4
                )

            print(f"The Rate-Limit Parameters have been exported to the following file:\n{expfp}\nTo load the parameters, use the `load_params` method. (The logger is not exported. You'll need to specify it again when loading the parameters.)")

    def load_params(export_fp: str = None, request_data_check: Callable[[Request], bool] = None, logger = None):
        """
        Used to load the previously exported parameters.

        :param export_fp: The path of the JSON file where the exported data was stored. If not specified, looks for `Rate-Limit-Params.json` in the current working dir.
        :type export_fp: str
                
        :param request_data_check: The function to check validity of request. It needs to specified (if used earlier) while loading the parameters as it is not exported, defaults to `None`.
        :type request_data_check: Union[function, Callable[[Flask.Request], bool]], optional

        :param logger: The logger to use needs to specified (if used earlier) while loading the parameters as the logger is not exported, defaults to `None`.
        :type logger: logging.Logger

        :raises ValueError: Indicates that there is something wrong with the `export_fp`.
        :raises json.JSONDecodeError: Indicates that the `export_fp` does not contain valid JSON data.
        :raises KeyError: Indicates that the data stored in the file was invalid.
        """
        if not export_fp:
            export_fp = os.path.join(os.getcwd(), "Rate-Limit-Params.json")
            if not os.path.exists(export_fp):
                raise ValueError("`export_fp` parameter was not defined and the current working directory does not contain `Rate-Limit-Params.json`.")
            
        if not os.path.exists(export_fp):
            raise ValueError("Invalid `export_fp`. The path specified does not exist.")
        
        with open(export_fp, "r") as f:
            data = json.load(f)

        return Sqlite3Handler(
            fp=data["fp"],
            table_name=data["table"],
            amount=data["amount"],
            time_window=data["window"],
            block_limit=data["block-limit"],
            block_exceed_duration=data["bld"],
            block_exceed_reset=data["ber"],
            relative_block=data["relative-block"],
            accumulate_requests=data["accumulate"],
            max_window_duration=data["mwd"],
            request_data_check=request_data_check,
            logger=logger,
            export_dir=None
        )

    def log_info(self, msg: str):
        """
        Used to log `INFO` level messages using the logger.
        Helps prevent excess lines of checking if the logger is set or not.

        :param msg: The message to log.
        :type msg: str
        """
        if self.logger:
            self.logger.info(msg)

    def cleanup(self):
        """
        The cleanup function that is run in a thread and cleans up `expired` request windows if the following inequality is true:\n
        `request_window_init_time + max_window_duration < current_time`\n
        Is only run if `max_window_duration != 'FOREVER'`.
        """
        while True:
            time.sleep(self.mwd)
            with self._connect() as (conn, cursor):
                self.log_info(f"Cleaning up request windows.")
                cursor.execute(f"DELETE FROM {self.table} WHERE last_window_request_limit <= ?", (round(time.time()) - self.mwd,))
                conn.commit()
                self.log_info(f"(?) Request windows cleaned.")

    def update_ip(self, ip: str):
        """
        Used to save / update data regarding an `IP`.

        :param ip: The IP to store / update data about.
        :type ip: str

        :raises IPRateLimitExceeded: Indicates that the IP has exceeded the specified rate limit.
        :raises IPBlackListed: Indicates that the IP has been blacklisted for exceeding the specified block limit. 
        """
        crtime = time.time()

        with self._connect() as (conn, cursor):
            cursor.execute(f"SELECT * FROM {self.table}Blacklist WHERE ip = ?", (ip,))
            if cursor.fetchone():
                self.log_info(f"IP - '{ip}' sent a request when it is already blacklisted.")
                raise IPBlackListed(f"IP - '{ip}' is already blacklisted for exceeding the `block_limit`.")
            
            cursor.execute(f"SELECT * FROM {self.table} WHERE ip = ?", (ip,))
            result = cursor.fetchone()

            if not result:
                cursor.execute(
                    f"INSERT INTO {self.table} (ip, amount, last_window_request_limit, blocked) VALUES (?, ?, ?, ?)",
                    (ip, 1, round(crtime + self.window), 0)
                )
                conn.commit()
                return
            elif result[2] <= crtime:
                a = (1 - (self.amount - result[1])) if self.accumulate and not result[1] > self.amount else 0
                self.update_result([ip, a, round(crtime + self.window), 0], conn, cursor)
                return
            
            result = list(result)
            
            result[1] += 1

            if result[1] > self.amount:
                if not self.relative_block and result[1] - 2 >= self.amount:
                    result[1] = self.amount + 1
                else:
                    result[2] = round(crtime + self.window)

                result[3] += 1

                if result[3] > self.block_limit:
                    if self.bld == "FOREVER":
                        self.delete_ip(ip, conn, cursor)
                        self.blacklist_ip(ip, conn, cursor)

                        self.log_info(f"IP - '{ip}' has been blacklisted.")
                        raise IPBlackListed(f"IP - '{ip}' has been blacklisted for exceeding the `block_limit` i.e. {self.block_limit}.")
                    
                    result[3] = 0 if self.ber else self.block_limit
                    result[2] += self.bld
                    self.update_result(result, conn, cursor)

                    self.log_info(f"IP - '{ip}' has been rate-limited.")
                    raise IPRateLimitExceeded(f"IP - '{ip}' has been rate-limited. Please wait {round(result[2] - crtime)}s.")
                
                self.update_result(result, conn, cursor)
                self.log_info(f"IP - '{ip}' has been rate-limited.")
                raise IPRateLimitExceeded(f"IP - '{ip}' has been rate-limited. Please wait {round(result[2] - crtime)}s.")

            self.update_result(result, conn, cursor)

    def update_result(self, data: Union[list, tuple], conn: sqlite3.Connection, cursor: sqlite3.Cursor):
        """
        Used to `UPDATE` a result in the DB.
        Helps prevent excess lines of code.

        :param data: The data to insert by updating.
        :type data: Union[list, tuple]

        :param conn: The Sqlite3 Database connection.
        :type conn: sqlite3.Connection

        :param cursor: The Sqlite3 Database connection cursor.
        :type cursor: sqlite3.Cursor
        """
        cursor.execute(
            f"UPDATE {self.table} SET ip = ?, amount = ?, last_window_request_limit = ?, blocked = ?",
            (data[0], data[1], data[2], data[3])
        )
        conn.commit()

    def delete_ip(self, ip: str, conn: sqlite3.Connection = None, cursor: sqlite3.Cursor = None):
        """
        Used to remove an IP from the DB.

        :param ip: The IP to remove.
        :type ip: str

        :param conn: The Sqlite3 Database connection, defaults to `None`.
        :type conn: sqlite3.Connection, optional

        :param cursor: The Sqlite3 Database connection cursor, defaults to `None`.
        :type cursor: sqlite3.Cursor, optional
        """
        if conn and cursor:
            cursor.execute(f"DELETE FROM {self.table} WHERE ip = ?", (ip,))
            conn.commit()
        else:
            with self._connect() as (conn, cursor):
                cursor.execute(f"DELETE FROM {self.table} WHERE ip = ?", (ip,))
                conn.commit()

    def blacklist_ip(self, ip: str, conn: sqlite3.Connection = None, cursor: sqlite3.Cursor = None):
        """
        Used to blacklist an `IP`.

        :param ip: The IP to blacklist.
        :type ip: str

        :param conn: The Sqlite3 Database connection, defaults to `None`.
        :type conn: sqlite3.Connection, optional

        :param cursor: The Sqlite3 Database connection cursor, defaults to `None`.
        :type cursor: sqlite3.Cursor, optional
        """
        if conn and cursor:
            cursor.execute(f"INSERT INTO {self.table}Blacklist (ip) VALUES (?)", (ip,))
            conn.commit()
        else:
            with self._connect() as (conn, cursor):
                cursor.execute(f"INSERT INTO {self.table}Blacklist (ip) VALUES (?)", (ip,))
                conn.commit()

    @contextmanager
    def _connect(self):
        """
        A context manager for Sqlite3 Database Connections.

        :return: A tuple object consisting of an Sqlite3 connection (at 0th index) and Sqlite3 connection cursor (at 1st index).
        :rtype: tuple[sqlite3.Connection, sqlite3.Cursor]
        """
        conn = sqlite3.connect(self._fp)
        cursor = conn.cursor()
        try:
            yield (conn, cursor)
        finally:
            cursor.close()
            conn.close()