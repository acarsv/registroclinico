from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from supabase import Client, create_client


def running_inside_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


if __name__ == "__main__" and not running_inside_streamlit():
    script_path = Path(__file__).resolve()
    print("Iniciando o aplicativo com Streamlit...")
    print("Se o navegador nao abrir automaticamente, acesse: http://localhost:8501")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(script_path),
            "--server.port",
            "8501",
        ],
        check=False,
    )
    sys.exit()


st.set_page_config(page_title="Registro Clinico", page_icon="RC", layout="wide")


TABLES = [
    "patients",
    "doctors",
    "conditions",
    "medications",
    "exams",
    "visits",
    "vaccines",
    "medication_catalog",
    "exam_groups",
    "exam_catalog",
    "cid_codes",
    "doencas",
    "disease_categories",
    "symptoms_catalog",
    "import_batches",
]


def secret(path: str, default: str = "") -> str:
    current: Any = st.secrets
    for part in path.split("."):
        try:
            current = current[part]
        except Exception:
            return default
    return str(current or default)


@st.cache_resource
def supabase_client() -> Client | None:
    url = secret("supabase.url")
    key = secret("supabase.key")
    if not url or not key or "SEU-PROJETO" in url or "SUA_SUPABASE" in key:
        return None
    return create_client(url, key)


@st.cache_data(ttl=20, show_spinner=False)
def fetch_table(table: str) -> pd.DataFrame:
    client = supabase_client()
    if client is None:
        return pd.DataFrame()
    try:
        response = client.table(table).select("*").execute()
        return pd.DataFrame(response.data or [])
    except Exception:
        return pd.DataFrame()


def insert_row(table: str, payload: dict[str, Any]) -> None:
    client = supabase_client()
    if client is None:
        st.error("Configure o Supabase em .streamlit/secrets.toml antes de salvar dados.")
        return
    clean = {
        key: (value.isoformat() if isinstance(value, (date, datetime)) else value)
        for key, value in payload.items()
        if value not in ("", None)
    }
    client.table(table).insert(clean).execute()
    st.cache_data.clear()
    st.success("Registro salvo.")


def update_row(table: str, row_id: str, payload: dict[str, Any]) -> None:
    client = supabase_client()
    if client is None:
        st.error("Configure o Supabase em .streamlit/secrets.toml antes de salvar dados.")
        return
    clean = {
        key: (value.isoformat() if isinstance(value, (date, datetime)) else value)
        for key, value in payload.items()
    }
    client.table(table).update(clean).eq("id", row_id).execute()
    st.cache_data.clear()
    st.success("Paciente atualizado.")


MIN_CLINICAL_DATE = date(1900, 1, 1)
MAX_CLINICAL_DATE = date(2100, 12, 31)


def parse_br_date(value: str, container: Any = st) -> date | None:
    if not value.strip():
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except ValueError:
        container.error("Use o formato DD/MM/AAAA. Exemplo: 15/08/1957.")
        return None
    if parsed < MIN_CLINICAL_DATE or parsed > date.today():
        container.error("Informe uma data entre 01/01/1900 e hoje.")
        return None
    return parsed


def format_br_date(value: Any) -> str:
    if value in ("", None) or pd.isna(value):
        return ""
    return pd.to_datetime(value).date().strftime("%d/%m/%Y")


def optional_date_input(label: str, key: str, container: Any = st) -> date | None:
    has_date = container.checkbox(f"Informar {label.lower()}", key=f"{key}_enabled")
    if not has_date:
        return None
    return container.date_input(
        label,
        value=date.today(),
        min_value=MIN_CLINICAL_DATE,
        max_value=MAX_CLINICAL_DATE,
        key=key,
    )


def birth_date_input(container: Any = st) -> date | None:
    has_date = container.checkbox("Informar data de nascimento", key="patient_birth_date_enabled")
    if not has_date:
        return None
    value = container.text_input("Data de nascimento", value="", placeholder="DD/MM/AAAA")
    return parse_br_date(value, container)


def optional_number_input(label: str, key: str, container: Any = st) -> float | None:
    has_value = container.checkbox(f"Informar {label.lower()}", key=f"{key}_enabled")
    if not has_value:
        return None
    return container.number_input(label, value=0.0, step=0.1, format="%.2f", key=key)


def patient_options(patients: pd.DataFrame) -> dict[str, str]:
    if patients.empty:
        return {}
    return dict(zip(patients["full_name"], patients["id"]))


def doctor_options(doctors: pd.DataFrame) -> dict[str, str]:
    if doctors.empty:
        return {}
    return dict(zip(doctors["full_name"], doctors["id"]))


