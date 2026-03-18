"""SQLAlchemy 2.0 declarative models for SkyNet."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class SyncMode(PyEnum):
    FULL = "full"
    INCREMENTAL = "incremental"


class JobStatus(PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MetricType(PyEnum):
    ATOMIC = "atomic"
    DERIVED = "derived"
    WINDOW = "window"


class ConditionType(PyEnum):
    THRESHOLD = "threshold"
    ANOMALY = "anomaly"
    CHANGE = "change"


class NotificationStatus(PyEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Severity(PyEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Base(DeclarativeBase):
    pass


class DataSource(Base):
    """Represents an external data source configuration."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # postgresql, mysql, api, file
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    sync_jobs: Mapped[list["SyncJob"]] = relationship(back_populates="data_source")


class SyncJob(Base):
    """Tracks sync execution history for a data source."""

    __tablename__ = "sync_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("data_sources.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(JobStatus), default=JobStatus.PENDING, nullable=False
    )
    sync_mode: Mapped[str] = mapped_column(
        Enum(SyncMode), default=SyncMode.FULL, nullable=False
    )
    rows_synced: Mapped[int | None] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    data_source: Mapped["DataSource"] = relationship(back_populates="sync_jobs")

    __table_args__ = Index("ix_sync_jobs_data_source_id", "data_source_id")


class Metric(Base):
    """Defines a metric specification."""

    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    metric_type: Mapped[str] = mapped_column(
        Enum(MetricType), default=MetricType.ATOMIC, nullable=False
    )
    source_table: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aggregation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dimensions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    window_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    values: Mapped[list["MetricValue"]] = relationship(back_populates="metric")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="metric")


class MetricValue(Base):
    """Stores computed metric values."""

    __tablename__ = "metric_values"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("metrics.id"), nullable=False
    )
    value: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    dimensions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    metric: Mapped["Metric"] = relationship(back_populates="values")

    __table_args__ = Index("ix_metric_values_metric_id_computed_at", "metric_id", "computed_at")


class Report(Base):
    """Report configuration."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)  # cron expression
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    executions: Mapped[list["ReportExecution"]] = relationship(back_populates="report")


class ReportExecution(Base):
    """Report execution history."""

    __tablename__ = "report_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reports.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(JobStatus), default=JobStatus.PENDING, nullable=False
    )
    output_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    report: Mapped["Report"] = relationship(back_populates="executions")

    __table_args__ = Index("ix_report_executions_report_id", "report_id")


class Alert(Base):
    """Alert configuration for metrics."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    metric_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("metrics.id"), nullable=False
    )
    condition_type: Mapped[str] = mapped_column(
        Enum(ConditionType), default=ConditionType.THRESHOLD, nullable=False
    )
    condition_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    severity: Mapped[str] = mapped_column(
        Enum(Severity), default=Severity.WARNING, nullable=False
    )
    channels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    metric: Mapped["Metric"] = relationship(back_populates="alerts")
    history: Mapped[list["AlertHistory"]] = relationship(back_populates="alert")


class AlertHistory(Base):
    """Alert trigger history."""

    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("alerts.id"), nullable=False
    )
    triggered_value: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notification_status: Mapped[str] = mapped_column(
        Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    alert: Mapped["Alert"] = relationship(back_populates="history")

    __table_args__ = Index("ix_alert_history_alert_id_triggered_at", "alert_id", "triggered_at")
