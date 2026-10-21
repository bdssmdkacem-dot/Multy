import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

os.environ.setdefault("MULTY_JWT_SECRET", "postgres-test-secret-not-for-production")
from backend.main import SessionLocal, app, get_db

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
        db.execute(text("TRUNCATE TABLE transactions, memberships, companies, users, firms RESTART IDENTITY CASCADE"))
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
