from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Numeric,
    Date,
    ForeignKey,
    BigInteger
)

from sqlalchemy.orm import relationship

from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id = Column(
        Integer,
        primary_key=True
    )

    brand_id = Column(
        Integer,
        ForeignKey(
            "brands.brand_id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    campaign_name = Column(
        String(200),
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    budget = Column(
        Numeric(12, 2),
        nullable=False
    )

    start_date = Column(
        Date,
        nullable=True
    )

    end_date = Column(
        Date,
        nullable=True
    )

    status = Column(
        String(50),
        default="active"
    )

    target_niche = Column(
        String(100),
        nullable=True
    )

    target_country = Column(
        String(100),
        nullable=True
    )

    target_platform = Column(
        String(50),
        nullable=True
    )

    min_followers = Column(
        BigInteger,
        nullable=True
    )

    max_followers = Column(
        BigInteger,
        nullable=True
    )

    brand = relationship(
        "Brand",
        back_populates="campaigns"
    )

    sponsorships = relationship(
        "Sponsorship",
        back_populates="campaign",
        cascade="all, delete-orphan"
    )
