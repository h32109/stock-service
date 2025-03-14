from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field, EmailStr, field_validator


class UserBaseModel(BaseModel):

    @field_validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric with optional underscores and hyphens')
        return v


class UserCreateRequest(UserBaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="사용자명")
    email: EmailStr = Field(..., description="이메일")
    password: str = Field(..., min_length=8, description="비밀번호")
    full_name: Optional[str] = Field(None, max_length=100, description="이름")
    phone: Optional[str] = Field(None, max_length=20, description="전화번호")
    date_of_birth: Optional[date] = Field(None, description="생년월일")


class UserUpdateRequest(UserBaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="사용자명")
    email: Optional[EmailStr] = Field(None, description="이메일")
    password: Optional[str] = Field(None, min_length=8, description="비밀번호")
    full_name: Optional[str] = Field(None, max_length=100, description="이름")
    phone: Optional[str] = Field(None, max_length=20, description="전화번호")
    date_of_birth: Optional[date] = Field(None, description="생년월일")


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="이메일")
    password: str = Field(..., description="비밀번호")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="액세스 토큰")
    token_type: str = Field(..., description="토큰 타입")
    expires_at: str = Field(..., description="만료 시간")


class UserResponse(BaseModel):
    id: str = Field(..., description="사용자 ID")
    username: str = Field(..., description="사용자명")
    email: str = Field(..., description="이메일")
    balance: float = Field(..., description="계좌 잔액")
    is_active: bool = Field(..., description="활성 상태")
    created_at: str = Field(..., description="생성 시간")


class UserProfileResponse(BaseModel):
    id: str = Field(..., description="사용자 ID")
    username: str = Field(..., description="사용자명")
    email: str = Field(..., description="이메일")
    full_name: Optional[str] = Field(None, description="이름")
    phone: Optional[str] = Field(None, description="전화번호")
    date_of_birth: Optional[str] = Field(None, description="생년월일")
    balance: float = Field(..., description="계좌 잔액")
    is_active: bool = Field(..., description="활성 상태")
    created_at: str = Field(..., description="생성 시간")


class UserBalanceResponse(BaseModel):
    user_id: str = Field(..., description="사용자 ID")
    balance: float = Field(..., description="계좌 잔액")
    updated_at: str = Field(..., description="마지막 업데이트 시간")


class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="입금 금액")


class WithdrawRequest(BaseModel):
    amount: float = Field(..., gt=0, description="출금 금액")


class TransactionResponse(BaseModel):
    id: int = Field(..., description="거래 ID")
    user_id: str = Field(..., description="사용자 ID")
    type: str = Field(..., description="거래 유형")
    amount: float = Field(..., description="거래 금액")
    balance_after: float = Field(..., description="거래 후 잔액")
    description: Optional[str] = Field(None, description="거래 설명")
    created_at: str = Field(..., description="거래 시간")


class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse] = Field(..., description="거래 내역 목록")
    total_count: int = Field(..., description="총 거래 내역 수")


class UserCreateResponse(BaseModel):
    data: UserResponse


class UserProfileSuccessResponse(BaseModel):
    data: UserProfileResponse


class UserBalanceSuccessResponse(BaseModel):
    data: UserBalanceResponse


class TokenSuccessResponse(BaseModel):
    data: TokenResponse


class TransactionListSuccessResponse(BaseModel):
    data: TransactionListResponse
