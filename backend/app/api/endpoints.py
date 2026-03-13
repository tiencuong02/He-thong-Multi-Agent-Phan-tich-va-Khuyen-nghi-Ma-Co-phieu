from fastapi import APIRouter

router = APIRouter()

@router.post("/analyze/{ticker}")
async def analyze_stock(ticker: str):
    # TODO: Implement agent trigger here
    return {"message": f"Analyzing {ticker}"}

@router.get("/history")
async def get_history():
    # TODO: Implement fetch from MongoDB
    return {"history": []}
