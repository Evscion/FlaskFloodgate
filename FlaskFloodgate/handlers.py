import json
import redis
import sqlite3

from abc import ABC, abstractmethod
from contextlib import contextmanager

__all__ = ["DBHandler", "MemoryHandler", "Sqlite3Handler"]

class IP:
    """
    Represents an IP.
    """
    addr: str = ""
    amount: int
    lwrl: float | int
    blocked: int

class DBHandler(ABC):
    """
    The storage handler for the rate-limit handler. You can create your own custom subclass and use it accordingly.

    Default Handlers provided
    *************************
        :class:`MemoryHandler`\n
        :class:`Sqlite3Handler`\n
        :class:`RedisHandler`

    :TODO: Add support for `JSON`.
    """
    @classmethod
    @abstractmethod
    def is_whitelisted(self, ip: str) -> bool:
        """
        Used to check if an IP is whitelisted or not.

        :param ip: The IP to check.
        :type ip: str

        :return: A boolean value indicating whether the IP is whitelisted or not.
        :rtype: bool

        :raises NotImplementedError: Indicates that custom subclass has not implemented this method. 
        """
        raise NotImplementedError("Custom subclass must implement `is_whitelisted`.")
    
    @classmethod
    @abstractmethod
    def is_blacklisted(self, ip: str) -> bool:
        """
        Used to check if an IP is blacklisted or not.

        :param ip: The IP to check.
        :type ip: str

        :return: A boolean value indicating whether the IP is blacklisted or not.
        :rtype: bool

        :raises NotImplementedError: Indicates that custom subclass has not implemented this method. 
        """
        raise NotImplementedError("Custom subclass must implement `is_blacklisted`.")
    
    @classmethod
    @abstractmethod
    def get_ip(self, ip: str) -> IP | None:
        """
        Used to get an :class:`IP`.

        :param ip: The IP to get.
        :type ip: str

        :return: The retrieved :class:`IP` or `None` (if not found).
        :rtype: Union[:class:`IP`, `None`]

        :raises NotImplementedError: Indicates that custom subclass has not implemented this method. 
        """
        raise NotImplementedError("Custom subclass must implement `get_ip`.")
    
    @classmethod
    @abstractmethod
    def save_ip(self, ip) -> None:
        """
        Used to save an :class:`IP`.

        :param ip: The IP to save.
        :type ip: :class:`IP`

        :raises NotImplementedError: Indicates that custom subclass has not implemented this method. 
        """
        raise NotImplementedError("Custom subclass must implement `save_ip`.")
    
    @classmethod
    @abstractmethod
    def blacklist_ip(self, ip: str, ddw: bool = True) -> None:
        """
        Used to blacklist an `IP`.

        :param ip: The IP to blacklist.
        :type ip: str

        :param ddw: Indicates whether to delete the IP data when it is blacklisted, defaults to `True`.
        :type ddw: bool, optional

        :raises NotImplementedError: Indicates that the custom subclass has not implemented this method.
        """
        raise NotImplementedError("Custom subclass must implement `blacklist_ip`.")
    
    @classmethod
    @abstractmethod
    def de_blacklist_ip(self, ip: str) -> None:
        """
        Used to de-blacklist an `IP`.

        :param ip: The IP to de-blacklist.
        :type ip: str

        :raises NotImplementedError: Indicates that the custom subclass has not implemented this method.
        """
        raise NotImplementedError("Custom subclass must implement `de_blacklist_ip`.")
    
    @classmethod
    @abstractmethod
    def whitelist_ip(self, ip: str, ddw: bool = True) -> None:
        """
        Used to whitelist an `IP`.

        :param ip: The IP to de-whitelist.
        :type ip: str

        :param ddw: Indicates whether to delete the IP data when it is whitelisted, defaults to `True`.
        :type ddw: bool, optional

        :raises NotImplementedError: Indicates that the custom subclass has not implemented this method.
        """
        raise NotImplementedError("Custom subclass must implement `whitelist_ip`.")
    
    @classmethod
    @abstractmethod
    def de_whitelist_ip(self, ip: str) -> None:
        """
        Used to de-whitelist an `IP`.

        :param ip: The IP to whitelist.
        :type ip: str

        :raises NotImplementedError: Indicates that the custom subclass has not implemented this method.
        """
        raise NotImplementedError("Custom subclass must implement `de_whitelist_ip`.")

