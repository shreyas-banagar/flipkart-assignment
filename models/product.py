from sqlalchemy import Column, String, Date, TIMESTAMP, text
from database.db import Base


class Product(Base):
    __tablename__ = "products"

    wid = Column(String(50), primary_key=True)
    ean = Column(String(13), nullable=False, index=True)
    manufacturing_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)

    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
