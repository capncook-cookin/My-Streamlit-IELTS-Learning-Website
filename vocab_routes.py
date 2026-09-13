"""
FastAPI router for the Groq-backed vocabulary helper.

Mounted from main.py via:
    from vocab_routes import router as vocab_router
    app.include_router(vocab_router)

Endpoints (the prefix "/api" is set on the router, so the final paths are):
    POST /api/vocab            -> { term, context } -> { term, plain_meaning, ... }
    GET  /api/vocab/cache-stats -> { size, hits, ttl_seconds }
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vocab_helpers import groq_define, cache_stats

router = APIRouter(prefix="/api", tags=["vocab"])


class VocabRequest(BaseModel):
    term: str
    context: str = ""


@router.post("/vocab")
def vocab_lookup(req: VocabRequest):
    if not req.term.strip():
        raise HTTPException(status_code=400, detail="Term is empty.")
    result = groq_define(req.term, req.context)
    if "error" in result:
        # 502 = upstream provider problem (matches the existing /api/dictionary pattern).
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/vocab/cache-stats")
def vocab_cache_stats():
    return cache_stats()
