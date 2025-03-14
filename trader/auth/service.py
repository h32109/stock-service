from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from trader.user.service import user_service
from trader.exceptions import PermissionDeniedError, DatabaseError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    현재 인증된 사용자를 가져옵니다.

    Args:
        token (str): OAuth2 스키마에서 추출한 인증 토큰

    Returns:
        User: 인증된 사용자 객체
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"message": "Could not validate credentials"},
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user = await user_service.verify_token(token)
        return user

    except (PermissionDeniedError, JWTError):
        raise credentials_exception
    except DatabaseError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Database error during authentication"}
        )