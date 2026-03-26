from typing import Optional, List
import logging

logger = logging.getLogger(__name__)
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
            # Handle legacy field name mapping
            if "hashed_password" in user_dict and "password_hash" not in user_dict:
                user_dict["password_hash"] = user_dict.pop("hashed_password")
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
            {"username": "tuvan", "password": "123456", "role": "USER", "gender": "female", "dob": "1995-01-01", "investment_style": "long_term"},
            {"username": "cuong", "password": "123456", "role": "USER", "gender": "male", "dob": "1988-01-01", "investment_style": "short_term"},
            {"username": "admin", "password": "admin", "role": "ADMIN", "gender": "other", "dob": "1985-01-01", "investment_style": "short_term"},
        ]
        for u in default_users:
            if not await self.get_by_username(u["username"]):
                await self.create(UserCreate(**u))

    async def update_profile(self, user_id: str, gender: str, dob: str, investment_style: str) -> bool:
        from bson import ObjectId
        try:
            object_id = ObjectId(user_id)
        except Exception as e:
            logger.error(f"Invalid user_id format: {user_id}. Error: {e}")
            return False

        logger.info(f"DB Update: user_id={user_id}, gender={gender}, dob={dob}, style={investment_style}")
        result = await self.collection.update_one(
            {"_id": object_id},
            {"$set": {
                "gender": gender,
                "dob": dob,
                "investment_style": investment_style
            }}
        )
        logger.info(f"DB Update Result: matched={result.matched_count}, modified={result.modified_count}, acknowledged={result.acknowledged}")
        return result.matched_count > 0
