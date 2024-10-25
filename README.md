# SimpleCryptoExchange-Optimisation

This is the repository containing the optimised SimpleCryptoExchange client code.

Steps:
1. pip install -r requirements.txt
2. python simple_rest_server.py
3. python simple_client.py


Changes proposed:
1. Replacing custom RateLimiter with Throttler from the asyncio-throttle library. 
Rationale: The custom RateLimiter works by tracking the latest request's time and ensuring that the difference between the current and the latest request's time is at least the minimum duration between requests (i.e. 50ms). This is not the optimised method for maximising requests made per second.
Throttler is optimised to work with asyncio, supporting concurrency in a more efficient way by using coroutines to manage delays. It also removes any complexity of building a custom RateLimiter.
2. Addition of the request rate logger. The logger tracks the number of requests generated per second and the number of successful requests per second. It logs the performance at 1 second intervals. The logger is used to measure the impact of the changes proposed on the performance of the client.


Bugs identified:
1. Incorrect parameter used in client's API request. “params” needs to be used instead of “data” when making the GET requests as the data we are using acts as the query parameters for the GET request. “data” is usually used for POST and PUT requests whereby we are actually sending data to a url.

