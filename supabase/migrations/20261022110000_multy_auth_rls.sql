-- Multy Supabase foundation: authentication, tenant isolation and audit trail.
-- Apply in a NEW Supabase project using the SQL Editor or Supabase CLI.
begin;

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists public.firms (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(trim(name)) between 2 and 180),
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists public.firm_members (
  firm_id uuid not null references public.firms(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('firm_admin','accountant','read_only')),
  created_at timestamptz not null default now(),
  primary key (firm_id, user_id)
);

create table if not exists public.companies (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete restrict,
  name text not null check (char_length(trim(name)) between 2 and 180),
  created_at timestamptz not null default now()
);
create index if not exists companies_firm_id_idx on public.companies(firm_id);

create table if not exists public.transactions (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete restrict,
  description text not null check (char_length(trim(description)) between 1 and 240),
  amount numeric(14,2) not null check (amount > -1000000000 and amount < 1000000000),
  currency text not null default 'MAD' check (currency = 'MAD'),
  created_by uuid not null default auth.uid() references auth.users(id),
  created_at timestamptz not null default now()
);
create index if not exists transactions_company_id_idx on public.transactions(company_id);

create table if not exists public.audit_logs (
  id bigint generated always as identity primary key,
  actor_user_id uuid references auth.users(id) on delete set null,
  firm_id uuid references public.firms(id) on delete set null,
  company_id uuid references public.companies(id) on delete set null,
  action text not null check (char_length(action) between 1 and 80),
  entity_type text not null check (char_length(entity_type) between 1 and 80),
  entity_id text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists audit_logs_firm_created_idx on public.audit_logs(firm_id, created_at desc);

-- Provision a minimal profile after successful Supabase Auth registration.
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'display_name', ''));
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- The user may create their first firm only for themselves; the membership is atomic.
create or replace function public.create_initial_firm(p_name text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  new_firm_id uuid;
  caller_id uuid := auth.uid();
begin
  if caller_id is null then
    raise exception 'Authentication required' using errcode = '28000';
  end if;
  if p_name is null or char_length(trim(p_name)) < 2 or char_length(trim(p_name)) > 180 then
    raise exception 'Firm name must be between 2 and 180 characters' using errcode = '22023';
  end if;
  if exists (select 1 from public.firm_members where user_id = caller_id) then
    raise exception 'Initial firm already exists' using errcode = '23505';
  end if;
  insert into public.firms(name, created_by) values (trim(p_name), caller_id)
    returning id into new_firm_id;
  insert into public.firm_members(firm_id, user_id, role)
    values (new_firm_id, caller_id, 'firm_admin');
  insert into public.audit_logs(actor_user_id, firm_id, action, entity_type, entity_id, details)
    values (caller_id, new_firm_id, 'firm.created', 'firm', new_firm_id::text, '{}'::jsonb);
  return new_firm_id;
end;
$$;
revoke all on function public.create_initial_firm(text) from public, anon;
grant execute on function public.create_initial_firm(text) to authenticated;

-- Audit events are append-only for ordinary application roles.
create or replace function public.reject_audit_mutation()
returns trigger language plpgsql set search_path = ''
as $$
begin
  raise exception 'audit_logs is append-only';
end;
$$;
drop trigger if exists audit_logs_append_only on public.audit_logs;
create trigger audit_logs_append_only
before update or delete on public.audit_logs
for each row execute function public.reject_audit_mutation();

alter table public.profiles enable row level security;
alter table public.firms enable row level security;
alter table public.firm_members enable row level security;
alter table public.companies enable row level security;
alter table public.transactions enable row level security;
alter table public.audit_logs enable row level security;

-- Revoke broad defaults first; only explicit policies below grant access.
revoke all on public.profiles, public.firms, public.firm_members, public.companies,
  public.transactions, public.audit_logs from anon, authenticated;
grant select, update on public.profiles to authenticated;
grant select on public.firms, public.firm_members, public.companies, public.audit_logs to authenticated;
grant select, insert, update, delete on public.transactions to authenticated;
grant usage, select on sequence public.audit_logs_id_seq to authenticated;

create policy profiles_read_self on public.profiles for select to authenticated using (id = (select auth.uid()));
create policy profiles_update_self on public.profiles for update to authenticated using (id = (select auth.uid())) with check (id = (select auth.uid()));

create policy firms_read_members on public.firms for select to authenticated
using (exists (select 1 from public.firm_members m where m.firm_id = id and m.user_id = (select auth.uid())));

create policy firm_members_read_same_firm on public.firm_members for select to authenticated
using (exists (select 1 from public.firm_members own where own.firm_id = firm_members.firm_id and own.user_id = (select auth.uid())));

create policy companies_read_member_firm on public.companies for select to authenticated
using (exists (select 1 from public.firm_members m where m.firm_id = companies.firm_id and m.user_id = (select auth.uid())));

create policy transactions_read_member_firm on public.transactions for select to authenticated
using (exists (
  select 1 from public.companies c join public.firm_members m on m.firm_id = c.firm_id
  where c.id = transactions.company_id and m.user_id = (select auth.uid())
));

create policy transactions_insert_editor on public.transactions for insert to authenticated
with check (
  created_by = (select auth.uid())
  and exists (
    select 1 from public.companies c join public.firm_members m on m.firm_id = c.firm_id
    where c.id = transactions.company_id
      and m.user_id = (select auth.uid())
      and m.role in ('firm_admin','accountant')
  )
);

create policy transactions_update_editor on public.transactions for update to authenticated
using (exists (
  select 1 from public.companies c join public.firm_members m on m.firm_id = c.firm_id
  where c.id = transactions.company_id and m.user_id = (select auth.uid())
    and m.role in ('firm_admin','accountant')
))
with check (exists (
  select 1 from public.companies c join public.firm_members m on m.firm_id = c.firm_id
  where c.id = transactions.company_id and m.user_id = (select auth.uid())
    and m.role in ('firm_admin','accountant')
));

create policy transactions_delete_admin on public.transactions for delete to authenticated
using (exists (
  select 1 from public.companies c join public.firm_members m on m.firm_id = c.firm_id
  where c.id = transactions.company_id and m.user_id = (select auth.uid())
    and m.role = 'firm_admin'
));

create policy audit_read_admin on public.audit_logs for select to authenticated
using (firm_id is not null and exists (
  select 1 from public.firm_members m where m.firm_id = audit_logs.firm_id
    and m.user_id = (select auth.uid()) and m.role = 'firm_admin'
));

-- Do not grant client roles INSERT/UPDATE/DELETE on audit_logs.
revoke insert, update, delete on public.audit_logs from anon, authenticated;

commit;
