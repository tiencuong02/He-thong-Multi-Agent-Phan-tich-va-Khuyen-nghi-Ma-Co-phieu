from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from app.core.security import ALGORITHM, SECRET_KEY
from app.models.user import Token, User, UserRole
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
from app.db.mongodb import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

def get_auth_service(db=Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection not available")
    repo = UserRepository(db)
    return AuthService(repo)

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    service: AuthService = Depends(get_auth_service)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await service.get_current_user(username)
    return User(
        id=user.id, 
        username=user.username, 
        role=user.role,
        gender=user.gender,
        dob=user.dob,
        investment_style=user.investment_style
    )

def check_admin_role(user: User = Depends(get_current_user)):
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return user

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service)
):
    return await service.login(form_data.username, form_data.password)

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

class ProfileUpdate(BaseModel):
    gender: Optional[str] = None
    dob: Optional[str] = None
    investment_style: Optional[str] = None

@router.put("/profile")
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    repo = UserRepository(db)
    logger.info(f"Updating profile for user {current_user.id}: {data}")
    updated = await repo.update_profile(
        current_user.id, 
        data.gender, 
        data.dob, 
        data.investment_style
    )
    if not updated:
        logger.error(f"Failed to update profile in DB for user {current_user.id}")
        raise HTTPException(status_code=500, detail="Failed to update profile")
    return {"message": "Profile updated"}
