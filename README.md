# Registro Clinico

Aplicativo Streamlit com Supabase/Postgres para cadastro clinico, historico de pacientes, graficos, tendencias e apoio opcional de IA.

## Como rodar localmente

1. Crie um projeto no Supabase.
2. Execute o SQL de `database/schema.sql` no SQL Editor do Supabase.
3. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`.
4. Preencha `url` e `key` no arquivo `.streamlit/secrets.toml`.
5. Instale as dependencias:

```bash
pip install -r requirements.txt
```

6. Inicie o app:

```bash
streamlit run app.py
```

## Publicar no Streamlit Community Cloud

1. Suba estes arquivos para um repositorio no GitHub.
2. Acesse `https://share.streamlit.io` ou `https://streamlit.io/cloud`.
3. Clique em `New app`.
4. Escolha o repositorio do GitHub.
5. Em `Main file path`, informe:

```text
app.py
```

6. Em `Advanced settings`, adicione os secrets:

```toml
[supabase]
url = "https://SEU-PROJETO.supabase.co"
key = "SUA_SUPABASE_ANON_KEY"

[openai]
api_key = ""
model = "gpt-4.1-mini"
```

7. Clique em `Deploy`.

Importante: nao publique `.streamlit/secrets.toml`. O arquivo ja esta no `.gitignore`. No Streamlit Cloud, use apenas a tela de secrets.

## Supabase

Antes de usar o app publicado, crie as tabelas no Supabase.

Opcao rapida:

1. Abra o SQL Editor do Supabase.
2. Cole o conteudo de `database/schema.sql`.
3. Execute o script.

Para habilitar a importacao da planilha `RegistroClinico.xlsx` em um banco que ja existia antes desta versao, execute tambem:

```text
supabase/migrations/20260704152000_excel_import_support.sql
supabase/migrations/20260704160000_doencas_table.sql
```

Opcao com Supabase CLI:

```bash
supabase db push
```

O esquema tambem esta versionado em:

```text
supabase/migrations/20260704121500_create_clinical_registry.sql
```

## IA

A tela de IA funciona em dois niveis:

- Sem chave OpenAI: gera uma analise objetiva baseada em regras e dados cadastrados.
- Com `openai.api_key` preenchida nos secrets: gera um resumo clinico narrativo e sugestoes de pontos de atencao.

Use a saida de IA como apoio a organizacao do historico, nunca como diagnostico automatico.

## Importar Excel

A tela `Importar Excel` aceita a planilha `RegistroClinico.xlsx` e distribui os dados em tabelas normalizadas:

- `patients`: pacientes e dados cadastrais.
- `doctors`: medicos e locais de atendimento.
- `visits`: consultas, sintomas, diagnosticos, tratamento e imagens.
- `exams`: resultados laboratoriais com grupo, unidade, valor e status.
- `vaccines`: vacinas.
- `doencas`: cadastro de doencas com CID, nome da doenca e descricao.
- `medication_catalog`, `exam_groups`, `exam_catalog`, `cid_codes`, `disease_categories`, `symptoms_catalog`: tabelas de referencia.

A importacao usa chaves unicas e `upsert`, entao pode ser reexecutada para corrigir dados sem duplicar os principais registros.
