from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase

class AuditRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["audit_logs"]

    async def log(
        self,
        user_id: Optional[str],
        username: Optional[str],
        action: str,
        resource_id: Optional[str] = None,
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """Lưu một bản ghi audit mới."""
        doc = {
            "timestamp": datetime.now(timezone.utc),
            "user_id": user_id,
            "username": username,
            "action": action,
            "resource_id": resource_id,
            "status": status,
            "metadata": metadata or {},
            "ip_address": ip_address
        }
        result = await self.collection.insert_one(doc)
        return bool(result.inserted_id)

    async def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lấy danh sách các hoạt động gần đây."""
        cursor = self.collection.find().sort("timestamp", -1).limit(limit)
        logs = await cursor.to_list(length=limit)
        # Chuyển ObjectId sang string để dễ dùng ở API
        for log in logs:
            log["id"] = str(log["_id"])
        return logs
