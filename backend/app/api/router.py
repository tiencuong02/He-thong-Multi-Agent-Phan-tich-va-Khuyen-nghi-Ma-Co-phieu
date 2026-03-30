from fastapi import APIRouter
from .endpoints import auth, quotes, stock, rag

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
router.include_router(stock.router, prefix="/stock", tags=["stock"])
router.include_router(rag.router, prefix="/rag", tags=["rag"])
