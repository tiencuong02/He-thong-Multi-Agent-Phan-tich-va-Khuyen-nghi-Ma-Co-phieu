import logging
from typing import Optional
from datetime import timedelta
from fastapi import HTTPException, status
from app.repositories.user_repository import UserRepository
from app.models.user import UserCreate, UserInDB, Token, User
from app.core.security import (
    verify_password, create_access_token,
    validate_password, create_reset_token, verify_reset_token,
    get_password_hash,
)

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def authenticate_user(self, username: str, password: str) -> Optional[UserInDB]:
        user = await self.user_repo.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def login(self, username: str, password: str) -> Token:
        user = await self.authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = create_access_token(subject=user.username)
        user_data = User(
            id=user.id, 
            username=user.username, 
            role=user.role,
            gender=user.gender,
            dob=user.dob,
            investment_style=user.investment_style
        )
        return Token(access_token=access_token, token_type="bearer", user=user_data)

    async def register(self, username: str, password: str, security_phrase: str) -> dict:
        if await self.user_repo.exists(username):
            raise HTTPException(status_code=400, detail="Username already exists")

        valid, msg = validate_password(password)
        if not valid:
            raise HTTPException(status_code=400, detail=msg)

        if len(security_phrase.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Security phrase must be at least 10 characters"
            )

        await self.user_repo.create_with_phrase(username, password, security_phrase)
        logger.info(f"[AUTH] New user registered: {username}")
        return {"message": "Registration successful"}

    async def verify_phrase(self, username: str, security_phrase: str) -> dict:
        result = await self.user_repo.verify_security_phrase(username, security_phrase)

        if result is None:
            # Distinguish "user not found" from "no phrase set"
            user = await self.user_repo.get_by_username(username)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            raise HTTPException(
                status_code=400,
                detail="This account has no security phrase. Please contact administrator."
            )

        if not result:
            raise HTTPException(status_code=401, detail="Incorrect security phrase")

        reset_token = create_reset_token(username)
        logger.info(f"[AUTH] Reset token issued for: {username}")
        return {"reset_token": reset_token}

    async def reset_password(self, reset_token: str, new_password: str) -> dict:
        username = verify_reset_token(reset_token)
        if not username:
            raise HTTPException(
                status_code=401,
                detail="Reset link has expired or is invalid. Please start over."
            )

        valid, msg = validate_password(new_password)
        if not valid:
            raise HTTPException(status_code=400, detail=msg)

        success = await self.user_repo.update_password(username, new_password)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update password")

        logger.info(f"[AUTH] Password reset completed for: {username}")
        return {"message": "Password reset successfully"}

    async def get_current_user(self, username: str) -> UserInDB:
        user = await self.user_repo.get_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
