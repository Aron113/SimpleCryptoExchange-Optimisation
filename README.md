# SimpleCryptoExchange-Optimisation

This is the repository containing the optimised SimpleCryptoExchange client code.

Steps:
1. pip install -r requirements.txt
2. python simple_rest_server.py
3. python simple_client.py

---
<br>

Changes proposed:
1. Replacing custom RateLimiter with Throttler from the asyncio-throttle library. 
Rationale: The custom RateLimiter works by tracking the latest request's time and ensuring that the difference between the current and the latest request's time is at least the minimum duration between requests (i.e. 50ms). This is not the optimised method for maximising requests made per second.
Throttler is optimised to work with asyncio, supporting concurrency in a more efficient way by using coroutines to manage delays. It also removes any complexity of building a custom RateLimiter.
2. Addition of the request rate logger. The logger tracks the number of requests generated per second and the number of successful requests per second. It logs the performance at 1 second intervals. The logger is used to measure the impact of the changes proposed on the performance of the client.
3. Addition of requeuing of requests that have timed out due to TTL being exceeded. The addition of the requeuing allows for a more graceful handling of requests that expire. The maximum number of retries for each request is set as MAX_RETRIES. The expired request is added back to the queue with its retry count updated and is given a fresh create_time. If the request is unsuccessful for all retries, it is permanently ignored. The client is able to handle TTL expiry more gracefully, giving requests a fair chance to complete while preventing endless requeuing for permanently failing requests.

<br>

Bugs identified:
1. Incorrect parameter used in client's API request. “params” needs to be used instead of “data” when making the GET requests as the data we are using acts as the query parameters for the GET request. “data” is usually used for POST and PUT requests whereby we are actually sending data to a url.

<br>
Design Choices: 
<br>
The client uses the asynchronous approach (i.e. asyncio and aiohttp) to handle concurrency over the multithreading and multiprocessing approaches.

Multiprocessing is not used as the client focuses primarily on network requests which is an I/O-bound task. Therefore, Multiprocessing, which benefits CPU-bound tasks, would not be beneficial.

Between Multithreading and asyncio, asyncio is more favorable than multithreading because it efficiently handles high concurrency for I/O-bound tasks, such as making frequent HTTP requests to an API within strict rate limits. 
asyncio allows tasks to be scheduled and paused non-blockingly, yielding control back to the event loop during network waits or sleep intervals, which maximises throughput without blocking other tasks. This approach significantly reduces the memory and CPU overhead that multithreading would introduce by avoiding the creation and management of multiple threads, each of which would consume resources and be subject to Python’s Global Interpreter Lock. 
Furthermore, using asyncio allows us to use aiohttp which is designed to work with asyncio to support HTTP client and server interactions. aiohttp allows for each request to be created as a coroutine that yields control back to asyncio’s event loop while waiting for network responses.

---
<br>

Results:
1. Higher successful API request rate. The modified client allows for a higher successful request rate compared to the legacy client.
2. Additionally, there is a lower rate of requests being ignored with the modified client compared to the legacy client.