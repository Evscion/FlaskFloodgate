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
- **Request Cooldown**: A cooldown after each request.
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


- Restrict a certain amount of requests in a specified time window.
- Add a limit to the number of times an IP can be rate-limited (blocked).
- Punish IPs for exceeding the max number of times an IP can be blocked by either black-listing them or block them for extended duration.
- Set the block duration based on either the first or the last blocked request.
- Set a max duration to the time a request window will be stored in the DB.
- Allow IPs to accumulate requests from past request windows.
- Allow requests with certain data.

# Suggested Features to add
- **Multiple DB**: Implement availability for other DBs.
- **Request Cooldown**: A cooldown after each request.
- **Async functions**: Implement async functions to prevent blocking the main thread.
- **Improved logging**: As of now, only INFO logs are made.
- **Window status**: Indicating whether a request window is 'active' or 'inactive'.
- **Adaptive blocking**: Increase the window/block duration based on the severity level.
- **Cache layer**: Implement a feature to add cache layers (Memory, Redis, etc.).
- **Database connections**: Implement a feature to add backup databases and automatically handle DB fail-overs.
- **Request targeting**: Rate-limit / Block specific requests based on certain traits (geo-blocking, malicious IPs).
- **Grace Period**: A grace period for new or infrequent IPs slightly exceeding the rate-limit for the first time.

# Installation

`pip install FlaskFloodgate`

# Usage

## Using **Sqlite3**
```python
import logging
from datetime import timedelta

from flask import Flask

from FlaskFloodgate import DefaultRateLimitHandler
from FlaskFloodgate.handlers import Sqlite3Handler

app = Flask(__name__)

def check_data(request):
    return request.headers.get('key') == 'value'

# No need to specify all the parameters!
db = Sqlite3Handler(
    fp="ip-data.db",
    table_name='IP_Data',
    amount=20, # All parameters below this are optional parameters.
    time_window=timedelta(minutes=1),
    block_limit=5,
    block_exceed_duration='FOREVER', # Indicates that the IP will be blacklisted.
    relative_block=False,
    block_exceed_reset=True,
    max_window_duration='FOREVER', # Indicates that none of the data will not be removed from the DB.
    accumulate_requests=True,
    request_data_check=check_data, # Function that checks for valid request data.
    logger=logging.Logger("IP-Data")
)

handler = DefaultRateLimitHandler(db=db)

@app.route('/rate-limited')
@handler.rate_limited_route()
def rate_limited():
    return 'Hello!', 200

```

## Using **Memory**
```python
import logging
from datetime import timedelta

from flask import Flask

from FlaskFloodgate import DefaultRateLimitHandler
from FlaskFloodgate.handlers import MemoryHandler

app = Flask(__name__)

# No need to specify all the parameters!
db = MemoryHandler(
    amount=20, # All parameters below this are optional parameters.
    time_window=timedelta(minutes=1),
    block_limit=5,
    block_exceed_duration=timedelta(days=7),
    relative_block=False,
    block_exceed_reset=True,
    max_window_duration=timedelta(days=30),
    accumulate_requests=True,
    logger=logging.Logger("IP-Data")
)

handler = DefaultRateLimitHandler(db=db)

@app.route('/rate-limited')
@handler.rate_limited_route()
def rate_limited():
    return 'Hello!', 200

```

# Documentation
For detailed functions, check out the documentation: [FlaskFloodgate Documentation](https://flaskfloodgate.readthedocs.io/en/latest/introduction.html)

# Contact
You can contact me on my email: ivoscev@gmail.com
