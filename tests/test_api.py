import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["MULTY_JWT_SECRET"] = "test-secret-not-for-production"
from backend.main import AuditLog, Base, Company, Firm, Membership, Transaction, User, app, get_db

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(engine)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestingSession() as db:
        db.add_all([
            Firm(id="firm-a", name="Cabinet A"), Firm(id="firm-b", name="Cabinet B"),
            User(id="alice", email="alice@example.test", active=True),
            User(id="bob", email="bob@example.test", active=True),
            User(id="reader", email="reader@example.test", active=True),
            Company(id="company-a", firm_id="firm-a", name="Atelier Nova"),
            Company(id="company-b", firm_id="firm-b", name="Atlas Distribution"),
            Membership(user_id="alice", company_id="company-a", role="accountant"),
            Membership(user_id="bob", company_id="company-b", role="accountant"),
            Membership(user_id="reader", company_id="company-a", role="read_only"),
            Transaction(company_id="company-a", description="Invoice A", amount=125.00, currency="MAD"),
            Transaction(company_id="company-b", description="Private invoice B", amount=999.00, currency="MAD"),
        ])
        db.commit()
    yield


def token(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, os.environ["MULTY_JWT_SECRET"], algorithm="HS256")


def auth(user_id: str) -> dict:
    return {"Authorization": f"Bearer {token(user_id)}"}


def test_company_list_contains_only_explicit_memberships():
    response = client.get("/companies", headers=auth("alice"))
    assert response.status_code == 200
    assert [c["id"] for c in response.json()] == ["company-a"]


def test_cross_tenant_company_is_hidden():
    response = client.get("/companies/company-b/transactions", headers=auth("alice"))
    assert response.status_code == 404


def test_transaction_list_never_leaks_other_tenant_rows():
    response = client.get("/companies/company-a/transactions", headers=auth("alice"))
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["description"] == "Invoice A"


def test_accountant_can_write_only_to_assigned_company():
    ok = client.post("/companies/company-a/transactions", headers=auth("alice"), json={"description": "Test", "amount": "20.00"})
    denied = client.post("/companies/company-b/transactions", headers=auth("alice"), json={"description": "Leak", "amount": "1.00"})
    assert ok.status_code == 201
    assert denied.status_code == 404


def test_read_only_cannot_create_transaction():
    response = client.post("/companies/company-a/transactions", headers=auth("reader"), json={"description": "Forbidden", "amount": "1.00"})
    assert response.status_code == 403


def test_missing_invalid_and_expired_tokens_are_rejected():
    assert client.get("/companies").status_code == 401
    assert client.get("/companies", headers={"Authorization": "Bearer garbage"}).status_code == 401
    expired = jwt.encode({"sub": "alice", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, os.environ["MULTY_JWT_SECRET"], algorithm="HS256")
    assert client.get("/companies", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_inactive_user_is_rejected():
    with TestingSession() as db:
        db.get(User, "alice").active = False
        db.commit()
    assert client.get("/companies", headers=auth("alice")).status_code == 401

def test_membership_revocation_takes_effect_for_existing_token():
    with TestingSession() as db:
        db.delete(db.get(Membership, ("alice", "company-a")))
        db.commit()
    response = client.get("/companies/company-a/transactions", headers=auth("alice"))
    assert response.status_code == 404


def test_role_change_takes_effect_without_reissuing_token():
    with TestingSession() as db:
        membership = db.get(Membership, ("alice", "company-a"))
        membership.role = "read_only"
        db.commit()
    response = client.post("/companies/company-a/transactions", headers=auth("alice"), json={"description": "Denied after role change", "amount": "1.00"})
    assert response.status_code == 403


def test_transaction_creation_writes_audit_event_atomically():
    response = client.post("/companies/company-a/transactions", headers=auth("alice"), json={"description": "Audited transaction", "amount": "15.00"})
    assert response.status_code == 201
    with TestingSession() as db:
        events = db.query(AuditLog).filter_by(actor_user_id="alice", company_id="company-a", action="transaction.created").all()
        assert len(events) == 1
        assert events[0].entity_type == "transaction"
        assert events[0].entity_id == str(response.json()["id"])

