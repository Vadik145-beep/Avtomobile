import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DistributionMode(str, enum.Enum):
    exclusive = "exclusive"
    speed = "speed"
    coverage = "coverage"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_qualified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    distribution_mode: Mapped[DistributionMode] = mapped_column(
        Enum(DistributionMode, name="distributionmode", create_type=False),
        nullable=False,
        default=DistributionMode.coverage,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    deliveries: Mapped[list["LeadDelivery"]] = relationship(  # noqa: F821
        "LeadDelivery", back_populates="lead", lazy="select",
        cascade="all, delete-orphan", passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Lead id={self.id} brand={self.brand} city={self.city}>"
