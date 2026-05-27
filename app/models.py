"""SQLAlchemy Models for Mavuno Protocol.

This module defines the production-ready schema using SQLAlchemy 2.0 style.
It centralizes identity in the User table and links role-specific profiles.
"""
from __future__ import annotations
import time
from typing import List, Optional
from sqlalchemy import String, Integer, Float, ForeignKey, Text, Boolean, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))
    updated_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()), onupdate=lambda: int(time.time()))

class User(Base, TimestampMixin):
    """Centralized identity table for all roles."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(16))  # farmer, buyer, agent, logistics
    password_hash: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    farmer_profile: Mapped[Optional["FarmerProfile"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    buyer_profile: Mapped[Optional["BuyerProfile"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reactions: Mapped[List["Reaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    flags: Mapped[List["PostFlag"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, role={self.role!r}, phone={self.phone!r})"

class Notification(Base, TimestampMixin):
    """System and protocol alerts for users."""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(32))  # payment_alert, price_alert, etc.
    read: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="notifications")

class FarmerProfile(Base, TimestampMixin):
    """Extension table for Farmer-specific metadata."""
    __tablename__ = "farmer_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    farmer_name: Mapped[str] = mapped_column(String(100))
    district: Mapped[str] = mapped_column(String(50), index=True)
    crop: Mapped[str] = mapped_column(String(50))
    acres: Mapped[float] = mapped_column(Float)
    lat: Mapped[Optional[float]] = mapped_column(Float)
    lng: Mapped[Optional[float]] = mapped_column(Float)
    collection_hub: Mapped[str] = mapped_column(String(64), default="Aggregation-Hub-01")
    current_stage: Mapped[str] = mapped_column(String(32), default="Land Prep")
    verification_status: Mapped[str] = mapped_column(String(32), default="pending_kyc")
    
    # Protocol Specifics
    discipline: Mapped[float] = mapped_column(Float, default=1.0)
    drought_factor: Mapped[float] = mapped_column(Float, default=1.0)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="farmer_profile")
    telemetry: Mapped[List["SoilTelemetry"]] = relationship(back_populates="farmer", order_by="desc(SoilTelemetry.timestamp)")
    priorities: Mapped[List["YieldPriority"]] = relationship(back_populates="farmer")
    offers: Mapped[List["MarketOffer"]] = relationship(back_populates="farmer")
    posts: Mapped[List["Post"]] = relationship(back_populates="farmer")
    certifications: Mapped[List["FarmerCertification"]] = relationship(back_populates="farmer")

    def __repr__(self) -> str:
        return f"FarmerProfile(user_id={self.user_id!r}, name={self.farmer_name!r})"

class BuyerProfile(Base, TimestampMixin):
    """Extension table for Buyer-specific metadata."""
    __tablename__ = "buyer_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    region: Mapped[str] = mapped_column(String(50))
    crops_json: Mapped[str] = mapped_column(Text)  # List of crops of interest
    floor_ugx: Mapped[int] = mapped_column(Integer)
    radius_km: Mapped[float] = mapped_column(Float, default=50.0)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="buyer_profile")
    settlements: Mapped[List["Settlement"]] = relationship(back_populates="buyer")
    batches: Mapped[List["PaymentBatch"]] = relationship(back_populates="buyer")

    def __repr__(self) -> str:
        return f"BuyerProfile(user_id={self.user_id!r}, name={self.name!r})"

class SoilTelemetry(Base):
    """High-frequency soil sensor history."""
    __tablename__ = "soil_telemetry"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    farm_id: Mapped[str] = mapped_column(ForeignKey("farmer_profiles.user_id"), index=True)
    timestamp: Mapped[int] = mapped_column(BigInteger, index=True)
    
    # The 7 live signals
    soil_moisture: Mapped[float] = mapped_column(Float)
    temp_c: Mapped[float] = mapped_column(Float)
    rainfall_mm: Mapped[float] = mapped_column(Float)
    humidity_pct: Mapped[float] = mapped_column(Float)
    n_mg_kg: Mapped[float] = mapped_column(Float)
    p_mg_kg: Mapped[float] = mapped_column(Float)
    k_mg_kg: Mapped[float] = mapped_column(Float)

    # Relationships
    farmer: Mapped["FarmerProfile"] = relationship(back_populates="telemetry")

class YieldPriority(Base, TimestampMixin):
    """Yield Priority (Trade Priority) issued to farmers."""
    __tablename__ = "yield_priorities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    farm_id: Mapped[str] = mapped_column(ForeignKey("farmer_profiles.user_id"))
    yps: Mapped[int] = mapped_column(Integer)
    kg_allocated: Mapped[int] = mapped_column(Integer)
    kg_remaining: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active, exhausted, expired
    aggregation_point: Mapped[str] = mapped_column(String(64), default="Aggregation-Hub-01")
    expires_at: Mapped[int] = mapped_column(BigInteger)
    signature: Mapped[str] = mapped_column(String(128))

    # Relationships
    farmer: Mapped["FarmerProfile"] = relationship(back_populates="priorities")

class MarketOffer(Base, TimestampMixin):
    """Crop listings in the Regional Marketplace."""
    __tablename__ = "market_offers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    farm_id: Mapped[str] = mapped_column(ForeignKey("farmer_profiles.user_id"))
    crop: Mapped[str] = mapped_column(String(32))
    kg: Mapped[int] = mapped_column(Integer)
    floor_ugx: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open, matched, closed
    
    # Relationships
    farmer: Mapped["FarmerProfile"] = relationship(back_populates="offers")
    settlements: Mapped[List["Settlement"]] = relationship(back_populates="offer")

class Settlement(Base, TimestampMixin):
    """Financial transactions between Buyers and Farmers."""
    __tablename__ = "settlements"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    offer_id: Mapped[str] = mapped_column(ForeignKey("market_offers.id"))
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyer_profiles.user_id"))
    farm_id: Mapped[str] = mapped_column(ForeignKey("farmer_profiles.user_id"))
    amount_ugx: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending, settled, failed
    ledger_hash: Mapped[str] = mapped_column(String(128))
    settled_at: Mapped[Optional[int]] = mapped_column(BigInteger)

    # Relationships
    offer: Mapped["MarketOffer"] = relationship(back_populates="settlements")
    buyer: Mapped["BuyerProfile"] = relationship(back_populates="settlements")

class PaymentBatch(Base, TimestampMixin):
    """Grouped financial transactions for bulk settlement."""
    __tablename__ = "payment_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyer_profiles.user_id"))
    total_amount_ugx: Mapped[int] = mapped_column(Integer)
    payment_ids_json: Mapped[str] = mapped_column(Text)  # List of settlement IDs
    status: Mapped[str] = mapped_column(String(16), default="pending")
    settled_at: Mapped[Optional[int]] = mapped_column(BigInteger)

    # Relationships
    buyer: Mapped["BuyerProfile"] = relationship(back_populates="batches")

class LedgerEntry(Base):
    """Immutable hash-chained audit log."""
    __tablename__ = "immutable_ledger"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prev_hash: Mapped[str] = mapped_column(String(128))
    curr_hash: Mapped[str] = mapped_column(String(128), index=True)
    type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()))

class Conversation(Base, TimestampMixin):
    """Chat threads between Buyers and Farmers."""
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    farm_id: Mapped[str] = mapped_column(ForeignKey("farmer_profiles.user_id"))
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyer_profiles.user_id"))
    offer_id: Mapped[Optional[str]] = mapped_column(ForeignKey("market_offers.id"))
    last_msg_at: Mapped[int] = mapped_column(BigInteger)

    # Relationships
    messages: Mapped[List["Message"]] = relationship(back_populates="conversation", order_by="Message.created_at")

class Message(Base, TimestampMixin):
    """Individual chat messages."""
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

class Post(Base, TimestampMixin):
    """Mavuno Social updates from farmers."""
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    farm_id: Mapped[str] = mapped_column(ForeignKey("farmer_profiles.user_id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_metadata: Mapped[Optional[str]] = mapped_column(Text) # JSON: {lat, lng, ts, hash}
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    farmer: Mapped["FarmerProfile"] = relationship(back_populates="posts")
    reactions: Mapped[List["Reaction"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    flags: Mapped[List["PostFlag"]] = relationship(back_populates="post", cascade="all, delete-orphan")

class Reaction(Base, TimestampMixin):
    """Emoji reactions on social posts."""
    __tablename__ = "reactions"

    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    emoji: Mapped[str] = mapped_column(String(8), primary_key=True)

    # Relationships
    post: Mapped["Post"] = relationship(back_populates="reactions")
    user: Mapped["User"] = relationship(back_populates="reactions")

class PostFlag(Base, TimestampMixin):
    """Reporting/Flagging content on the social feed."""
    __tablename__ = "post_flags"

    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    reason: Mapped[Optional[str]] = mapped_column(String(200))

    # Relationships
    post: Mapped["Post"] = relationship(back_populates="flags")
    user: Mapped["User"] = relationship(back_populates="flags")

class TrainingModule(Base, TimestampMixin):
    """Educational content for Mavuno Academy."""
    __tablename__ = "training_modules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64))
    xp_reward: Mapped[int] = mapped_column(Integer, default=0)
    content_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Relationships
    certifications: Mapped[List["FarmerCertification"]] = relationship(back_populates="module")

class FarmerCertification(Base, TimestampMixin):
    """Proofs of training completion for farmers."""
    __tablename__ = "farmer_certifications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    farm_id: Mapped[str] = mapped_column(ForeignKey("farmer_profiles.user_id"), index=True)
    module_id: Mapped[str] = mapped_column(ForeignKey("training_modules.id"))
    issued_at: Mapped[int] = mapped_column(BigInteger)
    expiry_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    ledger_hash: Mapped[str] = mapped_column(String(128))

    # Relationships
    farmer: Mapped["FarmerProfile"] = relationship(back_populates="certifications")
    module: Mapped["TrainingModule"] = relationship(back_populates="certifications")
