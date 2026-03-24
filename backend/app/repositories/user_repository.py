from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.user import UserInDB, UserCreate
from app.core.security import get_password_hash
from bson import ObjectId

class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["users"]

    async def get_by_username(self, username: str) -> Optional[UserInDB]:
        user_dict = await self.collection.find_one({"username": username})
        if user_dict:
            user_dict["id"] = str(user_dict.pop("_id"))
            return UserInDB(**user_dict)
        return None

    async def create(self, user_in: UserCreate) -> UserInDB:
        user_dict = user_in.model_dump()
        password = user_dict.pop("password")
        user_dict["password_hash"] = get_password_hash(password)
        
        result = await self.collection.insert_one(user_dict)
        user_dict["id"] = str(result.inserted_id)
        return UserInDB(**user_dict)

    async def init_default_users(self):
        # Create default users if they don't exist
        default_users = [
            {"username": "tuvan", "password": "123456", "role": "USER"},
            {"username": "cuong", "password": "123456", "role": "USER"},
            {"username": "admin", "password": "admin", "role": "ADMIN"},
        ]
        for u in default_users:
            if not await self.get_by_username(u["username"]):
                await self.create(UserCreate(**u))
