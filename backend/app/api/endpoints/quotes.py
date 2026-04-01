from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.quote import Quote, QuoteCreate, QuoteUpdate, QuoteLog, QuoteContext
from app.models.user import User
from app.api.endpoints.auth import get_current_user, check_admin_role
from app.services.quote_service import QuoteService
from app.repositories.quote_repository import QuoteRepository
from app.db.mongodb import get_db

router = APIRouter()

def get_quote_service(db=Depends(get_db)):
    repo = QuoteRepository(db)
    return QuoteService(repo)

@router.get("/", response_model=List[Quote])
async def get_quotes(
    service: QuoteService = Depends(get_quote_service),
    current_user: User = Depends(get_current_user)
):
    return await service.get_quotes()

@router.post("/", response_model=Quote)
async def create_quote(
    quote_in: QuoteCreate,
    service: QuoteService = Depends(get_quote_service),
    admin_user: User = Depends(check_admin_role)
):
    return await service.create_quote(quote_in)

@router.put("/{quote_id}", response_model=Quote)
async def update_quote(
    quote_id: str,
    quote_in: QuoteUpdate,
    service: QuoteService = Depends(get_quote_service),
    admin_user: User = Depends(check_admin_role)
):
    updated = await service.update_quote(quote_id, quote_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Quote not found")
    return updated

@router.delete("/{quote_id}")
async def delete_quote(
    quote_id: str,
    service: QuoteService = Depends(get_quote_service),
    admin_user: User = Depends(check_admin_role)
):
    deleted = await service.delete_quote(quote_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Quote not found")
    return {"message": "Quote deleted"}

@router.get("/random", response_model=Quote)
async def get_random_quote(
    context: QuoteContext = QuoteContext.HOLD,
    service: QuoteService = Depends(get_quote_service),
    current_user: User = Depends(get_current_user)
):
    quote = await service.get_random_quote(current_user.id, context)
    if not quote:
        raise HTTPException(status_code=404, detail="No quotes found for this context")
    return quote

@router.get("/stats/", response_model=dict)
async def get_quote_stats(
    service: QuoteService = Depends(get_quote_service),
    admin_user: User = Depends(check_admin_role)
):
    return await service.get_overall_stats()

@router.get("/stats/by-user/")
async def get_quote_stats_by_user(
    service: QuoteService = Depends(get_quote_service),
    admin_user: User = Depends(check_admin_role)
):
    return await service.get_user_stats()

@router.get("/recent-logs/")
async def get_recent_logs(
    limit: int = 20,
    skip: int = 0,
    user_id: Optional[str] = None,
    service: QuoteService = Depends(get_quote_service),
    admin_user: User = Depends(check_admin_role)
):
    """Return paginated log entries, optionally filtered by user_id."""
    return await service.get_recent_logs(limit=limit, skip=skip, user_id=user_id)

@router.get("/activity-summary/")
async def get_activity_summary(
    service: QuoteService = Depends(get_quote_service),
    admin_user: User = Depends(check_admin_role)
):
    """Return aggregated activity grouped by user with count and last_seen."""
    return await service.get_activity_summary()
