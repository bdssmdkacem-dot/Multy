-- Multy live Supabase schema preflight
-- READ-ONLY: this file contains SELECT statements only. It does not create,
-- alter, or delete any database object or application row.
-- Run this entire file in Supabase SQL Editor BEFORE applying or re-applying migrations.

-- 1) Required tables, RLS state, and role grants.
WITH expected(table_name) AS (
  VALUES ('profiles'), ('firms'), ('firm_members'), ('companies'),
         ('transactions'), ('audit_logs'), ('invoices'), ('invoice_lines')
)
SELECT
  e.table_name,
  to_regclass(format('public.%I', e.table_name)) IS NOT NULL AS exists_in_public_schema,
  COALESCE(c.relrowsecurity, false) AS rls_enabled,
  COALESCE(c.relforcerowsecurity, false) AS rls_forced,
  CASE WHEN to_regclass(format('public.%I', e.table_name)) IS NULL THEN false
       ELSE has_table_privilege('anon', to_regclass(format('public.%I', e.table_name)), 'SELECT') END AS anon_can_select,
  CASE WHEN to_regclass(format('public.%I', e.table_name)) IS NULL THEN false
       ELSE has_table_privilege('authenticated', to_regclass(format('public.%I', e.table_name)), 'SELECT') END AS authenticated_can_select,
  CASE WHEN to_regclass(format('public.%I', e.table_name)) IS NULL THEN false
       ELSE has_table_privilege('authenticated', to_regclass(format('public.%I', e.table_name)), 'INSERT') END AS authenticated_can_insert
FROM expected e
LEFT JOIN pg_class c ON c.oid = to_regclass(format('public.%I', e.table_name))
ORDER BY e.table_name;

-- 2) Column checks for invoice and expense functionality (missing rows mean a
-- column is absent; existing rows show the actual SQL type).
WITH expected(table_name, column_name) AS (
  VALUES
    ('invoices','id'), ('invoices','company_id'), ('invoices','customer_name'),
    ('invoices','customer_address'), ('invoices','customer_email'),
    ('invoices','customer_ice'), ('invoices','customer_if'),
    ('invoices','issue_date'), ('invoices','due_date'), ('invoices','status'),
    ('invoices','currency'), ('invoices','subtotal'), ('invoices','tax_total'),
    ('invoices','total'), ('invoices','created_by'), ('invoices','invoice_number'),
    ('invoice_lines','id'), ('invoice_lines','invoice_id'), ('invoice_lines','description'),
    ('invoice_lines','quantity'), ('invoice_lines','unit_price'), ('invoice_lines','tax_rate'),
    ('invoice_lines','line_subtotal'), ('invoice_lines','line_tax'),
    ('transactions','entry_type'), ('transactions','category'),
    ('transactions','counterparty'), ('transactions','transaction_date')
)
SELECT
  e.table_name,
  e.column_name,
  c.data_type,
  c.udt_name,
  c.is_nullable,
  c.column_default,
  (c.column_name IS NOT NULL) AS exists
FROM expected e
LEFT JOIN information_schema.columns c
  ON c.table_schema = 'public'
 AND c.table_name = e.table_name
 AND c.column_name = e.column_name
ORDER BY e.table_name, e.column_name;

-- 3) Policies currently installed on sensitive tables.
SELECT tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('profiles','firms','firm_members','companies','transactions',
                    'audit_logs','invoices','invoice_lines')
ORDER BY tablename, policyname;

-- 4) Expected security-critical functions, their exact signatures, and execute grants.
WITH expected(signature) AS (
  VALUES
    ('public.is_firm_member(uuid)'),
    ('public.create_initial_firm(text)'),
    ('public.create_initial_workspace(text,text)'),
    ('public.create_invoice_draft(uuid,text,text,text,text,text,date,date,jsonb)')
)
SELECT
  e.signature,
  p.oid IS NOT NULL AS exists,
  COALESCE(p.prosecdef, false) AS security_definer,
  CASE WHEN p.oid IS NULL THEN false ELSE has_function_privilege('anon', p.oid, 'EXECUTE') END AS anon_can_execute,
  CASE WHEN p.oid IS NULL THEN false ELSE has_function_privilege('authenticated', p.oid, 'EXECUTE') END AS authenticated_can_execute
FROM expected e
LEFT JOIN pg_proc p
  ON p.oid = to_regprocedure(e.signature)
ORDER BY e.signature;

-- 5) Foreign keys and invoice status/amount constraints on these tables.
SELECT
  conrelid::regclass::text AS table_name,
  conname AS constraint_name,
  contype AS constraint_type,
  pg_get_constraintdef(oid) AS definition,
  convalidated AS validated
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
  AND conrelid IN (
    to_regclass('public.transactions'),
    to_regclass('public.companies'),
    to_regclass('public.invoices'),
    to_regclass('public.invoice_lines')
  )
ORDER BY table_name, constraint_name;
