Usage
==================

.. code-block:: python
   
   import logging
   
   from datetime import timedelta
   from flask import Flask
   
   from FlaskFloodgate import RateLimiter
   from FlaskFloodgate.handlers import Sqlite3Handler
   
   app = Flask(__name__)
   
   # No need to specify all the parameters.
   handler = RateLimiter(
       db=MemoryHandler(),
       amount=20,
       time_window=timedelta(minutes=1),
       block_duration=timedelta(minutes=30), # All parameters below this are optional.
       block_limit=5,
       block_exceed_duration=timedelta(days=1),
       relative_block=True,
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
