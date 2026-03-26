from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.stock import AnalysisResult
from datetime import datetime

class ReportRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db["reports"]

    async def save_report(self, report: AnalysisResult):
        report_dict = report.dict()
        await self.collection.insert_one(report_dict)

    async def get_recent_reports(self, limit: int = 10, user_id: Optional[str] = None) -> List[AnalysisResult]:
        query = {"user_id": user_id} if user_id else {}
        cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
        reports = []
        async for doc in cursor:
            # Remove MongoDB's _id for Pydantic parsing
            doc.pop("_id", None)
            reports.append(AnalysisResult(**doc))
        return reports

    async def delete_all(self):
        await self.collection.delete_many({})

    async def get_ticker_stats(self, limit: int = 10) -> List[dict]:
        pipeline = [
            {"$group": {"_id": "$ticker", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit},
            {"$project": {"ticker": "$_id", "count": 1, "_id": 0}}
        ]
        cursor = self.collection.aggregate(pipeline)
        return await cursor.to_list(length=limit)

    async def get_recommendation_stats(self) -> List[dict]:
        pipeline = [
            {"$group": {"_id": "$recommendation", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$project": {"recommendation": "$_id", "count": 1, "_id": 0}}
        ]
        cursor = self.collection.aggregate(pipeline)
        return await cursor.to_list(length=10)
