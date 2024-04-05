import os
import time
import json
import flask
import logging

from .handlers import DBHandler, IP

from functools import wraps
from threading import Thread
from datetime import timedelta
from typing import Callable, Union, Literal

__all__ = ["RateLimiter"]

class RateLimiter:
    def __init__(
            self,
            db: DBHandler,
            amount: int,
            time_window: timedelta,
            block_limit: int = 5,
            block_exceed_duration: Union[timedelta, Literal["FOREVER"]] = timedelta(days=1),
            relative_block: bool = True,
            block_exceed_reset: bool = True,
            max_window_duration: Union[timedelta, Literal["FOREVER"]] = timedelta(days=2),
            accumulate_requests: bool = False,
            dl_data_wb: bool = True,
            logger: logging.Logger = None,
            export_dir: Union[str, None] = 0
    ) -> None:
        """
        Represents a IP Rate Limit Handler. It helps prevent spam requests and blocks them according to their IPs.
        If an IP passes the specified request limit per specified `time duration`, the IP is blocked for the specified `block duration`.
        If the IP gets blocked more than the specified `block limit`, it is blacklisted. Most of the work is done by the specified `DB` handler.

        :param db: The IP handler to use.
        :type db: class:`FlaskFloodgate.DBHandler`

        :param amount: The maximum amount of requests allowed for an IP in `time_window` time.
        :type amount: int

        :param time_window: The time window in which the specified `amount` requests are allowed.
        :type amount: :class:`datetime.timedelta`

        :param block_limit: The maximum number of times an IP can be blocked, defaults to `5`.
        :type block_limit: int, optional

        :param block_exceed_duration: The time duration for which an IP is blocked if it exceeds the specified `block_limit`. If set to 'FOREVER', it will be blacklisted forever until specifically removed from the blacklist, defaults to :class:`datetime.timedelta(days=1)`.
        :type block_exceed_duration: :class:`Union[datetime.timedelta, Literal['FOREVER']]`, optional

        :param relative_block: If set to `True`, the `block_exceed_duration` timer (if set to a `timedelta` object) will reset and start again everytime the IP sends a request during the ongoing `block_exceed_duration` timer. If set to `False`, the `block_exceed_duration` timer (if set to a `timedelta` object) will not reset and start from the first ever blocked request for the window, defaults to `True`.
        :type relative_block: bool, optional

        :param block_exceed_reset: If set to `True` and an IP exceeds the specified `block limit` and the `block_exceed_duration` is set to a `timedelta` object, then the IP will be blocked by `block_exceed_duration` everytime it exceeds the specified `amount` per specified `time_window`, defaults to `True`.
        :type block_exceed_reset: bool, optional

        :param max_window_duration: The time duration in which a request window data is removed from the DB. (Does not include the Blacklist and Whitelist DB.) Defaults to :class:`datetime.timedelta(days=2)`.
        :type max_window_duration: :class:`Union[datetime.timedelta, Literal['FOREVER']]`, optional

        :param accumulate_requests: If set to `True`, it allows an IP to use the left-over amount of requests from the previous time-window along with the new one, defaults to `True`.
        :type accumulate_requests: bool, optional

        :param dl_data_wb: Indicates whether to delete the IP data when it is blacklisted or whitelisted, defaults to `True`.
        :type dl_data_wb: bool, optional

        :param logger: The logger to use, defaults to `None`.
        :type logger: :class:`logging.Logger`, optional

        :param export_dir: The directory where the parameters will be exported to prevent data-loss in case of a server failure. If set to `None`, the parameters are not exported, defaults to `0` and the parameters are exported to the current working dir.
        :type export_dir: Union[`str`, `None`], optional
        """
        self.db = db
        self.amount = amount
        self.window = time_window.total_seconds()
        self.block_limit = block_limit
        self.bld = block_exceed_duration.total_seconds() if not isinstance(block_exceed_duration, str) else block_exceed_duration
        self.ber = block_exceed_reset
        self.relative_block = relative_block
        self.accumulate = accumulate_requests
        self.ddw = dl_data_wb
        self.logger = logger
        self.rule = None

        self.cmds = ["whitelist", "de-whitelist", "blacklist", "de-blacklist", "help", "exit"]

        self.blacklist = []

        if max_window_duration:
            self.mwd = round(max_window_duration.total_seconds())

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
                        "mwd": self.mwd,
                        "ddw": self.ddw
                    },
                    fp=f,
                    indent=4
                )

            print(f"The Rate-Limit Parameters have been exported to the following file:\n{expfp}\nTo load the parameters, use the `load_params` method. (The db, rule and logger are not exported. They need to be specified when loading.)")

    def load_params(db: DBHandler, export_fp: str = None, rule: Callable[[flask.Request], bool] = None, logger = None):
        """
        Used to load the previously exported parameters.

        :param db: The :class:`DBHandler` previously used. It needs to be specified while loading the parameters as it is not exported.
        :type db: :class:`DBHandler`

        :param export_fp: The path of the JSON file where the exported data was stored. If not specified, looks for `Rate-Limit-Params.json` in the current working dir.
        :type export_fp: str, optional
                
        :param rule: The rule function. It needs to specified (if used earlier) while loading the parameters as it is not exported, defaults to `None`.
        :type rule: Callable[[`Flask.Request`], bool], optional

        :param logger: The logger to use needs to specified (if used earlier) while loading the parameters as the logger is not exported, defaults to `None`.
        :type logger: `logging.Logger`

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

        r = RateLimiter(
            db=db,
            amount=data["amount"],
            time_window=data["window"],
            block_limit=data["block-limit"],
            block_exceed_duration=data["bld"],
            block_exceed_reset=data["ber"],
            relative_block=data["relative-block"],
            accumulate_requests=data["accumulate"],
            max_window_duration=data["mwd"],
            dl_data_wb=data["ddw"],
            logger=logger,
            export_dir=None
        )

        if rule:
            r.set_rule(rule)

        return r

    def log_info(self, msg: str):
        """
        Used to log `INFO` level messages using the logger.
        Helps prevent excess lines of checking if the logger is set or not.

        :param msg: The message to log.
        :type msg: str
        """
        if self.logger:
            self.logger.info(msg)

    def set_rule(self, rule: Callable[[flask.Request], bool], override: bool = False):
        """
        Used to add a function to check for a specific `flask.Request` object data. You can only add one rule.\n
        The function should return a `bool` where `True` indicates that the request is to be exempt from rate-limiting and vice-versa.

        :param func: A function which takes in a `flask.Request` and returns a `bool`.
        :type func: Callable[[`flask.Request`], bool]
        
        :param override: If set to `True`, the previous set `rule` (if exists) will be replaced with the new specified `rule`, defaults to `False`.
        :type override: bool, optional

        :raises ValueError: Indicates that either the specified `rule` is not callable or a rule already exists.
        """
        if not callable(rule):
            raise ValueError("Expected a callable function which takes in `flask.Request` and return a `bool`.")
        
        if self.rule and not override:
            raise ValueError("A rule already exists. To replace it, specify the `override` parameter as `True`.")
        
        self.rule = rule

    def rate_limited_route(self):
        """
        It wraps a `Flask` route and rate-limits the IPs.

        TODO
        ===============
        1. The `self.bld` is added everytime the block limit is exceeded.
        2. Relative block isn't applicable for `self.bld`.

        Usage
        ==========
        .. code-block:: python
           
           from datetime import timedelta
           from FlaskFloodgate import RateLimiter
           from FlaskFloodgate.handlers import MemoryHandler

           rlhandler = RateLimitHandler(
               db=MemoryHandler(),
               amount=30,
               time_window=timedelta(minutes=1) # Configure other params if required
           )

           # Initialization of the `Flask` app and other essentials.

           @app.route("/rate-limited")
           @rate_limited_route()
           def rate_limited():
               return "Hello World!", 200

           if __name__ == "__main__":
               app.run(host="localhost", port=5000)
        """
        def wrapper(func):
            @wraps(func)
            def inner(*args, **kwargs):
                ip_str = flask.request.remote_addr
                crtime = time.time()

                if (self.rule and self.rule(ip_str)) or self.db.is_whitelisted(ip_str):
                    return func(*args, **kwargs)
                
                if self.db.is_blacklisted(ip_str):
                    m = f"IP - '{ip_str}' is already blacklisted."
                    self.log_info(m)
                    return json.dumps({"error": m}), 429
                
                ip = self.db.get_ip(ip_str)
                if not ip or ip.lwrl <= crtime:
                    if not ip:
                        ip = IP()
                        ip.amount = 1
                    else:
                        ip.amount = (1 - ip.amount) if (ip.lwrl <= crtime and self.accumulate) else 1
                    ip.addr = ip_str
                    ip.lwrl = (crtime + self.window)
                    ip.blocked = 0
                    delay = 1
                    for _ in range(5):
                        try:
                            self.db.save_ip(ip)
                            break
                        except Exception as e:
                            self.logger.error("Unable to save data in db.", e)
                            delay *= 2
                            time.sleep(delay)
                    else:
                        self.logger.critical("Unable to save data in db. Attempts maxed!")
                        return json.dumps({"error": "Internal FlaskFloodgate Error"}), 500

                    return func(*args, **kwargs)

                ip.amount += 1
                if ip.amount > self.amount:
                    if (self.relative_block and not ip.amount - 2 >= self.amount): # detects first exceeded request
                        ip.lwrl = (crtime + self.window)

                    ip.amount = self.amount + 1

                    ip.blocked += 1
                    if ip.blocked > self.block_limit:
                        if self.bld == "FOREVER":
                            self.db.blacklist_ip(ip_str, ddw=self.ddw)
                            m = f"IP - '{ip}' has been blacklisted."
                            self.log_info(m)
                            return json.dumps({"error": m}), 429

                        ip.blocked = 0 if self.ber else self.block_limit
                        ip.lwrl += self.bld

                        ip.amount = self.amount + 1


                    self.db.save_ip(ip)
                    m = f"IP - '{ip}' has been rate-limited."
                    self.log_info(m)

                    return json.dumps({"error": m + f"Please wait {round(ip.lwrl - crtime)}s"}), 429
                
                self.db.save_ip(ip)
                return func(*args, **kwargs)
                
            return inner
        return wrapper

    def terminal_op(self):
        """
        Can be used to execute commands during runtime. Is run in a thread.\n

        Currently supported commands:
        =============================
        1. whitelist: To whitelist an IP.
        2. de-whitelist: To de-whitelist an IP.
        3. blacklist: To blacklist an IP.
        4. de-blacklist: To de-blacklist an IP.
        5. help: For help.
        6. exit: To exit the `FlaskFloodgate` terminal.

        Usage
        ==========
        .. code-block:: python

           from FlaskFloodgate import RateLimiter
           from FlaskFloodgate.handlers import MemoryHandler

           rlhandler = RateLimitHandler(
               db=MemoryHandler(),
               amount=30,
               time_window=timedelta(minutes=1) # Configure other params if required
           )

           # Initialization of the `Flask` app and other essentials.

           @app.route("/rate-limited")
           @rate_limited_route()
           def rate_limited():
               return "Hello World!", 200

           if __name__ == "__main__":
               rlhandler.terminal_op()
               app.run(host="localhost", port=5000)
        """
        def inner():
            while True:
                inp = input(">>> ").strip().lower()

                if inp == "whitelist":
                    try:
                        ip = input("Enter IP: ").strip().lower()
                        self.db.whitelist_ip(ip, ddw=self.ddw)
                    except Exception:
                        print(f"Unable to whitelist - '{ip}'. Internal error.\n")
                    else:
                        print(f"'{ip}' has been whitelisted!\n")

                elif inp == "de-whitelist":
                    try:
                        ip = input("Enter IP: ").strip().lower()
                        self.db.de_whitelist_ip(ip)
                    except Exception:
                        print(f"Unable to de-whitelist - '{ip}'. Internal error.\n")
                    else:
                        print(f"'{ip}' has been de-whitelisted!\n")

                elif inp == "blacklist":
                    try:
                        ip = input("Enter IP: ").strip().lower()
                        self.db.blacklist_ip(ip, ddw=self.ddw)
                    except Exception:
                        print(f"Unable to blacklist - '{ip}'. Internal error.\n")
                    else:
                        print(f"'{ip}' has been blacklisted!\n")

                elif inp == "de-blacklist":
                    try:
                        ip = input("Enter IP: ").strip().lower()
                        self.db.de_blacklist_ip(ip)
                    except Exception:
                        print(f"Unable to de-blacklist - '{ip}'. Internal error.\n")
                    else:
                        print(f"'{ip}' has been de-blacklist!\n")

                elif inp == "help":
                    print("Supported Commands:\n1. whitelist: To whitelist an IP.\n2. de-whitelist: To de-whitelist an IP.\n3. blacklist: To blacklist an IP.\n4. de-blacklist: To de-blacklist an IP.\n5. help: For help.\n6. exit: To exit the `FlaskFloodgate` terminal.\n")

                elif inp == "exit":
                    print("Successfully exited `FlaskFloodgate` terminal.\n")
                    break

                else:
                    print("Unsupported command. Use `help` for info.\n")
        
        Thread(target=inner).start()
