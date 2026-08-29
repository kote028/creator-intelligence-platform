from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    String,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint
)

from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Sponsorship(Base):
    __tablename__ = "sponsorships"

    __table_args__ = (
        UniqueConstraint(
            "creator_id",
            "campaign_id",
            name="unique_creator_campaign"
        ),
    )

    sponsorship_id = Column(
        Integer,
        primary_key=True
    )

    creator_id = Column(
        Integer,
        ForeignKey(
            "creators.creator_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    campaign_id = Column(
        Integer,
        ForeignKey(
            "campaigns.campaign_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    agreed_amount = Column(
        Numeric(12, 2),
        nullable=False
    )

    status = Column(
        String(50),
        default="pending"
    )

    start_date = Column(
        Date,
        nullable=True
    )

    end_date = Column(
        Date,
        nullable=True
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )

    creator = relationship(
        "Creator"
    )

    campaign = relationship(
        "Campaign",
        back_populates="sponsorships"
    )