def calc_age(value: Any) -> int | None:
    if pd.isna(value) or not value:
        return None
    born = pd.to_datetime(value).date()
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def load_data() -> dict[str, pd.DataFrame]:
    return {table: fetch_table(table) for table in TABLES}


def setup_warning() -> None:
    if supabase_client() is None:
        st.warning("Supabase ainda nao configurado.")
        st.markdown("Preencha o arquivo de configuracao local:")
        st.code(".streamlit/secrets.toml", language="text")
        st.markdown("Depois execute este script no SQL Editor do Supabase:")
        st.code("database/schema.sql", language="text")


def dashboard(data: dict[str, pd.DataFrame]) -> None:
    patients = data["patients"].copy()
    conditions = data["conditions"]
    medications = data["medications"]
    exams = data["exams"].copy()
    visits = data["visits"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pacientes", len(patients))
    col2.metric("Doencas ativas", int((conditions.get("status") == "Ativa").sum()) if not conditions.empty else 0)
    col3.metric("Medicamentos em uso", int((medications.get("status") == "Em uso").sum()) if not medications.empty else 0)
    col4.metric("Consultas", len(visits))

    left, right = st.columns(2)
    with left:
        st.subheader("Perfil etario")
        if not patients.empty and "birth_date" in patients:
            patients["idade"] = patients["birth_date"].apply(calc_age)
            patients["faixa"] = pd.cut(
                patients["idade"],
                bins=[0, 12, 18, 35, 50, 65, 120],
                labels=["0-12", "13-18", "19-35", "36-50", "51-65", "66+"],
            )
            chart_data = patients.dropna(subset=["faixa"]).groupby("faixa", observed=False).size().reset_index(name="total")
            st.plotly_chart(px.bar(chart_data, x="faixa", y="total"), use_container_width=True)
        else:
            st.info("Cadastre pacientes com data de nascimento para ver o grafico.")

    with right:
        st.subheader("Condicoes mais frequentes")
        if not conditions.empty:
            chart_data = conditions["name"].value_counts().head(10).reset_index()
            chart_data.columns = ["condicao", "total"]
            st.plotly_chart(px.bar(chart_data, x="total", y="condicao", orientation="h"), use_container_width=True)
        else:
            st.info("Cadastre condicoes clinicas para ver tendencias.")

    st.subheader("Linha do tempo de exames")
    if not exams.empty:
        exams["exam_date"] = pd.to_datetime(exams["exam_date"])
        timeline = exams.groupby([pd.Grouper(key="exam_date", freq="ME"), "exam_type"]).size().reset_index(name="total")
        st.plotly_chart(px.line(timeline, x="exam_date", y="total", color="exam_type", markers=True), use_container_width=True)
    else:
        st.info("Cadastre exames para acompanhar volume e recorrencia.")


def patient_form() -> None:
    with st.form("patient_form", clear_on_submit=True):
        st.subheader("Novo paciente")
        c1, c2, c3 = st.columns(3)
        full_name = c1.text_input("Nome completo")
        birth_date = birth_date_input(c2)
        sex = c3.selectbox("Sexo", ["Nao informado", "Feminino", "Masculino", "Outro"])
        c4, c5, c6 = st.columns(3)
        phone = c4.text_input("Telefone")
        email = c5.text_input("Email")
        city = c6.text_input("Cidade")
        notes = st.text_area("Observacoes")
        if st.form_submit_button("Salvar paciente", type="primary"):
            if not full_name.strip():
                st.error("Informe o nome do paciente.")
            else:
                insert_row(
                    "patients",
                    {
                        "full_name": full_name,
                        "birth_date": birth_date,
                        "sex": sex,
                        "phone": phone,
                        "email": email,
                        "city": city,
                        "notes": notes,
                    },
                )


def patient_edit_form(patients: pd.DataFrame) -> None:
    st.subheader("Editar paciente")
    if patients.empty:
        st.info("Cadastre um paciente antes de editar.")
        return

    options = patient_options(patients)
    selected_name = st.selectbox("Paciente", list(options), key="edit_patient_select")
    patient_id = options[selected_name]
    patient = patients[patients["id"] == patient_id].iloc[0]

    with st.form("patient_edit_form"):
        c1, c2, c3 = st.columns(3)
        full_name = c1.text_input("Nome completo", value=str(patient.get("full_name") or ""))
        birth_date_text = c2.text_input(
            "Data de nascimento",
            value=format_br_date(patient.get("birth_date")),
            placeholder="DD/MM/AAAA",
            help="Deixe em branco para remover a data.",
        )
        sex_options = ["Nao informado", "Feminino", "Masculino", "Outro"]
        current_sex = patient.get("sex") if patient.get("sex") in sex_options else "Nao informado"
        sex = c3.selectbox("Sexo", sex_options, index=sex_options.index(current_sex))

        c4, c5, c6 = st.columns(3)
        phone = c4.text_input("Telefone", value=str(patient.get("phone") or ""))
        email = c5.text_input("Email", value=str(patient.get("email") or ""))
        city = c6.text_input("Cidade", value=str(patient.get("city") or ""))
        notes = st.text_area("Observacoes", value=str(patient.get("notes") or ""))

        if st.form_submit_button("Atualizar paciente", type="primary"):
            if not full_name.strip():
                st.error("Informe o nome do paciente.")
                return
            birth_date = parse_br_date(birth_date_text) if birth_date_text.strip() else None
            if birth_date_text.strip() and birth_date is None:
                return
            update_row(
                "patients",
                patient_id,
                {
                    "full_name": full_name,
                    "birth_date": birth_date,
                    "sex": sex,
                    "phone": phone,
                    "email": email,
                    "city": city,
                    "notes": notes,
                },
            )


def doctor_form() -> None:
    with st.form("doctor_form", clear_on_submit=True):
        st.subheader("Novo medico")
        c1, c2, c3 = st.columns(3)
        full_name = c1.text_input("Nome")
        specialty = c2.text_input("Especialidade")
        crm = c3.text_input("CRM")
        c4, c5, c6 = st.columns(3)
        phone = c4.text_input("Telefone")
        email = c5.text_input("Email")
        location = c6.text_input("Local")
        if st.form_submit_button("Salvar medico", type="primary"):
            if not full_name.strip():
                st.error("Informe o nome do medico.")
            else:
                insert_row(
                    "doctors",
                    {
                        "full_name": full_name,
                        "specialty": specialty,
                        "crm": crm,
                        "phone": phone,
                        "email": email,
                        "location": location,
                    },
                )


def clinical_forms(data: dict[str, pd.DataFrame]) -> None:
    patients = patient_options(data["patients"])
    doctors = doctor_options(data["doctors"])
    if not patients:
        st.info("Cadastre um paciente antes de adicionar historico clinico.")
        return

    tabs = st.tabs(["Doencas", "Medicamentos", "Exames", "Consultas"])

    with tabs[0], st.form("condition_form", clear_on_submit=True):
        patient_id = patients[st.selectbox("Paciente", list(patients))]
        name = st.text_input("Doenca ou condicao")
        c1, c2 = st.columns(2)
        status = c1.selectbox("Status", ["Ativa", "Controlada", "Resolvida", "Suspeita"])
        severity = c2.selectbox("Gravidade", ["Baixa", "Moderada", "Alta", "Critica"], index=1)
        diagnosed_at = optional_date_input("Data de diagnostico", "condition_diagnosed_at")
        notes = st.text_area("Observacoes")
        if st.form_submit_button("Salvar condicao", type="primary"):
            if not name.strip():
                st.error("Informe a doenca ou condicao.")
            else:
                insert_row(
                    "conditions",
                    {
                        "patient_id": patient_id,
                        "name": name,
                        "status": status,
                        "severity": severity,
                        "diagnosed_at": diagnosed_at,
                        "notes": notes,
                    },
                )

    with tabs[1], st.form("medication_form", clear_on_submit=True):
        patient_id = patients[st.selectbox("Paciente", list(patients), key="med_patient")]
        name = st.text_input("Medicamento")
        c1, c2, c3 = st.columns(3)
        dosage = c1.text_input("Dose")
        frequency = c2.text_input("Frequencia")
        status = c3.selectbox("Status", ["Em uso", "Pausado", "Encerrado"])
        c4, c5 = st.columns(2)
        started_at = optional_date_input("Inicio", "medication_started_at", c4)
        ended_at = optional_date_input("Fim", "medication_ended_at", c5)
        notes = st.text_area("Observacoes")
        if st.form_submit_button("Salvar medicamento", type="primary"):
            if not name.strip():
                st.error("Informe o medicamento.")
            else:
                insert_row(
                    "medications",
                    {
                        "patient_id": patient_id,
                        "name": name,
                        "dosage": dosage,
                        "frequency": frequency,
                        "started_at": started_at,
                        "ended_at": ended_at,
                        "status": status,
                        "notes": notes,
                    },
                )

    with tabs[2], st.form("exam_form", clear_on_submit=True):
        patient_id = patients[st.selectbox("Paciente", list(patients), key="exam_patient")]
        exam_type = st.text_input("Tipo de exame")
        c1, c2, c3 = st.columns(3)
        exam_date = c1.date_input(
            "Data do exame",
            value=date.today(),
            min_value=MIN_CLINICAL_DATE,
            max_value=MAX_CLINICAL_DATE,
        )
        numeric_value = optional_number_input("Valor numerico", "exam_numeric_value", c2)
        unit = c3.text_input("Unidade")
        reference_range = st.text_input("Valor de referencia")
        result_text = st.text_area("Resultado descritivo")
        file_url = st.text_input("Link do arquivo")
        if st.form_submit_button("Salvar exame", type="primary"):
            if not exam_type.strip():
                st.error("Informe o tipo de exame.")
            else:
                insert_row(
                    "exams",
                    {
                        "patient_id": patient_id,
                        "exam_type": exam_type,
                        "exam_date": exam_date,
                        "result_text": result_text,
                        "numeric_value": numeric_value,
                        "unit": unit,
                        "reference_range": reference_range,
                        "file_url": file_url,
                    },
                )

    with tabs[3], st.form("visit_form", clear_on_submit=True):
        patient_id = patients[st.selectbox("Paciente", list(patients), key="visit_patient")]
        doctor_name = st.selectbox("Medico", [""] + list(doctors), key="visit_doctor")
        doctor_id = doctors.get(doctor_name)
        visit_date = st.date_input(
            "Data da consulta",
            value=date.today(),
            min_value=MIN_CLINICAL_DATE,
            max_value=MAX_CLINICAL_DATE,
        )
        reason = st.text_area("Motivo")
        diagnosis = st.text_area("Diagnostico/hipotese")
        plan = st.text_area("Conduta/plano")
        if st.form_submit_button("Salvar consulta", type="primary"):
            insert_row(
                "visits",
                {
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "visit_date": visit_date,
                    "reason": reason,
                    "diagnosis": diagnosis,
                    "plan": plan,
                },
            )


def history_view(data: dict[str, pd.DataFrame]) -> None:
    patients = patient_options(data["patients"])
    if not patients:
        st.info("Cadastre pacientes para visualizar historicos.")
        return
    name = st.selectbox("Paciente", list(patients))
    patient_id = patients[name]
    st.subheader(name)
    for table, title in [
        ("conditions", "Doencas"),
        ("medications", "Medicamentos"),
        ("exams", "Exames"),
        ("visits", "Consultas"),
    ]:
        frame = data[table]
        st.markdown(f"**{title}**")
        if frame.empty:
            st.caption("Sem registros.")
        else:
            st.dataframe(frame[frame["patient_id"] == patient_id], use_container_width=True, hide_index=True)


def local_insights(patient_name: str, frames: dict[str, pd.DataFrame]) -> str:
    active = frames["conditions"].query("status == 'Ativa'") if not frames["conditions"].empty else pd.DataFrame()
    meds = frames["medications"].query("status == 'Em uso'") if not frames["medications"].empty else pd.DataFrame()
    exams = frames["exams"]
    parts = [
        f"Paciente: {patient_name}.",
        f"Condicoes ativas: {len(active)}.",
        f"Medicamentos em uso: {len(meds)}.",
        f"Exames registrados: {len(exams)}.",
    ]
    if not exams.empty and "numeric_value" in exams:
        numeric = exams.dropna(subset=["numeric_value"])
        if not numeric.empty:
            latest = numeric.sort_values("exam_date").tail(3)[["exam_type", "exam_date", "numeric_value", "unit"]]
            parts.append("Ultimos exames numericos: " + latest.to_dict("records").__repr__())
    if len(active) >= 3 or len(meds) >= 5:
        parts.append("Ponto de atencao: revisar polifarmacia, interacoes e prioridades do plano terapeutico.")
    return "\n".join(parts)


def ai_view(data: dict[str, pd.DataFrame]) -> None:
    patients = patient_options(data["patients"])
    if not patients:
        st.info("Cadastre pacientes para usar a analise.")
        return
    patient_name = st.selectbox("Paciente para analise", list(patients))
    patient_id = patients[patient_name]
    scoped = {
        table: frame[frame["patient_id"] == patient_id].copy() if "patient_id" in frame.columns else frame
        for table, frame in data.items()
    }
    baseline = local_insights(patient_name, scoped)
    st.text_area("Resumo estruturado", baseline, height=180)

    if st.button("Gerar analise com IA", type="primary"):
        api_key = secret("openai.api_key")
        if not api_key:
            st.info("Preencha `openai.api_key` nos secrets para habilitar IA generativa. A analise por regras ja esta acima.")
            return
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            prompt = (
                "Voce apoia organizacao de registro clinico. Nao de diagnostico definitivo. "
                "Resuma historico, tendencias, lacunas de dados e perguntas para a proxima consulta.\n\n"
                f"{baseline}\n\nDados:\n"
                f"Doencas: {scoped['conditions'].to_dict('records')}\n"
                f"Medicamentos: {scoped['medications'].to_dict('records')}\n"
                f"Exames: {scoped['exams'].to_dict('records')}\n"
                f"Consultas: {scoped['visits'].to_dict('records')}"
            )
            response = client.responses.create(
                model=secret("openai.model", "gpt-4.1-mini"),
                input=prompt,
                max_output_tokens=700,
            )
            st.markdown(response.output_text)
        except Exception as exc:
            st.error(f"Nao foi possivel gerar a analise: {exc}")


def clean_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None
    return text


def clean_number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip().replace(".", "").replace(",", ".") if "," in value else value.strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_excel_date(value: Any, dayfirst: bool = True) -> date | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}", text)
    if match:
        text = match.group(0)
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=dayfirst)
    if pd.isna(parsed):
        return None
    return parsed.date()


