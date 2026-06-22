"""
RefreshToken ORM model.

Refresh tokens are persisted server-side so they can be revoked (logout,
rotation, or admin action) independently of their JWT expiry. The token
string itself is never stored — only a hash of it — so a DB leak doesn't
hand out usable tokens.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # JWT ID (jti claim) — used to look up this row without storing the raw token.
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # SHA-256 hex digest of the raw token, for an extra verification step
    # beyond just trusting the jti from an otherwise-valid-looking JWT.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RefreshToken id={self.id} user_id={self.user_id} revoked={self.revoked}>"
