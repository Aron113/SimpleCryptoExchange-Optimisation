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
