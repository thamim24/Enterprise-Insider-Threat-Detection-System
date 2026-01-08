"""
Authentication API Routes
Handles login, token refresh, and user authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import timedelta
from typing import Optional

from ..db import get_db, User, UserRole as DBUserRole
from ..core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    TokenData,
    Token,
    UserRole,
    decode_token,
    get_password_hash
)
from ..core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


class UserCreate(BaseModel):
    """User creation request"""
    username: str
    email: str
    password: str
    full_name: str
    department: str


class UserResponse(BaseModel):
    """User response model"""
    user_id: str
    username: str
    email: str
    full_name: str
    department: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response with tokens and user info"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens
    
    - **username**: User's username
    - **password**: User's password
    """
    # Find user
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create tokens
    token_data = {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role.value,
        "department": user.department
    }
    
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    refresh_token = create_refresh_token(data=token_data)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            department=user.department,
            role=user.role.value,
            is_active=user.is_active
        )
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token
    """
    try:
        token_data = decode_token(refresh_token)
        
        new_access_token = create_access_token(
            data={
                "user_id": token_data.user_id,
                "username": token_data.username,
                "role": token_data.role.value,
                "department": token_data.department
            }
        )
        
        new_refresh_token = create_refresh_token(
            data={
                "user_id": token_data.user_id,
                "username": token_data.username,
                "role": token_data.role.value,
                "department": token_data.department
            }
        )
        
        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user information
    """
    user = db.query(User).filter(User.user_id == current_user.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        department=user.department,
        role=user.role.value,
        is_active=user.is_active
    )


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user (admin only in production)
    """
    # Check if username exists
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user_count = db.query(User).count()
    new_user = User(
        user_id=f"U{user_count + 1:04d}",
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        department=user_data.department,
        role=DBUserRole.USER
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse(
        user_id=new_user.user_id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        department=new_user.department,
        role=new_user.role.value,
        is_active=new_user.is_active
    )


@router.post("/logout")
async def logout(current_user: TokenData = Depends(get_current_active_user)):
    """
    Logout user (client-side token removal)
    In production, implement token blacklisting
    """
    return {"message": "Successfully logged out", "user": current_user.username}


@router.post("/reset-demo-users")
async def reset_demo_users(db: Session = Depends(get_db)):
    """
    Reset demo users for development (REMOVE IN PRODUCTION)
    """
    from ..db.models import UserRole as DBUserRole
    
    demo_users = [
        {
            "user_id": "USR001",
            "username": "jsmith",
            "email": "jsmith@company.com",
            "full_name": "John Smith",
            "password": "password123",
            "department": "FINANCE",
            "role": DBUserRole.USER,
        },
        {
            "user_id": "USR002",
            "username": "mjohnson",
            "email": "mjohnson@company.com",
            "full_name": "Mary Johnson",
            "password": "password123",
            "department": "HR",
            "role": DBUserRole.USER,
        },
        {
            "user_id": "USR003",
            "username": "analyst",
            "email": "analyst@company.com",
            "full_name": "Security Analyst",
            "password": "analyst123",
            "department": "IT",
            "role": DBUserRole.ANALYST,
        },
        {
            "user_id": "USR004",
            "username": "admin",
            "email": "admin@company.com",
            "full_name": "System Administrator",
            "password": "admin123",
            "department": "IT",
            "role": DBUserRole.ADMIN,
        },
    ]
    
    created = []
    updated = []
    
    for user_data in demo_users:
        existing = db.query(User).filter(User.username == user_data["username"]).first()
        
        if existing:
            # Update existing user
            existing.hashed_password = get_password_hash(user_data["password"])
            existing.user_id = user_data["user_id"]
            existing.department = user_data["department"]
            existing.role = user_data["role"]
            existing.is_active = True
            updated.append(user_data["username"])
        else:
            # Create new user
            new_user = User(
                user_id=user_data["user_id"],
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                department=user_data["department"],
                role=user_data["role"],
                is_active=True,
            )
            db.add(new_user)
            created.append(user_data["username"])
    
    db.commit()
    
    return {
        "message": "Demo users reset successfully",
        "created": created,
        "updated": updated
    }