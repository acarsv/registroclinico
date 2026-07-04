create table if not exists doencas (
  id uuid primary key default gen_random_uuid(),
  cid text not null unique,
  doenca text,
  descricao text,
  created_at timestamptz not null default now()
);

alter table doencas enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'doencas' and policyname = 'anon read doencas') then
    create policy "anon read doencas" on doencas for select to anon using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'doencas' and policyname = 'anon write doencas') then
    create policy "anon write doencas" on doencas for insert to anon with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'doencas' and policyname = 'anon update doencas') then
    create policy "anon update doencas" on doencas for update to anon using (true);
  end if;
end $$;
