# Introduction

FlaskFloodgate is a small Python package that provides rate limiting functionalities for Flask endpoints.

# Current Features
- Rate limit IPs.
- Restrict a certain amount of requests in a specified time window.
- Add a limit to the number of times an IP can be rate-limited (blocked).
- Punish IPs for exceeding block limit by either black-listing them or blocking them for an extended duration.
- Set the block duration based on either the first or the last blocked request.
- Set a max duration to the time a request window will be stored in the DB.
- Allow IPs to accumulate requests from past request windows.
- Allow requests with certain data.
- Blacklist and whitelist IPs during runtime.

# TODO
- **Multiple DB**: Implement availability for other DBs.
- **Improved logging**: As of now, only INFO logs are made.
- **Adaptive blocking**: Increase the window/block duration based on the severity level.

# Installation

`pip install FlaskFloodgate`

# Usage
```python

import logging

from datetime import timedelta
from flask import Flask

from FlaskFloodgate import RateLimiter
from FlaskFloodgate.handlers import Sqlite3Handler

app = Flask(__name__)

# No need to specify all the parameters.
handler = RateLimiter(
    db=MemoryHandler(),
    amount=20, # All parameters below this are optional.
    time_window=timedelta(minutes=1)
    block_limit=5,
    block_exceed_duration=timedelta(days=1),
    relative_block=True,
    block_exceed_reset=True,
    max_window_duration=timedelta(days=2),
    accumulate_requests=True,
    dl_data_wb=True,
    logger=logging.Logger("FlaskFloodgate"),
    export_dir=os.getcwd()
)

handler = RateLimiter(db=db)

@app.route('/rate-limited')
@handler.rate_limited_route()
def rate_limited():
    return 'Hello!', 200

if __name__ == "__main__":
    app.run(host="localhost")

```

# Documentation
For detailed functions, check out the documentation: [FlaskFloodgate Documentation](https://flaskfloodgate.readthedocs.io/en/latest/introduction.html)

# Contact
You can contact me on my email: ivoscev@gmail.com

# Updates
- # 1.1
- Updated with a runtime terminal.
- Moved rate limiting parameters to the `RateLimiter` handler instead of the `DBHandler`.
- Introduced whitelisting of IPs.
- Introduced `RedisHandler`.

- # 1.0.1
- The first version (with updated PyPI README).

- # 1.0
- The first version.
