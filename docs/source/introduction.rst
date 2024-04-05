Introduction
============

FlaskFloodgate is a small package to safeguard your Flask applications from excessive requests.
It acts as a gatekeeper, throttling the number of requests an IP address can make within a defined timeframe.
This functionality is crucial for preventing abuse and ensuring a smooth user experience for everyone. 
With its straightforward integration and configuration options, you can setup the Rate Limiting however you like.

While custom-built rate limiters offer fine-grained control tailored to specific application needs, FlaskFloodgate prioritizes a general-purpose design.
This approach strives for broad applicability, accommodating a wide range of use cases.

Installation
============

.. code-block:: shell
    
   pip install FlaskFloodgate