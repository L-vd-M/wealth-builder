from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Strategy(Base):
    __tablename__ = "strategies"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_strategy_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    versions: Mapped[list["StrategyVersion"]] = relationship(
        "StrategyVersion",
        back_populates="strategy",
        order_by="StrategyVersion.version",
        cascade="all, delete-orphan",
    )


class StrategyVersion(Base):
    __tablename__ = "strategy_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    signals: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_rules: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="versions")


class UserBot(Base):
    __tablename__ = "user_bots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    strategy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="idle")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
