from database.db import engine, SessionLocal
from models.product import Base
from database.seed import seed_users

import models

def init_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_users(db)
