-- Create the first tenant atomically for the authenticated user.
begin;

create or replace function public.create_initial_workspace(p_firm_name text, p_company_name text)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_id uuid := auth.uid();
  new_firm_id uuid;
  new_company_id uuid;
begin
  if caller_id is null then
    raise exception 'Authentication required' using errcode = '28000';
  end if;
  if p_firm_name is null or char_length(trim(p_firm_name)) < 2 or char_length(trim(p_firm_name)) > 180
    or p_company_name is null or char_length(trim(p_company_name)) < 2 or char_length(trim(p_company_name)) > 180 then
    raise exception 'Firm and company names must be between 2 and 180 characters' using errcode = '22023';
  end if;

  -- Serialize first-workspace creation per user to prevent duplicate tenants on concurrent requests.
  perform pg_advisory_xact_lock(hashtextextended(caller_id::text, 0));
  if exists (select 1 from public.firm_members where user_id = caller_id) then
    raise exception 'Initial workspace already exists' using errcode = '23505';
  end if;

  insert into public.firms(name, created_by) values (trim(p_firm_name), caller_id)
    returning id into new_firm_id;
  insert into public.firm_members(firm_id, user_id, role)
    values (new_firm_id, caller_id, 'firm_admin');
  insert into public.companies(firm_id, name)
    values (new_firm_id, trim(p_company_name)) returning id into new_company_id;
  insert into public.audit_logs(actor_user_id, firm_id, company_id, action, entity_type, entity_id, details)
    values (caller_id, new_firm_id, new_company_id, 'workspace.created', 'company', new_company_id::text, '{}'::jsonb);

  return jsonb_build_object('firm_id', new_firm_id, 'company_id', new_company_id);
end;
$$;
revoke all on function public.create_initial_workspace(text,text) from public, anon;
grant execute on function public.create_initial_workspace(text,text) to authenticated;

commit;
