"""
Declarative base for all ORM models.

All models in app/models should inherit from `Base` so that Alembic's
autogenerate can detect them via `Base.metadata`.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base class."""
    pass
