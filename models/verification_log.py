from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, text
from database.db import Base


class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id = Column(Integer, primary_key=True, index=True)

    wid = Column(String(50), ForeignKey("products.wid"))

    user_id = Column(String(50))
    image_path = Column(String(255))

    verified_at = Column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), index=True
    )
