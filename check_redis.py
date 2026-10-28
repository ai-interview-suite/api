import asyncio
import os

import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = redis.from_url(
        os.environ["REDIS_URL"],
        decode_responses=True,
    )
    try:
        result = await client.ping()
        print("Redis connection:", result)
    finally:
        await client.aclose()

asyncio.run(main())