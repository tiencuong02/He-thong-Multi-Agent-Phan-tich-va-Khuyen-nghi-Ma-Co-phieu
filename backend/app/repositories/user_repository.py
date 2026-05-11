from typing import Optional, List
import logging

logger = logging.getLogger(__name__)
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.user import UserInDB, UserCreate
from app.core.security import get_password_hash, verify_password
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
        from app.core.config import settings
        if not settings.ADMIN_PASSWORD or not settings.USER_PASSWORD:
            logger.warning(
                "[SEED] ADMIN_PASSWORD / USER_PASSWORD not set in .env — skipping default user seeding. "
                "Set both variables before first run."
            )
            return
        default_users = [
            {"username": "tuvan", "password": settings.USER_PASSWORD, "role": "USER", "gender": "female", "dob": "1995-01-01", "investment_style": "long_term"},
            {"username": "cuong", "password": settings.USER_PASSWORD, "role": "USER", "gender": "male", "dob": "1988-01-01", "investment_style": "short_term"},
            {"username": "admin", "password": settings.ADMIN_PASSWORD, "role": "ADMIN", "gender": "other", "dob": "1985-01-01", "investment_style": "short_term"},
        ]
        for u in default_users:
            if not await self.get_by_username(u["username"]):
                await self.create(UserCreate(**u))

    async def exists(self, username: str) -> bool:
        doc = await self.collection.find_one({"username": username}, {"_id": 1})
        return doc is not None

    async def create_with_phrase(self, username: str, password: str, security_phrase: str) -> UserInDB:
        doc = {
            "username": username,
            "role": "USER",
            "gender": "male",
            "dob": "1990-01-01",
            "investment_style": "short_term",
            "password_hash": get_password_hash(password),
            "security_phrase_hash": get_password_hash(security_phrase.strip().lower()),
        }
        result = await self.collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        return UserInDB(**doc)

    async def verify_security_phrase(self, username: str, phrase: str) -> bool | None:
        """
        Returns:
            True  – phrase matches
            False – phrase wrong
            None  – user not found or no phrase set (legacy account)
        """
        doc = await self.collection.find_one({"username": username}, {"security_phrase_hash": 1})
        if not doc:
            return None
        phrase_hash = doc.get("security_phrase_hash")
        if not phrase_hash:
            return None
        return verify_password(phrase.strip().lower(), phrase_hash)

    async def update_password(self, username: str, new_password: str) -> bool:
        result = await self.collection.update_one(
            {"username": username},
            {"$set": {"password_hash": get_password_hash(new_password)}}
        )
        return result.matched_count > 0

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