def source_key(*parts: Any) -> str:
    return "|".join(clean_text(part) or "" for part in parts)


def clean_payload(row: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (date, datetime)):
            clean[key] = value.isoformat()
        elif value is None or (not isinstance(value, list) and pd.isna(value)):
            clean[key] = None
        else:
            clean[key] = value
    return clean


def upsert_rows(table: str, rows: list[dict[str, Any]], on_conflict: str, chunk_size: int = 500) -> int:
    client = supabase_client()
    if client is None or not rows:
        return 0
    cleaned = [clean_payload(row) for row in rows]
    for index in range(0, len(cleaned), chunk_size):
        client.table(table).upsert(cleaned[index : index + chunk_size], on_conflict=on_conflict).execute()
    return len(cleaned)


def fetch_id_map(table: str, label_col: str = "full_name") -> dict[str, str]:
    client = supabase_client()
    if client is None:
        return {}
    response = client.table(table).select(f"id,{label_col}").execute()
    return {
        str(row[label_col]): row["id"]
        for row in response.data or []
        if row.get(label_col) and row.get("id")
    }


def read_sheet(xl: pd.ExcelFile, sheet: str | list[str]) -> pd.DataFrame:
    sheet_options = [sheet] if isinstance(sheet, str) else sheet
    selected = next((option for option in sheet_options if option in xl.sheet_names), None)
    if selected is None:
        return pd.DataFrame()
    return pd.read_excel(xl, sheet_name=selected)


