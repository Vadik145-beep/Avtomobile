import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DeliveryStatus(str, enum.Enum):
    sent = "sent"
    opened = "opened"
    blocked = "blocked"


class LeadDelivery(Base):
    __tablename__ = "lead_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="deliverystatus", create_type=False),
        nullable=False,
        default=DeliveryStatus.sent,
    )
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lead: Mapped["Lead"] = relationship("Lead", back_populates="deliveries")  # noqa: F821
    user: Mapped["User"] = relationship("User", back_populates="lead_deliveries")  # noqa: F821

    def __repr__(self) -> str:
        return f"<LeadDelivery id={self.id} lead_id={self.lead_id} user_id={self.user_id} status={self.status}>"
