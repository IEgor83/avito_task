from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import database.models as models
import database.schemas as schemas


async def get_tenders(db: AsyncSession):
    result = await db.execute(select(models.Tender))
    return result.scalars().all()


async def create_tender(db: AsyncSession, tender: schemas.TenderCreate):
    db_tender = models.Tender(**tender.dict())
    db.add(db_tender)
    await db.commit()
    await db.refresh(db_tender)
    return db_tender


async def check_user_organization(db: AsyncSession, obj):
    user_result = await db.execute(select(models.User).where(models.User.username == obj.creator_username))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    organization_result = await db.execute(select(
        models.Organization).where(models.Organization.id == obj.organization_id))
    organization = organization_result.scalar_one_or_none()

    if not organization:
        raise HTTPException(status_code=401, detail="Organization not found")

    responsible_result = await db.execute(
        select(models.OrganizationResponsible).where(
            models.OrganizationResponsible.user_id == user.id,
            models.OrganizationResponsible.organization_id == obj.organization_id
        )
    )
    responsible = responsible_result.scalar_one_or_none()

    if not responsible:
        raise HTTPException(status_code=403, detail="User does not belong to the specified organization")


async def get_user(db: AsyncSession, username: str):
    if not username:
        raise HTTPException(status_code=401, detail='user not found')

    user_query = select(models.User).filter(models.User.username == username)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="user not found")

    return user


async def check_author(db: AsyncSession, obj):
    if obj.authorType == "Organization":
        organization_result = await db.execute(select(
            models.Organization).where(models.Organization.id == obj.authorId))
        organization = organization_result.scalar_one_or_none()

        if not organization:
            raise HTTPException(status_code=401, detail="Organization not found")

        return organization
    elif obj.authorType == "User":
        user_result = await db.execute(select(models.User).where(models.User.username == obj.creator_username))
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    else:
        raise HTTPException(status_code=401, detail="Incorrect type")


async def check_tender(db: AsyncSession, obj):
    tender_query = select(models.Tender).filter(models.Tender.id == obj.tenderId,
                                                models.Tender.status == models.TenderStatusEnum.PUBLISHED)
    tender_result = await db.execute(tender_query)
    tender = tender_result.scalar_one_or_none()

    if not tender:
        raise HTTPException(status_code=404, detail="tender not found")


async def check_user_tender(db: AsyncSession, username: str, tender_id: UUID):
    if not username:
        raise HTTPException(status_code=401, detail='user not found')

    user_query = select(models.User).filter(models.User.username == username)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="user not found")

    tender_query = select(models.Tender).filter(models.Tender.id == tender_id)
    tender_result = await db.execute(tender_query)
    tender = tender_result.scalar_one_or_none()

    if not tender:
        raise HTTPException(status_code=404, detail="tender not found")

    return user, tender


async def check_user_bid(db: AsyncSession, username: str, bid_id: UUID):
    if not username:
        raise HTTPException(status_code=401, detail='user not found')

    user_query = select(models.User).filter(models.User.username == username)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="user not found")

    bid_query = select(models.Tender).filter(models.Bid.id == bid_id)
    bid_result = await db.execute(bid_query)
    bid = bid_result.scalar_one_or_none()

    if not bid:
        raise HTTPException(status_code=404, detail="bid not found")

    return user, bid


async def check_responsible(db, user, db_tender):
    responsible_query = select(models.OrganizationResponsible).filter(
        models.OrganizationResponsible.user_id == user.id,
        models.OrganizationResponsible.organization_id == db_tender.organization_id
    )
    responsible_result = await db.execute(responsible_query)
    responsible = responsible_result.scalar_one_or_none()

    if not responsible:
        raise HTTPException(status_code=403, detail="user does not have access to this tender")


async def check_responsible_bid(db, user, bid):
    if bid.author_type == models.BidAuthorTypeEnum.USER:
        responsible_query_1 = select(models.OrganizationResponsible).filter(
            models.OrganizationResponsible.user_id == bid.author_id
        )
        responsible_result = await db.execute(responsible_query_1)
        responsible_1 = responsible_result.scalar_one_or_none()

        responsible_query_2 = select(models.OrganizationResponsible).filter(
            models.OrganizationResponsible.user_id == user.id
        )
        responsible_result = await db.execute(responsible_query_2)
        responsible_2 = responsible_result.scalar_one_or_none()

        if not responsible_1 or not responsible_2:
            raise HTTPException(status_code=403, detail="user does not have access to this tender")

        if not responsible_1.organization_id == responsible_2.organization_id:
            raise HTTPException(status_code=403, detail="user does not have access to this tender")
    else:
        responsible_query = select(models.OrganizationResponsible).filter(
            models.OrganizationResponsible.user_id == user.id,
            models.OrganizationResponsible.organization_id == bid.author_id
        )
        responsible_result = await db.execute(responsible_query)
        responsible = responsible_result.scalar_one_or_none()
        if not responsible:
            raise HTTPException(status_code=403, detail="user does not have access to this tender")


async def get_bid(db: AsyncSession, bid_id: UUID):
    if not bid_id:
        raise HTTPException(status_code=401, detail='bid not found')

    bid_query = select(models.Bid).filter(models.Bid.id == bid_id)
    bid_result = await db.execute(bid_query)
    bid = bid_result.scalar_one_or_none()

    if not bid:
        raise HTTPException(status_code=401, detail="bid not found")

    return bid


async def get_tender(db: AsyncSession, tender_id: UUID):
    if not tender_id:
        raise HTTPException(status_code=404, detail='tender not found')

    tender_query = select(models.Tender).filter(models.Tender.id == tender_id)
    tender_result = await db.execute(tender_query)
    tender = tender_result.scalar_one_or_none()

    if not tender:
        raise HTTPException(status_code=404, detail="tender not found")

    return tender


async def get_user_organization(db: AsyncSession, user):
    responsible_result = await db.execute(
        select(models.OrganizationResponsible).where(
            models.OrganizationResponsible.user_id == user.id,
        )
    )
    responsible = responsible_result.scalar_one_or_none()

    if not responsible:
        raise HTTPException(status_code=403, detail="User does not belong to the specified organization")

    return responsible.organization_id
