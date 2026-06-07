from contextlib import asynccontextmanager
from fastapi import FastAPI

# Import models so SQLAlchemy registers them



from database.startup import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)
