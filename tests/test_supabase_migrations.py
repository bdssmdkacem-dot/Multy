"""Run Supabase migrations against an isolated PostgreSQL database and assert RLS behavior.

This integration test is opt-in because it creates and drops one uniquely named database.
Set MULTY_SUPABASE_TEST_ADMIN_DSN only to a disposable PostgreSQL superuser connection.
"""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.errors import CheckViolation, InsufficientPrivilege


ADMIN_DSN = os.getenv("MULTY_SUPABASE_TEST_ADMIN_DSN")
pytestmark = pytest.mark.skipif(
    not ADMIN_DSN,
    reason="Set MULTY_SUPABASE_TEST_ADMIN_DSN to an isolated disposable PostgreSQL cluster",
)


def test_supabase_invoicing_migration_enforces_tenant_rls_and_totals():
    assert ADMIN_DSN
    database_name = f"multy_supabase_test_{uuid4().hex}"
    admin_options = conninfo_to_dict(ADMIN_DSN)
    admin_options["dbname"] = database_name
    test_dsn = make_conninfo(**admin_options)

    with psycopg.connect(ADMIN_DSN, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{database_name}"')

    try:
        root = Path(__file__).resolve().parents[1]
        migration_paths = sorted((root / "supabase" / "migrations").glob("*.sql"))
        assert [path.name for path in migration_paths] == [
            "20261022110000_multy_auth_rls.sql",
            "20261029120000_multy_invoicing.sql",
        ]

        with psycopg.connect(test_dsn, autocommit=True) as db:
            db.execute(
                """
                do $roles$
                begin
                  if not exists (select 1 from pg_roles where rolname = 'anon') then
                    create role anon nologin;
                  end if;
                  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
                    create role authenticated nologin;
                  end if;
                end
                $roles$;
                create schema auth;
                create table auth.users (
                  id uuid primary key,
                  raw_user_meta_data jsonb not null default '{}'::jsonb
                );
                create function auth.uid()
                returns uuid language sql stable
                as $uid$
                  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
                $uid$;
                grant usage on schema auth to anon, authenticated;
                grant execute on function auth.uid() to anon, authenticated;
                """
            )
            for migration in migration_paths:
                db.execute(migration.read_text(encoding="utf-8"), prepare=False)

            firm_a, firm_b = uuid4(), uuid4()
            alice, bob, reader = uuid4(), uuid4(), uuid4()
            company_a, company_b = uuid4(), uuid4()
            db.execute("insert into auth.users (id) values (%s), (%s), (%s)", (alice, bob, reader))
            db.execute(
                "insert into public.firms (id, name, created_by) values (%s, 'Cabinet A', %s), (%s, 'Cabinet B', %s)",
                (firm_a, alice, firm_b, bob),
            )
            db.execute(
                "insert into public.firm_members (firm_id, user_id, role) values (%s, %s, 'firm_admin'), (%s, %s, 'firm_admin'), (%s, %s, 'read_only')",
                (firm_a, alice, firm_b, bob, firm_a, reader),
            )
            db.execute(
                "insert into public.companies (id, firm_id, name) values (%s, %s, 'Atelier A'), (%s, %s, 'Entreprise B')",
                (company_a, firm_a, company_b, firm_b),
            )

            client_a = uuid4()
            invoice_a = uuid4()
            line_a = uuid4()
            with db.transaction():
                db.execute("set local role authenticated")
                db.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(alice),))
                db.execute(
                    "insert into public.clients (id, company_id, name, email) values (%s, %s, %s, %s)",
                    (client_a, company_a, "Client A", "private@example.test"),
                )
                db.execute(
                    """
                    insert into public.invoices (id, company_id, client_id, issue_date, due_date)
                    values (%s, %s, %s, date '2026-10-01', date '2026-10-31')
                    """,
                    (invoice_a, company_a, client_a),
                )
                db.execute(
                    """
                    insert into public.invoice_items
                      (id, company_id, invoice_id, description, quantity, unit_price, vat_rate)
                    values (%s, %s, %s, 'Conseil', 2, 100, 20)
                    """,
                    (line_a, company_a, invoice_a),
                )
                totals = db.execute(
                    """
                    select line_count, total_ht, total_vat, total_ttc
                    from public.invoice_totals where company_id = %s and invoice_id = %s
                    """,
                    (company_a, invoice_a),
                ).fetchone()
                assert totals == (1, 200, 40, 240)

                assert db.execute("select count(*) from public.clients").fetchone()[0] == 1
                assert db.execute("select count(*) from public.invoices").fetchone()[0] == 1

                with pytest.raises(InsufficientPrivilege):
                    with db.transaction():
                        db.execute(
                            "insert into public.clients (company_id, name) values (%s, 'Cross tenant')",
                            (company_b,),
                        )

                assert db.execute(
                    "select action from public.audit_logs where entity_id = %s order by id",
                    (str(invoice_a),),
                ).fetchall() == [("invoice.insert",)]

            with db.transaction():
                db.execute("set local role authenticated")
                db.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(bob),))
                assert db.execute("select count(*) from public.clients").fetchone()[0] == 0
                assert db.execute("select count(*) from public.invoices").fetchone()[0] == 0
                assert db.execute("select count(*) from public.invoice_totals").fetchone()[0] == 0

            with db.transaction():
                db.execute("set local role authenticated")
                db.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(reader),))
                with pytest.raises(InsufficientPrivilege):
                    with db.transaction():
                        db.execute(
                            """
                            insert into public.invoices
                              (company_id, client_id, issue_date, due_date)
                            values (%s, %s, date '2026-10-01', date '2026-10-31')
                            """,
                            (company_a, client_a),
                        )

            with db.transaction():
                db.execute("set local role authenticated")
                db.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(alice),))
                audit_text = " ".join(
                    str(row[0])
                    for row in db.execute(
                        "select details from public.audit_logs where company_id = %s", (company_a,)
                    ).fetchall()
                )
                assert "private@example.test" not in audit_text
                assert "Conseil" not in audit_text
                assert "200" not in audit_text
    finally:
        with psycopg.connect(ADMIN_DSN, autocommit=True) as admin:
            admin.execute(
                """
                select pg_terminate_backend(pid)
                from pg_stat_activity
                where datname = %s and pid <> pg_backend_pid()
                """,
                (database_name,),
            )
            admin.execute(f'DROP DATABASE IF EXISTS "{database_name}"')

