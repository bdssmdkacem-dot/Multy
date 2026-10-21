"""Multy API foundation. Registration and token issuance are intentionally absent."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Generator

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import DateTime, ForeignKey, Numeric, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./multy-dev.db")
JWT_SECRET = os.getenv("MULTY_JWT_SECRET", "")
JWT_ALGORITHM = "HS256"

_engine_options = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    active: Mapped[bool] = mapped_column(default=True)


class Firm(Base):
    __tablename__ = "firms"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(180))


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    firm_id: Mapped[str] = mapped_column(ForeignKey("firms.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))


class Membership(Base):
    __tablename__ = "memberships"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String(24))


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="MAD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TransactionIn(BaseModel):
    description: str = Field(min_length=1, max_length=240)
    amount: Decimal = Field(gt=Decimal("-1000000000"), lt=Decimal("1000000000"), max_digits=14, decimal_places=2)
    currency: str = Field(default="MAD", pattern="^MAD$")


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: str
    description: str
    amount: Decimal
    currency: str
    created_at: datetime


class CompanyOut(BaseModel):
    id: str
    name: str
    role: str


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def authenticated_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not JWT_SECRET:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    token = authorization[7:].strip()
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"require": ["sub", "exp"]})
        user_id = claims["sub"]
    except (jwt.InvalidTokenError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, user_id)
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="Inactive or unknown user")
    return user


def company_membership(company_id: str, user: User, db: Session) -> tuple[Company, str]:
    row = db.execute(
        select(Company, Membership.role)
        .join(Membership, Membership.company_id == Company.id)
        .where(Company.id == company_id, Membership.user_id == user.id)
    ).first()
    if row is None:
        # Deliberately avoid disclosing whether another tenant's company exists.
        raise HTTPException(status_code=404, detail="Company not found")
    company, role = row
    if role not in {"firm_admin", "accountant", "read_only"}:
        raise HTTPException(status_code=403, detail="Role is not permitted")
    return company, role


app = FastAPI(title="Multy API", version="0.1.0", description="Private pilot API; no public registration.")
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/companies", response_model=list[CompanyOut])
def list_companies(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Company, Membership.role)
        .join(Membership, Membership.company_id == Company.id)
        .where(Membership.user_id == user.id)
        .order_by(Company.name)
    ).all()
    return [{"id": company.id, "name": company.name, "role": role} for company, role in rows]


@app.get("/companies/{company_id}/transactions", response_model=list[TransactionOut])
def list_transactions(company_id: str, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    company, _role = company_membership(company_id, user, db)
    return list(db.scalars(select(Transaction).where(Transaction.company_id == company.id).order_by(Transaction.id.desc())))


@app.post("/companies/{company_id}/transactions", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(company_id: str, payload: TransactionIn, user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    company, role = company_membership(company_id, user, db)
    if role == "read_only":
        raise HTTPException(status_code=403, detail="Read-only membership cannot create transactions")
    transaction = Transaction(company_id=company.id, description=payload.description, amount=payload.amount, currency=payload.currency)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction
