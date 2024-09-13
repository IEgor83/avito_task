from .engine import Base
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
import uuid


class OrganizationTypeEnum(enum.Enum):
    IE = "IE"
    LLC = "LLC"
    JSC = "JSC"


class TenderStatusEnum(enum.Enum):
    CREATED = "CREATED"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"


class TenderServiceTypeEnum(enum.Enum):
    CONSTRUCTION = "CONSTRUCTION"
    DELIVERY = "DELIVERY"
    MANUFACTURE = "MANUFACTURE"


class BidStatusEnum(enum.Enum):
    CREATED = "CREATED"
    PUBLISHED = "PUBLISHED"
    CANCELED = "CANCELED"


class BidAuthorTypeEnum(enum.Enum):
    ORGANIZATION = "Organization"
    USER = "User"


class User(Base):
    __tablename__ = "employee"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    responsibilities = relationship("OrganizationResponsible", back_populates="user", cascade="all, delete")
    reviews = relationship("Review", back_populates="creator", cascade="all, delete-orphan")
    bids = relationship("Bid", back_populates="creator")


class Organization(Base):
    __tablename__ = "organization"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    type = Column(Enum(OrganizationTypeEnum), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    responsible_users = relationship("OrganizationResponsible", back_populates="organization", cascade="all, delete")


class OrganizationResponsible(Base):
    __tablename__ = "organization_responsible"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organization.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("employee.id", ondelete="CASCADE"))

    organization = relationship("Organization", back_populates="responsible_users")
    user = relationship("User", back_populates="responsibilities")


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    service_type = Column(Enum(TenderServiceTypeEnum), nullable=False)
    status = Column(Enum(TenderStatusEnum), nullable=False, default=TenderStatusEnum.CREATED)
    version = Column(Integer, nullable=False, default=1)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organization.id', ondelete='CASCADE'))
    creator_username = Column(String(50), ForeignKey('employee.username', ondelete='CASCADE'))
    createdAt = Column(TIMESTAMP, server_default=func.now())

    bids = relationship("Bid", back_populates="tender", cascade="all, delete-orphan")
    history = relationship("TenderHistory", back_populates="tender")


class TenderHistory(Base):
    __tablename__ = "tender_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    service_type = Column(Enum(TenderServiceTypeEnum), nullable=False)
    status = Column(Enum(TenderStatusEnum), nullable=False)
    version = Column(Integer, nullable=False, index=True)

    tender = relationship("Tender", back_populates="history")


class Bid(Base):
    __tablename__ = "bids"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)
    description = Column(Text)
    status = Column(Enum(BidStatusEnum), nullable=False, default=BidStatusEnum.CREATED)
    version = Column(Integer, nullable=False, default=1)
    tender_id = Column(UUID(as_uuid=True), ForeignKey('tenders.id', ondelete='CASCADE'))
    author_type = Column(Enum(BidAuthorTypeEnum), nullable=False, default=BidAuthorTypeEnum.USER)
    author_id = Column(UUID(as_uuid=True))
    createdAt = Column(TIMESTAMP, server_default=func.now())

    tender = relationship("Tender", back_populates="bids")
    reviews = relationship('Review', back_populates='bid', cascade="all, delete-orphan")
    history = relationship("BidHistory", back_populates="bid")


class BidHistory(Base):
    __tablename__ = "bid_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bid_id = Column(UUID(as_uuid=True), ForeignKey("bids.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    status = Column(Enum(BidStatusEnum), nullable=False)
    version = Column(Integer, nullable=False, index=True)

    bid = relationship("Bid", back_populates="history")


class Review(Base):
    __tablename__ = 'review'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    createdAt = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    bid_id = Column(UUID(as_uuid=True), ForeignKey('bids.id', ondelete='CASCADE'), nullable=False)
    creator_username = Column(String(50), ForeignKey('employee.username', ondelete='CASCADE'))

    bid = relationship('Bid', back_populates='reviews')
    creator = relationship("User", back_populates="reviews")
