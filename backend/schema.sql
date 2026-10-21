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
