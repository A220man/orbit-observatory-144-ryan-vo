from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from app.models import Session, Message, Fold, AuditLog
import hashlib


async def compress_range(
    session: AsyncSession,
    session_id: str,
    start_ref: str,
    end_ref: str,
    summary: Optional[str] = None,
) -> Dict[str, Any]:
    """Compress a range of messages into a fold."""
    # Get session
    stmt = select(Session).where(Session.id == session_id)
    result = await session.execute(stmt)
    sess = result.scalar_one_or_none()
    if not sess:
        return {"success": False, "error": "Session not found"}

    # Get messages in range
    stmt = select(Message).where(
        Message.session_id == session_id,
        Message.ref >= start_ref,
        Message.ref <= end_ref,
    ).order_by(Message.ref)
    result = await session.execute(stmt)
    messages = result.scalars().all()

    if not messages:
        return {"success": False, "error": "No messages in range"}

    # Get ALL messages in session for protected zone calculation
    stmt_all = select(Message).where(
        Message.session_id == session_id
    ).order_by(Message.ref)
    result_all = await session.execute(stmt_all)
    all_messages = result_all.scalars().all()

    # Check protected zones (recent-N, last user message, protected tools)
    protected_refs = await _get_protected_refs(session, session_id, all_messages)
    filtered_messages = [m for m in messages if m.ref not in protected_refs]

    if not filtered_messages:
        return {
            "success": False,
            "error": "Range fully protected",
            "excluded_protected": {"fully_protected": [m.ref for m in messages]},
        }

    # Calculate token savings
    total_tokens = sum(m.token_count for m in filtered_messages)
    folded_refs = [m.ref for m in filtered_messages]

    # Generate summary if not provided
    if not summary:
        content = "\n".join(m.content for m in filtered_messages[:5])
        summary = f"Compressed {len(filtered_messages)} messages (~{total_tokens} tokens): {content[:200]}..."

    # Create fold
    fold = Fold(
        session_id=session_id,
        start_ref=start_ref,
        end_ref=end_ref,
        summary=summary,
        folded_refs=folded_refs,
        token_count=total_tokens,
    )
    session.add(fold)

    # Mark messages as folded
    for msg in filtered_messages:
        if not msg.message_metadata:
            msg.message_metadata = {}
        msg.message_metadata["folded"] = True
        msg.message_metadata["fold_id"] = fold.id

    # Audit log
    audit = AuditLog(
        session_id=session_id,
        action="compress",
        details={
            "fold_id": fold.id,
            "start_ref": start_ref,
            "end_ref": end_ref,
            "folded_count": len(filtered_messages),
            "tokens_saved": total_tokens,
        },
    )
    session.add(audit)
    await session.commit()

    return {
        "success": True,
        "folded_refs": folded_refs,
        "excluded_protected": _categorize_protected(protected_refs, messages),
        "withdrawn_turns": [],
        "consumed_blocks": [fold.id],
        "estimated_tokens_saved": total_tokens,
        "post_compression_window_usage": max(0, total_tokens - 5000),
    }


async def decompress_range(
    session: AsyncSession,
    session_id: str,
    ref: str,
) -> Dict[str, Any]:
    """Decompress a folded range."""
    stmt = select(Fold).where(Fold.session_id == session_id, Fold.id == ref)
    result = await session.execute(stmt)
    fold = result.scalar_one_or_none()
    if not fold:
        return {"success": False, "error": "Fold not found"}

    content = f"[Decompressed fold {fold.id}]\n{fold.summary}\n\nOriginal refs: {', '.join(fold.folded_refs)}"

    return {"success": True, "content": content}


