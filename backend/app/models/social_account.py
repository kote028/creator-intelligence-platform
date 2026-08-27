from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship


from app.database import Base


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    account_id = Column(Integer, primary_key=True, index=True)

    creator_id = Column(
        Integer,
        ForeignKey("creators.creator_id", ondelete="CASCADE"),
        nullable=False
    )

    platform = Column(String(50), nullable=False)
    username = Column(String(100), nullable=False)
    profile_url = Column(Text, nullable=True)

    followers = Column(BigInteger, default=0)
    following = Column(BigInteger, default=0)
    total_posts = Column(Integer, default=0)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )

    creator = relationship(
        "Creator",
        back_populates="social_accounts"
    )
    metrics = relationship(
      "CreatorMetric",
       back_populates="account",
       cascade="all, delete-orphan"
    )
