import asyncio
import getpass

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine


async def main():
    raw_url = getpass.getpass("Paste Neon URL (hidden): ")
    url = make_url(raw_url)

    if not url.host or "neon.tech" not in url.host:
        raise ValueError("This does not look like a Neon URL.")

    # Adapt the URL for SQLAlchemy's asyncpg driver.
    url = url.difference_update_query(
        ["channel_binding", "sslmode", "ssl"]
    ).update_query_dict({"ssl": "require"})

    engine = create_async_engine(url)

    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
            )
            print("Tables:", [row[0] for row in result])

            result = await connection.execute(
                text("SELECT to_regclass('public.alembic_version')")
            )
            version_table = result.scalar()

            if version_table is None:
                print("No Alembic version table found.")
            else:
                result = await connection.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                print("Alembic revisions:", [row[0] for row in result])
    finally:
        await engine.dispose()


asyncio.run(main())