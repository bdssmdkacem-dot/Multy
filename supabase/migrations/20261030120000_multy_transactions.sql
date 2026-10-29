-- Add the fields required by the transaction register without changing existing rows.
begin;

alter table public.transactions
  add column occurred_on date not null default current_date,
  add column category text not null default 'Divers'
    check (char_length(trim(category)) between 1 and 80);

create index transactions_company_occurred_on_idx
  on public.transactions(company_id, occurred_on desc);

commit;
