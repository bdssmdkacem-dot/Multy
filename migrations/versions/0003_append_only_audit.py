"""Enforce append-only audit event rows in PostgreSQL."""
from alembic import op

revision = "0003_append_only_audit"
down_revision = "0002_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep audit actor/company identifiers as historical references, not FKs
    # whose ON DELETE behavior would mutate historical audit rows.
    op.drop_constraint("audit_logs_actor_user_id_fkey", "audit_logs", type_="foreignkey")
    op.drop_constraint("audit_logs_company_id_fkey", "audit_logs", type_="foreignkey")
    op.execute("""
        CREATE FUNCTION reject_audit_log_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER audit_logs_append_only
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION reject_audit_log_mutation()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS reject_audit_log_mutation()")
    op.create_foreign_key(
        "audit_logs_actor_user_id_fkey", "audit_logs", "users",
        ["actor_user_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "audit_logs_company_id_fkey", "audit_logs", "companies",
        ["company_id"], ["id"], ondelete="SET NULL"
    )