def import_patients(xl: pd.ExcelFile) -> int:
    rows: dict[str, dict[str, Any]] = {}

    cadastro = read_sheet(xl, "CadastroTab")
    for _, item in cadastro.iterrows():
        name = clean_text(item.get("Nome"))
        if not name:
            continue
        rows[name] = {
            "full_name": name,
            "birth_date": parse_excel_date(item.get("Data Nascimento")),
            "naturality": clean_text(item.get("Naturalidade")),
            "cpf": clean_text(item.get("CPF")),
            "address": clean_text(item.get("Endereço")),
            "address_number": clean_text(item.get("Número")),
            "address_complement": clean_text(item.get("Complemento")),
            "city": clean_text(item.get("Cidade")),
            "state": clean_text(item.get("Estado")),
        }

    pacientes = read_sheet(xl, "PacienteTab")
    for _, item in pacientes.iterrows():
        name = clean_text(item.get("Paciente"))
        if not name:
            continue
        rows[name] = {
            **rows.get(name, {}),
            "full_name": name,
            "birth_date": parse_excel_date(item.get("DataNasc")),
            "naturality": clean_text(item.get("Naturalidade")),
            "cpf": clean_text(item.get("CPF")),
            "address": clean_text(item.get("Endereço")),
            "address_complement": clean_text(item.get("Complemento")),
            "neighborhood": clean_text(item.get("Bairro")),
            "city": clean_text(item.get("Cidade")),
            "state": clean_text(item.get("Estado")),
            "phone": clean_text(item.get("Telefone")),
            "health_plan": clean_text(item.get("Plano ")),
            "registration_date": parse_excel_date(item.get("Data")),
            "preexisting_conditions": clean_text(item.get("D. Preexistentes")),
        }

    return upsert_rows("patients", list(rows.values()), "full_name")