class RedisHandler(DBHandler):
    def __init__(self, redis_url: str):
        """
        A custom subclass of `DBHandler`. Represents a `Redis` Handler for IP-related data.

        :param redis_url: The URL of the redis connection.
        :type redis_url: str
        """
        super().__init__()
        self.conn: redis.Redis = redis.from_url(redis_url)

    def is_whitelisted(self, ip: str):
        """
        Used to check if an IP is whitelisted or not.

        :param ip: The IP to check.
        :type ip: str

        :return: A boolean value indicating whether the IP is whitelisted or not.
        :rtype: bool
        """
        if self.conn.get(f"whitelist:{ip}"):
            return True
        return False
    
    def is_blacklisted(self, ip: str):
        """
        Used to check if an IP is blacklisted or not.

        :param ip: The IP to check.
        :type ip: str

        :return: A boolean value indicating whether the IP is blacklisted or not.
        :rtype: bool
        """
        if self.conn.get(f"blacklist:{ip}"):
            return True
        return False
    
    def get_ip(self, ip: str):
        """
        Used to get an :class:`IP`.

        :param ip: The IP to get.
        :type ip: str

        :return: The retrieved :class:`IP` or `None` (if not found).
        :rtype: Union[:class:`IP`, `None`]
        """
        res = self.conn.get(ip)
        if res:
            res = json.loads(res)
            ip: IP = IP()

            ip.addr = res["addr"]
            ip.amount = res["amount"]
            ip.lwrl = res["lwrl"]
            ip.blocked = res["blocked"]

            return ip
        else:
            return None
        
    def save_ip(self, ip: IP):
        """
        Used to save an :class:`IP`.

        :param ip: The IP to save.
        :type ip: :class:`IP`
        """
        data = {
            "addr": ip.addr,
            "amount": ip.amount,
            "lwrl": ip.lwrl,
            "blocked": ip.blocked
        }
        self.conn.setex(ip.addr, int(ip.lwrl), json.dumps(data))

    def blacklist_ip(self, ip: str, ddw: bool = True):
        """
        Used to blacklist an `IP`.

        :param ip: The IP to blacklist.
        :type ip: str

        :param ddw: Indicates whether to delete the IP data when it is blacklisted, defaults to `True`.
        :type ddw: bool, optional
        """
        if ddw:
            self.conn.delete(ip, f"whitelist:{ip}")
        self.conn.set(f"blacklist:{ip}", "blacklist")

    def de_blacklist_ip(self, ip: str) -> None:
        """
        Used to de-blacklist an `IP`.

        :param ip: The IP to de-blacklist.
        :type ip: str
        """
        self.conn.delete(f"blacklist:{ip}")

    def whitelist_ip(self, ip: str, ddw: bool = True):
        """
        Used to whitelist an `IP`.

        :param ip: The IP to whitelist.
        :type ip: str

        :param ddw: Indicates whether to delete the IP data when it is whitelisted, defaults to `True`.
        :type ddw: bool, optional
        """
        if ddw:
            self.conn.delete(ip, f"blacklist:{ip}")
        self.conn.set(f"whitelist:{ip}", "whitelist")

    def de_whitelist_ip(self, ip: str) -> None:
        """
        Used to de-whitelist an `IP`.

        :param ip: The IP to whitelist.
        :type ip: str
        """
        self.conn.delete(f"whitelist:{ip}")

