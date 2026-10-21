import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

os.environ.setdefault("MULTY_JWT_SECRET", "postgres-test-secret-not-for-production")
from backend.main import AuditLog, Membership, SessionLocal, User, app, get_db

client = TestClient(app)


def override_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db


@pytest.fixture(autouse=True)
def seed_postgres():
    # This suite intentionally targets PostgreSQL, not the SQLite unit-test database.
    with SessionLocal() as db:
        db.execute(text("TRUNCATE TABLE audit_logs, transactions, memberships, companies, users, firms RESTART IDENTITY CASCADE"))
        statements = [
            "INSERT INTO firms (id, name) VALUES ('pg-firm-a', 'Cabinet A'), ('pg-firm-b', 'Cabinet B')",
            """INSERT INTO users (id, email, active) VALUES
                ('pg-alice', 'alice-pg@example.test', true),
                ('pg-bob', 'bob-pg@example.test', true),
                ('pg-reader', 'reader-pg@example.test', true)""",
            """INSERT INTO companies (id, firm_id, name) VALUES
                ('pg-company-a', 'pg-firm-a', 'Atelier Nova'),
                ('pg-company-b', 'pg-firm-b', 'Atlas Distribution')""",
            """INSERT INTO memberships (user_id, company_id, role) VALUES
                ('pg-alice', 'pg-company-a', 'accountant'),
                ('pg-bob', 'pg-company-b', 'accountant'),
                ('pg-reader', 'pg-company-a', 'read_only')""",
            """INSERT INTO transactions (company_id, description, amount, currency) VALUES
                ('pg-company-a', 'Invoice A', 125.00, 'MAD'),
                ('pg-company-b', 'Private invoice B', 999.00, 'MAD')""",
        ]
        for statement in statements:
            db.execute(text(statement))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(text("TRUNCATE TABLE transactions, memberships, companies, users, firms RESTART IDENTITY CASCADE"))
        db.commit()


def token(user_id: str, *, expired: bool = False) -> str:
    exp = datetime.now(timezone.utc) - timedelta(minutes=1) if expired else datetime.now(timezone.utc) + timedelta(minutes=5)
    return jwt.encode({"sub": user_id, "exp": exp}, os.environ["MULTY_JWT_SECRET"], algorithm="HS256")


def auth(user_id: str) -> dict:
    return {"Authorization": f"Bearer {token(user_id)}"}


def test_postgres_lists_only_companies_assigned_to_user():
    response = client.get("/companies", headers=auth("pg-alice"))
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == ["pg-company-a"]


def test_postgres_blocks_cross_tenant_read_and_write():
    read = client.get("/companies/pg-company-b/transactions", headers=auth("pg-alice"))
    write = client.post("/companies/pg-company-b/transactions", headers=auth("pg-alice"), json={"description": "Leak attempt", "amount": "1.00"})
    assert read.status_code == 404
    assert write.status_code == 404


def test_postgres_transaction_query_is_scoped_to_company():
    response = client.get("/companies/pg-company-a/transactions", headers=auth("pg-alice"))
    assert response.status_code == 200
    assert [row["description"] for row in response.json()] == ["Invoice A"]


def test_postgres_read_only_member_cannot_write():
    response = client.post("/companies/pg-company-a/transactions", headers=auth("pg-reader"), json={"description": "Forbidden", "amount": "1.00"})
    assert response.status_code == 403


def test_postgres_valid_write_persists_and_is_visible_to_authorized_user():
    created = client.post("/companies/pg-company-a/transactions", headers=auth("pg-alice"), json={"description": "Persisted test", "amount": "42.50"})
    assert created.status_code == 201
    assert Decimal(created.json()["amount"]) == Decimal("42.50")
    listed = client.get("/companies/pg-company-a/transactions", headers=auth("pg-alice"))
    assert any(row["description"] == "Persisted test" for row in listed.json())


def test_postgres_rejects_missing_and_expired_tokens():
    assert client.get("/companies").status_code == 401
    assert client.get("/companies", headers={"Authorization": f"Bearer {token('pg-alice', expired=True)}"}).status_code == 401

def test_postgres_membership_revocation_invalidates_existing_token_access():
    with SessionLocal() as db:
        db.delete(db.get(Membership, ("pg-alice", "pg-company-a")))
        db.commit()
    response = client.get("/companies/pg-company-a/transactions", headers=auth("pg-alice"))
    assert response.status_code == 404


