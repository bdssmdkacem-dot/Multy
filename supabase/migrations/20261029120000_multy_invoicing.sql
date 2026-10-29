-- Persistent invoice data for the private pilot.
-- Apply only after reviewing the target project's current schema and policies.
begin;

create or replace function public.is_company_editor(p_company_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $function$
  select exists (
    select 1
    from public.companies c
    join public.firm_members m on m.firm_id = c.firm_id
    where c.id = p_company_id
      and m.user_id = auth.uid()
      and m.role in ('firm_admin', 'accountant')
  );
$function$;
revoke all on function public.is_company_editor(uuid) from public, anon;
grant execute on function public.is_company_editor(uuid) to authenticated;

-- Let firm administrators create their first operating company without exposing
-- direct writes to the shared companies table.
create or replace function public.create_company(p_firm_id uuid, p_name text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $function$
declare
  new_company_id uuid;
begin
  if p_name is null or char_length(trim(p_name)) < 2 or char_length(trim(p_name)) > 180 then
    raise exception 'Company name must be between 2 and 180 characters' using errcode = '22023';
  end if;
  if not exists (
    select 1 from public.firm_members m
    where m.firm_id = p_firm_id and m.user_id = auth.uid() and m.role = 'firm_admin'
  ) then
    raise exception 'Firm administrator access required' using errcode = '42501';
  end if;
  insert into public.companies(firm_id, name)
  values (p_firm_id, trim(p_name)) returning id into new_company_id;
  return new_company_id;
end;
$function$;
revoke all on function public.create_company(uuid, text) from public, anon;
grant execute on function public.create_company(uuid, text) to authenticated;

create table public.clients (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete restrict,
  name text not null check (char_length(trim(name)) between 1 and 180),
  email text check (email is null or char_length(email) <= 254),
  phone text check (phone is null or char_length(phone) <= 80),
  tax_identifier text check (tax_identifier is null or char_length(tax_identifier) <= 80),
  address jsonb not null default '{}'::jsonb check (jsonb_typeof(address) = 'object'),
  created_by uuid not null default auth.uid() references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (company_id, id)
);
create index clients_company_name_idx on public.clients(company_id, lower(name));

create table public.invoices (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete restrict,
  client_id uuid not null,
  issue_date date not null,
  due_date date not null,
  status text not null default 'draft' check (status = 'draft'),
  currency text not null default 'MAD' check (currency = 'MAD'),
  note text not null default '' check (char_length(note) <= 2000),
  created_by uuid not null default auth.uid() references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (due_date >= issue_date),
  unique (company_id, id),
  foreign key (company_id, client_id)
    references public.clients(company_id, id) on delete restrict
);
create index invoices_company_issue_date_idx on public.invoices(company_id, issue_date desc);

create table public.invoice_items (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null,
  invoice_id uuid not null,
  description text not null check (char_length(trim(description)) between 1 and 500),
  quantity numeric(14, 3) not null check (quantity > 0 and quantity <= 1000000),
  unit_price numeric(14, 2) not null check (unit_price >= 0 and unit_price < 1000000000),
  vat_rate numeric(5, 2) not null check (vat_rate >= 0 and vat_rate <= 100),
  line_ht numeric(18, 2) generated always as (round(quantity * unit_price, 2)) stored,
  line_vat numeric(18, 2) generated always as (round(round(quantity * unit_price, 2) * vat_rate / 100, 2)) stored,
  line_ttc numeric(18, 2) generated always as (
    round(quantity * unit_price, 2) + round(round(quantity * unit_price, 2) * vat_rate / 100, 2)
  ) stored,
  created_at timestamptz not null default now(),
  foreign key (company_id, invoice_id)
    references public.invoices(company_id, id) on delete cascade
);
create index invoice_items_invoice_idx on public.invoice_items(company_id, invoice_id);

-- Totals are computed from persisted lines. The caller's RLS policies remain in force.
create or replace view public.invoice_totals with (security_invoker = true) as
select i.company_id,
       i.id as invoice_id,
       count(ii.id)::integer as line_count,
       coalesce(sum(ii.line_ht), 0)::numeric(24, 2) as total_ht,
       coalesce(sum(ii.line_vat), 0)::numeric(24, 2) as total_vat,
       coalesce(sum(ii.line_ttc), 0)::numeric(24, 2) as total_ttc
from public.invoices i
left join public.invoice_items ii
  on ii.company_id = i.company_id and ii.invoice_id = i.id
group by i.company_id, i.id;

create function public.set_billing_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $function$
begin
  new.updated_at := now();
  return new;
end;
$function$;
revoke all on function public.set_billing_updated_at() from public, anon, authenticated;

create trigger clients_set_updated_at
before update on public.clients
for each row execute function public.set_billing_updated_at();
create trigger invoices_set_updated_at
before update on public.invoices
for each row execute function public.set_billing_updated_at();

create function public.guard_invoice_identity_update()
returns trigger
language plpgsql
set search_path = ''
as $function$
begin
  if new.id <> old.id or new.company_id <> old.company_id
    or new.created_by <> old.created_by or new.created_at <> old.created_at then
    raise exception 'Invoice identity and ownership cannot be changed' using errcode = '23514';
  end if;
  return new;
end;
$function$;
revoke all on function public.guard_invoice_identity_update() from public, anon, authenticated;

create trigger invoices_guard_update
before update on public.invoices
for each row execute function public.guard_invoice_identity_update();

create function public.guard_client_update()
returns trigger
language plpgsql
set search_path = ''
as $function$
begin
  if new.id <> old.id or new.company_id <> old.company_id
    or new.created_by <> old.created_by or new.created_at <> old.created_at then
    raise exception 'Client identity and ownership cannot be changed' using errcode = '23514';
  end if;
  return new;
end;
$function$;
revoke all on function public.guard_client_update() from public, anon, authenticated;
create trigger clients_guard_update
before update on public.clients
for each row execute function public.guard_client_update();

create function public.audit_billing_change()
returns trigger
language plpgsql
security definer
set search_path = ''
as $function$
declare
  target_company_id uuid;
  target_firm_id uuid;
  target_id uuid;
  target_actor uuid := auth.uid();
  target_action text;
  target_details jsonb := '{}'::jsonb;
begin
  if tg_op = 'DELETE' then
    target_company_id := old.company_id;
    target_id := old.id;
  else
    target_company_id := new.company_id;
    target_id := new.id;
  end if;

  if target_actor is null then
    if tg_table_name <> 'invoice_items' then
      if tg_op = 'DELETE' then target_actor := old.created_by;
      else target_actor := new.created_by;
      end if;
    end if;
  end if;

  if tg_table_name = 'clients' then
    target_action := 'client.' || lower(tg_op);
  elsif tg_table_name = 'invoice_items' then
    target_action := 'invoice_line.' || lower(tg_op);
  else
    target_action := 'invoice.' || lower(tg_op);
    target_details := jsonb_build_object(
      'currency', case when tg_op = 'DELETE' then old.currency else new.currency end
    );
  end if;

  select c.firm_id into target_firm_id
  from public.companies c where c.id = target_company_id;

  insert into public.audit_logs(actor_user_id, firm_id, company_id, action, entity_type, entity_id, details)
  values (target_actor, target_firm_id, target_company_id, target_action,
          case when tg_table_name = 'clients' then 'client'
               when tg_table_name = 'invoice_items' then 'invoice_line' else 'invoice' end,
          target_id::text, target_details);

  if tg_op = 'DELETE' then return old; end if;
  return new;
end;
$function$;
revoke all on function public.audit_billing_change() from public, anon, authenticated;

create trigger clients_audit_change
after insert or update or delete on public.clients
for each row execute function public.audit_billing_change();
create trigger invoices_audit_change
after insert or update or delete on public.invoices
for each row execute function public.audit_billing_change();
create trigger invoice_items_audit_change
after insert or update or delete on public.invoice_items
for each row execute function public.audit_billing_change();

alter table public.clients enable row level security;
alter table public.invoices enable row level security;
alter table public.invoice_items enable row level security;

revoke all on public.clients, public.invoices, public.invoice_items from anon, authenticated;
grant select, insert, update, delete on public.clients, public.invoices, public.invoice_items to authenticated;
grant select on public.invoice_totals to authenticated;

create policy clients_read_member on public.clients for select to authenticated
using (exists (
  select 1 from public.companies c
  where c.id = clients.company_id and public.is_firm_member(c.firm_id)
));
create policy clients_insert_editor on public.clients for insert to authenticated
with check (created_by = (select auth.uid()) and public.is_company_editor(company_id));
create policy clients_update_editor on public.clients for update to authenticated
using (public.is_company_editor(company_id))
with check (public.is_company_editor(company_id));
create policy clients_delete_admin on public.clients for delete to authenticated
using (exists (
  select 1 from public.companies c
  join public.firm_members m on m.firm_id = c.firm_id
  where c.id = clients.company_id and m.user_id = (select auth.uid()) and m.role = 'firm_admin'
));

create policy invoices_read_member on public.invoices for select to authenticated
using (exists (
  select 1 from public.companies c
  where c.id = invoices.company_id and public.is_firm_member(c.firm_id)
));
create policy invoices_insert_editor on public.invoices for insert to authenticated
with check (
  created_by = (select auth.uid())
  and public.is_company_editor(company_id)
);
create policy invoices_update_editor on public.invoices for update to authenticated
using (public.is_company_editor(company_id))
with check (public.is_company_editor(company_id));
create policy invoices_delete_admin_draft on public.invoices for delete to authenticated
using (status = 'draft' and exists (
  select 1 from public.companies c
  join public.firm_members m on m.firm_id = c.firm_id
  where c.id = invoices.company_id and m.user_id = (select auth.uid()) and m.role = 'firm_admin'
));

create policy invoice_items_read_member on public.invoice_items for select to authenticated
using (exists (
  select 1 from public.invoices i
  where i.id = invoice_items.invoice_id and i.company_id = invoice_items.company_id
));
create policy invoice_items_insert_editor_draft on public.invoice_items for insert to authenticated
with check (exists (
  select 1 from public.invoices i
  where i.id = invoice_items.invoice_id and i.company_id = invoice_items.company_id
    and i.status = 'draft' and public.is_company_editor(i.company_id)
));
create policy invoice_items_update_editor_draft on public.invoice_items for update to authenticated
using (exists (
  select 1 from public.invoices i
  where i.id = invoice_items.invoice_id and i.company_id = invoice_items.company_id
    and i.status = 'draft' and public.is_company_editor(i.company_id)
))
with check (exists (
  select 1 from public.invoices i
  where i.id = invoice_items.invoice_id and i.company_id = invoice_items.company_id
    and i.status = 'draft' and public.is_company_editor(i.company_id)
));
create policy invoice_items_delete_editor_draft on public.invoice_items for delete to authenticated
using (exists (
  select 1 from public.invoices i
  where i.id = invoice_items.invoice_id and i.company_id = invoice_items.company_id
    and i.status = 'draft' and public.is_company_editor(i.company_id)
));

-- Persist an entire draft in one transaction, including its client and lines.
-- This function runs as the caller so every statement remains subject to RLS.
create or replace function public.save_invoice_draft(
  p_company_id uuid,
  p_invoice_id uuid,
  p_client_id uuid,
  p_client_name text,
  p_tax_identifier text,
  p_issue_date date,
  p_due_date date,
  p_note text,
  p_vat_rate numeric,
  p_items jsonb
)
returns uuid
language plpgsql
set search_path = ''
as $function$
declare
  target_client_id uuid := p_client_id;
  target_invoice_id uuid := coalesce(p_invoice_id, gen_random_uuid());
begin
  if p_items is null or jsonb_typeof(p_items) <> 'array' or jsonb_array_length(p_items) = 0 then
    raise exception 'At least one invoice line is required' using errcode = '22023';
  end if;
  if p_vat_rate < 0 or p_vat_rate > 100 then
    raise exception 'VAT rate is outside the supported range' using errcode = '22023';
  end if;

  if target_client_id is null then
    insert into public.clients(company_id, name, tax_identifier)
    values (p_company_id, p_client_name, nullif(trim(coalesce(p_tax_identifier, '')), ''))
    returning id into target_client_id;
  else
    update public.clients
       set name = p_client_name,
           tax_identifier = nullif(trim(coalesce(p_tax_identifier, '')), '')
     where id = target_client_id and company_id = p_company_id;
    if not found then
      raise exception 'Client is unavailable in this company' using errcode = '42501';
    end if;
  end if;

  if p_invoice_id is null then
    insert into public.invoices(id, company_id, client_id, issue_date, due_date, note)
    values (target_invoice_id, p_company_id, target_client_id, p_issue_date, p_due_date, coalesce(p_note, ''));
  else
    update public.invoices
       set client_id = target_client_id, issue_date = p_issue_date,
           due_date = p_due_date, note = coalesce(p_note, '')
     where id = p_invoice_id and company_id = p_company_id and status = 'draft';
    if not found then
      raise exception 'Draft invoice is unavailable in this company' using errcode = '42501';
    end if;
    delete from public.invoice_items where invoice_id = p_invoice_id and company_id = p_company_id;
  end if;

  insert into public.invoice_items(company_id, invoice_id, description, quantity, unit_price, vat_rate)
  select p_company_id, target_invoice_id, item.description, item.quantity, item.unit_price, p_vat_rate
  from jsonb_to_recordset(p_items) as item(description text, quantity numeric, unit_price numeric);

  return target_invoice_id;
end;
$function$;
revoke all on function public.save_invoice_draft(uuid, uuid, uuid, text, text, date, date, text, numeric, jsonb) from public, anon;
grant execute on function public.save_invoice_draft(uuid, uuid, uuid, text, text, date, date, text, numeric, jsonb) to authenticated;

commit;

