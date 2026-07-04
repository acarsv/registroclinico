create extension if not exists pgcrypto;

create table if not exists patients (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  birth_date date,
  sex text check (sex in ('Feminino', 'Masculino', 'Outro', 'Nao informado')) default 'Nao informado',
  phone text,
  email text,
  city text,
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists doctors (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  specialty text,
  crm text,
  phone text,
  email text,
  created_at timestamptz not null default now()
);

create table if not exists conditions (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references patients(id) on delete cascade,
  name text not null,
  status text check (status in ('Ativa', 'Controlada', 'Resolvida', 'Suspeita')) default 'Ativa',
  severity text check (severity in ('Baixa', 'Moderada', 'Alta', 'Critica')) default 'Moderada',
  diagnosed_at date,
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists medications (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references patients(id) on delete cascade,
  name text not null,
  dosage text,
  frequency text,
  started_at date,
  ended_at date,
  status text check (status in ('Em uso', 'Pausado', 'Encerrado')) default 'Em uso',
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists exams (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references patients(id) on delete cascade,
  exam_type text not null,
  exam_date date not null default current_date,
  result_text text,
  numeric_value numeric,
  unit text,
  reference_range text,
  file_url text,
  created_at timestamptz not null default now()
);

create table if not exists visits (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references patients(id) on delete cascade,
  doctor_id uuid references doctors(id) on delete set null,
  visit_date date not null default current_date,
  reason text,
  diagnosis text,
  plan text,
  created_at timestamptz not null default now()
);

create index if not exists idx_conditions_patient on conditions(patient_id);
create index if not exists idx_medications_patient on medications(patient_id);
create index if not exists idx_exams_patient_date on exams(patient_id, exam_date desc);
create index if not exists idx_visits_patient_date on visits(patient_id, visit_date desc);

alter table patients enable row level security;
alter table doctors enable row level security;
alter table conditions enable row level security;
alter table medications enable row level security;
alter table exams enable row level security;
alter table visits enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'patients' and policyname = 'anon read patients') then
    create policy "anon read patients" on patients for select to anon using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'patients' and policyname = 'anon write patients') then
    create policy "anon write patients" on patients for insert to anon with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'patients' and policyname = 'anon update patients') then
    create policy "anon update patients" on patients for update to anon using (true);
  end if;
end $$;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'doctors' and policyname = 'anon read doctors') then
    create policy "anon read doctors" on doctors for select to anon using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'doctors' and policyname = 'anon write doctors') then
    create policy "anon write doctors" on doctors for insert to anon with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'doctors' and policyname = 'anon update doctors') then
    create policy "anon update doctors" on doctors for update to anon using (true);
  end if;
end $$;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'conditions' and policyname = 'anon read conditions') then
    create policy "anon read conditions" on conditions for select to anon using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'conditions' and policyname = 'anon write conditions') then
    create policy "anon write conditions" on conditions for insert to anon with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'conditions' and policyname = 'anon update conditions') then
    create policy "anon update conditions" on conditions for update to anon using (true);
  end if;
end $$;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'medications' and policyname = 'anon read medications') then
    create policy "anon read medications" on medications for select to anon using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'medications' and policyname = 'anon write medications') then
    create policy "anon write medications" on medications for insert to anon with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'medications' and policyname = 'anon update medications') then
    create policy "anon update medications" on medications for update to anon using (true);
  end if;
end $$;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'exams' and policyname = 'anon read exams') then
    create policy "anon read exams" on exams for select to anon using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'exams' and policyname = 'anon write exams') then
    create policy "anon write exams" on exams for insert to anon with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'exams' and policyname = 'anon update exams') then
    create policy "anon update exams" on exams for update to anon using (true);
  end if;
end $$;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'visits' and policyname = 'anon read visits') then
    create policy "anon read visits" on visits for select to anon using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'visits' and policyname = 'anon write visits') then
    create policy "anon write visits" on visits for insert to anon with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'visits' and policyname = 'anon update visits') then
    create policy "anon update visits" on visits for update to anon using (true);
  end if;
end $$;
