from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class OrganizationTypeEnum(str, Enum):
    IE = "IE"
    LLC = "LLC"
    JSC = "JSC"


class TenderStatusEnum(str, Enum):
    CREATED = "CREATED"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"


class TenderServiceTypeEnum(str, Enum):
    CONSTRUCTION = "CONSTRUCTION"
    DELIVERY = "DELIVERY"
    MANUFACTURE = "MANUFACTURE"


class BidStatusEnum(str, Enum):
    CREATED = "CREATED"
    PUBLISHED = "PUBLISHED"
    CANCELED = "CANCELED"


class BidAuthorTypeEnum(str, Enum):
    ORGANIZATION = "Organization"
    USER = "User"


class UserBase(BaseModel):
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class OrganizationBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: OrganizationTypeEnum


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationRead(OrganizationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TenderBase(BaseModel):
    name: str
    description: Optional[str] = None
    service_type: TenderServiceTypeEnum
    status: TenderStatusEnum
    organization_id: UUID
    creator_username: str


class TenderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    service_type: TenderServiceTypeEnum


class TenderCreate(BaseModel):
    name: str
    description: Optional[str] = None
    service_type: TenderServiceTypeEnum
    organization_id: UUID
    creator_username: str


class TenderRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    service_type: TenderServiceTypeEnum
    status: TenderStatusEnum
    version: int
    createdAt: datetime

    class Config:
        orm_mode = True


class BidBase(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    status: BidStatusEnum
    tenderId: UUID = Field(..., alias='tender_id')
    authorType: BidAuthorTypeEnum = Field(..., alias='author_type')
    authorId: UUID = Field(..., alias='author_id')
    createdAt: datetime


class BidUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class BidCreate(BaseModel):
    name: str
    description: Optional[str] = None
    tenderId: UUID = Field(..., alias='tender_id')
    authorType: BidAuthorTypeEnum = Field(..., alias='author_type')
    authorId: UUID = Field(..., alias='author_id')

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class BidRead(BidBase):
    class Config:
        orm_mode = True


class ReviewBase(BaseModel):
    content: str
    bid_id: UUID
    creator_username: str


class ReviewCreate(ReviewBase):
    pass


class ReviewRead(ReviewBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
