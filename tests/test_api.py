import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["MULTY_JWT_SECRET"] = "unit-test-secret-never-use-in-production-32bytes"
import backend.main as main_module
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
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=5), "iss": "multy-api", "aud": "multy-client"},
        os.environ["MULTY_JWT_SECRET"],
        algorithm="HS256",
    )


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
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {"sub": "alice", "iat": now - timedelta(minutes=2), "exp": now - timedelta(minutes=1),
         "iss": "multy-api", "aud": "multy-client"},
        os.environ["MULTY_JWT_SECRET"],
        algorithm="HS256",
    )
    assert client.get("/companies", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_weak_jwt_secret_fails_closed(monkeypatch):
    monkeypatch.setattr(main_module, "JWT_SECRET", "short")
    response = client.get("/companies", headers=auth("alice"))
    assert response.status_code == 503


def test_unsigned_jwt_is_rejected():
    unsigned = jwt.encode(
        {"sub": "alice", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        key=None,
        algorithm="none",
    )
    response = client.get("/companies", headers={"Authorization": f"Bearer {unsigned}"})
    assert response.status_code == 401


def test_jwt_missing_expiration_is_rejected():
    missing_exp = jwt.encode({"sub": "alice"}, os.environ["MULTY_JWT_SECRET"], algorithm="HS256")
    response = client.get("/companies", headers={"Authorization": f"Bearer {missing_exp}"})
    assert response.status_code == 401


def test_jwt_wrong_issuer_or_audience_is_rejected():
    now = datetime.now(timezone.utc)
    base = {"sub": "alice", "iat": now, "exp": now + timedelta(minutes=5)}
    wrong_issuer = jwt.encode({**base, "iss": "other-api", "aud": "multy-client"}, os.environ["MULTY_JWT_SECRET"], algorithm="HS256")
    wrong_audience = jwt.encode({**base, "iss": "multy-api", "aud": "other-client"}, os.environ["MULTY_JWT_SECRET"], algorithm="HS256")
    assert client.get("/companies", headers={"Authorization": f"Bearer {wrong_issuer}"}).status_code == 401
    assert client.get("/companies", headers={"Authorization": f"Bearer {wrong_audience}"}).status_code == 401


def test_jwt_lifetime_over_15_minutes_is_rejected():
    now = datetime.now(timezone.utc)
    long_lived = jwt.encode(
        {"sub": "alice", "iat": now, "exp": now + timedelta(hours=1), "iss": "multy-api", "aud": "multy-client"},
        os.environ["MULTY_JWT_SECRET"],
        algorithm="HS256",
    )
    assert client.get("/companies", headers={"Authorization": f"Bearer {long_lived}"}).status_code == 401


def test_jwt_wrong_algorithm_is_rejected():
    now = datetime.now(timezone.utc)
    token_wrong_algorithm = jwt.encode(
        {"sub": "alice", "iat": now, "exp": now + timedelta(minutes=5), "iss": "multy-api", "aud": "multy-client"},
        os.environ["MULTY_JWT_SECRET"],
        algorithm="HS384",
    )
    assert client.get("/companies", headers={"Authorization": f"Bearer {token_wrong_algorithm}"}).status_code == 401


def test_deactivated_user_existing_token_is_rejected_immediately():
    existing_token = auth("alice")
    with TestingSession() as db:
        db.get(User, "alice").active = False
        db.commit()
    assert client.get("/companies", headers=existing_token).status_code == 401

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

def test_request_body_cannot_override_company_scope():
    response = client.post(
        "/companies/company-a/transactions",
        headers=auth("alice"),
        json={"description": "Scoped by path", "amount": "7.00", "company_id": "company-b"},
    )
    assert response.status_code == 201
    assert response.json()["company_id"] == "company-a"
    with TestingSession() as db:
        assert db.query(Transaction).filter_by(company_id="company-b", description="Scoped by path").count() == 0


def test_company_in_same_firm_is_not_accessible_without_explicit_membership():
    with TestingSession() as db:
        db.add(Company(id="company-a2", firm_id="firm-a", name="Unassigned client"))
        db.commit()
    listed = client.get("/companies", headers=auth("alice"))
    denied = client.get("/companies/company-a2/transactions", headers=auth("alice"))
    assert [row["id"] for row in listed.json()] == ["company-a"]
    assert denied.status_code == 404


def test_invalid_currency_and_malformed_financial_values_are_rejected():
    wrong_currency = client.post("/companies/company-a/transactions", headers=auth("alice"), json={"description": "Wrong currency", "amount": "1.00", "currency": "USD"})
    malformed_amount = client.post("/companies/company-a/transactions", headers=auth("alice"), json={"description": "Malformed amount", "amount": "not-a-number"})
    overlong_description = client.post("/companies/company-a/transactions", headers=auth("alice"), json={"description": "x" * 241, "amount": "1.00"})
    assert wrong_currency.status_code == 422
    assert malformed_amount.status_code == 422
    assert overlong_description.status_code == 422

