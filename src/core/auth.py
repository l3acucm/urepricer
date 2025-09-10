"""
JWT Authentication system for Arbitrage Hero.
Handles user authentication, token generation, and validation.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.database import get_db
from src.models.accounts import UserAccount
from src.schemas.accounts import TokenData

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token scheme
security = HTTPBearer()

# Settings
settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time override
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        TokenData if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id: str = payload.get("user_id")
        seller_id: str = payload.get("seller_id")
        
        if user_id is None:
            return None
            
        return TokenData(user_id=user_id, seller_id=seller_id)
    
    except JWTError:
        return None


def authenticate_user(db: Session, seller_id: str, refresh_token: str) -> Optional[UserAccount]:
    """
    Authenticate user with seller_id and Amazon refresh_token.
    
    Args:
        db: Database session
        seller_id: Amazon seller ID
        refresh_token: Amazon SP-API refresh token
        
    Returns:
        UserAccount if authentication successful, None otherwise
    """
    user = db.query(UserAccount).filter(
        UserAccount.seller_id == seller_id,
        UserAccount.refresh_token == refresh_token,
        UserAccount.enabled == True,
        UserAccount.status == "ACTIVE"
    ).first()
    
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserAccount:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Authorization credentials
        db: Database session
        
    Returns:
        Current UserAccount
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        token_data = verify_token(token)
        
        if token_data is None or token_data.user_id is None:
            raise credentials_exception
            
    except Exception:
        raise credentials_exception
    
    user = db.query(UserAccount).filter(
        UserAccount.user_id == token_data.user_id
    ).first()
    
    if user is None:
        raise credentials_exception
        
    # Check if user is still active
    if not user.enabled or user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    
    return user


def get_current_active_user(
    current_user: UserAccount = Depends(get_current_user)
) -> UserAccount:
    """
    Get current active user (additional validation).
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Active UserAccount
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    
    return current_user


def create_user_token(user: UserAccount) -> Dict[str, Any]:
    """
    Create a token for a user.
    
    Args:
        user: UserAccount to create token for
        
    Returns:
        Token response dictionary
    """
    access_token_expires = timedelta(minutes=settings.jwt_expire_minutes)
    
    token_data = {
        "user_id": user.user_id,
        "seller_id": user.seller_id,
        "marketplace_type": user.marketplace_type
    }
    
    access_token = create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expire_minutes * 60,  # Convert to seconds
        "user_id": user.user_id,
        "seller_id": user.seller_id,
        "marketplace_type": user.marketplace_type
    }


class OptionalAuth:
    """
    Optional authentication dependency.
    Returns user if authenticated, None if not authenticated.
    Useful for endpoints that work with or without authentication.
    """
    
    def __call__(
        self, 
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: Session = Depends(get_db)
    ) -> Optional[UserAccount]:
        
        if not credentials:
            return None
            
        try:
            token = credentials.credentials
            token_data = verify_token(token)
            
            if token_data is None or token_data.user_id is None:
                return None
                
            user = db.query(UserAccount).filter(
                UserAccount.user_id == token_data.user_id,
                UserAccount.enabled == True,
                UserAccount.status == "ACTIVE"
            ).first()
            
            return user
            
        except Exception:
            return None


# Create instance for optional auth
optional_auth = OptionalAuth()


def require_seller_access(seller_id: str):
    """
    Dependency factory for requiring access to specific seller account.
    
    Args:
        seller_id: Seller ID to check access for
        
    Returns:
        Dependency function that validates seller access
    """
    def check_seller_access(
        current_user: UserAccount = Depends(get_current_active_user)
    ) -> UserAccount:
        
        if current_user.seller_id != seller_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient permissions for this seller account"
            )
        
        return current_user
    
    return check_seller_access


def require_marketplace_access(marketplace_type: str):
    """
    Dependency factory for requiring access to specific marketplace.
    
    Args:
        marketplace_type: Marketplace to check access for
        
    Returns:
        Dependency function that validates marketplace access
    """
    def check_marketplace_access(
        current_user: UserAccount = Depends(get_current_active_user)
    ) -> UserAccount:
        
        if current_user.marketplace_type != marketplace_type:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient permissions for this marketplace"
            )
        
        return current_user
    
    return check_marketplace_access