def test_postgres_role_change_is_enforced_on_next_request():
    with SessionLocal() as db:
        membership = db.get(Membership, ("pg-alice", "pg-company-a"))
        membership.role = "read_only"
        db.commit()
    response = client.post("/companies/pg-company-a/transactions", headers=auth("pg-alice"), json={"description": "Denied after role change", "amount": "1.00"})
    assert response.status_code == 403


def test_postgres_audit_event_commits_with_transaction():
    response = client.post("/companies/pg-company-a/transactions", headers=auth("pg-alice"), json={"description": "Audited PG transaction", "amount": "22.50"})
    assert response.status_code == 201
    with SessionLocal() as db:
        events = db.query(AuditLog).filter_by(actor_user_id="pg-alice", company_id="pg-company-a", action="transaction.created").all()
        assert len(events) == 1
        assert events[0].entity_id == str(response.json()["id"])

def test_postgres_deactivation_rejects_previously_issued_token():
    existing_token = auth("pg-alice")
    with SessionLocal() as db:
        db.get(User, "pg-alice").active = False
        db.commit()
    response = client.get("/companies", headers=existing_token)
    assert response.status_code == 401

def test_postgres_request_body_cannot_override_company_scope():
    response = client.post(
        "/companies/pg-company-a/transactions",
        headers=auth("pg-alice"),
        json={"description": "Scoped by URL", "amount": "8.00", "company_id": "pg-company-b"},
    )
    assert response.status_code == 201
    assert response.json()["company_id"] == "pg-company-a"
    with SessionLocal() as db:
        assert db.execute(text("SELECT count(*) FROM transactions WHERE company_id='pg-company-b' AND description='Scoped by URL'")).scalar_one() == 0


def test_postgres_company_in_same_firm_still_requires_explicit_membership():
    with SessionLocal() as db:
        db.execute(text("INSERT INTO companies (id, firm_id, name) VALUES ('pg-company-a2', 'pg-firm-a', 'Unassigned client')"))
        db.commit()
    listed = client.get("/companies", headers=auth("pg-alice"))
    denied = client.get("/companies/pg-company-a2/transactions", headers=auth("pg-alice"))
    assert [row["id"] for row in listed.json()] == ["pg-company-a"]
    assert denied.status_code == 404


def test_postgres_rejects_invalid_currency_amount_and_description():
    wrong_currency = client.post("/companies/pg-company-a/transactions", headers=auth("pg-alice"), json={"description": "Wrong currency", "amount": "1.00", "currency": "USD"})
    malformed_amount = client.post("/companies/pg-company-a/transactions", headers=auth("pg-alice"), json={"description": "Malformed amount", "amount": "not-a-number"})
    overlong_description = client.post("/companies/pg-company-a/transactions", headers=auth("pg-alice"), json={"description": "x" * 241, "amount": "1.00"})
    assert wrong_currency.status_code == 422
    assert malformed_amount.status_code == 422
    assert overlong_description.status_code == 422


def test_postgres_audit_log_rejects_update_and_delete():
    created = client.post("/companies/pg-company-a/transactions", headers=auth("pg-alice"), json={"description": "Protected audit event", "amount": "19.00"})
    assert created.status_code == 201
    with SessionLocal() as db:
        event_id = db.execute(text("SELECT id FROM audit_logs WHERE entity_id=:entity_id AND action='transaction.created'"), {"entity_id": str(created.json()["id"])}).scalar_one()
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(text("UPDATE audit_logs SET action='tampered' WHERE id=:id"), {"id": event_id})
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(text("DELETE FROM audit_logs WHERE id=:id"), {"id": event_id})
            db.commit()
        db.rollback()
        assert db.execute(text("SELECT action FROM audit_logs WHERE id=:id"), {"id": event_id}).scalar_one() == "transaction.created"


def test_postgres_audit_rows_do_not_contain_financial_description_or_amount():
    client.post("/companies/pg-company-a/transactions", headers=auth("pg-alice"), json={"description": "Sensitive invoice text", "amount": "321.45"})
    with SessionLocal() as db:
        details = db.execute(text("SELECT details::text FROM audit_logs WHERE action='transaction.created' AND company_id='pg-company-a'")).scalar_one()
        assert "Sensitive invoice text" not in details
        assert "321.45" not in details

