import json
import redis
import sqlite3

from abc import ABC, abstractmethod
from contextlib import contextmanager

__all__ = ["DBHandler", "MemoryHandler", "Sqlite3Handler", "RedisHandler"]

class IP:
    """
    Represents an IP.
    """
    addr: str
    amount: int
    lwrl: float | int
    blocked: int

class DBHandler(ABC):
    """
    The storage handler for the rate-limit handler. You can create your own custom subclass and use it accordingly.

    Default Handlers provided
    *************************
        :class:`MemoryHandler`\n
        :clasS:`Sqlite3Handler`\n
        :class:`RedisHandler`\n

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
            ip = IP()

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
        self.conn.setex(ip.addr, json.dumps(data), ip.lwrl)

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
    def __init__(self, separate_data: bool = True):
        """
        A custom subclass of `DBHandler`. Represents a `RAM / Memory` Handler for IP-related data.

        :param separate_data: Indicates whether to have different variables for normal data, blacklist and whitelist, defaults to `True`.
        :type separate_data: bool, optional
        """
        super().__init__()

        self._cache = {}
        self._sep = separate_data

        if self._sep:
            self.blacklist = []
            self.whitelist = []

    def is_whitelisted(self, ip: str):
        """
        Used to check if an IP is whitelisted or not.

        :param ip: The IP to check.
        :type ip: str

        :return: A boolean value indicating whether the IP is whitelisted or not.
        :rtype: bool
        """
        return (self._sep and ip in self.whitelist) or self._cache.get(f"whitelist:{ip}")
    
    def is_blacklisted(self, ip: str):
        """
        Used to check if an IP is blacklisted or not.

        :param ip: The IP to check.
        :type ip: str

        :return: A boolean value indicating whether the IP is blacklisted or not.
        :rtype: bool
        """
        return (self._sep and ip in self.blacklist) or self._cache.get(f"blacklist:{ip}")
    
    def save_ip(self, ip: IP):
        """
        Used to save an :class:`IP`.

        :param ip: The IP to save.
        :type ip: :class:`IP`
        """
        self._cache.update({
            ip.addr: {
                "addr": ip.addr,
                "amount": ip.amount,
                "lwrl": ip.lwrl,
                "blocked": ip.blocked
            }
        })

    def get_ip(self, ip: str):
        """
        Used to get an :class:`IP`.

        :param ip: The IP to get.
        :type ip: str

        :return: The retrieved :class:`IP` or `None` (if not found).
        :rtype: Union[:class:`IP`, `None`]
        """
        data = self._cache.get(ip)
        if data:
            ip: IP = IP()
            ip.addr = data["addr"]
            ip.amount = data["amount"]
            ip.lwrl = data["lwrl"]
            ip.blocked = data["blocked"]
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
        if self._sep:
            if ip in self.whitelist:
                self.whitelist.remove(ip)
            if ddw:
                self._cache.pop(ip, None)
            self.blacklist.append(ip)
        else:
            if ddw:
                self._cache.pop(ip, None)
            self._cache.pop(f"whitelist:{ip}", None)
            self._cache.update({f"blacklist:{ip}": ip})

    def de_blacklist_ip(self, ip: str) -> None:
        """
        Used to de-blacklist an `IP`.

        :param ip: The IP to de-blacklist.
        :type ip: str
        """
        if self._sep:
            if ip in self.blacklist:
                self.blacklist.remove(ip)
        else:
            self._cache.pop(f"blacklist:{ip}", None)

    def whitelist_ip(self, ip: str, ddw: bool = True):
        """
        Used to whitelist an `IP`.

        :param ip: The IP to whitelist.
        :type ip: str

        :param ddw: Indicates whether to delete the IP data when it is whitelisted, defaults to `True`.
        :type ddw: bool, optional
        """
        if self._sep:
            if ip in self.blacklist:
                self.blacklist.remove(ip)
            if ddw:
                self._cache.pop(ip, None)
            self.whitelist.append(ip)
        else:
            if ddw:
                self._cache.pop(ip, None)
            self._cache.pop(f"blacklist:{ip}", None)
            self._cache.update({f"whitelist:{ip}": ip})

    def de_whitelist_ip(self, ip: str) -> None:
        """
        Used to de-whitelist an `IP`.

        :param ip: The IP to whitelist.
        :type ip: str
        """
        if self._sep:
            if ip in self.whitelist:
                self.whitelist.remove(ip)
        else:
            self._cache.pop(f"whitelist:{ip}")

class Sqlite3Handler(DBHandler):
    def __init__(self, fp: str, table_name: str, extra_table_name: str) -> None:
        """
        A custom subclass of `DBHandler`. Represents an `Sqlite3` Handler for IP-related data.

        :param fp: The file-path of the `.db` file.
        :type fp: str

        :param table_name: The name of the table.
        :type table_name: str

        :param extra_table_name: The name of the extra table where the blacklist and whitelist data are stored.
        :type extra_table_name: str
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
        if not self.get_ip(ip):
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
            ip.addr = ip[0]
            ip.amount = ip[1]
            ip.lwrl = ip[2]
            ip.blocked = ip[3]
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
