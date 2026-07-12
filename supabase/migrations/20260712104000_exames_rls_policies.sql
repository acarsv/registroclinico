alter table exames enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'exames'
      and policyname = 'anon read exames'
  ) then
    create policy "anon read exames" on exames for select to anon using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'exames'
      and policyname = 'anon write exames'
  ) then
    create policy "anon write exames" on exames for insert to anon with check (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'exames'
      and policyname = 'anon update exames'
  ) then
    create policy "anon update exames" on exames for update to anon using (true) with check (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'exames'
      and policyname = 'anon delete exames'
  ) then
    create policy "anon delete exames" on exames for delete to anon using (true);
  end if;
end $$;
