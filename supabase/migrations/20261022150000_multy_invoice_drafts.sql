-- Draft invoicing foundations for Moroccan companies.
-- Draft invoices are not numbered or represented as issued/compliant invoices.
begin;

create table if not exists public.invoices (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references public.companies(id) on delete restrict,
  customer_name text not null check (char_length(trim(customer_name)) between 2 and 180),
  customer_address text not null default '',
  customer_email text not null default '',
  customer_ice text not null default '',
  customer_if text not null default '',
  issue_date date not null,
  due_date date,
  status text not null default 'draft' check (status in ('draft','issued','paid','void')),
  currency text not null default 'MAD' check (currency = 'MAD'),
  subtotal numeric(14,2) not null check (subtotal >= 0),
  tax_total numeric(14,2) not null check (tax_total >= 0),
  total numeric(14,2) not null check (total >= 0),
  created_by uuid not null default auth.uid() references auth.users(id),
  created_at timestamptz not null default now(),
  invoice_number text,
  check (status = 'draft' or invoice_number is not null)
);
create index if not exists invoices_company_created_idx on public.invoices(company_id, created_at desc);

create table if not exists public.invoice_lines (
  id uuid primary key default gen_random_uuid(),
  invoice_id uuid not null references public.invoices(id) on delete restrict,
  description text not null check (char_length(trim(description)) between 1 and 240),
  quantity numeric(12,3) not null check (quantity > 0 and quantity < 1000000000),
  unit_price numeric(14,2) not null check (unit_price >= 0 and unit_price < 1000000000),
  tax_rate numeric(5,2) not null default 0 check (tax_rate >= 0 and tax_rate <= 100),
  line_subtotal numeric(14,2) not null check (line_subtotal >= 0),
  line_tax numeric(14,2) not null check (line_tax >= 0),
  created_at timestamptz not null default now()
);
create index if not exists invoice_lines_invoice_id_idx on public.invoice_lines(invoice_id);

alter table public.invoices enable row level security;
alter table public.invoice_lines enable row level security;
revoke all on public.invoices, public.invoice_lines from anon, authenticated;
grant select on public.invoices, public.invoice_lines to authenticated;

create policy invoices_read_member on public.invoices for select to authenticated
using (exists (
  select 1 from public.companies c
  where c.id = invoices.company_id and public.is_firm_member(c.firm_id)
));
create policy invoice_lines_read_member on public.invoice_lines for select to authenticated
using (exists (
  select 1 from public.invoices i join public.companies c on c.id = i.company_id
  where i.id = invoice_lines.invoice_id and public.is_firm_member(c.firm_id)
));

create or replace function public.create_invoice_draft(
  p_company_id uuid,
  p_customer_name text,
  p_customer_address text,
  p_customer_email text,
  p_customer_ice text,
  p_customer_if text,
  p_issue_date date,
  p_due_date date,
  p_lines jsonb
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_id uuid := auth.uid();
  company_firm_id uuid;
  invoice_id uuid;
  line jsonb;
  line_description text;
  line_quantity numeric;
  line_unit_price numeric;
  line_tax_rate numeric;
  line_subtotal numeric;
  line_tax numeric;
  subtotal numeric := 0;
  tax_total numeric := 0;
begin
  if caller_id is null then
    raise exception 'Authentication required' using errcode = '28000';
  end if;
  if p_customer_name is null or char_length(trim(p_customer_name)) < 2 or char_length(trim(p_customer_name)) > 180 then
    raise exception 'Customer name must be between 2 and 180 characters' using errcode = '22023';
  end if;
  if p_issue_date is null or (p_due_date is not null and p_due_date < p_issue_date) then
    raise exception 'Invoice dates are invalid' using errcode = '22023';
  end if;
  if p_lines is null or jsonb_typeof(p_lines) <> 'array' or jsonb_array_length(p_lines) < 1 or jsonb_array_length(p_lines) > 100 then
    raise exception 'An invoice needs between 1 and 100 lines' using errcode = '22023';
  end if;

  select c.firm_id into company_firm_id
  from public.companies c
  join public.firm_members m on m.firm_id = c.firm_id
  where c.id = p_company_id and m.user_id = caller_id and m.role in ('firm_admin','accountant');
  if company_firm_id is null then
    raise exception 'Company access denied' using errcode = '42501';
  end if;

  for line in select item from jsonb_array_elements(p_lines) as line_items(item) loop
    line_description := trim(coalesce(line ->> 'description', ''));
    line_quantity := (line ->> 'quantity')::numeric;
    line_unit_price := (line ->> 'unit_price')::numeric;
    line_tax_rate := coalesce((line ->> 'tax_rate')::numeric, 0);
    if char_length(line_description) < 1 or char_length(line_description) > 240
      or line_quantity <= 0 or line_quantity >= 1000000000
      or line_unit_price < 0 or line_unit_price >= 1000000000
      or line_tax_rate < 0 or line_tax_rate > 100 then
      raise exception 'Invoice line values are invalid' using errcode = '22023';
    end if;
    line_subtotal := round(line_quantity * line_unit_price, 2);
    line_tax := round(line_subtotal * line_tax_rate / 100, 2);
    subtotal := subtotal + line_subtotal;
    tax_total := tax_total + line_tax;
  end loop;

  insert into public.invoices(
    company_id, customer_name, customer_address, customer_email, customer_ice, customer_if,
    issue_date, due_date, status, currency, subtotal, tax_total, total, created_by
  ) values (
    p_company_id, trim(p_customer_name), coalesce(trim(p_customer_address), ''),
    coalesce(trim(p_customer_email), ''), coalesce(trim(p_customer_ice), ''),
    coalesce(trim(p_customer_if), ''), p_issue_date, p_due_date, 'draft', 'MAD',
    subtotal, tax_total, subtotal + tax_total, caller_id
  ) returning id into invoice_id;

  for line in select item from jsonb_array_elements(p_lines) as line_items(item) loop
    line_description := trim(line ->> 'description');
    line_quantity := (line ->> 'quantity')::numeric;
    line_unit_price := (line ->> 'unit_price')::numeric;
    line_tax_rate := coalesce((line ->> 'tax_rate')::numeric, 0);
    line_subtotal := round(line_quantity * line_unit_price, 2);
    line_tax := round(line_subtotal * line_tax_rate / 100, 2);
    insert into public.invoice_lines(invoice_id, description, quantity, unit_price, tax_rate, line_subtotal, line_tax)
    values (invoice_id, line_description, line_quantity, line_unit_price, line_tax_rate, line_subtotal, line_tax);
  end loop;

  insert into public.audit_logs(actor_user_id, firm_id, company_id, action, entity_type, entity_id, details)
  values (caller_id, company_firm_id, p_company_id, 'invoice.draft_created', 'invoice', invoice_id::text,
    jsonb_build_object('currency', 'MAD', 'total', subtotal + tax_total));

  return invoice_id;
end;
$$;
revoke all on function public.create_invoice_draft(uuid,text,text,text,text,text,date,date,jsonb) from public, anon;
grant execute on function public.create_invoice_draft(uuid,text,text,text,text,text,date,date,jsonb) to authenticated;

commit;
