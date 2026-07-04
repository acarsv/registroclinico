# Deploy no Streamlit Community Cloud

Checklist para publicar este app no Streamlit Cloud.

## Arquivos necessarios

- `app.py`
- `requirements.txt`
- `.streamlit/config.toml`
- `database/schema.sql`
- `supabase/migrations/20260704121500_create_clinical_registry.sql`

Nao subir:

- `.streamlit/secrets.toml`
- `.env`
- `.venv`
- `__pycache__`

## Configuracao do app

No Streamlit Cloud, configure:

```text
Main file path: app.py
```

Secrets:

```toml
[supabase]
url = "https://SEU-PROJETO.supabase.co"
key = "SUA_SUPABASE_ANON_KEY"

[openai]
api_key = ""
model = "gpt-4.1-mini"
```

## Banco de dados

No Supabase, execute `database/schema.sql` no SQL Editor antes de usar o app.

Depois que o app estiver publicado, ele deve parar de mostrar o aviso "Supabase ainda nao configurado" quando os secrets estiverem corretos.