async def search_context(
    session: AsyncSession,
    session_id: str,
    query: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """Search folded and unfolded content."""
    # Search messages
    stmt = select(Message).where(
        Message.session_id == session_id,
        Message.content.contains(query),
    ).limit(limit)
    result = await session.execute(stmt)
    messages = result.scalars().all()

    # Search folds
    stmt = select(Fold).where(
        Fold.session_id == session_id,
        Fold.summary.contains(query),
    ).limit(limit)
    result = await session.execute(stmt)
    folds = result.scalars().all()

    results = []
    for m in messages:
        results.append({"type": "message", "ref": m.ref, "content": m.content[:500], "score": 1.0})
    for f in folds:
        results.append({"type": "fold", "ref": f.id, "content": f.summary[:500], "score": 0.8})

    return {"success": True, "results": results[:limit]}


async def get_acp_status(
    session: AsyncSession,
    session_id: str,
) -> Dict[str, Any]:
    """Get ACP compressible spans and protected zones."""
    stmt = select(Message).where(Message.session_id == session_id).order_by(Message.ref)
    result = await session.execute(stmt)
    messages = result.scalars().all()

    protected_zones = await _get_protected_zones(session, session_id, messages)

    compressible_spans = []
    current_span = None
    for msg in messages:
        if msg.ref in protected_zones:
            if current_span:
                compressible_spans.append(current_span)
                current_span = None
        else:
            if not current_span:
                current_span = {"start_ref": msg.ref, "end_ref": msg.ref, "token_count": msg.token_count}
            else:
                current_span["end_ref"] = msg.ref
                current_span["token_count"] += msg.token_count
    if current_span:
        compressible_spans.append(current_span)

    return {
        "success": True,
        "compressible_spans": compressible_spans,
        "protected_zones": protected_zones,
    }


async def get_acp_cache(
    session: AsyncSession,
    session_id: str,
) -> Dict[str, Any]:
    """Get ACP cache entries."""
    stmt = select(Fold).where(Fold.session_id == session_id)
    result = await session.execute(stmt)
    folds = result.scalars().all()

    cache_entries = []
    for fold in folds:
        cache_entries.append({
            "ref": fold.id,
            "start_ref": fold.start_ref,
            "end_ref": fold.end_ref,
            "summary": fold.summary[:200],
            "token_count": fold.token_count,
            "folded_count": len(fold.folded_refs),
        })

    return {"success": True, "cache_entries": cache_entries}


async def preview_compression(
    session: AsyncSession,
    session_id: str,
    start_ref: str,
    end_ref: str,
    summary: Optional[str] = None,
) -> Dict[str, Any]:
    """Preview compression without committing (dry-run)."""
    stmt = select(Session).where(Session.id == session_id)
    result = await session.execute(stmt)
    sess = result.scalar_one_or_none()
    if not sess:
        return {"success": False, "error": "Session not found"}

    stmt = select(Message).where(
        Message.session_id == session_id,
        Message.ref >= start_ref,
        Message.ref <= end_ref,
    ).order_by(Message.ref)
    result = await session.execute(stmt)
    messages = result.scalars().all()

    if not messages:
        return {"success": False, "error": "No messages in range"}

    # Get ALL messages in session for protected zone calculation
    stmt_all = select(Message).where(
        Message.session_id == session_id
    ).order_by(Message.ref)
    result_all = await session.execute(stmt_all)
    all_messages = result_all.scalars().all()

    protected_refs = await _get_protected_refs(session, session_id, all_messages)
    filtered_messages = [m for m in messages if m.ref not in protected_refs]

    if not filtered_messages:
        return {
            "success": False,
            "error": "Range fully protected",
            "excluded_protected": {"fully_protected": [m.ref for m in messages]},
        }

    total_tokens = sum(m.token_count for m in filtered_messages)
    folded_refs = [m.ref for m in filtered_messages]

    # Determine validation errors
    errors = []
    if len(filtered_messages) < 1:
        errors.append("below_min_range")
    if total_tokens <= 0:
        errors.append("negative_net_benefit")

    excluded = _categorize_protected(protected_refs, messages)

    ranges = [{
        "start_ref": start_ref,
        "end_ref": end_ref,
        "would_fold": folded_refs,
        "excluded_protected": excluded,
        "withdrawn_turns": [],
        "consumed_blocks": [],
        "estimated_tokens_saved": total_tokens,
        "post_compression_window_usage": max(0, total_tokens - 5000),
        "valid": len(errors) == 0,
        "errors": errors,
    }]

    return {"success": True, "ranges": ranges}


async def _get_protected_refs(
    session: AsyncSession,
    session_id: str,
    messages: List[Message],
) -> set:
    """Get refs that should be protected from folding."""
    protected = set()

    # Last user message
    user_msgs = [m for m in messages if m.role == "user"]
    if user_msgs:
        protected.add(user_msgs[-1].ref)

    # Recent N (last 10 messages)
    for m in messages[-10:]:
        protected.add(m.ref)

    # Protected tools
    for m in messages:
        if m.message_metadata.get("protected_tool"):
            protected.add(m.ref)

    return protected


async def _get_protected_zones(
    session: AsyncSession,
    session_id: str,
    messages: List[Message],
) -> Dict[str, Any]:
    """Get protected zones for ACP status."""
    zones = {"recent_n": [], "last_user_message": [], "protected_tools": []}

    user_msgs = [m for m in messages if m.role == "user"]
    if user_msgs:
        zones["last_user_message"].append(user_msgs[-1].ref)

    for m in messages[-10:]:
        zones["recent_n"].append(m.ref)

    for m in messages:
        if m.message_metadata.get("protected_tool"):
            zones["protected_tools"].append(m.ref)

    return zones


def _categorize_protected(protected_refs: set, messages: List[Message]) -> Dict[str, List[str]]:
    """Categorize protected refs by reason."""
    categories = {"recent_n_zone": [], "last_user_message": [], "protected_tools": []}
    user_msgs = [m for m in messages if m.role == "user"]
    last_user_ref = user_msgs[-1].ref if user_msgs else None

    for m in messages:
        if m.ref in protected_refs:
            if m.message_metadata.get("protected_tool"):
                categories["protected_tools"].append(m.ref)
            elif m.ref == last_user_ref:
                categories["last_user_message"].append(m.ref)
            else:
                categories["recent_n_zone"].append(m.ref)

    return {k: v for k, v in categories.items() if v}