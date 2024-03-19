class IPRateLimitExceeded(Exception):
    """
    Indicates that an IP has been rate-limited for exceeding the specified amount of requests per specified request time window.
    """
    pass

class IPBlackListed(Exception):
    """
    Indicates that an IP has been black-listed for exceeding the specified max number of times an IP can be blocked.
    """
    pass