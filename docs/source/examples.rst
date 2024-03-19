Usage
=============

Example 1
*************

.. code-block:: python

    """
    This example uses `Sqlite3Handler` as the database handler.
    """
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


Example 2
*************

.. code-block:: python

   """
   This example uses `MemoryHandler` as the database handler.
   """
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
