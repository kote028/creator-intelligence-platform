from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Creator(Base):
    __tablename__ = "creators"

    creator_id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        unique=True,
        nullable=True
    )
    username = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(150), nullable=True)
    email = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    niche = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    user = relationship("User", back_populates="creator")

    social_accounts = relationship(
        "SocialAccount",
        back_populates="creator",
        cascade="all, delete-orphan"
    )
