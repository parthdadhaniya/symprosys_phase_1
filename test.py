import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def test_connection():
    if not DATABASE_URL:
        print("DATABASE_URL not found in .env")
        return
    
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            row = result.fetchone()
            print("Database connected successfully!")
            print(f"PostgreSQL Version: {row[0]}")
    except Exception as e:
        print("Connection failed:")
        print(e)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())