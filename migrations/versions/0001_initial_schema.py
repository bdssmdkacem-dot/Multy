"""Initial Multy tenant schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "firms",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=180), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("firm_id", sa.String(length=36), sa.ForeignKey("firms.id"), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
    )
    op.create_index("ix_companies_firm_id", "companies", ["firm_id"])
    op.create_table(
        "memberships",
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), primary_key=True),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.CheckConstraint("role IN ('firm_admin', 'accountant', 'read_only')", name="ck_memberships_role"),
    )
    op.create_index("ix_memberships_company_id", "memberships", ["company_id"])
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="MAD", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("currency = 'MAD'", name="ck_transactions_currency_mad"),
    )
    op.create_index("ix_transactions_company_id", "transactions", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_transactions_company_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_memberships_company_id", table_name="memberships")
    op.drop_table("memberships")
    op.drop_index("ix_companies_firm_id", table_name="companies")
    op.drop_table("companies")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("firms")
