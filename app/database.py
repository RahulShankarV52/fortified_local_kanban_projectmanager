from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# 1. Load environment variables
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

# 2. Create the Async Database URL
# Note: We use 'postgresql+asyncpg' driver
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

# 3. Create the Engine
engine = create_async_engine(DATABASE_URL, echo=True)

# 4. Create the Session Factory
# This is what we will use in our API dependency to get a DB session
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 5. Base class for our models (Users, Boards, etc.)
Base = declarative_base()

# 6. Dependency Injection Helper
# This function will be used in FastAPI routes later
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
