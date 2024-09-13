from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy import select, delete, asc
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional

from database.engine import get_db, Base, engine
from database.models import Tender as DBTender, Bid as DBBid, Review as DBReview, TenderHistory, BidHistory, \
    TenderStatusEnum, TenderServiceTypeEnum, BidStatusEnum
from database.schemas import TenderCreate, TenderRead, BidCreate, BidRead, ReviewRead, \
    TenderUpdate, BidUpdate
from database.crud import check_user_organization, check_user_tender, check_responsible, check_author, check_tender, \
    get_user, check_user_bid, check_responsible_bid, get_bid, get_tender, get_user_organization

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/api/ping", response_model=str)
async def ping():
    return "ok"


@app.get("/api/tenders", response_model=List[TenderRead])
async def get_tenders(
        service_type: Optional[List[str]] = Query(None),
        limit: int = 5,
        offset: int = 0,
        db: AsyncSession = Depends(get_db)
):
    query = select(DBTender)

    print(service_type)
    if service_type:
        try:
            service_types_enum = [TenderServiceTypeEnum(st) for st in service_type]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid service type provided.")
        query = query.where(DBTender.service_type.in_(service_types_enum))

    query = query.order_by(asc(DBTender.name))
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    tenders = result.scalars().all()
    return tenders


@app.post("/api/tenders/new", response_model=TenderRead)
async def create_tender(tender: TenderCreate, db: AsyncSession = Depends(get_db)):
    db_tender = DBTender(**tender.dict())
    await check_user_organization(db, tender)
    db.add(db_tender)
    try:
        await db.commit()
        await db.refresh(db_tender)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return db_tender


@app.get("/api/tenders/my", response_model=List[TenderRead])
async def get_my_tenders(
        username: str,
        limit: int = 5,
        offset: int = 0,
        db: AsyncSession = Depends(get_db)
):
    if not username:
        raise HTTPException(status_code=401, detail='user not found')

    query = select(DBTender).filter(DBTender.creator_username == username).order_by(DBTender.name).limit(limit).offset(
        offset)

    result = await db.execute(query)
    tenders = result.scalars().all()

    return tenders


@app.get("/api/tenders/{tender_id}/status")
async def get_tender_status(tender_id: UUID, username: str, db: AsyncSession = Depends(get_db)):
    user, tender = await check_user_tender(db, username, tender_id)
    await check_responsible(db, user, tender)
    return tender.status


@app.put("/api/tenders/{tender_id}/status", response_model=TenderRead)
async def update_tender_status(tender_id: UUID, status: TenderStatusEnum, username: str,
                               db: AsyncSession = Depends(get_db)):
    user, tender = await check_user_tender(db, username, tender_id)
    await check_responsible(db, user, tender)
    tender.status = status
    await db.commit()
    await db.refresh(tender)
    return tender


@app.patch("/api/tenders/{tender_id}/edit", response_model=TenderRead)
async def update_tender(tender_id: UUID, username: str, update_data: TenderUpdate, db: AsyncSession = Depends(get_db)):
    user, tender = await check_user_tender(db, username, tender_id)
    await check_responsible(db, user, tender)

    history = TenderHistory(
        tender_id=tender.id,
        name=tender.name,
        description=tender.description,
        service_type=tender.service_type,
        status=tender.status,
        version=tender.version
    )
    db.add(history)

    try:
        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(tender, key, value)
        tender.version += 1
        await db.commit()
        await db.refresh(tender)
        return tender
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/tenders/{tender_id}/rollback/{version}", response_model=TenderRead)
async def rollback_tender(tender_id: UUID, username: str, version: int, db: AsyncSession = Depends(get_db)):
    user, tender = await check_user_tender(db, username, tender_id)
    await check_responsible(db, user, tender)
    if tender.version < version or version < 1:
        raise HTTPException(status_code=404, detail="version not found")
    if tender.version == version:
        return tender
    result = await db.execute(select(TenderHistory).filter(
        TenderHistory.tender_id == tender_id, TenderHistory.version == version))
    db_old_tender_version = result.scalar_one_or_none()

    tender.name = db_old_tender_version.name
    tender.description = db_old_tender_version.description
    tender.service_type = db_old_tender_version.service_type
    tender.status = db_old_tender_version.status
    tender.version = db_old_tender_version.version

    await db.execute(delete(TenderHistory).where(
        TenderHistory.tender_id == tender_id,
        TenderHistory.version > version
    ))

    try:
        await db.commit()
        await db.refresh(tender)
        return tender
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/bids/new", response_model=BidRead)
async def create_bid(bid: BidCreate, db: AsyncSession = Depends(get_db)):
    db_bid = DBBid(**bid.dict())
    await check_author(db, bid)
    await check_tender(db, bid)
    db.add(db_bid)
    try:
        await db.commit()
        await db.refresh(db_bid)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return db_bid


