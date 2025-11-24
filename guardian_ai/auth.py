import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

"""
This module handles user authentication, password hashing, and JWT creation.
"""
from .database import SESSION_LOCAL, User as DBUser

# --- Configuration ---
SECRET_KEY = os.getenv("SECRET_KEY", "a_super_secret_key_for_development")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- OAuth2 Scheme ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# --- Pydantic Models ---
class Token(BaseModel):
    """Represents the structure of an access token."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Represents the data encoded within a token."""

    username: Optional[str] = None


class User(BaseModel):
    """Base user model for request and response."""

    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserInDB(User):
    """User model as stored in the database, including hashed password."""

    hashed_password: str


class UserCreate(User):
    """User model for creating a new user, including a plain-text password."""

    password: str

# --- Database Dependency ---
def get_db():
    """Generator function to get a database session."""
    db = SESSION_LOCAL()
    try:
        yield db
    finally:
        db.close()


# --- Utility Functions ---
def get_user(db: Session, username: str):
    """Retrieves a user from the database by username."""
    return db.query(DBUser).filter(DBUser.username == username).first()


def verify_password(plain_password, hashed_password):
    """Verifies a plain-text password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_user(db: Session, user: UserCreate):
    """Creates a new user in the database."""
    db_user = DBUser(
        username=user.username,
        hashed_password=pwd_context.hash(user.password),
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# --- Dependency for Getting Current User ---
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """
    Dependency to get the current authenticated user from a token.
    Raises HTTPException if the token is invalid or the user does not exist.
    """
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
        token_data = TokenData(username=username)
    except JWTError as exc:
        raise credentials_exception from exc
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user
