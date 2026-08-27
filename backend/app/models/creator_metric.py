from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    ForeignKey,
    Numeric,
    DateTime,
    Date
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class CreatorMetric(Base):
    __tablename__ = "creator_metrics"

    metric_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    account_id = Column(
        Integer,
        ForeignKey(
            "social_accounts.account_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    followers = Column(BigInteger, default=0)
    total_views = Column(BigInteger, default=0)
    avg_views = Column(BigInteger, default=0)
    total_likes = Column(BigInteger, default=0)
    total_comments = Column(BigInteger, default=0)

    engagement_rate = Column(
        Numeric(5, 2),
        default=0.00
    )

    recorded_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )

    metric_date = Column(Date)

    account = relationship(
        "SocialAccount",
        back_populates="metrics"
    )
