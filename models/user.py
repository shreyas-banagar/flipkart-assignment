from sqlalchemy import Column, Integer, String, TIMESTAMP, text
from database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(50), unique=True, nullable=False)

    hashed_password = Column(String(255), nullable=False)

    role = Column(String(20), nullable=False)

    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
