"""
Pydantic schemas for account-related API operations.
Provides request/response validation and serialization.
"""
from datetime import datetime, time
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# Base schemas
class PriceResetBase(BaseModel):
    """Base schema for price reset configuration."""
    reset_time: time = Field(..., description="Time to reset prices (HH:MM format)")
    resume_time: time = Field(..., description="Time to resume normal pricing (HH:MM format)")
    enabled: bool = Field(default=False, description="Whether price reset is active")
    product_condition: str = Field(..., max_length=100, description="Product condition filter (e.g., 'New', 'Used')")
    
    @field_validator('product_condition')
    @classmethod
    def validate_condition(cls, v):
        allowed_conditions = ['New', 'Used', 'Collectible', 'Refurbished', 'All']
        if v not in allowed_conditions:
            raise ValueError(f'Product condition must be one of: {allowed_conditions}')
        return v
    
    @field_validator('resume_time')
    @classmethod
    def validate_time_order(cls, v, info):
        if hasattr(info, 'data') and info.data and 'reset_time' in info.data and v <= info.data['reset_time']:
            raise ValueError('Resume time must be after reset time')
        return v


class PriceResetCreate(PriceResetBase):
    """Schema for creating price reset configuration."""
    pass


class PriceResetUpdate(BaseModel):
    """Schema for updating price reset configuration."""
    reset_time: Optional[time] = None
    resume_time: Optional[time] = None
    enabled: Optional[bool] = None
    product_condition: Optional[str] = None
    
    @field_validator('product_condition')
    @classmethod
    def validate_condition(cls, v):
        if v is not None:
            allowed_conditions = ['New', 'Used', 'Collectible', 'Refurbished', 'All']
            if v not in allowed_conditions:
                raise ValueError(f'Product condition must be one of: {allowed_conditions}')
        return v


class PriceResetResponse(PriceResetBase):
    """Schema for price reset response."""
    id: int
    reset_active: bool = Field(description="Current reset state")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# User Account schemas
class UserAccountBase(BaseModel):
    """Base schema for user account."""
    seller_id: str = Field(..., max_length=100, description="Amazon seller ID")
    marketplace_type: str = Field(..., max_length=100, description="Amazon marketplace (US, UK, CA, AU)")
    enabled: bool = Field(default=True, description="Account enabled status")
    repricer_enabled: bool = Field(default=True, description="Repricing functionality enabled")
    
    @field_validator('marketplace_type')
    @classmethod
    def validate_marketplace(cls, v):
        allowed_marketplaces = ['US', 'UK', 'CA', 'AU']
        if v not in allowed_marketplaces:
            raise ValueError(f'Marketplace must be one of: {allowed_marketplaces}')
        return v


class UserAccountCreate(UserAccountBase):
    """Schema for creating user account."""
    user_id: str = Field(..., max_length=100, description="Unique user identifier")
    refresh_token: str = Field(..., description="Amazon SP-API refresh token")


class UserAccountUpdate(BaseModel):
    """Schema for updating user account."""
    enabled: Optional[bool] = None
    repricer_enabled: Optional[bool] = None
    refresh_token: Optional[str] = None
    is_notifications_active: Optional[bool] = None


class UserAccountResponse(UserAccountBase):
    """Schema for user account response."""
    id: int
    user_id: str
    status: str = Field(description="Account status (ACTIVE, INACTIVE)")
    is_notifications_active: bool
    anyoffer_changed_subscription_id: str
    feed_ready_notification_subscription_id: str
    anyoffer_changed_destination_id: str
    feed_ready_destination_id: str
    price_reset: Optional[PriceResetResponse] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @property
    def marketplace_id(self) -> str:
        """Get marketplace ID for Amazon SP-API."""
        marketplace_ids = {
            "US": "ATVPDKIKX0DER",
            "UK": "A1F83G8C2ARO7P", 
            "AU": "A39IBJ37TRP1C6",
            "CA": "A2EUQ1WTGCTBG2"
        }
        return marketplace_ids.get(self.marketplace_type, "")


# Authentication schemas
class Token(BaseModel):
    """JWT token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Token payload data schema."""
    user_id: Optional[str] = None
    seller_id: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request schema."""
    seller_id: str = Field(..., description="Amazon seller ID")
    refresh_token: str = Field(..., description="Amazon SP-API refresh token")


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserAccountResponse


# Notification schemas
class NotificationSubscriptionRequest(BaseModel):
    """Schema for notification subscription requests."""
    action: str = Field(..., description="Action: 'subscribe' or 'unsubscribe'")
    notification_type: str = Field(..., description="Notification type: 'ANY_OFFER_CHANGED' or 'FEED_PROCESSING_FINISHED'")
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ['subscribe', 'unsubscribe']:
            raise ValueError('Action must be either "subscribe" or "unsubscribe"')
        return v
    
    @field_validator('notification_type')
    @classmethod
    def validate_notification_type(cls, v):
        allowed_types = ['ANY_OFFER_CHANGED', 'FEED_PROCESSING_FINISHED']
        if v not in allowed_types:
            raise ValueError(f'Notification type must be one of: {allowed_types}')
        return v


class NotificationSubscriptionResponse(BaseModel):
    """Schema for notification subscription response."""
    success: bool
    message: str
    subscription_id: Optional[str] = None
    destination_id: Optional[str] = None


# Account status schemas
class AccountStatusUpdate(BaseModel):
    """Schema for updating account status."""
    status: str = Field(..., description="Account status")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ['ACTIVE', 'INACTIVE', 'SUSPENDED', 'PENDING']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v


class AccountListFilter(BaseModel):
    """Schema for filtering account lists."""
    marketplace: Optional[str] = None
    enabled: Optional[bool] = None
    status: Optional[str] = None
    repricer_enabled: Optional[bool] = None
    
    @field_validator('marketplace')
    @classmethod
    def validate_marketplace(cls, v):
        if v is not None:
            allowed_marketplaces = ['US', 'UK', 'CA', 'AU']
            if v not in allowed_marketplaces:
                raise ValueError(f'Marketplace must be one of: {allowed_marketplaces}')
        return v


class AccountListResponse(BaseModel):
    """Schema for account list response."""
    total: int
    accounts: list[UserAccountResponse]
    filters: AccountListFilter