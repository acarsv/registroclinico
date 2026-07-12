grant select, insert, update, delete on table public.exames to anon;
grant select, insert, update, delete on table public.exames to authenticated;

alter table public.exames enable row level security;

drop policy if exists "anon read exames" on public.exames;
drop policy if exists "anon write exames" on public.exames;
drop policy if exists "anon update exames" on public.exames;
drop policy if exists "anon delete exames" on public.exames;

create policy "anon read exames"
on public.exames for select
to anon
using (true);

create policy "anon write exames"
on public.exames for insert
to anon
with check (true);

create policy "anon update exames"
on public.exames for update
to anon
using (true)
with check (true);

create policy "anon delete exames"
on public.exames for delete
to anon
using (true);