def import_doctors(xl: pd.ExcelFile) -> int:
    doctors = read_sheet(xl, "MedicoTab")
    rows = []
    for _, item in doctors.iterrows():
        name = clean_text(item.get("Medico"))
        if not name:
            continue
        rows.append(
            {
                "full_name": name,
                "specialty": clean_text(item.get("Especialidade")),
                "phone": clean_text(item.get("Telefone")),
                "location": clean_text(item.get("Local")),
            }
        )

    consultas = read_sheet(xl, "ConsultaTab")
    existing = {row["full_name"] for row in rows}
    for name in consultas.get("Medico", pd.Series(dtype=object)).dropna().unique():
        doctor_name = clean_text(name)
        if doctor_name and doctor_name not in existing:
            rows.append({"full_name": doctor_name})
            existing.add(doctor_name)
    return upsert_rows("doctors", rows, "full_name")


def import_reference_tables(xl: pd.ExcelFile) -> dict[str, int]:
    counts: dict[str, int] = {}

    meds = read_sheet(xl, "Medicamentos")
    med_rows = []
    for _, item in meds.iterrows():
        name = clean_text(item.get("Nome"))
        if name:
            med_rows.append(
                {
                    "name": name,
                    "indicated_for": clean_text(item.get("Indicado")),
                    "generic_name": clean_text(item.get("Generico")),
                    "image_url": clean_text(item.get("Imagem")),
                }
            )
    counts["medication_catalog"] = upsert_rows("medication_catalog", med_rows, "name")

    groups = read_sheet(xl, "GrupoTab")
    group_rows = [{"name": clean_text(row.get("NomeGrupo"))} for _, row in groups.iterrows() if clean_text(row.get("NomeGrupo"))]

    exam_tab = pd.read_excel(xl, sheet_name="ExameTab", header=None) if "ExameTab" in xl.sheet_names else pd.DataFrame()
    for _, item in exam_tab.iterrows():
        group_name = clean_text(item.get(4))
        if group_name:
            group_rows.append({"name": group_name})
    group_rows = list({row["name"]: row for row in group_rows}.values())
    counts["exam_groups"] = upsert_rows("exam_groups", group_rows, "name")

    group_map = fetch_id_map("exam_groups", "name")
    exam_rows = []
    for _, item in exam_tab.iterrows():
        name = clean_text(item.get(0))
        group_name = clean_text(item.get(4))
        if not name:
            continue
        exam_rows.append(
            {
                "name": name,
                "group_id": group_map.get(group_name or ""),
                "unit": clean_text(item.get(1)),
                "reference_range": clean_text(item.get(2)),
                "source_position": int(clean_number(item.get(5)) or 0) or None,
            }
        )
    counts["exam_catalog"] = upsert_rows("exam_catalog", exam_rows, "name,group_id")

    cid = read_sheet(xl, "CIDTab")
    cid_rows = []
    for _, item in cid.iterrows():
        code = clean_text(item.get("SUBCAT"))
        description = clean_text(item.get("DESCRICAO"))
        if code and description:
            cid_rows.append(
                {
                    "code": code,
                    "description": description,
                    "abbreviated_description": clean_text(item.get("DESCRABREV")),
                }
            )
    counts["cid_codes"] = upsert_rows("cid_codes", cid_rows, "code")
    cid_descriptions = {row["code"]: row["description"] for row in cid_rows}

    diseases = read_sheet(xl, "DoençasTab")
    if diseases.empty:
        diseases = read_sheet(xl, ["Doen\u00e7asTab", "DoencasTab"])
    doenca_rows = []
    disease_rows = []
    for _, item in diseases.iterrows():
        code = clean_text(item.get("CID"))
        disease_name = clean_text(item.get("NomeDoen\u00e7a")) or clean_text(item.get("NomeDoen\u00c3\u00a7a"))
        description = (
            clean_text(item.get("Descri\u00e7\u00e3o"))
            or clean_text(item.get("Descricao"))
            or clean_text(item.get("DESCRICAO"))
            or cid_descriptions.get(code or "")
        )
        if code:
            doenca_rows.append(
                {
                    "cid": code,
                    "doenca": disease_name,
                    "descricao": description,
                }
            )
            disease_rows.append(
                {
                    "cid": code,
                    "disease_group": clean_text(item.get("GrupoDoença")),
                    "disease_name": clean_text(item.get("NomeDoença")),
                }
            )
    counts["doencas"] = upsert_rows("doencas", doenca_rows, "cid")
    counts["disease_categories"] = upsert_rows("disease_categories", disease_rows, "cid")

    symptoms = read_sheet(xl, "SintomaTab")
    symptom_rows = []
    for _, item in symptoms.iterrows():
        name = clean_text(item.get("Sintoma"))
        if name:
            symptom_rows.append(
                {
                    "name": name,
                    "description": clean_text(item.get("Descricao")),
                    "english_name": clean_text(item.get("Synptoms")),
                }
            )
    counts["symptoms_catalog"] = upsert_rows("symptoms_catalog", symptom_rows, "name")

    return counts


