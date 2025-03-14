import typing as t
import uuid
from datetime import datetime, timedelta
import bcrypt
import jwt
from sqlalchemy import select, desc, func
from sqlalchemy.exc import SQLAlchemyError

from trader.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
    InsufficientBalanceError,
    PermissionDeniedError,
    DatabaseError
)
from trader.service import ServiceBase, Service
from trader.globals import sql, transaction
from trader.user.model import (
    User,
    UserProfile,
    UserSession,
    AccountTransaction,
    TransactionType
)
from trader.user.schema import (
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
    UserProfileResponse,
    UserBalanceResponse,
    TransactionResponse,
    UserLoginRequest,
    TokenResponse
)


class UserServiceBase(ServiceBase):
    config: t.Any

    async def configuration(self, config):
        self.config = config


class UserService(UserServiceBase):

    @transaction
    async def create_user(self, request: UserCreateRequest) -> UserResponse:
        try:
            # 이메일 중복 확인
            query = select(User).filter(User.email == request.email)
            result = await sql.session.execute(query)
            existing_user = result.scalars().first()

            if existing_user:
                raise UserAlreadyExistsError(
                    "User with this email already exists",
                    {"email": request.email}
                )

            # 사용자명 중복 확인
            query = select(User).filter(User.username == request.username)
            result = await sql.session.execute(query)
            existing_username = result.scalars().first()

            if existing_username:
                raise UserAlreadyExistsError(
                    "Username already taken",
                    {"username": request.username}
                )

            # 비밀번호 해싱
            hashed_password = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt())

            user_id = str(uuid.uuid4())

            user = User(
                id=user_id,
                username=request.username,
                email=request.email,
                password=hashed_password.decode('utf-8'),
                balance=0.0,
                is_active=True
            )
            sql.session.add(user)

            profile = UserProfile(
                user_id=user_id,
                full_name=request.full_name if hasattr(request, 'full_name') else None,
                phone=request.phone if hasattr(request, 'phone') else None,
                date_of_birth=request.date_of_birth if hasattr(request, 'date_of_birth') else None
            )
            sql.session.add(profile)

            user_response = UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                balance=float(user.balance),
                is_active=user.is_active,
                created_at=user.created_dt.isoformat()
            )

            return user_response

        except UserAlreadyExistsError as e:
            raise e
        except SQLAlchemyError as e:
            raise DatabaseError(
                "Database error while creating user",
                {"error": str(e)}
            )

    async def login(self, request: UserLoginRequest) -> TokenResponse:
        try:
            # 사용자 조회
            query = select(User).filter(User.email == request.email)
            result = await sql.session.execute(query)
            user = result.scalars().first()

            if not user:
                raise InvalidCredentialsError(
                    "Invalid email or password",
                    {"email": request.email}
                )

            # 비밀번호 검증
            if not bcrypt.checkpw(request.password.encode('utf-8'), user.password.encode('utf-8')):
                raise InvalidCredentialsError(
                    "Invalid email or password",
                    {"email": request.email}
                )

            # 세션 토큰 생성
            token_expires = datetime.utcnow() + timedelta(days=1)

            payload = {
                "sub": user.id,
                "username": user.username,
                "exp": token_expires
            }

            token = jwt.encode(
                payload,
                self.config.SECRET_KEY,
                algorithm="HS256"
            )

            session = UserSession(
                user_id=user.id,
                token=token,
                expires_at=token_expires
            )
            sql.session.add(session)
            await sql.session.commit()

            return TokenResponse(
                access_token=token,
                token_type="bearer",
                expires_at=token_expires.isoformat()
            )

        except InvalidCredentialsError as e:
            raise e
        except SQLAlchemyError as e:
            raise DatabaseError(
                "Database error during login",
                {"error": str(e)}
            )

    async def get_user(self, user_id: str) -> UserResponse:
        try:
            query = select(User).filter(User.id == user_id)
            result = await sql.session.execute(query)
            user = result.scalars().first()

            if not user:
                raise UserNotFoundError(
                    "User not found",
                    {"user_id": user_id}
                )

            return UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                balance=float(user.balance),
                is_active=user.is_active,
                created_at=user.created_dt.isoformat()
            )

        except UserNotFoundError as e:
            raise e
        except SQLAlchemyError as e:
            raise DatabaseError(
                "Database error while fetching user",
                {"user_id": user_id, "error": str(e)}
            )

    async def get_user_profile(self, user_id: str) -> UserProfileResponse:
        try:
            query = select(User, UserProfile).join(
                UserProfile, User.id == UserProfile.user_id
            ).filter(User.id == user_id)

            result = await sql.session.execute(query)
            data = result.first()

            if not data:
                raise UserNotFoundError(
                    "User not found",
                    {"user_id": user_id}
                )

            user, profile = data

            return UserProfileResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=profile.full_name,
                phone=profile.phone,
                date_of_birth=profile.date_of_birth.isoformat() if profile.date_of_birth else None,
                balance=float(user.balance),
                is_active=user.is_active,
                created_at=user.created_dt.isoformat()
            )

        except UserNotFoundError as e:
            raise e
        except SQLAlchemyError as e:
            raise DatabaseError(
                "Database error while fetching user profile",
                {"user_id": user_id, "error": str(e)}
            )

    @transaction
    async def update_user(self, user_id: str, request: UserUpdateRequest) -> UserResponse:
        try:
            # 사용자 존재 확인
            query = select(User).filter(User.id == user_id)
            result = await sql.session.execute(query)
            user = result.scalars().first()

            if not user:
                raise UserNotFoundError(
                    "User not found",
                    {"user_id": user_id}
                )

            # 사용자 프로필 조회
            profile_query = select(UserProfile).filter(UserProfile.user_id == user_id)
            profile_result = await sql.session.execute(profile_query)
            profile = profile_result.scalars().first()

            if not profile:
                # 프로필이 없는 경우 새로 생성
                profile = UserProfile(user_id=user_id)
                sql.session.add(profile)

            # 필드별 업데이트
            if hasattr(request, 'username') and request.username:
                # 사용자명 중복 확인
                username_query = select(User).filter(
                    User.username == request.username,
                    User.id != user_id
                )
                username_result = await sql.session.execute(username_query)
                existing_user = username_result.scalars().first()

                if existing_user:
                    raise UserAlreadyExistsError(
                        "Username already taken",
                        {"username": request.username}
                    )

                user.username = request.username

            if hasattr(request, 'email') and request.email:
                # 이메일 중복 확인
                email_query = select(User).filter(
                    User.email == request.email,
                    User.id != user_id
                )
                email_result = await sql.session.execute(email_query)
                existing_user = email_result.scalars().first()

                if existing_user:
                    raise UserAlreadyExistsError(
                        "Email already in use",
                        {"email": request.email}
                    )

                user.email = request.email

            if hasattr(request, 'password') and request.password:
                # 비밀번호 업데이트
                hashed_password = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt())
                user.password = hashed_password.decode('utf-8')

            if hasattr(request, 'full_name') and request.full_name is not None:
                profile.full_name = request.full_name

            if hasattr(request, 'phone') and request.phone is not None:
                profile.phone = request.phone

            if hasattr(request, 'date_of_birth') and request.date_of_birth is not None:
                profile.date_of_birth = request.date_of_birth

            user_response = UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                balance=float(user.balance),
                is_active=user.is_active,
                created_at=user.created_dt.isoformat()
            )

            return user_response

        except (UserNotFoundError, UserAlreadyExistsError) as e:
            raise e
        except SQLAlchemyError as e:
            raise DatabaseError(
                "Database error while updating user",
                {"user_id": user_id, "error": str(e)}
            )

    async def get_balance(self, user_id: str) -> UserBalanceResponse:
        try:
            query = select(User).filter(User.id == user_id)
            result = await sql.session.execute(query)
            user = result.scalars().first()

            if not user:
                raise UserNotFoundError(
                    "User not found",
                    {"user_id": user_id}
                )

            return UserBalanceResponse(
                user_id=user.id,
                balance=float(user.balance),
                updated_at=user.updated_dt.isoformat()
            )

        except UserNotFoundError as e:
            raise e
        except SQLAlchemyError as e:
            raise DatabaseError(
                "Database error while fetching balance",
                {"user_id": user_id, "error": str(e)}
            )

    async def deposit(self, user_id: str, amount: float) -> UserBalanceResponse:
        async with sql.session.begin():
            try:
                if amount <= 0:
                    raise ValueError("Deposit amount must be positive")

                # 사용자 조회
                query = select(User).filter(User.id == user_id)
                result = await sql.session.execute(query)
                user = result.scalars().first()

                if not user:
                    raise UserNotFoundError(
                        "User not found",
                        {"user_id": user_id}
                    )

                # 잔액 업데이트
                user.balance += amount

                # 트랜잭션 기록
                transaction = AccountTransaction(
                    user_id=user_id,
                    type=TransactionType.DEPOSIT,  # Enum 타입 사용
                    amount=amount,
                    balance_after=user.balance,
                    description="Deposit to account"
                )
                sql.session.add(transaction)

                return UserBalanceResponse(
                    user_id=user.id,
                    balance=float(user.balance),
                    updated_at=user.updated_dt.isoformat()
                )

            except UserNotFoundError as e:
                raise e
            except ValueError as e:
                raise InvalidCredentialsError(
                    str(e),
                    {"amount": amount}
                )
            except SQLAlchemyError as e:
                raise DatabaseError(
                    "Database error during deposit",
                    {"user_id": user_id, "amount": amount, "error": str(e)}
                )

    async def withdraw(self, user_id: str, amount: float) -> UserBalanceResponse:
        """잔액 출금"""
        async with sql.session.begin():
            try:
                if amount <= 0:
                    raise ValueError("Withdrawal amount must be positive")

                query = select(User).filter(User.id == user_id)
                result = await sql.session.execute(query)
                user = result.scalars().first()

                if not user:
                    raise UserNotFoundError(
                        "User not found",
                        {"user_id": user_id}
                    )

                # 잔액 확인
                if user.balance < amount:
                    raise InsufficientBalanceError(
                        "Insufficient balance for withdrawal",
                        {
                            "user_id": user_id,
                            "current_balance": float(user.balance),
                            "withdrawal_amount": amount
                        }
                    )

                user.balance -= amount

                # 트랜잭션 기록
                transaction = AccountTransaction(
                    user_id=user_id,
                    type=TransactionType.WITHDRAWAL,  # Enum 타입 사용
                    amount=-amount,  # 마이너스로 저장
                    balance_after=user.balance,
                    description="Withdrawal from account"
                )
                sql.session.add(transaction)

                return UserBalanceResponse(
                    user_id=user.id,
                    balance=float(user.balance),
                    updated_at=user.updated_dt.isoformat()
                )

            except (UserNotFoundError, InsufficientBalanceError) as e:
                raise e
            except ValueError as e:
                raise InvalidCredentialsError(
                    str(e),
                    {"amount": amount}
                )
            except SQLAlchemyError as e:
                raise DatabaseError(
                    "Database error during withdrawal",
                    {"user_id": user_id, "amount": amount, "error": str(e)}
                )

    async def get_transactions(
            self,
            user_id: str,
            transaction_type: str = None,
            start_date: datetime = None,
            end_date: datetime = None,
            page: int = 1,
            size: int = 20
    ) -> t.Tuple[t.List[TransactionResponse], int]:
        try:
            # 기본 쿼리
            query = select(AccountTransaction).filter(AccountTransaction.user_id == user_id)

            # 필터 적용
            if transaction_type:
                tx_type = TransactionType[transaction_type.upper()]
                query = query.filter(AccountTransaction.type == tx_type)

            if start_date:
                query = query.filter(AccountTransaction.created_dt >= start_date)

            if end_date:
                query = query.filter(AccountTransaction.created_dt <= end_date)

            # 총 개수 쿼리
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await sql.session.execute(count_query)
            total_count = count_result.scalar_one()

            # 정렬 및 페이지네이션
            query = query.order_by(desc(AccountTransaction.created_dt))
            offset = (page - 1) * size
            query = query.offset(offset).limit(size)

            result = await sql.session.execute(query)
            transactions = result.scalars().all()

            transaction_responses = [
                TransactionResponse(
                    id=tx.id,
                    user_id=tx.user_id,
                    type=tx.type.value,
                    amount=float(tx.amount),
                    balance_after=float(tx.balance_after),
                    description=tx.description,
                    created_at=tx.created_dt.isoformat()
                ) for tx in transactions
            ]

            return transaction_responses, total_count

        except SQLAlchemyError as e:
            raise DatabaseError(
                "Database error while fetching transactions",
                {"user_id": user_id, "error": str(e)}
            )

    async def verify_token(self, token: str) -> User:
        try:
            # 토큰 디코드
            payload = jwt.decode(
                token,
                self.config.SECRET_KEY,
                algorithms=["HS256"]
            )

            user_id = payload["sub"]

            # 세션 유효성 확인
            session_query = select(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.token == token,
                UserSession.expires_at > datetime.utcnow()
            )
            session_result = await sql.session.execute(session_query)
            session = session_result.scalars().first()

            if not session:
                raise PermissionDeniedError(
                    "Invalid or expired token",
                    {"token": "****"}
                )

            # 사용자 조회
            user_query = select(User).filter(User.id == user_id, User.is_active == True)
            user_result = await sql.session.execute(user_query)
            user = user_result.scalars().first()

            if not user:
                raise PermissionDeniedError(
                    "User not found or inactive",
                    {"user_id": user_id}
                )

            return user

        except jwt.PyJWTError:
            raise PermissionDeniedError(
                "Invalid token",
                {"token": "****"}
            )
        except SQLAlchemyError as e:
            raise DatabaseError(
                "Database error during token verification",
                {"error": str(e)}
            )


user_service = Service.add_service(UserService)