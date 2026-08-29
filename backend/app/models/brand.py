from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Brand(Base):
    __tablename__ = "brands"

    brand_id = Column(
        Integer,
        primary_key=True
    )

    company_name = Column(
        String(150),
        nullable=False
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False
    )

    website = Column(
        Text,
        nullable=True
    )

    industry = Column(
        String(100),
        nullable=True
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )

    campaigns = relationship(
        "Campaign",
        back_populates="brand",
        cascade="all, delete-orphan"
    )