def import_visits(xl: pd.ExcelFile, patient_map: dict[str, str], doctor_map: dict[str, str]) -> int:
    consultas = read_sheet(xl, "ConsultaTab")
    rows = []
    for _, item in consultas.iterrows():
        patient_name = clean_text(item.get("Paciente"))
        visit_date = parse_excel_date(item.get("DataConsulta"))
        if not patient_name or not visit_date or patient_name not in patient_map:
            continue
        doctor_name = clean_text(item.get("Medico"))
        meds = [clean_text(item.get(col)) for col in ["Medicamentos", "Medicamentos1", "Medicamentos2"]]
        rows.append(
            {
                "patient_id": patient_map[patient_name],
                "doctor_id": doctor_map.get(doctor_name or ""),
                "visit_date": visit_date,
                "source_num": int(clean_number(item.get("NumConsulta")) or 0) or None,
                "source_key": source_key(patient_name, visit_date, item.get("NumConsulta"), doctor_name, item.get("Sintoma")),
                "reason": clean_text(item.get("Sintoma")),
                "symptom": clean_text(item.get("Sintoma")),
                "diagnosis": clean_text(item.get("Diagnostico")),
                "medications_text": "; ".join([med for med in meds if med]),
                "plan": clean_text(item.get("Tratamento")),
                "analysis": clean_text(item.get("Analise")),
                "image_url": clean_text(item.get("Imagem")),
                "image_url_2": clean_text(item.get("Imagem1")),
            }
        )
    return upsert_rows("visits", rows, "source_key")


