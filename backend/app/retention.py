from datetime import date, timedelta

from app.database import SessionLocal
from app.models.creator_metric import CreatorMetric


def delete_expired_public_youtube_metrics() -> int:
    """Delete non-authorized YouTube API statistics after the 30-day window."""
    cutoff = date.today() - timedelta(days=30)
    with SessionLocal() as db:
        deleted = (
            db.query(CreatorMetric)
            .filter(
                CreatorMetric.data_source == "youtube_public",
                CreatorMetric.metric_date < cutoff,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted
