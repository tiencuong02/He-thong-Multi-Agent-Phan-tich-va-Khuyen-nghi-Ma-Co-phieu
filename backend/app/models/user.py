from typing import Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class UserBase(BaseModel):
    username: str
    role: UserRole = UserRole.USER
    gender: Optional[str] = "male"
    dob: Optional[str] = "1990-01-01" # YYYY-MM-DD
    investment_style: Optional[str] = "short_term" # short_term or long_term

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: str
    password_hash: str
    security_phrase_hash: Optional[str] = None  # None for legacy users

    model_config = ConfigDict(from_attributes=True)

class UserRegister(BaseModel):
    username: str
    password: str
    security_phrase: str

class User(UserBase):
    id: str
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: User

class TokenData(BaseModel):
    username: Optional[str] = None
