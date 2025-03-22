from datetime import datetime
import fastapi as fa
from fastapi import Depends, HTTPException, Path, Query, status

from trader import exceptions, status as app_status
from trader.auth.service import get_current_user  # 인증 서비스에서 현재 사용자 가져오기 (구현 필요)
from trader.order.schema import (
    OrderCreateRequest,
    OrderUpdateRequest,
    OrderCreateResponse,
    OrderDetailSuccessResponse,
    OrderListSuccessResponse,
    OrderUpdateResponse,
    OrderCancelResponse
)
from trader.order.service import order_service


router = fa.APIRouter()


@router.post("/orders/buy", response_model=OrderCreateResponse)
async def create_buy_order(
    request: OrderCreateRequest,
    current_user = Depends(get_current_user)  # 현재 인증된 사용자 정보
):
    """매수 주문을 생성합니다."""
    try:
        order = await order_service.create_buy_order(current_user.id, request)
        return {"data": order}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # 로깅 추가
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to create buy order", "details": str(e)}
        )


@router.post("/orders/sell", response_model=OrderCreateResponse)
async def create_sell_order(
    request: OrderCreateRequest,
    current_user = Depends(get_current_user)
):
    """매도 주문을 생성합니다."""
    try:
        order = await order_service.create_sell_order(current_user.id, request)
        return {"data": order}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # 로깅 추가
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to create sell order", "details": str(e)}
        )


@router.get("/orders/{order_id}", response_model=OrderDetailSuccessResponse)
async def get_order(
    order_id: str = Path(..., description="주문 ID"),
    current_user = Depends(get_current_user)
):
    """주문 상세 정보를 조회합니다."""
    try:
        # 자신의 주문만 조회할 수 있도록 user_id 전달
        order = await order_service.get_order(order_id, current_user.id)
        return {"data": order}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # 로깅 추가
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get order details", "details": str(e)}
        )


@router.get("/orders", response_model=OrderListSuccessResponse)
async def get_user_orders(
    order_type: str = Query(None, description="주문 유형 필터 (buy/sell)"),
    status: str = Query(None, description="주문 상태 필터"),
    start_date: datetime = Query(None, description="시작 날짜"),
    end_date: datetime = Query(None, description="종료 날짜"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    current_user = Depends(get_current_user)
):
    """사용자의 주문 목록을 조회합니다."""
    try:
        orders, total_count = await order_service.get_user_orders(
            user_id=current_user.id,
            order_type=order_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size
        )
        return {"data": {"orders": orders, "total_count": total_count}}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # 로깅 추가
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get order list", "details": str(e)}
        )


@router.put("/orders/{order_id}", response_model=OrderUpdateResponse)
async def update_order(
    order_id: str = Path(..., description="주문 ID"),
    request: OrderUpdateRequest = fa.Body(...),
    current_user = Depends(get_current_user)
):
    """주문을 수정합니다."""
    try:
        order = await order_service.update_order(order_id, current_user.id, request)
        return {"data": order}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # 로깅 추가
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to update order", "details": str(e)}
        )


@router.delete("/orders/{order_id}", response_model=OrderCancelResponse)
async def cancel_order(
    order_id: str = Path(..., description="주문 ID"),
    current_user = Depends(get_current_user)
):
    """주문을 취소합니다."""
    try:
        order = await order_service.cancel_order(order_id, current_user.id)
        return {"data": order}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # 로깅 추가
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to cancel order", "details": str(e)}
        )