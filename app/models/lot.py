from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Lot(Base):
    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    buy_price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    buy_currency: Mapped[str] = mapped_column()
    buy_date: Mapped[date] = mapped_column(Date)
    fees: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at_utc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    asset = relationship("Asset", back_populates="lots")
