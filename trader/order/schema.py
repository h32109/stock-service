from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class OrderBaseModel(BaseModel):

    @field_validator('price')
    def validate_price(cls, v):
        # 가격은 소수점 둘째 자리까지만 허용
        if v != round(v, 2):
            raise ValueError("Price must have at most 2 decimal places")
        return v


class OrderCreateRequest(OrderBaseModel):
    stock_id: str = Field(..., description="주식 종목 코드")
    price: float = Field(..., gt=0, description="주문 가격")
    quantity: int = Field(..., gt=0, description="주문 수량")


class OrderUpdateRequest(OrderBaseModel):
    price: Optional[float] = Field(None, gt=0, description="수정할 주문 가격")
    quantity: Optional[int] = Field(None, gt=0, description="수정할 주문 수량")

    class Config:
        validate_assignment = True


class OrderResponse(BaseModel):
    id: str = Field(..., description="주문 ID (UUID)")
    user_id: str = Field(..., description="사용자 ID")
    stock_id: str = Field(..., description="주식 종목 코드")
    stock_name: str = Field(..., description="주식 회사명")
    order_type: str = Field(..., description="주문 유형 (buy/sell)")
    status: str = Field(..., description="주문 상태")
    price: float = Field(..., description="주문 가격")
    quantity: int = Field(..., description="주문 수량")
    filled_quantity: int = Field(..., description="체결된 수량")
    total_amount: float = Field(..., description="총 주문 금액")
    created_at: str = Field(..., description="주문 생성 시간")


class OrderHistoryResponse(BaseModel):
    previous_status: Optional[str] = Field(None, description="이전 상태")
    current_status: str = Field(..., description="현재 상태")
    note: Optional[str] = Field(None, description="상태 변경 사유")
    created_at: str = Field(..., description="상태 변경 시간")


class TransactionResponse(BaseModel):
    id: int = Field(..., description="거래 ID")
    transaction_type: str = Field(..., description="거래 유형 (buy/sell)")
    price: float = Field(..., description="체결 가격")
    quantity: int = Field(..., description="체결 수량")
    amount: float = Field(..., description="체결 금액")
    is_complete: bool = Field(..., description="주문 완전 체결 여부")
    transaction_at: str = Field(..., description="체결 시간")


class OrderDetailResponse(BaseModel):
    id: str = Field(..., description="주문 ID (UUID)")
    user_id: str = Field(..., description="사용자 ID")
    stock_id: str = Field(..., description="주식 종목 코드")
    stock_name: str = Field(..., description="주식 회사명")
    order_type: str = Field(..., description="주문 유형 (buy/sell)")
    status: str = Field(..., description="주문 상태")
    price: float = Field(..., description="주문 가격")
    quantity: int = Field(..., description="주문 수량")
    filled_quantity: int = Field(..., description="체결된 수량")
    total_amount: float = Field(..., description="총 주문 금액")
    retry_count: int = Field(..., description="재시도 횟수")
    created_at: str = Field(..., description="주문 생성 시간")
    updated_at: str = Field(..., description="주문 수정 시간")
    history: List[OrderHistoryResponse] = Field(..., description="주문 상태 변경 이력")
    transactions: List[TransactionResponse] = Field(..., description="거래 내역")


class OrderListResponse(BaseModel):
    orders: List[OrderResponse] = Field(..., description="주문 목록")
    total_count: int = Field(..., description="총 주문 수")


class ErrorResponse(BaseModel):
    message: str = Field(..., description="에러 메시지")
    details: Optional[dict] = Field(None, description="에러 상세 정보")


class OrderCreateResponse(BaseModel):
    data: OrderResponse


class OrderDetailSuccessResponse(BaseModel):
    data: OrderDetailResponse


class OrderListSuccessResponse(BaseModel):
    data: OrderListResponse


class OrderUpdateResponse(BaseModel):
    data: OrderResponse


class OrderCancelResponse(BaseModel):
    data: OrderResponse
