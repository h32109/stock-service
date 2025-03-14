import enum

from fastapi import HTTPException


class ExceptionErrorCode(str, enum.Enum):
    # common
    DatabaseError = "CO00"

    # stock
    InvalidStockError = "ST00"

    # user
    UserAlreadyExistsError = "US00"
    UserNotFoundError = "US01"
    InsufficientBalanceError = "US02"

    # auth
    InvalidCredentialsError = "AU00"
    PermissionDeniedError = "AU01"


class BaseCustomException(Exception):
    """
        ## Error code ABCD means
        AB: resources. CO means common, AP means applications.
            The first two letters of the resource's alphabet.
        CD: numbering. You just need to number them in order.

        ## Usage
        def something():
            if some_bool:
                raise DataFormatError("data format is wrong")

        try:
            something()
        except DataFormatError as e:
            raise e.raise_http(status.ClientError.HTTP_400_BAD_REQUEST)

    """
    code_class = ExceptionErrorCode

    @property
    def message(self):
        return self.args[0]

    @property
    def info(self):
        try:
            info = self.args[1]
        except IndexError:
            return {}
        return info

    @property
    def error_code(self):
        return self.code_class[self.__class__.__name__]

    def __str__(self):
        return f"error_code: {self.error_code}, message: {self.message}"

    def __repr__(self):
        return f"<{self.__class__.__name__}:{self.error_code}>"

    def raise_http(self, status_code: int):
        return HTTPException(
            status_code=status_code,
            detail={
                "message": self.message,
                "error_code": self.error_code,
                "info": self.info
            }
        )


class InvalidStockError(BaseCustomException):
    """사용자가 존재하지 않는 주식 코드 조회시 예외"""
    ...


class UserAlreadyExistsError(BaseCustomException):
    """사용자가 이미 존재하는 경우의 예외"""
    ...


class UserNotFoundError(BaseCustomException):
    """사용자를 찾을 수 없는 경우의 예외"""
    ...


class InvalidCredentialsError(BaseCustomException):
    """인증 정보가 유효하지 않은 경우의 예외"""
    ...


class PermissionDeniedError(BaseCustomException):
    """권한이 없는 경우의 예외"""
    ...


class DatabaseError(BaseCustomException):
    """데이터베이스 오류 예외"""
    ...


class InsufficientBalanceError(BaseCustomException):
    """잔액이 부족할 때 예외"""
    ...