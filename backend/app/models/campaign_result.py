from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CampaignResult(Base):
    __tablename__ = "campaign_results"
    __table_args__ = (UniqueConstraint("sponsorship_id", name="uq_campaign_results_sponsorship"),)

    result_id = Column(Integer, primary_key=True)
    sponsorship_id = Column(
        Integer,
        ForeignKey("sponsorships.sponsorship_id", ondelete="CASCADE"),
        nullable=False,
    )
    impressions = Column(BigInteger, nullable=False, default=0, server_default="0")
    clicks = Column(BigInteger, nullable=False, default=0, server_default="0")
    conversions = Column(BigInteger, nullable=False, default=0, server_default="0")
    attributed_revenue = Column(Numeric(14, 2), nullable=False, default=0, server_default="0")
    reported_at = Column(Date, nullable=False)
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    sponsorship = relationship("Sponsorship", back_populates="result")
