import enum

from fastapi import HTTPException


class ExceptionErrorCode(str, enum.Enum):
    # stock
    InvalidStockError = "ST00"


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
    """Exception raised when user try to search invalid stock."""