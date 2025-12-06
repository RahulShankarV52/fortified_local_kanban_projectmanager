import asyncio
from app.database import engine, Base
from app import models # Importing models so Base knows about them

async def init_models():
    async with engine.begin() as conn:
        # This deletes all tables (Good for dev, BAD for production!)
        await conn.run_sync(Base.metadata.drop_all)
        
        # This creates all tables
        print("Creating tables in the database...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_models())
