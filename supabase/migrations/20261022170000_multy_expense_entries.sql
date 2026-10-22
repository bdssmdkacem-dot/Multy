-- Extend the shared movement ledger for Moroccan expense capture.
begin;

alter table public.transactions
  add column if not exists entry_type text not null default 'adjustment',
  add column if not exists category text not null default 'Divers',
  add column if not exists counterparty text not null default '',
  add column if not exists transaction_date date not null default current_date;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'transactions_entry_type_check') then
    alter table public.transactions add constraint transactions_entry_type_check
      check (entry_type in ('income','expense','adjustment'));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'transactions_category_check') then
    alter table public.transactions add constraint transactions_category_check
      check (char_length(trim(category)) between 1 and 80);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'transactions_counterparty_check') then
    alter table public.transactions add constraint transactions_counterparty_check
      check (char_length(counterparty) <= 180);
  end if;
end;
$$;

create index if not exists transactions_company_date_idx
  on public.transactions(company_id, transaction_date desc, created_at desc);

commit;