@app.get("/api/bids/my", response_model=List[BidRead])
async def get_my_bids(
        username: str,
        limit: int = 5,
        offset: int = 0,
        db: AsyncSession = Depends(get_db)
):
    user = await get_user(db, username)
    query = select(DBBid).filter(DBBid.author_id == user.id).order_by(DBBid.name).limit(limit).offset(offset)
    result = await db.execute(query)
    bids = result.scalars().all()
    return bids


@app.get("/api/bids/{tender_id}/list", response_model=List[BidRead])
async def get_bids_by_tender(
        tender_id: UUID,
        username: str,
        limit: int = 5,
        offset: int = 0,
        db: AsyncSession = Depends(get_db)
):
    user, tender = await check_user_tender(db, username, tender_id)
    await check_responsible(db, user, tender)

    query = select(DBBid).filter(DBBid.tender_id == tender_id).order_by(DBBid.name).limit(limit).offset(offset)
    result = await db.execute(query)
    bids = result.scalars().all()
    return bids


@app.get("/api/bids/{bidId}/status")
async def get_bid_status(bidId: UUID, username: str, db: AsyncSession = Depends(get_db)):
    user, bid = await check_user_bid(db, username, bidId)
    if bid.status == BidStatusEnum.PUBLISHED:
        return
    await check_responsible_bid(db, user, bid)
    return bid.status


@app.put("/api/bids/{bidId}/status", response_model=BidRead)
async def update_bid_status(bidId: UUID, status: BidStatusEnum, username: str,
                               db: AsyncSession = Depends(get_db)):
    user, bid = await check_user_bid(db, username, bidId)
    await check_responsible_bid(db, user, bid)
    bid.status = status
    await db.commit()
    await db.refresh(bid)
    return bid


@app.patch("/api/bids/{bidId}/edit", response_model=BidRead)
async def update_bid(bidId: UUID, username: str, update_data: BidUpdate, db: AsyncSession = Depends(get_db)):
    user, bid = await check_user_bid(db, username, bidId)
    await check_responsible_bid(db, user, bid)

    history = BidHistory(
        bid_id=bid.id,
        name=bid.name,
        description=bid.description,
        status=bid.status,
        version=bid.version
    )
    db.add(history)

    try:
        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(bid, key, value)
        bid.version += 1
        await db.commit()
        await db.refresh(bid)
        return bid
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/bids/{bidId}/rollback/{version}", response_model=BidRead)
async def rollback_bid(bidId: UUID, username: str, version: int, db: AsyncSession = Depends(get_db)):
    user, bid = await check_user_bid(db, username, bidId)
    await check_responsible_bid(db, user, bid)
    if bid.version < version or version < 1:
        raise HTTPException(status_code=404, detail="version not found")
    if bid.version == version:
        return bid
    result = await db.execute(select(BidHistory).filter(
        BidHistory.bid_id == bidId, BidHistory.version == version))
    db_old_bid_version = result.scalar_one_or_none()

    bid.name = db_old_bid_version.name
    bid.description = db_old_bid_version.description
    bid.status = db_old_bid_version.status
    bid.version = db_old_bid_version.version

    await db.execute(delete(BidHistory).where(
        BidHistory.bid_id == bidId,
        BidHistory.version > version
    ))

    try:
        await db.commit()
        await db.refresh(bid)
        return bid
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/bids/{bidId}/submit_decision", response_model=BidRead)
async def submit_decision(bidId: UUID, decision: str, username: str, db: AsyncSession = Depends(get_db)):
    bid = await get_bid(db, bidId)
    tender = await get_tender(db, bid.tender_id)
    user = await get_user(db, username)
    user_organization = await get_user_organization(db, user)
    if tender.organization_id == user_organization:
        if decision == 'Approved':
            tender.status = TenderStatusEnum.CLOSED
            bid.status = BidStatusEnum.CANCELED
            await db.commit()
            await db.refresh(tender)
            return bid
        elif decision == 'Rejected':
            bid.status = BidStatusEnum.CANCELED
            await db.commit()
            await db.refresh(tender)
            return bid
        else:
            raise HTTPException(status_code=400, detail='decision not found')


@app.get("/api/bids/{tender_id}/reviews", response_model=List[ReviewRead])
async def get_reviews(tender_id: UUID, author_username: Optional[str] = None, organization_id: Optional[UUID] = None,
                      db: AsyncSession = Depends(get_db)):
    query = db.query(DBReview).join(DBBid).filter(DBBid.tender_id == tender_id)
    if author_username:
        query = query.filter(DBReview.creator_username == author_username)
    if organization_id:
        query = query.join(DBBid).filter(DBBid.organization_id == organization_id)
    result = await query.all()
    return result
