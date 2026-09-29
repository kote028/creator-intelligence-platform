from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(
        Integer,
        primary_key=True
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    google_subject = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    role = Column(
        String(20),
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )

    creator = relationship(
        "Creator",
        back_populates="user",
        uselist=False
    )

    brand = relationship(
        "Brand",
        back_populates="user",
        uselist=False
    )
