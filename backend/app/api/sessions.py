from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models import Session, Message, Fold
from app.services.database import get_db_session

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    name: str
    session_metadata: Optional[dict] = {}


class SessionResponse(BaseModel):
    id: str
    name: str
    created_at: str
    session_metadata: dict


class MessageResponse(BaseModel):
    id: str
    session_id: str
    ref: str
    role: str
    content: str
    token_count: int
    message_metadata: dict
    created_at: str


class FoldResponse(BaseModel):
    id: str
    session_id: str
    start_ref: str
    end_ref: str
    summary: str
    folded_refs: List[str]
    token_count: int
    fold_metadata: dict
    created_at: str


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: SessionCreate,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Create a new session."""
    sess = Session(name=request.name, session_metadata=request.session_metadata or {})
    db_session.add(sess)
    await db_session.commit()
    await db_session.refresh(sess)
    return SessionResponse(
        id=sess.id,
        name=sess.name,
        created_at=sess.created_at.isoformat() if sess.created_at else "",
        session_metadata=sess.session_metadata or {},
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Get a session by ID."""
    stmt = select(Session).where(Session.id == session_id)
    result = await db_session.execute(stmt)
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(
        id=sess.id,
        name=sess.name,
        created_at=sess.created_at.isoformat() if sess.created_at else "",
        session_metadata=sess.session_metadata or {},
    )


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: str,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Get all messages for a session."""
    stmt = select(Session).where(Session.id == session_id)
    result = await db_session.execute(stmt)
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    stmt = select(Message).where(Message.session_id == session_id).order_by(Message.ref)
    result = await db_session.execute(stmt)
    messages = result.scalars().all()

    return [
        MessageResponse(
            id=m.id,
            session_id=m.session_id,
            ref=m.ref,
            role=m.role,
            content=m.content,
            token_count=m.token_count,
            message_metadata=m.message_metadata or {},
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in messages
    ]


@router.get("/{session_id}/folds", response_model=List[FoldResponse])
async def get_session_folds(
    session_id: str,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Get all folds for a session."""
    stmt = select(Session).where(Session.id == session_id)
    result = await db_session.execute(stmt)
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    stmt = select(Fold).where(Fold.session_id == session_id).order_by(Fold.created_at)
    result = await db_session.execute(stmt)
    folds = result.scalars().all()

    return [
        FoldResponse(
            id=f.id,
            session_id=f.session_id,
            start_ref=f.start_ref,
            end_ref=f.end_ref,
            summary=f.summary,
            folded_refs=f.folded_refs or [],
            token_count=f.token_count,
            fold_metadata=f.fold_metadata or {},
            created_at=f.created_at.isoformat() if f.created_at else "",
        )
        for f in folds
    ]