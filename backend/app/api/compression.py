from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.services.database import get_session
from backend.app.services.compression import (
    compress_range,
    decompress_range,
    search_context,
    get_acp_status,
    get_acp_cache,
    preview_compression,
)

router = APIRouter()


class CompressRequest(BaseModel):
    session_id: str
    start_ref: str
    end_ref: str
    summary: Optional[str] = None
    dry_run: bool = False


class DecompressRequest(BaseModel):
    session_id: str
    ref: str


class SearchRequest(BaseModel):
    session_id: str
    query: str
    limit: int = 10


class ACPStatusRequest(BaseModel):
    session_id: str


class CompressResponse(BaseModel):
    success: bool
    folded_refs: List[str] = []
    excluded_protected: Dict[str, List[str]] = {}
    withdrawn_turns: List[Dict[str, Any]] = []
    consumed_blocks: List[str] = []
    estimated_tokens_saved: int = 0
    post_compression_window_usage: int = 0
    error: Optional[str] = None
    ranges: List[Dict[str, Any]] = []

class DecompressResponse(BaseModel):
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None


class SearchResponse(BaseModel):
    success: bool
    results: List[Dict[str, Any]] = []
    error: Optional[str] = None


class ACPStatusResponse(BaseModel):
    success: bool
    compressible_spans: List[Dict[str, Any]] = []
    protected_zones: Dict[str, Any] = {}
    error: Optional[str] = None


class ACPCacheResponse(BaseModel):
    success: bool
    cache_entries: List[Dict[str, Any]] = []
    error: Optional[str] = None


class PreviewCompressionResponse(BaseModel):
    success: bool
    ranges: List[Dict[str, Any]] = []
    error: Optional[str] = None


@router.post("/compress", response_model=CompressResponse)
async def compress(
    request: CompressRequest,
    session: AsyncSession = Depends(get_session),
):
    if request.dry_run:
        result = await preview_compression(session, request.session_id, request.start_ref, request.end_ref, request.summary)
    else:
        result = await compress_range(session, request.session_id, request.start_ref, request.end_ref, request.summary)
    # Return result even on validation failures (e.g., protected zones)
    # Only raise on server errors (session not found, etc.)
    if not result["success"] and result.get("error") not in ("Range fully protected", "No messages in range", "Session not found"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error"))
    return result


@router.post("/decompress", response_model=DecompressResponse)
async def decompress(
    request: DecompressRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await decompress_range(session, request.session_id, request.ref)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("error"))
    return result


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await search_context(session, request.session_id, request.query, request.limit)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error"))
    return result


@router.post("/acp_status", response_model=ACPStatusResponse)
async def acp_status(
    request: ACPStatusRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await get_acp_status(session, request.session_id)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error"))
    return result


@router.post("/acp_cache", response_model=ACPCacheResponse)
async def acp_cache(
    request: ACPStatusRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await get_acp_cache(session, request.session_id)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error"))
    return result