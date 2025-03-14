from datetime import datetime
import fastapi as fa
from fastapi import Depends, HTTPException, Query, status

from trader import exceptions, status as app_status
from trader.user.schema import (
    UserCreateRequest,
    UserUpdateRequest,
    UserLoginRequest,
    DepositRequest,
    WithdrawRequest,
    UserCreateResponse,
    UserProfileSuccessResponse,
    UserBalanceSuccessResponse,
    TokenSuccessResponse,
    TransactionListSuccessResponse
)
from trader.user.service import user_service
from trader.auth.service import get_current_user

router = fa.APIRouter()


@router.post("/users", response_model=UserCreateResponse)
async def create_user(request: UserCreateRequest):
    try:
        user = await user_service.create_user(request)
        return {"data": user}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # 로깅 추가
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to create user", "details": str(e)}
        )


@router.post("/users/login", response_model=TokenSuccessResponse)
async def login(request: UserLoginRequest):
    try:
        token = await user_service.login(request)
        return {"data": token}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Login failed", "details": str(e)}
        )


@router.get("/users/profile", response_model=UserProfileSuccessResponse)
async def get_user_profile(current_user=Depends(get_current_user)):
    try:
        profile = await user_service.get_user_profile(current_user.id)
        return {"data": profile}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get user profile", "details": str(e)}
        )


@router.put("/users/profile", response_model=UserProfileSuccessResponse)
async def update_user_profile(
        request: UserUpdateRequest,
        current_user=Depends(get_current_user)
):
    try:
        updated_user = await user_service.update_user(current_user.id, request)
        profile = await user_service.get_user_profile(current_user.id)
        return {"data": profile}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to update user profile", "details": str(e)}
        )


@router.get("/users/balance", response_model=UserBalanceSuccessResponse)
async def get_balance(current_user=Depends(get_current_user)):
    try:
        balance = await user_service.get_balance(current_user.id)
        return {"data": balance}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get balance", "details": str(e)}
        )


@router.post("/users/deposit", response_model=UserBalanceSuccessResponse)
async def deposit(
        request: DepositRequest,
        current_user=Depends(get_current_user)
):
    try:
        balance = await user_service.deposit(current_user.id, request.amount)
        return {"data": balance}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Deposit failed", "details": str(e)}
        )


@router.post("/users/withdraw", response_model=UserBalanceSuccessResponse)
async def withdraw(
        request: WithdrawRequest,
        current_user=Depends(get_current_user)
):
    try:
        balance = await user_service.withdraw(current_user.id, request.amount)
        return {"data": balance}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Withdrawal failed", "details": str(e)}
        )


@router.get("/users/transactions", response_model=TransactionListSuccessResponse)
async def get_transactions(
        transaction_type: str = Query(None, description="거래 유형 필터 (deposit/withdrawal 등)"),
        start_date: datetime = Query(None, description="시작 날짜"),
        end_date: datetime = Query(None, description="종료 날짜"),
        page: int = Query(1, ge=1, description="페이지 번호"),
        size: int = Query(20, ge=1, le=100, description="페이지 크기"),
        current_user=Depends(get_current_user)
):
    try:
        transactions, total_count = await user_service.get_transactions(
            user_id=current_user.id,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size
        )
        return {"data": {"transactions": transactions, "total_count": total_count}}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get transactions", "details": str(e)}
        )
