import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.lead import DistributionMode


class LeadDeliveryMode(str, enum.Enum):
    pull_broadcast = "pull_broadcast"
    pull_exclusive = "pull_exclusive"


class DistributionSetting(Base):
    __tablename__ = "distribution_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mode: Mapped[DistributionMode] = mapped_column(
        Enum(DistributionMode, name="distributionmode", create_type=False),
        nullable=False,
        default=DistributionMode.coverage,
    )
    speed_group_size: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    lead_delivery_mode: Mapped[LeadDeliveryMode] = mapped_column(
        Enum(LeadDeliveryMode, name="leaddeliverymode", create_type=True),
        nullable=False,
        default=LeadDeliveryMode.pull_broadcast,
        server_default=LeadDeliveryMode.pull_broadcast.value,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    def __repr__(self) -> str:
        return f"<DistributionSetting id={self.id} mode={self.mode} lead_delivery_mode={self.lead_delivery_mode}>"
