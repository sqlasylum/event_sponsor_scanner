from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, TIMESTAMP, BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Sponsor(Base):
    __tablename__ = "sponsors"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    company: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    attendee_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sponsor_email: Mapped[str] = mapped_column(
        String, ForeignKey("sponsors.email"), nullable=False, index=True
    )
    scanned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(String, nullable=True)


class EventAttendee(Base):
    __tablename__ = "event_attendees"

    attendee_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    attendee_first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    attendee_last_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization: Mapped[str | None] = mapped_column(Text, nullable=True)
    attendee_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_code: Mapped[str | None] = mapped_column(Text, nullable=True)
