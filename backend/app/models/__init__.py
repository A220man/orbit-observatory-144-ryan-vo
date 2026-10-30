from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Index
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship
from app.services.database import Base
from datetime import datetime
import uuid


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    session_metadata = Column(JSON, default={})

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    folds = relationship("Fold", back_populates="session", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    ref = Column(String(64), nullable=False, index=True)
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    message_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_session_ref", "session_id", "ref", unique=True),
    )


class Fold(Base):
    __tablename__ = "folds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    start_ref = Column(String(64), nullable=False)
    end_ref = Column(String(64), nullable=False)
    summary = Column(Text, nullable=False)
    folded_refs = Column(JSON, default=[])
    token_count = Column(Integer, default=0)
    fold_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="folds")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    details = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="audit_logs")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    roles = Column(JSON, default=["viewer"])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)