from database.db import engine
from models.product import Base

import models

def init_db():
    Base.metadata.create_all(bind=engine)
