# Read-only preflight for an existing Supabase project

**Do not apply migrations to the live project until this inspection has been reviewed.** This file is a read-only catalog query. It does not alter tables, policies, functions, or application data.

## Run the inspection

1. Open the target Supabase project and go to **SQL Editor**.
2. Open `supabase/diagnostics/20261022_live_schema_preflight.sql` from this branch and paste/run its full contents.
3. Save/export all five result sets: required tables and RLS/grants; invoice/expense columns; policies; security-critical functions; constraints.
4. Keep the output private if it contains project-specific schema details. It should not contain customer rows or secrets.

## Interpret the output

- The `invoices` and `invoice_lines` tables should exist before the invoice page can save or list drafts.
- `transactions.entry_type`, `category`, `counterparty`, and `transaction_date` should exist before the expense page can save or query its records.
- `invoices` and `invoice_lines` should have RLS enabled. Their authenticated read policies should scope through a company whose firm membership belongs to the current user.
- `create_invoice_draft(uuid,text,text,text,text,text,date,date,jsonb)` should exist and be executable by `authenticated`, not by `anon`. Direct authenticated INSERT on invoice tables should remain revoked so draft writes go through the validating RPC.
- The base function `is_firm_member(uuid)` and the workspace RPC must match the signatures shown by the diagnostic.

A missing row in the column result means the column is absent. A missing table/function should be interpreted together with the other result sets; do not infer that the entire base migration failed from one missing feature.

## Do not blindly replay the base migration

These SQL files are ordered schema changes, **not** a migration runner with a reliable applied-migrations ledger when they are pasted into SQL Editor manually. The base file `20261022110000_multy_auth_rls.sql` creates named policies without first dropping them; re-running it after it has already succeeded will hit duplicate-policy errors. The invoice migration also creates named policies that are not all written for arbitrary re-execution.

If the base tables and policies already exist but invoices or expense columns are missing, do not start again from the first file. First review the diagnostic results against the exact migration files and determine which migration transactions actually completed. Then apply only the missing, dependency-satisfied migration in the existing project, one file at a time, and stop on the first SQL error. Do not use `DROP TABLE`, disable RLS, delete policies wholesale, or reset the database to make the migration pass.

The CI workflow `Supabase migration chain and isolation` validates the full sequence against a **fresh temporary PostgreSQL database**. That is useful evidence for SQL syntax and expected behavior, but it is not proof that replaying migrations against the existing Supabase project is safe.

## Current live-project status

No live-project inspection query has been executed by this repository workflow, and no live database change has been made. Record and review the diagnostic results from the actual project before preparing a project-specific apply plan. After the missing migrations are applied, test actual Supabase signup, email confirmation, sign-in, workspace creation, invoice draft creation, expense creation, and cross-tenant denial using two dedicated test accounts before removing the PR's draft status.
