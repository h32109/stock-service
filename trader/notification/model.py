from sqlalchemy import (
    Column,
    String,
    DateTime,
    Index,
    ForeignKey,
    BigInteger,
    Boolean,
    Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from trader.globals import Base


class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(BigInteger, primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    order_id = Column(String(36), ForeignKey('orders.id'), nullable=True)  # 알림과 관련된 주문 (없을 수도 있음)
    type = Column(String(50), nullable=False)  # 알림 유형 (주문체결, 상태변경, 시스템 등)
    title = Column(String(100), nullable=False)  # 알림 제목
    message = Column(Text, nullable=False)  # 알림 내용
    is_read = Column(Boolean, nullable=False, default=False)  # 읽음 여부
    created_dt = Column(DateTime, nullable=False, server_default=func.now())

    # 관계 설정
    user = relationship("User")
    order = relationship("Order")

    __table_args__ = (
        Index('ix_notifications_user_id', user_id),
        Index('ix_notifications_order_id', order_id),
        Index('ix_notifications_is_read', is_read),
        Index('ix_notifications_created_dt', created_dt),
    )