class MemoryHandler(DBHandler):
    def __init__(self):
        """
        A custom subclass of `DBHandler`. Represents a `RAM / Memory` Handler for IP-related data.
        """
        super().__init__()

        self._cache = {}
        self._blacklist = []
        self._whitelist = []

    def is_whitelisted(self, ip: str):
        """
        Used to check if an IP is whitelisted or not.

        :param ip: The IP to check.
        :type ip: str

        :return: A boolean value indicating whether the IP is whitelisted or not.
        :rtype: bool
        """
        return ip in self._whitelist
    
    def is_blacklisted(self, ip: str):
        """
        Used to check if an IP is blacklisted or not.

        :param ip: The IP to check.
        :type ip: str

        :return: A boolean value indicating whether the IP is blacklisted or not.
        :rtype: bool
        """
        return ip in self._blacklist
    
    def save_ip(self, ip: IP):
        """
        Used to save an :class:`IP`.

        :param ip: The IP to save.
        :type ip: :class:`IP`
        """
        self._cache.update({ip.addr: ip})

    def get_ip(self, ip: str):
        """
        Used to get an :class:`IP`.

        :param ip: The IP to get.
        :type ip: str

        :return: The retrieved :class:`IP` or `None` (if not found).
        :rtype: Union[:class:`IP`, `None`]
        """
        return self._cache.get(ip, None)
    
    def blacklist_ip(self, ip: str, ddw: bool = True):
        """
        Used to blacklist an `IP`.

        :param ip: The IP to blacklist.
        :type ip: str

        :param ddw: Indicates whether to delete the IP data when it is blacklisted, defaults to `True`.
        :type ddw: bool, optional
        """
        self.de_whitelist_ip(ip)

        if not self.is_blacklisted(ip):
            self._blacklist.append(ip)

        if ddw:
            self._cache.pop(ip, None)

    def de_blacklist_ip(self, ip: str) -> None:
        """
        Used to de-blacklist an `IP`.

        :param ip: The IP to de-blacklist.
        :type ip: str
        """
        if self.is_blacklisted(ip):
            self._blacklist.remove(ip)

    def whitelist_ip(self, ip: str, ddw: bool = True):
        """
        Used to whitelist an `IP`.

        :param ip: The IP to whitelist.
        :type ip: str

        :param ddw: Indicates whether to delete the IP data when it is whitelisted, defaults to `True`.
        :type ddw: bool, optional
        """
        self.de_blacklist_ip(ip)

        if not self.is_whitelisted(ip):
            self._whitelist.append(ip)

        if ddw:
            self._cache.pop(ip, None)

    def de_whitelist_ip(self, ip: str) -> None:
        """
        Used to de-whitelist an `IP`.

        :param ip: The IP to whitelist.
        :type ip: str
        """
        if self.is_whitelisted(ip):
            self._whitelist.remove(ip)

