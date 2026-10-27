-- Initial PostgreSQL schema. Apply through a controlled migration before deployment.
CREATE TABLE IF NOT EXISTS firms (
    id varchar(36) PRIMARY KEY,
    name varchar(180) NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id varchar(36) PRIMARY KEY,
    email varchar(254) NOT NULL UNIQUE,
    active boolean NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS companies (
    id varchar(36) PRIMARY KEY,
    firm_id varchar(36) NOT NULL REFERENCES firms(id),
    name varchar(180) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_companies_firm_id ON companies(firm_id);
CREATE TABLE IF NOT EXISTS memberships (
    user_id varchar(36) NOT NULL REFERENCES users(id),
    company_id varchar(36) NOT NULL REFERENCES companies(id),
    role varchar(24) NOT NULL CHECK (role IN ('firm_admin', 'accountant', 'read_only')),
    PRIMARY KEY (user_id, company_id)
);
CREATE INDEX IF NOT EXISTS ix_memberships_company_id ON memberships(company_id);
CREATE TABLE IF NOT EXISTS transactions (
    id bigserial PRIMARY KEY,
    company_id varchar(36) NOT NULL REFERENCES companies(id),
    description varchar(240) NOT NULL,
    amount numeric(14,2) NOT NULL,
    currency varchar(3) NOT NULL DEFAULT 'MAD' CHECK (currency = 'MAD'),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_transactions_company_id ON transactions(company_id);

CREATE TABLE IF NOT EXISTS audit_logs (
    id bigserial PRIMARY KEY,
    actor_user_id varchar(36),
    company_id varchar(36),
    action varchar(80) NOT NULL,
    entity_type varchar(80) NOT NULL,
    entity_id varchar(80),
    details json NOT NULL DEFAULT '{}'::json,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_user_id ON audit_logs(actor_user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_company_id ON audit_logs(company_id);

-- Append-only audit protection. Migration 0003 is the canonical deployment path.
CREATE OR REPLACE FUNCTION reject_audit_log_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs;
CREATE TRIGGER audit_logs_append_only
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION reject_audit_log_mutation();
