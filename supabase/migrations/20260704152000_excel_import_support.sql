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