def import_vaccines(xl: pd.ExcelFile, patient_map: dict[str, str]) -> int:
    vacinas = read_sheet(xl, "Vacinas")
    rows = []
    for _, item in vacinas.iterrows():
        patient_name = clean_text(item.get("Paciente"))
        vaccine_name = clean_text(item.get("Nome da Vacina"))
        vaccine_date = parse_excel_date(item.get("Data da Vacina"))
        if not patient_name or not vaccine_name:
            continue
        rows.append(
            {
                "patient_id": patient_map.get(patient_name),
                "vaccine_name": vaccine_name,
                "lot": clean_text(item.get("Lote ")),
                "expiration": clean_text(item.get("Validade")),
                "vaccine_date": vaccine_date,
                "location": clean_text(item.get("Local")),
                "city": clean_text(item.get("Cidade")),
                "state": clean_text(item.get("Estado")),
                "source_key": source_key(patient_name, vaccine_name, vaccine_date, item.get("Lote ")),
            }
        )
    return upsert_rows("vaccines", rows, "source_key")


def import_exam_results(xl: pd.ExcelFile, patient_map: dict[str, str]) -> int:
    registros = read_sheet(xl, "RegistroClinico")
    rows = []
    for index, item in registros.iterrows():
        patient_name = clean_text(item.get("Paciente"))
        exam_name = clean_text(item.get("NomeExame"))
        if not patient_name or not exam_name or patient_name not in patient_map:
            continue
        exam_date = parse_excel_date(item.get("DataConsulta"), dayfirst=True)
        numeric_value = clean_number(item.get("Valor"))
        raw_value = clean_text(item.get("Valor"))
        rows.append(
            {
                "patient_id": patient_map[patient_name],
                "exam_type": exam_name,
                "exam_group": clean_text(item.get("NomeGrupo")),
                "exam_date": exam_date or date.today(),
                "numeric_value": numeric_value,
                "unit": clean_text(item.get("Unidade")),
                "result_text": None if numeric_value is not None else raw_value,
                "status_color": clean_text(item.get("Obs")),
                "source_position": clean_number(item.get("Pos")),
                "source_key": clean_text(item.get("RegistroKey")) or source_key(patient_name, exam_date, exam_name, index),
            }
        )
    return upsert_rows("exams", rows, "source_key")


def workbook_summary(file_bytes: bytes) -> pd.DataFrame:
    xl = pd.ExcelFile(BytesIO(file_bytes))
    rows = []
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        rows.append({"aba": sheet, "linhas": len(df), "colunas": len(df.columns)})
    return pd.DataFrame(rows)


def import_schema_status() -> tuple[bool, str]:
    client = supabase_client()
    if client is None:
        return False, "Supabase nao configurado."
    try:
        client.table("patients").select("id,address,health_plan,preexisting_conditions").limit(1).execute()
        client.table("vaccines").select("id,source_key").limit(1).execute()
        client.table("exam_catalog").select("id,name").limit(1).execute()
        client.table("doencas").select("id,cid,doenca,descricao").limit(1).execute()
        client.table("import_batches").select("id,file_name").limit(1).execute()
        return True, "Schema de importacao pronto."
    except Exception as exc:
        return (
            False,
            "O banco ainda nao tem as colunas/tabelas de importacao. "
            "Execute `supabase/migrations/20260704152000_excel_import_support.sql` e "
            "`supabase/migrations/20260704160000_doencas_table.sql` "
            "no SQL Editor do Supabase e depois reinicie o app. "
            f"Detalhe tecnico: {exc}",
        )


