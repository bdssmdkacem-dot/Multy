\set ON_ERROR_STOP on
BEGIN;

-- Validate that the entire migration chain created the objects the UI relies on.
DO $$
BEGIN
  IF to_regclass('public.invoices') IS NULL THEN RAISE EXCEPTION 'Missing public.invoices'; END IF;
  IF to_regclass('public.invoice_lines') IS NULL THEN RAISE EXCEPTION 'Missing public.invoice_lines'; END IF;
  IF to_regclass('public.transactions') IS NULL THEN RAISE EXCEPTION 'Missing public.transactions'; END IF;
  IF to_regprocedure('public.create_initial_workspace(text,text)') IS NULL THEN RAISE EXCEPTION 'Missing create_initial_workspace RPC'; END IF;
  IF to_regprocedure('public.create_invoice_draft(uuid,text,text,text,text,text,date,date,jsonb)') IS NULL THEN RAISE EXCEPTION 'Missing create_invoice_draft RPC'; END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='transactions' AND column_name='entry_type') THEN RAISE EXCEPTION 'Missing transactions.entry_type'; END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='transactions' AND column_name='category') THEN RAISE EXCEPTION 'Missing transactions.category'; END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='transactions' AND column_name='counterparty') THEN RAISE EXCEPTION 'Missing transactions.counterparty'; END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='transactions' AND column_name='transaction_date') THEN RAISE EXCEPTION 'Missing transactions.transaction_date'; END IF;
  IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid='public.invoices'::regclass) THEN RAISE EXCEPTION 'RLS disabled on invoices'; END IF;
  IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid='public.invoice_lines'::regclass) THEN RAISE EXCEPTION 'RLS disabled on invoice_lines'; END IF;
  IF NOT has_function_privilege('authenticated', 'public.create_invoice_draft(uuid,text,text,text,text,text,date,date,jsonb)', 'EXECUTE') THEN RAISE EXCEPTION 'Authenticated role cannot execute draft RPC'; END IF;
  IF has_function_privilege('anon', 'public.create_invoice_draft(uuid,text,text,text,text,text,date,date,jsonb)', 'EXECUTE') THEN RAISE EXCEPTION 'Anonymous role can execute draft RPC'; END IF;
  IF has_table_privilege('authenticated', 'public.invoices', 'INSERT') OR has_table_privilege('authenticated', 'public.invoice_lines', 'INSERT') THEN RAISE EXCEPTION 'Direct invoice table inserts should be revoked; use the validated RPC'; END IF;
END;
$$;

-- Create two synthetic auth users. The trigger should make their profiles.
INSERT INTO auth.users(id, raw_user_meta_data) VALUES
  ('10000000-0000-0000-0000-000000000001', '{"display_name":"Tenant A"}'::jsonb),
  ('20000000-0000-0000-0000-000000000002', '{"display_name":"Tenant B"}'::jsonb);

GRANT USAGE ON SCHEMA public, auth TO authenticated, anon;
GRANT EXECUTE ON FUNCTION auth.uid() TO authenticated, anon;
SET ROLE authenticated;

SELECT set_config('request.jwt.claim.sub', '10000000-0000-0000-0000-000000000001', true);
SELECT (public.create_initial_workspace('Cabinet A', 'Entreprise A')->>'company_id') AS company_id \gset tenant_a_
INSERT INTO public.transactions(company_id, description, amount, currency, entry_type, category, counterparty, transaction_date)
VALUES (:'tenant_a_company_id'::uuid, 'Test expense A', -125.50, 'MAD', 'expense', 'Tests', 'Fournisseur A', current_date);
SELECT public.create_invoice_draft(
  :'tenant_a_company_id'::uuid,
  'Client A', '', '', 'ICE-A', 'IF-A', current_date, NULL,
  '[{"description":"Prestation A","quantity":2,"unit_price":50,"tax_rate":10}]'::jsonb
) AS invoice_id \gset invoice_a_
SELECT (subtotal = 100.00 AND tax_total = 10.00 AND total = 110.00) AS invoice_totals_ok
FROM public.invoices WHERE id = :'invoice_a_invoice_id'::uuid \gset
\if :invoice_totals_ok
\else
  \echo 'Invoice server-side total calculation failed'
  \quit 1
\endif

SELECT set_config('request.jwt.claim.sub', '20000000-0000-0000-0000-000000000002', true);
SELECT (public.create_initial_workspace('Cabinet B', 'Entreprise B')->>'company_id') AS company_id \gset tenant_b_

-- Tenant B must not be able to read Tenant A's company, expense, invoice or invoice lines.
SELECT count(*) = 0 AS isolated_company FROM public.companies WHERE id = :'tenant_a_company_id'::uuid \gset
\if :isolated_company
\else
  \echo 'Tenant isolation failure: Tenant B can read Tenant A company'
  \quit 1
\endif

SELECT count(*) = 0 AS isolated_transaction FROM public.transactions
WHERE company_id = :'tenant_a_company_id'::uuid \gset
\if :isolated_transaction
\else
  \echo 'Tenant isolation failure: Tenant B can read Tenant A transactions'
  \quit 1
\endif

SELECT count(*) = 0 AS isolated_invoice FROM public.invoices
WHERE id = :'invoice_a_invoice_id'::uuid \gset
\if :isolated_invoice
\else
  \echo 'Tenant isolation failure: Tenant B can read Tenant A invoice'
  \quit 1
\endif

SELECT count(*) = 0 AS isolated_invoice_lines FROM public.invoice_lines
WHERE invoice_id = :'invoice_a_invoice_id'::uuid \gset
\if :isolated_invoice_lines
\else
  \echo 'Tenant isolation failure: Tenant B can read Tenant A invoice lines'
  \quit 1
\endif

ROLLBACK;
