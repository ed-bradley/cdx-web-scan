from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, List

from cdx_web_scan import db

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

# ----------------------------
# Helpers
# ----------------------------

def utcnow() -> datetime:
    # SQLite has no real TZ; store UTC consistently.
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())

# ----------------------------
# Enums
# ----------------------------

class ScanSource(str, enum.Enum):
    scanner = "scanner"
    camera = "camera"
    manual = "manual"


class CaptureMethod(str, enum.Enum):
    scanner = "scanner"
    camera = "camera"
    manual = "manual"


class IntakeStatus(str, enum.Enum):
    pending = "pending"   # created locally, not attempted yet
    sent = "sent"         # HTTP request completed (any status code)
    success = "success"   # 2xx response
    failed = "failed"     # non-2xx or request error
    retrying = "retrying" # scheduled/ready for retry


# ----------------------------
# Models
# ----------------------------

class ScanSession(db.Model):
    """
    Optional: groups scans from one sitting/run (one box of CDs, one shift, etc.).
    """
    __tablename__ = "scan_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    operator: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source: Mapped[Optional[ScanSource]] = mapped_column(Enum(ScanSource), nullable=True)

    device_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    host: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    app_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    git_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    scans: Mapped[List["Scan"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class Scan(db.Model):
    """
    Canonical scan event (one user action that captures 1+ barcodes).
    """
    __tablename__ = "scan"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)

    session_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("scan_session.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    source: Mapped[ScanSource] = mapped_column(Enum(ScanSource), default=ScanSource.scanner, nullable=False, index=True)
    operator: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    # Lightweight for troubleshooting; avoid storing PII.
    client_fingerprint: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)

    # Raw HTMX payload or scanner input; useful for replay/debugging.
    raw_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Notes like "sticker over barcode", "box set", etc.
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Optional: prefer one barcode as the "primary" for display / default.
    primary_barcode_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("barcode_capture.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    session: Mapped[Optional["ScanSession"]] = relationship(back_populates="scans")

    barcodes: Mapped[List["BarcodeCapture"]] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="BarcodeCapture.created_at.asc()",
        foreign_keys=lambda: [BarcodeCapture.scan_id],
        overlaps="primary_barcode",
    )

    intake_calls: Mapped[List["AwsIntakeCall"]] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AwsIntakeCall.created_at.asc()",
    )

    primary_barcode: Mapped[Optional["BarcodeCapture"]] = relationship(
        foreign_keys=[primary_barcode_id],
        post_update=True,
        overlaps="barcodes,scan",
    )

    __table_args__ = (
        Index("ix_scan_created_source", "created_at", "source"),
    )

class BarcodeCapture(db.Model):
    """
    Barcodes captured from CD packaging. Supports multiple per scan.
    """
    __tablename__ = "barcode_capture"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)

    scan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scan.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Keep symbology flexible (EAN_13, UPC_A, etc.)
    symbology: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    value_raw: Mapped[str] = mapped_column(String(64), nullable=False)

    # Store app-derived normalization (strip, checksum, leading-zero rules, etc.)
    value_normalized: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    checksum_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    capture_method: Mapped[CaptureMethod] = mapped_column(Enum(CaptureMethod), default=CaptureMethod.scanner, nullable=False)

    # Decoder metadata (confidence, library/version, camera params)
    decode_meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    scan: Mapped["Scan"] = relationship(
        back_populates="barcodes",
        foreign_keys=[scan_id],
        overlaps="primary_barcode",
    )

    __table_args__ = (
        # Prevent obvious duplicates within the same scan.
        UniqueConstraint("scan_id", "symbology", "value_raw", name="uq_barcode_per_scan_raw"),
        Index("ix_barcode_norm_sym", "value_normalized", "symbology"),
        CheckConstraint("length(value_raw) > 0", name="ck_barcode_raw_nonempty"),
    )


class AwsIntakeCall(db.Model):
    """
    Audit trail of calls made from CDX-WEB-SCAN to the AWS Intake API
    (which will enqueue to SQS and trigger the enrichment worker).

    This table is the replay + troubleshooting history for:
    - what payload was sent
    - what the API returned
    - whether retries were needed
    """
    __tablename__ = "aws_intake_call"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)

    scan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scan.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Idempotency: generated client-side and sent as header (recommended)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)

    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[IntakeStatus] = mapped_column(Enum(IntakeStatus), default=IntakeStatus.pending, nullable=False, index=True)

    # Where you sent it (useful if you have dev/stage/prod)
    api_base_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    api_path: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Outbound request (store a trimmed JSON payload; avoid secrets)
    request_headers: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    request_body: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Response summary
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    response_headers: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Response body can be big; store only what you need (or truncate upstream)
    response_body: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Optional: if API returns an intake id / correlation id / sqs message id, store it
    correlation_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)

    scan: Mapped["Scan"] = relationship(back_populates="intake_calls")

    __table_args__ = (
        # For safety: prevent duplicate rows for same scan + idempotency key.
        UniqueConstraint("scan_id", "idempotency_key", name="uq_intake_scan_idempotency"),
        Index("ix_intake_scan_attempt", "scan_id", "attempt"),
    )


