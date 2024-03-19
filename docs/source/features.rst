Current Features
================
- Rate limit IPs.
- Restrict a certain amount of requests in a specified time window.
- Add a limit to the number of times an IP can be rate-limited (blocked).
- Punish IPs for exceeding the max number of times an IP can be blocked by either black-listing them or block them for extended duration.
- Set the block duration based on either the first or the last blocked request.
- Set a max duration to the time a request window will be stored in the DB.
- Allow IPs to accumulate requests from past request windows.
- Allow requests with certain data.

Suggested Features to add
=========================
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