def import_workbook(file_name: str, file_bytes: bytes) -> dict[str, int]:
    xl = pd.ExcelFile(BytesIO(file_bytes))
    counts: dict[str, int] = {}
    counts["patients"] = import_patients(xl)
    counts["doctors"] = import_doctors(xl)
    counts.update(import_reference_tables(xl))

    patient_map = fetch_id_map("patients", "full_name")
    doctor_map = fetch_id_map("doctors", "full_name")
    counts["visits"] = import_visits(xl, patient_map, doctor_map)
    counts["vaccines"] = import_vaccines(xl, patient_map)
    counts["exams"] = import_exam_results(xl, patient_map)

    client = supabase_client()
    if client is not None:
        client.table("import_batches").insert(
            {"file_name": file_name, "summary": json.loads(json.dumps(counts))}
        ).execute()
    st.cache_data.clear()
    return counts


def import_excel_view() -> None:
    st.subheader("Importar planilha Excel")
    if supabase_client() is None:
        st.warning("Configure o Supabase antes de importar.")
        return

    uploaded = st.file_uploader("Planilha RegistroClinico.xlsx", type=["xlsx"])
    if uploaded is None:
        st.info("Envie a planilha para validar abas e importar dados.")
        return

    file_bytes = uploaded.getvalue()
    st.markdown("**Previa da planilha**")
    st.dataframe(workbook_summary(file_bytes), use_container_width=True, hide_index=True)

    st.markdown("**Destino dos dados**")
    st.write(
        "Pacientes, medicos, consultas, vacinas, resultados de exames, doencas e tabelas de referencia "
        "serao importados com atualizacao por chave unica para reduzir duplicidade."
    )

    schema_ok, schema_message = import_schema_status()
    if not schema_ok:
        st.error(schema_message)
        st.markdown("Execute estas migrations no **SQL Editor** do Supabase:")
        st.code("supabase/migrations/20260704152000_excel_import_support.sql", language="text")
        with open("supabase/migrations/20260704152000_excel_import_support.sql", encoding="utf-8") as migration:
            st.code(migration.read(), language="sql")
        st.code("supabase/migrations/20260704160000_doencas_table.sql", language="text")
        with open("supabase/migrations/20260704160000_doencas_table.sql", encoding="utf-8") as migration:
            st.code(migration.read(), language="sql")
        return

    if st.button("Importar para Supabase", type="primary"):
        try:
            counts = import_workbook(uploaded.name, file_bytes)
            st.success("Importacao concluida.")
            st.json(counts)
        except Exception as exc:
            st.error(f"Falha na importacao: {exc}")


def raw_tables(data: dict[str, pd.DataFrame]) -> None:
    table = st.selectbox("Tabela", TABLES)
    st.dataframe(data[table], use_container_width=True, hide_index=True)


def diseases_view(data: dict[str, pd.DataFrame]) -> None:
    st.subheader("Doencas")
    diseases = data["doencas"].copy()
    if diseases.empty:
        st.info("Importe a planilha Excel para preencher o cadastro de doencas.")
        return

    search = st.text_input("Buscar por CID, doenca ou descricao")
    if search.strip():
        query = search.strip().casefold()
        searchable = diseases[["cid", "doenca", "descricao"]].fillna("").astype(str)
        mask = searchable.apply(lambda col: col.str.casefold().str.contains(query, regex=False)).any(axis=1)
        diseases = diseases[mask]

    st.dataframe(diseases, use_container_width=True, hide_index=True)


def main() -> None:
    st.title("Registro Clinico")
    setup_warning()
    data = load_data()

    page = st.sidebar.radio(
        "Navegacao",
        [
            "Dashboard",
            "Pacientes",
            "Medicos",
            "Doencas",
            "Historico clinico",
            "Historico por paciente",
            "Importar Excel",
            "IA",
            "Tabelas",
        ],
    )

    if page == "Dashboard":
        dashboard(data)
    elif page == "Pacientes":
        new_tab, edit_tab = st.tabs(["Novo paciente", "Editar paciente"])
        with new_tab:
            patient_form()
        with edit_tab:
            patient_edit_form(data["patients"])
        st.dataframe(data["patients"], use_container_width=True, hide_index=True)
    elif page == "Medicos":
        doctor_form()
        st.dataframe(data["doctors"], use_container_width=True, hide_index=True)
    elif page == "Doencas":
        diseases_view(data)
    elif page == "Historico clinico":
        clinical_forms(data)
    elif page == "Historico por paciente":
        history_view(data)
    elif page == "Importar Excel":
        import_excel_view()
    elif page == "IA":
        ai_view(data)
    else:
        raw_tables(data)


if __name__ == "__main__":
    main()
