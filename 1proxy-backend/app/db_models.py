from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    oauth_provider = Column(String(20), nullable=False)
    oauth_id = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False)
    username = Column(String(100), nullable=False)
    avatar_url = Column(Text, nullable=True)
    role = Column(String(20), default="user", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    sources = relationship(
        "ProxySource", back_populates="owner", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_oauth_provider_id", "oauth_provider", "oauth_id", unique=True),
    )


class ProxySource(Base):
    __tablename__ = "proxy_sources"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    url = Column(Text, nullable=False, unique=True, index=True)
    type = Column(String(50), nullable=False)
    name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    is_paid = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True, index=True)
    validated = Column(Boolean, default=False)
    validation_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_scraped = Column(DateTime(timezone=True), nullable=True)
    total_scraped = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    is_admin_source = Column(Boolean, default=False)

    owner = relationship("User", back_populates="sources")
    proxies = relationship("Proxy", back_populates="source")


class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(
        Integer, ForeignKey("proxy_sources.id", ondelete="SET NULL"), nullable=True
    )
    url = Column(Text, nullable=False, unique=True, index=True)
    protocol = Column(String(50), nullable=False, index=True)
    ip = Column(String(50), nullable=True)
    port = Column(Integer, nullable=True)
    country_code = Column(String(2), nullable=True, index=True)
    country_name = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    latency_ms = Column(Integer, nullable=True, index=True)
    speed_mbps = Column(Float, nullable=True)
    uptime_percent = Column(Float, nullable=True)

    anonymity = Column(String(20), nullable=True, index=True)
    proxy_type = Column(String(20), nullable=True)
    can_access_google = Column(Boolean, nullable=True)
    quality_score = Column(Integer, nullable=True, index=True)

    validation_status = Column(
        String(20), default="pending", nullable=False, index=True
    )  # pending, validating, validated, failed
    last_validated = Column(DateTime(timezone=True), nullable=True)
    validation_failures = Column(Integer, default=0)
    is_working = Column(Boolean, default=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())

    source = relationship("ProxySource", back_populates="proxies")
    validation_history = relationship(
        "ValidationHistory", back_populates="proxy", cascade="all, delete-orphan"
    )


class ValidationHistory(Base):
    __tablename__ = "validation_history"

    id = Column(Integer, primary_key=True, index=True)
    proxy_id = Column(
        Integer,
        ForeignKey("proxies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    validated_at = Column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    latency_ms = Column(Integer, nullable=True)
    anonymity = Column(String(20), nullable=True)
    can_access_google = Column(Boolean, nullable=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)

    proxy = relationship("Proxy", back_populates="validation_history")
