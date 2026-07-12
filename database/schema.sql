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
  source_num integer,
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

-- Para prototipo com anon key. Em producao, troque por politicas vinculadas ao usuario autenticado.
create policy "anon read patients" on patients for select to anon using (true);
create policy "anon write patients" on patients for insert to anon with check (true);
create policy "anon update patients" on patients for update to anon using (true);

create policy "anon read doctors" on doctors for select to anon using (true);
create policy "anon write doctors" on doctors for insert to anon with check (true);
create policy "anon update doctors" on doctors for update to anon using (true);

create policy "anon read conditions" on conditions for select to anon using (true);
create policy "anon write conditions" on conditions for insert to anon with check (true);
create policy "anon update conditions" on conditions for update to anon using (true);

create policy "anon read medications" on medications for select to anon using (true);
create policy "anon write medications" on medications for insert to anon with check (true);
create policy "anon update medications" on medications for update to anon using (true);

create policy "anon read exams" on exams for select to anon using (true);
create policy "anon write exams" on exams for insert to anon with check (true);
create policy "anon update exams" on exams for update to anon using (true);

create policy "anon read visits" on visits for select to anon using (true);
create policy "anon write visits" on visits for insert to anon with check (true);
create policy "anon update visits" on visits for update to anon using (true);

-- Suporte a importacao da planilha RegistroClinico.xlsx.
alter table patients add column if not exists naturality text;
alter table patients add column if not exists cpf text;
alter table patients add column if not exists address text;
alter table patients add column if not exists address_number text;
alter table patients add column if not exists address_complement text;
alter table patients add column if not exists neighborhood text;
alter table patients add column if not exists state text;
alter table patients add column if not exists health_plan text;
alter table patients add column if not exists registration_date date;
alter table patients add column if not exists preexisting_conditions text;

alter table doctors add column if not exists location text;

alter table visits add column if not exists source_key text;
alter table visits add column if not exists source_num integer;
alter table visits add column if not exists symptom text;
alter table visits add column if not exists analysis text;
alter table visits add column if not exists medications_text text;
alter table visits add column if not exists image_url text;
alter table visits add column if not exists image_url_2 text;

alter table exams add column if not exists source_key text;
alter table exams add column if not exists source_num integer;
alter table exams add column if not exists exam_group text;
alter table exams add column if not exists status_color text;
alter table exams add column if not exists source_position numeric;

create unique index if not exists idx_patients_full_name_unique on patients(full_name);
create unique index if not exists idx_doctors_full_name_unique on doctors(full_name);
create unique index if not exists idx_visits_source_key_unique on visits(source_key) where source_key is not null;
create unique index if not exists idx_exams_source_key_unique on exams(source_key) where source_key is not null;

create table if not exists import_batches (
  id uuid primary key default gen_random_uuid(),
  file_name text not null,
  summary jsonb,
  created_at timestamptz not null default now()
);

create table if not exists medication_catalog (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  indicated_for text,
  generic_name text,
  image_url text,
  created_at timestamptz not null default now()
);

create table if not exists exam_groups (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists exam_catalog (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  group_id uuid references exam_groups(id) on delete set null,
  unit text,
  reference_range text,
  source_position integer,
  created_at timestamptz not null default now(),
  unique(name, group_id)
);

create table if not exists cid_codes (
  code text primary key,
  description text not null,
  abbreviated_description text,
  created_at timestamptz not null default now()
);

create table if not exists doencas (
  id uuid primary key default gen_random_uuid(),
  cid text not null unique,
  doenca text,
  descricao text,
  created_at timestamptz not null default now()
);

create table if not exists disease_categories (
  cid text primary key,
  disease_group text,
  disease_name text,
  created_at timestamptz not null default now()
);

create table if not exists symptoms_catalog (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  description text,
  english_name text,
  created_at timestamptz not null default now()
);

create table if not exists vaccines (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid references patients(id) on delete cascade,
  vaccine_name text not null,
  lot text,
  expiration text,
  vaccine_date date,
  location text,
  city text,
  state text,
  source_key text unique,
  created_at timestamptz not null default now()
);

alter table import_batches enable row level security;
alter table medication_catalog enable row level security;
alter table exam_groups enable row level security;
alter table exam_catalog enable row level security;
alter table cid_codes enable row level security;
alter table doencas enable row level security;
alter table disease_categories enable row level security;
alter table symptoms_catalog enable row level security;
alter table vaccines enable row level security;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'import_batches',
    'medication_catalog',
    'exam_groups',
    'exam_catalog',
    'cid_codes',
    'doencas',
    'disease_categories',
    'symptoms_catalog',
    'vaccines'
  ]
  loop
    if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = table_name and policyname = 'anon read ' || table_name) then
      execute format('create policy %I on %I for select to anon using (true)', 'anon read ' || table_name, table_name);
    end if;
    if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = table_name and policyname = 'anon write ' || table_name) then
      execute format('create policy %I on %I for insert to anon with check (true)', 'anon write ' || table_name, table_name);
    end if;
    if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = table_name and policyname = 'anon update ' || table_name) then
      execute format('create policy %I on %I for update to anon using (true)', 'anon update ' || table_name, table_name);
    end if;
  end loop;
end $$;
