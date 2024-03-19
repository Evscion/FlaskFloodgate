import json

from .exceptions import *

from flask import request
from functools import wraps

__all__ = ["DefaultRateLimitHandler"]

class DefaultRateLimitHandler:
    def __init__(self, db) -> None:
        """
        Represents a IP Rate Limit Handler. It helps prevent spam requests and blocks them according to their IPs.
        If an IP passes the specified request limit per specified `time duration`, the IP is blocked for the specified `block duration`.
        If the IP gets blocked more than the specified `block limit`, it is blacklisted. Most of the work is done by the specified `DB` handler.

        :param db: The database handler to use.
        :type db: class:`FlaskFloodgate.DBHandler`
        """
        self.db = db

    def rate_limited_route(self):
        """
        It wraps a `Flask` route and rate-limits the IPs.

        Usage
        ==========
        .. code-block:: python
        
           from HTTPE.server.rate_limit import DefaultRateLimitHandler, MemoryHandler

           rlhandler = RateLimitHandler(db=MemoryHandler(...)) # configure as required

           # Initialization of the `Flask` app and other essentials.

           @app.route("/rate-limited")
           @rate_limited_route()
           def rate_limited():
               ... # Your code
        """
        def wrapper(func):
            @wraps(func)
            def inner(*args, **kwargs):
                ip = request.remote_addr

                if self.db.rdc and (self.db.rdc() is True):
                    self.db.log_info(f"Bypassed IP rate-limit check for IP - '{ip}'.")
                    return func(**args, **kwargs)
                
                try:
                    self.db.update_ip(ip)
                except (IPRateLimitExceeded, IPBlackListed) as e:
                    return json.dumps({"error": str(e)}), 429
                except Exception as e:
                    if self.db.logger:
                        self.db.logger.error(f"Unexpected internal error.", exc_info=e)
 
                return func(*args, **kwargs)
            
            return inner
        return wrapper