class Sqlite3Handler(DBHandler):
    def __init__(self, fp: str, table_name: str, extra_table_name: str, wal_mode: bool = False) -> None:
        """
        A custom subclass of `DBHandler`. Represents an `Sqlite3` Handler for IP-related data.

        :param fp: The file-path of the `.db` file.
        :type fp: str

        :param table_name: The name of the table.
        :type table_name: str

        :param extra_table_name: The name of the extra table where the blacklist and whitelist data are stored.
        :type extra_table_name: str

        :param wal_mode: Indicates whether to set the journal_mode to `wal`, defaults to `False`.
        :type wal_mode: bool, optional
        """
        super().__init__()
        self.fp = fp
        self.table = table_name
        self.extable = extra_table_name

        with self._connect() as (conn, cursor):
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table} (
                    ip TEXT NOT NULL,
                    amount INTEGER,
                    lwrl INTEGER,
                    blocked INTEGER
                )
            """)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.extable} (
                    ip TEXT NOT NULL,
                    data TEXT
                )
            """)

            if wal_mode:
                cursor.execute("PRAGMA journal_mode=WAL")

            conn.commit()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.fp)
        cursor = conn.cursor()
        try:
            yield conn, cursor
        finally:
            cursor.close()
            conn.close()

    def is_whitelisted(self, ip: str):
        """
        Used to check if an IP is whitelisted or not.

        :param ip: The IP to check.
        :type ip: str

        :return: A boolean value indicating whether the IP is whitelisted or not.
        :rtype: bool
        """
        with self._connect() as (conn, cursor):
            cursor.execute(f"SELECT * FROM {self.extable} WHERE ip = ?", (ip,))
            res = cursor.fetchone()

        return res and res[1] == "whitelist"
    
    def is_blacklisted(self, ip: str):
        """
        Used to check if an IP is blacklisted or not.

        :param ip: The IP to check.
        :type ip: str

        :return: A boolean value indicating whether the IP is blacklisted or not.
        :rtype: bool
        """
        with self._connect() as (conn, cursor):
            cursor.execute(f"SELECT * FROM {self.extable} WHERE ip = ?", (ip,))
            res = cursor.fetchone()

        return res and res[1] == "blacklist"
    
    def save_ip(self, ip: IP):
        """
        Used to save an :class:`IP`.

        :param ip: The IP to save.
        :type ip: :class:`IP`
        """
        if not self.get_ip(ip.addr):
            with self._connect() as (conn, cursor):
                cursor.execute(f"INSERT INTO {self.table} (ip, amount, lwrl, blocked) VALUES (?, ?, ?, ?)", (ip.addr, ip.amount, ip.lwrl, ip.blocked))
                conn.commit()
        else:
            with self._connect() as (conn, cursor):
                cursor.execute(f"UPDATE {self.table} SET ip = ?, amount = ?, lwrl = ?, blocked = ?", (ip.addr, ip.amount, ip.lwrl, ip.blocked))

    def get_ip(self, ip: str):
        """
        Used to get an :class:`IP`.

        :param ip: The IP to get.
        :type ip: str

        :return: The retrieved :class:`IP` or `None` (if not found).
        :rtype: Union[:class:`IP`, `None`]
        """
        with self._connect() as (_, cursor):
            cursor.execute(f"SELECT * FROM {self.table} WHERE ip = ?", (ip,))
            res = cursor.fetchone()

        if res:
            ip: IP = IP()
            ip.addr = res[0]
            ip.amount = res[1]
            ip.lwrl = res[2]
            ip.blocked = res[3]
            return ip
        
        return None
    
    def blacklist_ip(self, ip: str, ddw: bool = True):
        """
        Used to blacklist an `IP`.

        :param ip: The IP to blacklist.
        :type ip: str

        :param ddw: Indicates whether to delete the IP data when it is blacklisted, defaults to `True`.
        :type ddw: bool, optional
        """
        if self.is_blacklisted(ip):
            return
        with self._connect() as (conn, cursor):
            if ddw:
                cursor.execute(f"DELETE FROM {self.extable} WHERE ip = ? AND data = 'whitelist'", (ip,))
            cursor.execute(f"INSERT INTO {self.extable} (ip, data) VALUES (?, ?)", (ip, "blacklist"))
            conn.commit()

    def de_blacklist_ip(self, ip: str) -> None:
        """
        Used to de-blacklist an `IP`.

        :param ip: The IP to de-blacklist.
        :type ip: str
        """
        if not self.is_blacklisted(ip):
            return
        with self._connect() as (conn, cursor):
            cursor.execute(f"DELETE FROM {self.extable} WHERE ip = ? AND data = 'blacklist'", (ip,))         
            conn.commit()   

    def whitelist_ip(self, ip: str, ddw: bool = True):
        """
        Used to whitelist an `IP`.

        :param ip: The IP to whitelist.
        :type ip: str

        :param ddw: Indicates whether to delete the IP data when it is whitelisted, defaults to `True`.
        :type ddw: bool, optional
        """
        if self.is_blacklisted(ip):
            return
        with self._connect() as (conn, cursor):
            if ddw:
                cursor.execute(f"DELETE FROM {self.extable} WHERE ip = ? AND data = 'blacklist'", (ip,))
            cursor.execute(f"INSERT INTO {self.extable} (ip, data) VALUES (?, ?)", (ip, "whitelist"))
            conn.commit()

    def de_whitelist_ip(self, ip: str) -> None:
        """
        Used to de-whitelist an `IP`.

        :param ip: The IP to whitelist.
        :type ip: str
        """
        if not self.is_whitelisted(ip):
            return
        with self._connect() as (conn, cursor):
            cursor.execute(f"DELETE FROM {self.table} WHERE ip = ? AND data = 'whitelist'", (ip,))
            conn.commit()
