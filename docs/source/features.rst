Features
===================
- Rate limit IPs.
- Restrict a certain amount of requests in a specified time window.
- Add a limit to the number of times an IP can be rate-limited (blocked).
- Punish IPs for exceeding block limit by either black-listing them or blocking them for an extended duration.
- Set the block duration based on either the first or the last blocked request.
- Set a max duration to the time a request window will be stored in the DB.
- Allow IPs to accumulate requests from past request windows.
- Allow requests with certain data.
- Blacklist and whitelist IPs during runtime.

TODO
====================
- **Multiple DB**: Implement availability for other DBs.
- **Request Cooldown**: A cooldown after each request.
- **Improved logging**: As of now, only INFO logs are made.
- **Adaptive blocking**: Increase the window/block duration based on the severity level.