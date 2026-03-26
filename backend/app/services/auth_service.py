import logging
from typing import Optional
from datetime import timedelta
from fastapi import HTTPException, status
from app.repositories.user_repository import UserRepository
from app.models.user import UserCreate, UserInDB, Token, User
from app.core.security import verify_password, create_access_token

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

    async def get_current_user(self, username: str) -> UserInDB:
        user = await self.user_repo.get_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
