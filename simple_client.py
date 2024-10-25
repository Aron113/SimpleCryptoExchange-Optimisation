import sys
import time
import random
import logging
import contextlib

import asyncio
from asyncio import Queue
import aiohttp
import async_timeout
from asyncio_throttle import Throttler


# region: DO NOT CHANGE - the code within this region can be assumed to be "correct"

PER_SEC_RATE = 20
DURATION_MS_BETWEEN_REQUESTS = int(1000 / PER_SEC_RATE)
REQUEST_TTL_MS = 1000
MAX_RETRIES = 1 #Maximum number of retries for expired requests
VALID_API_KEYS = ['UT4NHL1J796WCHULA1750MXYF9F5JYA6',
                  '8TY2F3KIL38T741G1UCBMCAQ75XU9F5O',
                  '954IXKJN28CBDKHSKHURQIVLQHZIEEM9',
                  'EUU46ID478HOO7GOXFASKPOZ9P91XGYS',
                  '46V5EZ5K2DFAGW85J18L50SGO25WJ5JE']


async def generate_requests(queue: Queue, request_counter):
    """
    co-routine responsible for generating requests

    :param queue:
    :param logger:
    :return:
    """
    curr_req_id = 0
    MAX_SLEEP_MS = 1000 / PER_SEC_RATE / len(VALID_API_KEYS) * 1.05 * 2.0
    while True:
        request_counter['generated'] += 1
        queue.put_nowait(Request(curr_req_id))
        curr_req_id += 1
        sleep_ms = random.randint(0, MAX_SLEEP_MS)
        await asyncio.sleep(sleep_ms / 1000.0)


def timestamp_ms() -> int:
    return int(time.time() * 1000)

# endregion


def configure_logger(name=None):
    logger = logging.getLogger(name)
    if name is None:
        # only add handlers to root logger
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

        fh = logging.FileHandler(f"async-debug.log", mode="a")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        logger.setLevel(logging.DEBUG)
    return logger


class RateLimiterTimeout(Exception):
    pass


# class RateLimiter:
#     def __init__(self, per_second_rate, min_duration_ms_between_requests):
#         self.__per_second_rate = per_second_rate
#         self.__min_duration_ms_between_requests = min_duration_ms_between_requests
#         self.__last_request_time = 0
#         self.__request_times = [0] * per_second_rate
#         self.__curr_idx = 0

#     @contextlib.asynccontextmanager
#     async def acquire(self, timeout_ms=0):
#         enter_ms = timestamp_ms()
#         while True:
#             now = timestamp_ms()
#             if now - enter_ms > timeout_ms > 0:
#                 raise RateLimiterTimeout()

#             if now - self.__last_request_time <= self.__min_duration_ms_between_requests:
#                 await asyncio.sleep(0.001)
#                 continue

#             if now - self.__request_times[self.__curr_idx] <= 1000:
#                 await asyncio.sleep(0.001)
#                 continue

#             break

#         self.__last_request_time = self.__request_times[self.__curr_idx] = now
#         self.__curr_idx = (self.__curr_idx + 1) % self.__per_second_rate
#         yield self


async def exchange_facing_worker(url: str, api_key: str, queue: Queue, logger: logging.Logger, request_counter):
    #Use asyncio's Throttler instead of custom Rate Limiter
    rate_limiter = Throttler(PER_SEC_RATE + 10, period=1) #Throttler(RATE, PERIOD)

    async with aiohttp.ClientSession() as session:
        while True:
            request: Request = await queue.get()
            remaining_ttl = REQUEST_TTL_MS - (timestamp_ms() - request.create_time)
            if remaining_ttl <= 0:
                if request.retries < MAX_RETRIES:
                    request.retries += 1
                    request.create_time = timestamp_ms()  # Reset creation time for fresh TTL
                    queue.put_nowait(request)
                    logger.warning(f"Request {request.req_id} expired. Requeueing attempt {request.retries}.")
                else:
                    request_counter["ignored"] += 1
                    logger.error(f"Request {request.req_id} failed permanently after {request.retries} retries.")
                continue

            try:
                nonce = timestamp_ms()
                async with rate_limiter:
                    #Check that request has not timed out before ratelimiter is acquired
                    remaining_ttl = REQUEST_TTL_MS - (timestamp_ms() - request.create_time)
                    if remaining_ttl <= 0:
                        if request.retries < MAX_RETRIES:
                            request.retries += 1
                            request.create_time = timestamp_ms()  # Reset creation time for fresh TTL
                            queue.put_nowait(request)
                            logger.warning(f"Request {request.req_id} expired. Requeueing attempt {request.retries}.")
                            continue
                        else:
                            request_counter["ignored"] += 1
                            raise RateLimiterTimeout()
                    
                    async with async_timeout.timeout(1.0):
                        data = {'api_key': api_key, 'nonce': nonce, 'req_id': request.req_id}
                        async with session.request('GET',
                                                   url,
                                                   params=data) as resp:  # type: aiohttp.ClientResponse
                            json = await resp.json()
                            if json['status'] == 'OK':
                                request_counter['successful'] += 1  # Increment successful requests
                                logger.info(f"API response: status {resp.status}, resp {json}")
                            else:
                                logger.warning(f"API response: status {resp.status}, resp {json}")
            except RateLimiterTimeout:
                logger.warning(f"ignoring request {request.req_id} in limiter due to TTL")

#Function to log average requests per second
async def log_request_rate(request_counter, logger):
    start_time = timestamp_ms()
    while True:
        await asyncio.sleep(1)  #Report every second
        elapsed_time = (timestamp_ms() - start_time) / 1000.0  #Convert ms to seconds
        if elapsed_time > 0:
            avg_requests_per_second = request_counter['successful'] / elapsed_time
            avg_requests_generated_per_second = request_counter['generated'] / elapsed_time
            avg_requests_ignored_per_second = request_counter['ignored'] / elapsed_time
            logger.info(f"Avg Successful Requests per Second: {avg_requests_per_second:.2f} (Total: {request_counter['total']})")
            logger.info(f"Avg Requests generated per Second: {avg_requests_generated_per_second:.2f}")
            logger.info(f"Avg Requests ignored per Second: {avg_requests_ignored_per_second:.2f}")
        else:
            logger.info("No requests yet.")

class Request:
    def __init__(self, req_id):
        self.req_id = req_id
        self.create_time = timestamp_ms()
        self.retries = 0 #Track the number of requeue attempts


def main():
    url = "http://127.0.0.1:9999/api/request"
    loop = asyncio.get_event_loop()
    queue = Queue()
    logger = configure_logger()

    #Track successful requests and generated requests rates
    request_counter = {'total': 0, 'successful': 0, 'generated': 0, 'ignored':0}  # Counter for requests
    loop.create_task(log_request_rate(request_counter, logger))
    
    loop.create_task(generate_requests(queue=queue, request_counter = request_counter))

    for api_key in VALID_API_KEYS:
        loop.create_task(exchange_facing_worker(url=url, api_key=api_key, queue=queue, logger=logger, request_counter=request_counter))

    loop.run_forever()


if __name__ == '__main__':
    main()
