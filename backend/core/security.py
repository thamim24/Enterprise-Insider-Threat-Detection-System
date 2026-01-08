"""
Security utilities for authentication and authorization
JWT token handling, password hashing, and role-based access control
"""
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from enum import Enum

from .config import get_settings, ROLES

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class UserRole(str, Enum):
    """User role enumeration"""
    USER = "USER"
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


class TokenData(BaseModel):
    """Token payload data"""
    user_id: str
    username: str
    role: UserRole
    department: str
    exp: datetime


class Token(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Payload data (user_id, username, role, department)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token
    
    Args:
        data: Payload data
        
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData object with user information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        user_id: str = payload.get("user_id")
        username: str = payload.get("username")
        role: str = payload.get("role")
        department: str = payload.get("department")
        exp: datetime = datetime.fromtimestamp(payload.get("exp"))
        
        if user_id is None or username is None:
            raise credentials_exception
            
        return TokenData(
            user_id=user_id,
            username=username,
            role=UserRole(role),
            department=department,
            exp=exp
        )
        
    except JWTError:
        raise credentials_exception


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    Get current user from JWT token
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        TokenData with current user information
    """
    return decode_token(token)


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Get current active user (can add additional checks here)
    
    Args:
        current_user: Current user from token
        
    Returns:
        TokenData if user is active
    """
    # Add any additional active user checks here
    return current_user


def require_role(allowed_roles: list[UserRole]):
    """
    Dependency to require specific roles
    
    Args:
        allowed_roles: List of roles that are allowed
        
    Returns:
        Dependency function that validates role
    """
    async def role_checker(
        current_user: TokenData = Depends(get_current_active_user)
    ) -> TokenData:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role} not authorized. Required: {allowed_roles}"
            )
        return current_user
    
    return role_checker


def require_analyst():
    """Require ANALYST or ADMIN role"""
    return require_role([UserRole.ANALYST, UserRole.ADMIN])


def require_admin():
    """Require ADMIN role"""
    return require_role([UserRole.ADMIN])


def check_department_access(
    user_department: str,
    target_department: str,
    action: str
) -> dict:
    """
    Check if user has access to target department and calculate risk
    
    Args:
        user_department: User's department
        target_department: Department being accessed
        action: Type of action (view, download, modify, etc.)
        
    Returns:
        Dictionary with access_allowed, is_cross_department, risk_multiplier
    """
    is_cross_department = user_department.lower() != target_department.lower()
    
    # Cross-department access increases risk
    risk_multiplier = 1.0
    if is_cross_department:
        if action in ["download", "modify", "delete"]:
            risk_multiplier = 2.0  # High risk for cross-dept sensitive actions
        else:
            risk_multiplier = 1.5  # Medium risk for cross-dept viewing
    
    return {
        "access_allowed": True,  # All access is allowed but monitored
        "is_cross_department": is_cross_department,
        "risk_multiplier": risk_multiplier,
        "warning": "This action is monitored for security." if is_cross_department else None
    }
